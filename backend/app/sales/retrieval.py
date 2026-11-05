"""Bounded public-page retrieval with SSRF protection. Pages are untrusted evidence.

Every hop validates the URL, resolves every address, refuses non-global targets,
connects to the exact validated address (not a second DNS answer) and re-checks
each redirect. Sizes, timeouts, page counts and content types are capped. Text from
pages is data: it never becomes an instruction, a tool authorization or a send.
"""

import http.client
import ipaddress
import re
import socket
import ssl
import time
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit

from ..execution.artifacts import sha256
from ..execution.controller import ROOT, now
from ..execution.runner import RunError

MAX_URL = 2048
MAX_PAGES = 4
MAX_REDIRECTS = 3
MAX_BODY = 512 * 1024
MAX_TEXT = 24 * 1024
PAGE_TIMEOUT = 10
TOTAL_DEADLINE = 45
ALLOWED_TYPES = frozenset({"text/html", "application/xhtml+xml", "text/plain"})
BLOCKED_SUFFIXES = (".localhost", ".local", ".internal", ".arpa", ".home", ".lan", ".test")
DISCOVERY_HINTS = (
    "about",
    "company",
    "who-we-are",
    "services",
    "solutions",
    "products",
    "platform",
    "operations",
    "industries",
    "customers",
    "careers",
    "jobs",
    "team",
)
FIXTURES = ROOT / "fixtures/prospects"
_LABEL = re.compile(r"^(?!-)[a-z0-9-]{1,63}(?<!-)$")


class RetrievalBlocked(RunError):
    """Policy refusal; distinct from a page that merely failed to load."""


def _blocked(reason):
    raise RetrievalBlocked(reason)


def validate_url(url):
    """Return a normalized https/http URL or raise a stable policy reason."""
    if not isinstance(url, str) or not url or len(url) > MAX_URL:
        _blocked("url_length_rejected")
    if any(ord(c) < 0x21 or ord(c) == 0x7F for c in url):
        _blocked("url_characters_rejected")
    parts = urlsplit(url.strip())
    if parts.scheme not in ("http", "https"):
        _blocked("url_scheme_rejected")
    if "@" in parts.netloc or not parts.hostname:
        _blocked("url_host_rejected")
    host = parts.hostname.rstrip(".").lower()
    try:
        host = host.encode("idna").decode()
    except UnicodeError:
        _blocked("url_host_rejected")
    try:
        ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        pass
    else:
        _blocked("ip_literal_rejected")
    try:
        port = parts.port
    except ValueError:
        _blocked("url_port_rejected")
    default = 443 if parts.scheme == "https" else 80
    if port not in (None, default):
        _blocked("url_port_rejected")
    labels = host.split(".")
    if (
        len(labels) < 2
        or not all(_LABEL.fullmatch(label) for label in labels)
        or host == "localhost"
        or host.endswith(BLOCKED_SUFFIXES)
    ):
        _blocked("url_host_rejected")
    path = parts.path or "/"
    return urlunsplit((parts.scheme, host, path, parts.query, ""))


def public_addresses(host, port, *, resolve=socket.getaddrinfo):
    """Every resolved address must be globally routable; one bad answer blocks all."""
    try:
        answers = resolve(host, port, type=socket.SOCK_STREAM)
    except (OSError, UnicodeError) as exc:
        raise RunError("dns_resolution_failed") from exc
    addresses = []
    for family, _, _, _, sockaddr in answers:
        if family not in (socket.AF_INET, socket.AF_INET6):
            continue
        try:
            address = ipaddress.ip_address(sockaddr[0].split("%")[0])
        except ValueError:
            _blocked("address_blocked")
        mapped = getattr(address, "ipv4_mapped", None)
        candidates = [address] + ([mapped] if mapped else [])
        for candidate in candidates:
            if (
                not candidate.is_global
                or candidate.is_private
                or candidate.is_loopback
                or candidate.is_link_local
                or candidate.is_multicast
                or candidate.is_reserved
                or candidate.is_unspecified
            ):
                _blocked("address_blocked")
        if address.version == 6 and (address.sixtofour or address.teredo):
            _blocked("address_blocked")
        addresses.append((family, sockaddr[0]))
    if not addresses:
        raise RunError("dns_resolution_failed")
    return addresses


