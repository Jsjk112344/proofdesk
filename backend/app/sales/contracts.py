"""Separate validated model-response contracts with bounded, sanitized diagnostics.

A diagnostic names the failure stage, the rejected field path and the expected/observed
types or lengths. It never contains response text, credentials or prompts. Sales prose is
never run through the Python-source validator and source is never parsed as sales JSON.

What these checks establish, and what they do not:

- A quotation (`excerpt`) is verified verbatim against the fetched source text.
- A claim's `text` is the model's restatement. It is accepted only when every content
  word, number and symbol in it also occurs in its own quotation (after light stemming),
  so an unrelated assertion cannot ride on a genuine quotation. This is lexical grounding,
  not entailment: word order and sense can still differ, which is why the UI shows the
  quotation as the fact and labels the restatement.
- A quantity (numeral, written number, quantifier, percentage or currency amount) in
  model prose is accepted only when the same canonical number appears in the cited
  evidence, the seller's offering or a verified demonstration summary, counting the same
  thing (a shared head word, or the same unit, or a year cue on both sides). A genuine
  number reused for a different subject is rejected. "one", ordinals and vague words such
  as "many" are not treated as quantities; a reviewer still reads every draft.
"""

import re
from decimal import Decimal, InvalidOperation

from ..execution.artifacts import Rejected, strict_json
from ..execution.controller import TASK_BYTES
from .evidence import SUPPORTED_CAPABILITY, company_name, normalize

MAX_KEYS = 20
MAX_KEY_CHARS = 40
TOPICS = frozenset({"document_workflow", "operations", "other"})
_FENCE = re.compile(rb"^\s*```")
_DEMO_WORDS = re.compile(
    r"\b(sandbox|demonstrat\w*|demo|extractor|extraction run|worked example|test run)\b",
    re.IGNORECASE,
)
_RISKY_WORDS = re.compile(
    r"\b(guarantee[sd]?|ROI|payback|savings?|save[sd]?|cut costs?|faster by|x faster|"
    r"reduce[sd]? (?:costs?|errors?|time) by)\b",
    re.IGNORECASE,
)
_TOKEN = re.compile(
    r"(?P<word>[A-Za-z0-9]*[A-Za-z][A-Za-z0-9']*)"
    r"|(?P<number>\d(?:[\d,]*\d)?(?:\.\d+)?)"
    r"|(?P<symbol>[$€£%])"
    r"|(?P<brk>[.,;:!?()\[\]\"“”—–])"
)
STOPWORDS = frozenset(
    """a an the and or but of to in on at for from with by as is are was were be been being
    am has have had having do does did done it its they them their theirs there this that
    these those which who whom whose what when where how why than then so such also can
    could may might must shall should will would about into onto over under after before
    during through per each every all any some both either more most much many few less
    least own same other another very just only even still yet already too via while whether
    if because although though since until unless upon within across along around between
    among against toward towards up down out off again further here now once we us our ours
    you your yours i me my mine he him his she her hers one ones like get got make made say
    says said see seen seem seems etc s""".split()
)
NUMBER_WORDS = {
    "zero": 0,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
    "thirty": 30,
    "forty": 40,
    "fifty": 50,
    "sixty": 60,
    "seventy": 70,
    "eighty": 80,
    "ninety": 90,
    "hundred": 100,
    "thousand": 1000,
    "million": 1000000,
    "billion": 1000000000,
}
QUANTIFIERS = {
    "dozen": "dozen",
    "dozens": "dozen",
    "hundreds": "hundreds",
    "thousands": "thousands",
    "millions": "millions",
    "several": "several",
    "twice": "twice",
    "double": "double",
    "triple": "triple",
    "half": "half",
    "quarter": "quarter",
}
CURRENCY = {"$": "usd", "€": "eur", "£": "gbp", "usd": "usd", "eur": "eur", "gbp": "gbp"}
_YEAR_STOPS = frozenset("in since from until by before after during".split())
_YEAR_WORDS = ("founded", "established", "started", "began", "begun", "opened", "launched", "year")


class ContractError(Exception):
    def __init__(self, reason, diagnostic):
        super().__init__(reason)
        self.reason = reason
        self.diagnostic = diagnostic


