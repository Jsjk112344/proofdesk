"""Check tracked publication files without displaying possible secret values."""

import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SECRET_PATTERNS = [
    re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(rb"gh[pousr]_" + rb"[A-Za-z0-9]{30,}"),
    re.compile(rb"github_pat_" + rb"[A-Za-z0-9_]{30,}"),
    re.compile(rb"AKIA" + rb"[A-Z0-9]{16}"),
    re.compile(
        rb"(?i)(?:api[_-]?key|access[_-]?token|secret[_-]?key)\s*=\s*[\"']?[A-Za-z0-9_/-]{24,}"
    ),
]
PRIVATE_PARTS = {".venv", "node_modules", ".local", "uploads", "artifacts"}


def main() -> int:
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).split(b"\0")
    failures = []
    paths = [Path(item.decode()) for item in tracked if item]
    if not paths:
        print("No tracked files. Stage the intended publication first.")
        return 1
    for relative in paths:
        path = ROOT / relative
        if path.is_symlink():
            failures.append(f"{relative}: symlink requires explicit publication review")
            continue
        if (
            PRIVATE_PARTS.intersection(relative.parts)
            or (path.name.startswith(".env") and path.name != ".env.example")
            or path.suffix in {".pem", ".key", ".p12", ".pfx"}
        ):
            failures.append(f"{relative}: private/local file must not be tracked")
        content = path.read_bytes()
        if any(pattern.search(content) for pattern in SECRET_PATTERNS):
            failures.append(f"{relative}: possible secret; inspect locally")
        if path.suffix == ".md":
            text = re.sub(r"```.*?```", "", content.decode(), flags=re.S)
            for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
                target = target.strip("<>")
                parsed = urlsplit(target)
                if parsed.scheme or target.startswith("#"):
                    continue
                destination = path.parent / unquote(parsed.path)
                if not destination.exists():
                    failures.append(f"{relative}: missing local link {target}")
    for failure in failures:
        print(failure)
    if failures:
        return 1
    print(f"Checked {len(paths)} tracked files: publication patterns and local links passed.")
    print("This bounded check is not a comprehensive secret or security audit.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