class _PinnedConnection(http.client.HTTPConnection):
    """Connects to the validated address; TLS still verifies the hostname."""

    def __init__(self, hostname, family, address, port, scheme, timeout):
        super().__init__(hostname, port, timeout=timeout)
        self._pinned = (family, address, port)
        self._scheme = scheme

    def connect(self):
        family, address, port = self._pinned
        sock = socket.socket(family, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        try:
            sock.connect((address, port))
        except OSError:
            sock.close()
            raise
        if self._scheme == "https":
            context = ssl.create_default_context()
            context.minimum_version = ssl.TLSVersion.TLSv1_2
            sock = context.wrap_socket(sock, server_hostname=self.host)
        self.sock = sock


def open_connection(hostname, family, address, port, scheme, timeout):
    return _PinnedConnection(hostname, family, address, port, scheme, timeout)


@dataclass
class Page:
    requested_url: str
    final_url: str | None = None
    status: str = "pending"
    failure_reason: str | None = None
    fetched_at: str | None = None
    http_status: int | None = None
    content_type: str | None = None
    bytes: int | None = None
    sha256: str | None = None
    title: str | None = None
    description: str | None = None
    text: str = ""
    blocks: list = field(default_factory=list)
    links: list = field(default_factory=list)
    redirects: list = field(default_factory=list)
    kind: str = "public_http"

    def record(self):
        data = {k: v for k, v in self.__dict__.items() if k not in {"blocks", "links"}}
        return data


class _Text(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "template", "head"}
    BLOCKS = {"p", "li", "h1", "h2", "h3", "h4", "td", "th", "blockquote", "dd", "dt", "figcaption"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.title = None
        self.description = None
        self.blocks = []
        self.links = []
        self._skip = 0
        self._title = False
        self._current = []
        self._tag = None

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag in self.SKIP and tag != "head":
            self._skip += 1
        if tag == "title":
            self._title = True
        if tag == "meta":
            name = (attributes.get("name") or attributes.get("property") or "").lower()
            if name in ("description", "og:description") and attributes.get("content"):
                self.description = self.description or " ".join(attributes["content"].split())
        if tag == "a" and attributes.get("href"):
            self.links.append(attributes["href"])
        if tag in self.BLOCKS or tag in ("br", "div", "section", "article", "tr"):
            self._flush()
            self._tag = tag if tag in self.BLOCKS else None

    def handle_endtag(self, tag):
        if tag in self.SKIP and tag != "head" and self._skip:
            self._skip -= 1
        if tag == "title":
            self._title = False
        if tag in self.BLOCKS or tag in ("div", "section", "article", "tr"):
            self._flush()

    def handle_data(self, data):
        if self._title:
            self.title = " ".join(((self.title or "") + " " + data).split()) or None
            return
        if not self._skip:
            self._current.append(data)

    def _flush(self):
        text = " ".join("".join(self._current).split())
        if len(text) >= 2:
            self.blocks.append((self._tag or "text", text))
        self._current = []

    def close(self):
        super().close()
        self._flush()


def extract_text(raw, content_type):
    charset = "utf-8"
    match = re.search(r"charset=([A-Za-z0-9._-]+)", content_type or "")
    if match:
        charset = match.group(1)
    try:
        text = raw.decode(charset, errors="replace")
    except LookupError:
        text = raw.decode("utf-8", errors="replace")
    if content_type.startswith("text/plain"):
        blocks = [("text", " ".join(line.split())) for line in text.splitlines() if line.strip()]
        return None, None, blocks, []
    parser = _Text()
    try:
        parser.feed(text)
        parser.close()
    except Exception:  # Malformed HTML stays data; keep whatever was parsed.
        pass
    return parser.title, parser.description, parser.blocks, parser.links


def _bounded_text(blocks):
    joined = []
    size = 0
    for _, text in blocks:
        if size + len(text) + 1 > MAX_TEXT:
            break
        joined.append(text)
        size += len(text) + 1
    return "\n".join(joined)


def fetch_page(url, *, deadline, resolve=socket.getaddrinfo, connector=open_connection):
    """One page with bounded redirects. Returns a Page; policy refusals are 'blocked'."""
    page = Page(requested_url=url)
    current = url
    try:
        for hop in range(MAX_REDIRECTS + 1):
            current = validate_url(current)
            parts = urlsplit(current)
            port = 443 if parts.scheme == "https" else 80
            family, address = public_addresses(parts.hostname, port, resolve=resolve)[0]
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise RunError("retrieval_deadline_exceeded")
            connection = connector(
                parts.hostname, family, address, port, parts.scheme, min(PAGE_TIMEOUT, remaining)
            )
            try:
                target = parts.path + ("?" + parts.query if parts.query else "")
                connection.request(
                    "GET",
                    target,
                    headers={
                        "Host": parts.hostname,
                        "User-Agent": "SalesDesk-research/0.3 (+bounded public page fetch)",
                        "Accept": "text/html, text/plain;q=0.8",
                        "Accept-Encoding": "identity",
                        "Connection": "close",
                    },
                )
                response = connection.getresponse()
                page.http_status = response.status
                if 300 <= response.status < 400:
                    location = response.getheader("Location")
                    if not location or hop == MAX_REDIRECTS:
                        _blocked("redirect_limit_exceeded")
                    page.redirects.append(current)
                    current = urljoin(current, location)
                    continue
                if response.status != 200:
                    raise RunError(f"http_status_{response.status}")
                if response.getheader("Content-Encoding", "identity").lower() != "identity":
                    raise RunError("content_encoding_rejected")
                content_type = (response.getheader("Content-Type") or "").strip()
                media = content_type.split(";")[0].strip().lower()
                if media not in ALLOWED_TYPES:
                    raise RunError("content_type_rejected")
                declared = response.getheader("Content-Length")
                if declared is not None and (not declared.isdecimal() or int(declared) > MAX_BODY):
                    raise RunError("response_too_large")
                body = response.read(MAX_BODY + 1)
                if len(body) > MAX_BODY:
                    raise RunError("response_too_large")
            finally:
                connection.close()
            page.final_url = current
            page.content_type = media
            page.bytes = len(body)
            page.sha256 = sha256(body)
            page.title, page.description, page.blocks, page.links = extract_text(body, content_type)
            page.text = _bounded_text(page.blocks)
            page.status = "fetched"
            page.fetched_at = now()
            return page
        _blocked("redirect_limit_exceeded")
    except RetrievalBlocked as exc:
        page.status, page.failure_reason = "blocked", exc.reason
    except RunError as exc:
        page.status, page.failure_reason = "failed", exc.reason
    except (socket.timeout, TimeoutError):
        page.status, page.failure_reason = "failed", "fetch_timeout"
    except (OSError, http.client.HTTPException, ssl.SSLError):
        page.status, page.failure_reason = "failed", "transport_error"
    page.fetched_at = now()
    return page


def same_site(origin_host, host):
    strip = lambda h: h[4:] if h.startswith("www.") else h  # noqa: E731
    origin, candidate = strip(origin_host), strip(host)
    return candidate == origin or candidate.endswith("." + origin)


def discover(origin, links):
    """Pick a few same-site informational pages; never follow off-site links."""
    base = urlsplit(origin)
    chosen = []
    seen = {urlsplit(origin).path.rstrip("/") or "/"}
    scored = []
    for href in links:
        try:
            candidate = validate_url(urljoin(origin, href.strip()))
        except RunError:
            continue
        parts = urlsplit(candidate)
        if not same_site(base.hostname, parts.hostname) or parts.query:
            continue
        path = parts.path.rstrip("/") or "/"
        if path in seen or re.search(r"\.(pdf|png|jpe?g|gif|svg|zip|xml|json|css|js)$", path):
            continue
        lowered = path.lower()
        hint = next((i for i, h in enumerate(DISCOVERY_HINTS) if h in lowered), None)
        if hint is None:
            continue
        seen.add(path)
        scored.append((hint, len(path), urlunsplit((base.scheme, base.hostname, path, "", ""))))
    for _, _, candidate in sorted(scored):
        chosen.append(candidate)
        if len(chosen) == MAX_PAGES - 1:
            break
    return chosen


def fetch_site(url, *, resolve=socket.getaddrinfo, connector=open_connection):
    """Homepage plus up to MAX_PAGES-1 discovered same-site pages, under one deadline."""
    deadline = time.monotonic() + TOTAL_DEADLINE
    first = fetch_page(url, deadline=deadline, resolve=resolve, connector=connector)
    pages = [first]
    if first.status != "fetched":
        return pages
    for candidate in discover(first.final_url, first.links):
        if time.monotonic() >= deadline:
            pages.append(
                Page(
                    requested_url=candidate,
                    status="failed",
                    failure_reason="retrieval_deadline_exceeded",
                    fetched_at=now(),
                )
            )
            continue
        pages.append(fetch_page(candidate, deadline=deadline, resolve=resolve, connector=connector))
    return pages


def fixture_site(name):
    """Synthetic prospect pages from the repository; no network. Labelled synthetic."""
    if not re.fullmatch(r"[a-z0-9-]{1,40}", name or ""):
        raise RunError("unknown_sample_scenario")
    directory = FIXTURES / name
    if not directory.is_dir():
        raise RunError("unknown_sample_scenario")
    pages = []
    ordered = sorted(directory.glob("*.html"), key=lambda p: (p.name != "index.html", p.name))
    for path in ordered[:MAX_PAGES]:
        if path.is_symlink() or path.stat().st_size > MAX_BODY:
            raise RunError("fixture_page_rejected")
        raw = path.read_bytes()
        page = Page(requested_url=f"fixture://{name}/{path.name}", kind="synthetic_fixture")
        page.final_url = page.requested_url
        page.http_status = 200
        page.content_type = "text/html"
        page.bytes = len(raw)
        page.sha256 = sha256(raw)
        page.title, page.description, page.blocks, page.links = extract_text(raw, "text/html")
        page.text = _bounded_text(page.blocks)
        page.status = "fetched"
        page.fetched_at = now()
        pages.append(page)
    if not pages:
        raise RunError("unknown_sample_scenario")
    return pages


def fixture_names():
    return sorted(p.name for p in FIXTURES.iterdir() if p.is_dir()) if FIXTURES.is_dir() else []


def page_text_path(directory: Path, index: int):
    return directory / "sources" / f"{index}.txt"