def observed_type(value):
    return type(value).__name__


def diagnostic(stage, field="$", *, expected=None, observed=None, **extra):
    data = {"stage": stage, "field": str(field)[:200]}
    if expected is not None:
        data["expected"] = str(expected)[:120]
    if observed is not None:
        data["observed"] = str(observed)[:120]
    for key, value in extra.items():
        if isinstance(value, (int, bool)) or value is None:
            data[key] = value
        elif isinstance(value, str):
            data[key] = value[:120]
        elif isinstance(value, list):
            data[key] = [str(v)[:MAX_KEY_CHARS] for v in value[:MAX_KEYS]]
    return data


def classify_head(data: bytes):
    head = data.lstrip()[:64]
    if not head:
        return "empty"
    if head.startswith(b"```"):
        return "markdown_fence"
    if head[:1] in (b"{", b"["):
        return "json_like"
    if re.match(rb"(#|import |from |def |class |\"\"\"|'''|[A-Za-z_][A-Za-z_0-9]* ?=)", head):
        return "python_like"
    return "prose"


def source_contract(content: str) -> bytes:
    """Executable Python source for the sandbox. Rejections are diagnostics, never code."""
    script = content.encode("utf-8")
    kind = classify_head(script)
    if not script.strip():
        raise ContractError(
            "provider_malformed_response",
            diagnostic(
                "content",
                "choices[0].message.content",
                expected="python_source",
                observed="empty",
                content_head=kind,
                content_bytes=len(script),
            ),
        )
    if b"\x00" in script:
        raise ContractError(
            "provider_malformed_response",
            diagnostic(
                "content",
                "choices[0].message.content",
                expected="python_source",
                observed="nul_byte",
                content_head=kind,
                content_bytes=len(script),
            ),
        )
    if _FENCE.match(script):
        raise ContractError(
            "provider_malformed_response",
            diagnostic(
                "content",
                "choices[0].message.content",
                expected="python_source",
                observed="markdown_fence",
                content_head=kind,
                content_bytes=len(script),
            ),
        )
    if len(script) > TASK_BYTES:
        raise ContractError(
            "generated_script_limit",
            diagnostic(
                "content",
                "choices[0].message.content",
                expected=f"<= {TASK_BYTES} bytes",
                observed=f"{len(script)} bytes",
                content_head=kind,
            ),
        )
    return script


def json_object(content: str, contract_name: str):
    raw = content.encode("utf-8")
    kind = classify_head(raw)
    try:
        value = strict_json(raw)
    except (ValueError, Rejected, RecursionError) as exc:
        raise ContractError(
            f"{contract_name}_contract_rejected",
            diagnostic(
                "content",
                "$",
                expected="json_object",
                observed="unparseable",
                content_head=kind,
                content_bytes=len(raw),
                detail=exc.args[0] if isinstance(exc, Rejected) else "json_decode_error",
            ),
        ) from None
    if not isinstance(value, dict):
        raise ContractError(
            f"{contract_name}_contract_rejected",
            diagnostic(
                "content",
                "$",
                expected="object",
                observed=observed_type(value),
                content_head=kind,
                content_bytes=len(raw),
            ),
        )
    return value


def _fail(contract_name, field, *, expected=None, observed=None, **extra):
    raise ContractError(
        f"{contract_name}_contract_rejected",
        diagnostic("contract", field, expected=expected, observed=observed, **extra),
    )


def _string(contract_name, data, field, path, *, minimum=1, maximum=400):
    value = data.get(field)
    if not isinstance(value, str):
        _fail(contract_name, path, expected="string", observed=observed_type(value))
    value = normalize(value)
    if not minimum <= len(value) <= maximum:
        _fail(
            contract_name,
            path,
            expected=f"{minimum}..{maximum} chars",
            observed=f"{len(value)} chars",
        )
    return value


def _excerpt_in_source(contract_name, sources, source_id, excerpt, path):
    source = sources.get(source_id)
    if source is None or source.get("status") != "fetched":
        _fail(
            contract_name,
            path + ".source_id",
            expected="fetched source id",
            observed="unknown_or_unfetched_source",
            known_sources=sorted(sources),
        )
    if normalize(excerpt) not in normalize(source["text"]):
        _fail(
            contract_name,
            path + ".excerpt",
            expected="verbatim text from source",
            observed="excerpt_not_in_source",
            excerpt_chars=len(excerpt),
        )


def research_contract(content: str, sources: list) -> dict:
    """Brief JSON whose every citation is checked against the fetched page text."""
    name = "research"
    data = json_object(content, name)
    required = {"company_summary", "claims", "opportunity_hypothesis", "unknowns", "demo_relevance"}
    if set(data) != required:
        _fail(
            name,
            "$",
            expected=sorted(required),
            observed="keys_mismatch",
            keys=sorted(str(k) for k in data)[:MAX_KEYS],
        )
    by_id = {s["id"]: s for s in sources}
    summary = data["company_summary"]
    if not isinstance(summary, dict):
        _fail(name, "company_summary", expected="object", observed=observed_type(summary))
    text = _string(name, summary, "text", "company_summary.text")
    source_id = _string(name, summary, "source_id", "company_summary.source_id", maximum=8)
    excerpt = _string(name, summary, "excerpt", "company_summary.excerpt", minimum=10, maximum=400)
    _excerpt_in_source(name, by_id, source_id, excerpt, "company_summary")
    company = company_name(sources)
    company_words = re.findall(r"[A-Za-z0-9']+", company)
    brief = {
        "provenance": "live_model",
        "company_summary": {
            "text": text,
            "text_kind": None,  # Set below once every quotation is verified.
            "source_id": source_id,
            "excerpt": excerpt,
            "verification": "verbatim_quotation",
        },
    }
    claims_in = data["claims"]
    if not isinstance(claims_in, list) or len(claims_in) > 8:
        _fail(name, "claims", expected="array of <= 8", observed=observed_type(claims_in))
    claims, ids = [], {}
    for index, claim in enumerate(claims_in):
        path = f"claims[{index}]"
        if not isinstance(claim, dict):
            _fail(name, path, expected="object", observed=observed_type(claim))
        model_id = _string(name, claim, "id", path + ".id", maximum=10)
        if model_id in ids:
            _fail(name, path + ".id", expected="unique id", observed="duplicate")
        claim_text = _string(name, claim, "text", path + ".text", maximum=300)
        claim_source = _string(name, claim, "source_id", path + ".source_id", maximum=8)
        claim_excerpt = _string(name, claim, "excerpt", path + ".excerpt", minimum=20, maximum=400)
        _excerpt_in_source(name, by_id, claim_source, claim_excerpt, path)
        topic = claim.get("topic", "other")
        if topic not in TOPICS:
            _fail(name, path + ".topic", expected=sorted(TOPICS), observed=observed_type(topic))
        # The quotation is the verified fact. The text is the model's restatement and may
        # only recombine that quotation's own words and numbers (plus the company name).
        text_kind = check_restatement(
            name, claim_text, claim_excerpt, path + ".text", company_words
        )
        ids[model_id] = f"c{len(claims) + 1}"
        claims.append(
            {
                "id": ids[model_id],
                "text": claim_text,
                "text_kind": text_kind,
                "source_id": claim_source,
                "excerpt": claim_excerpt,
                "verification": "verbatim_quotation",
                "topic": topic,
                "strength": None,  # The controller rule re-derives strength from the excerpt.
            }
        )
    brief["claims"] = claims
    # Interpretations are kept and labelled, never marked verified; their quantities must
    # come from the verified quotations and they cannot add savings or performance claims.
    pool = Evidence([excerpt, company] + [c["excerpt"] for c in claims])
    check_free_text(name, text, "company_summary.text", pool, demo_verified=True)
    brief["company_summary"]["text_kind"] = (
        "verbatim" if normalize(text) == normalize(excerpt) else "model_summary"
    )

    def claim_ids(value, path):
        if not isinstance(value, list) or len(value) > 8:
            _fail(name, path, expected="array of claim ids", observed=observed_type(value))
        mapped = []
        for item in value:
            if not isinstance(item, str) or item not in ids:
                _fail(
                    name,
                    path,
                    expected="known claim id",
                    observed="unknown_claim_id",
                    known_claims=sorted(ids),
                )
            mapped.append(ids[item])
        return mapped

    hypothesis = data["opportunity_hypothesis"]
    if not isinstance(hypothesis, dict):
        _fail(name, "opportunity_hypothesis", expected="object", observed=observed_type(hypothesis))
    hypothesis_text = _string(name, hypothesis, "text", "opportunity_hypothesis.text", maximum=600)
    check_free_text(
        name,
        hypothesis_text,
        "opportunity_hypothesis.text",
        pool,
        demo_verified=True,
        risky_words=False,
    )
    brief["opportunity_hypothesis"] = {
        "text": hypothesis_text,
        "claim_ids": claim_ids(hypothesis.get("claim_ids"), "opportunity_hypothesis.claim_ids"),
        "label": "hypothesis",
    }
    unknowns = data["unknowns"]
    if not isinstance(unknowns, list) or len(unknowns) > 10:
        _fail(name, "unknowns", expected="array of <= 10 strings", observed=observed_type(unknowns))
    brief["unknowns"] = []
    for index, item in enumerate(unknowns):
        if not isinstance(item, str) or not 1 <= len(normalize(item)) <= 300:
            _fail(
                name,
                f"unknowns[{index}]",
                expected="1..300 char string",
                observed=observed_type(item),
            )
        check_free_text(
            name, item, f"unknowns[{index}]", pool, demo_verified=True, risky_words=False
        )
        brief["unknowns"].append(normalize(item))
    relevance = data["demo_relevance"]
    if not isinstance(relevance, dict) or type(relevance.get("relevant")) is not bool:
        _fail(
            name,
            "demo_relevance.relevant",
            expected="boolean",
            observed=observed_type(
                relevance.get("relevant") if isinstance(relevance, dict) else relevance
            ),
        )
    reason = _string(name, relevance, "reason", "demo_relevance.reason", maximum=300)
    check_free_text(
        name, reason, "demo_relevance.reason", pool, demo_verified=True, risky_words=False
    )
    brief["demo_relevance"] = {
        "relevant": relevance["relevant"],
        "claim_ids": claim_ids(relevance.get("claim_ids"), "demo_relevance.claim_ids"),
        "reason": reason,
        "capability": SUPPORTED_CAPABILITY["id"],
    }
    return brief


def stem(word):
    """Light, deterministic stemming so plural/tense forms count as the same word."""
    word = word.lower()
    if word.endswith("'s"):
        word = word[:-2]
    word = word.replace("'", "")
    if word.endswith("ies") and len(word) > 4:
        word = word[:-3] + "i"
    elif word.endswith("sses"):
        word = word[:-2]
    elif word.endswith("es") and len(word) > 4:
        word = word[:-2]
    elif word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        word = word[:-1]
    if word.endswith("ing") and len(word) > 5:
        word = word[:-3]
    elif word.endswith("ed") and len(word) > 4:
        word = word[:-2]
    elif word.endswith("ly") and len(word) > 5:
        word = word[:-2]
    if word.endswith("e") and len(word) > 3:
        word = word[:-1]
    if word.endswith("y") and len(word) > 3:
        word = word[:-1] + "i"
    return word


YEAR_CUES = _YEAR_STOPS | frozenset(stem(w) for w in _YEAR_WORDS)


def canonical_number(text):
    try:
        value = Decimal(text.replace(",", "")).normalize()
    except InvalidOperation:
        return text
    return format(value, "f")


def lexemes(text):
    """Token stream: (kind, value, form). Number words fold into numbers; kinds are
    word (stemmed), stop (function word), number (canonical), symbol, quantifier, break."""
    items = []
    raw = []
    for match in _TOKEN.finditer(text or ""):
        kind = match.lastgroup
        raw.append((kind, match.group(0)))
    index = 0
    while index < len(raw):
        kind, value = raw[index]
        lower = value.lower()
        if kind == "word" and lower in NUMBER_WORDS and lower != "one":
            total = current = 0
            end = index
            while end < len(raw) and raw[end][0] == "word" and raw[end][1].lower() in NUMBER_WORDS:
                amount = NUMBER_WORDS[raw[end][1].lower()]
                if amount >= 1000:
                    total += max(current, 1) * amount
                    current = 0
                elif amount == 100:
                    current = max(current, 1) * amount
                else:
                    current += amount
                end += 1
            items.append(("number", str(total + current), "written"))
            index = end
            continue
        if kind == "word" and lower in QUANTIFIERS:
            items.append(("quantifier", QUANTIFIERS[lower], "quantifier"))
        elif kind == "word" and lower in CURRENCY:
            items.append(("symbol", CURRENCY[lower], None))
        elif kind == "word":
            if lower in STOPWORDS:
                items.append(("stop", lower, None))
            else:
                items.append(("word", stem(lower), None))
        elif kind == "number":
            items.append(("number", canonical_number(value), "numeral"))
        elif kind == "symbol":
            items.append(("symbol", "percent" if value == "%" else CURRENCY[value], None))
        else:
            items.append(("break", value, None))
        index += 1
    return items


def ungrounded_count(text, excerpt, extra_words=()):
    """How many content lexemes of `text` are absent from its own quotation."""
    skip = {"break", "stop"}
    allowed = {(k, v) for k, v, _ in lexemes(excerpt) if k not in skip}
    allowed |= {("word", stem(w)) for w in extra_words}
    return sum(1 for k, v, _ in lexemes(text) if k not in skip and (k, v) not in allowed)


def _anchors(items, index, direction):
    """Up to two content words next to a quantity, not crossing a clause break."""
    found = []
    step = 1 if direction > 0 else -1
    position = index + step
    while 0 <= position < len(items) and len(found) < 2:
        kind, value, _ = items[position]
        if kind == "break":
            break
        if kind in ("word", "symbol"):
            found.append(value)
        position += step
    return frozenset(found)


def quantity_mentions(text):
    """Quantities with the words that say what they count."""
    items = lexemes(text)
    mentions = []
    for index, (kind, value, form) in enumerate(items):
        if kind not in ("number", "quantifier"):
            continue
        following = _anchors(items, index, +1)
        preceding = _anchors(items, index, -1)
        quantity_kind = form
        if kind == "number":
            if "percent" in following:
                quantity_kind = "percent"
            elif preceding & {"usd", "eur", "gbp"} or following & {"usd", "eur", "gbp"}:
                quantity_kind = "currency"
        cues = {items[i][1] for i in (index - 1, index - 2) if i >= 0}
        year = (
            kind == "number"
            and form == "numeral"
            and value.isdigit()
            and 1800 <= int(value) <= 2099
            and bool(cues & YEAR_CUES)
        )
        mentions.append(
            {
                "value": value,
                "kind": quantity_kind,
                "following": following,
                "preceding": preceding,
                "year": year,
            }
        )
    return mentions


def _same_subject(mention, candidate):
    if mention["year"] and candidate["year"]:
        return True
    if mention["following"] and candidate["following"]:
        return bool(mention["following"] & candidate["following"])
    return bool(mention["preceding"] & candidate["preceding"])


class Evidence:
    """Texts a model may draw numbers and risky words from: cited quotations, the
    seller's offering and a verified demonstration summary."""

    def __init__(self, texts):
        self.texts = [t for t in texts if t]
        self.joined = normalize(" ".join(self.texts)).lower()
        self.quantities = {}
        for text in self.texts:
            for mention in quantity_mentions(text):
                self.quantities.setdefault(mention["value"], []).append(mention)

    def unsupported_quantity(self, text):
        for mention in quantity_mentions(text):
            candidates = self.quantities.get(mention["value"], [])
            if not candidates:
                return mention["kind"], "no_matching_number"
            if not any(_same_subject(mention, c) for c in candidates):
                return mention["kind"], "number_in_other_context"
        return None

    def unsupported_word(self, text):
        for match in _RISKY_WORDS.finditer(text):
            word = match.group(0).lower()
            if not re.search(r"\b" + re.escape(word) + r"\b", self.joined):
                return True
        return False


def check_free_text(contract_name, text, path, evidence, *, demo_verified, risky_words=True):
    unsupported = evidence.unsupported_quantity(text)
    if unsupported:
        kind, attribution = unsupported
        _fail(
            contract_name,
            path,
            expected="quantities only from cited evidence, offering or verified demonstration",
            observed="unsupported_quantity",
            quantity_kind=kind,
            attribution=attribution,
        )
    if risky_words and evidence.unsupported_word(text):
        _fail(
            contract_name,
            path,
            expected="no unsupported savings/performance claim",
            observed="unsupported_claim_word",
        )
    if not demo_verified and _DEMO_WORDS.search(text):
        _fail(
            contract_name,
            path,
            expected="no demonstration mention without verified result",
            observed="demo_claim_without_verified_result",
        )


def check_restatement(contract_name, text, excerpt, path, extra_words=()):
    """A claim's text may only recombine its own quotation's words and numbers."""
    missing = ungrounded_count(text, excerpt, extra_words)
    if missing:
        _fail(
            contract_name,
            path,
            expected="restatement using only the quotation's words and numbers",
            observed="interpretation_not_grounded",
            ungrounded_lexemes=missing,
        )
    check_free_text(contract_name, text, path, Evidence([excerpt]), demo_verified=True)
    return "verbatim" if normalize(text) == normalize(excerpt) else "grounded_restatement"


def outreach_contract(content: str, *, claims: list, offering: str, demo: dict | None) -> dict:
    """Body paragraphs only. Greeting and sign-off are controller-owned; no contacts."""
    name = "outreach"
    data = json_object(content, name)
    if set(data) != {"subject", "paragraphs", "mentions_demo"}:
        _fail(
            name,
            "$",
            expected=["subject", "paragraphs", "mentions_demo"],
            observed="keys_mismatch",
            keys=sorted(str(k) for k in data)[:MAX_KEYS],
        )
    verified = bool(demo and demo.get("status") == "verified")
    if type(data["mentions_demo"]) is not bool:
        _fail(
            name, "mentions_demo", expected="boolean", observed=observed_type(data["mentions_demo"])
        )
    if data["mentions_demo"] and not verified:
        _fail(
            name,
            "mentions_demo",
            expected="false without verified demonstration",
            observed="demo_claim_without_verified_result",
        )
    ids = {c["id"]: c for c in claims}
    shared = [offering or "", (demo or {}).get("result_text") if verified else None]
    everything = Evidence(shared + [c["excerpt"] for c in claims])
    subject = _string(name, data, "subject", "subject", maximum=120)
    check_free_text(name, subject, "subject", everything, demo_verified=verified)
    paragraphs_in = data["paragraphs"]
    if not isinstance(paragraphs_in, list) or not 1 <= len(paragraphs_in) <= 6:
        _fail(name, "paragraphs", expected="array of 1..6", observed=observed_type(paragraphs_in))
    paragraphs = []
    for index, paragraph in enumerate(paragraphs_in):
        path = f"paragraphs[{index}]"
        if not isinstance(paragraph, dict) or set(paragraph) != {"text", "claim_ids"}:
            _fail(name, path, expected=["text", "claim_ids"], observed=observed_type(paragraph))
        text = _string(name, paragraph, "text", path + ".text", maximum=700)
        cited = paragraph["claim_ids"]
        if not isinstance(cited, list) or any(
            not isinstance(c, str) or c not in ids for c in cited
        ):
            _fail(
                name,
                path + ".claim_ids",
                expected="known claim ids",
                observed="unknown_claim_id",
                known_claims=sorted(ids),
            )
        # Numbers in a paragraph must come from the claims that paragraph cites (so the
        # footnote shows the source), the seller's offering or the verified demonstration.
        evidence = Evidence(shared + [ids[c]["excerpt"] for c in cited])
        check_free_text(name, text, path + ".text", evidence, demo_verified=verified)
        if re.search(r"\b(Dear|Hi|Hello)\s+[A-Z][a-z]+\b", text):
            _fail(name, path + ".text", expected="no named greeting", observed="named_contact")
        paragraphs.append({"text": text, "claim_ids": list(dict.fromkeys(cited))})
    return {"subject": subject, "paragraphs": paragraphs, "mentions_demo": data["mentions_demo"]}
