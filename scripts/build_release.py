"""Allowlisted private deployment bundle. Never archive the checkout or .env wholesale."""

import io
import json
import tarfile

from backend.app.execution.artifacts import sha256
from backend.app.execution.controller import ROOT, now, revision


def main():
    output = ROOT / ".local/deployment"
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    files = [
        ROOT / name
        for name in (
            "pyproject.toml",
            "uv.lock",
            "README.md",
            "LICENSE",
            "SECURITY.md",
            "THIRD_PARTY.md",
            "infra/task-image.txt",
            "infra/proofdesk.service",
            "infra/install-private.sh",
            "infra/proofdesk-public.conf",
            "infra/Caddyfile.public",
        )
    ]
    files += sorted((ROOT / "backend/app").rglob("*.py"))
    files += sorted(p for p in (ROOT / "fixtures").rglob("*") if p.is_file())
    files += sorted(p for p in (ROOT / "frontend/dist").rglob("*") if p.is_file())
    checkpoint = ROOT / ".local/inference-checkpoint.json"
    if checkpoint.is_file():
        files.append(checkpoint)
    if not (ROOT / "frontend/dist/index.html").is_file():
        raise SystemExit("Build frontend before packaging")
    manifest = {"built_at": now(), **revision(), "files": {}}
    with tarfile.open(output / "release.tar.gz", "w:gz") as archive:
        for path in files:
            relative = path.relative_to(ROOT)
            if path.is_symlink() or path.suffix.lower() in {".png", ".key", ".pem"}:
                raise SystemExit("Rejected release path")
            content = path.read_bytes()
            manifest["files"][str(relative)] = sha256(content)
            info = tarfile.TarInfo(str(relative))
            info.mode, info.size = 0o644, len(content)
            archive.addfile(info, io.BytesIO(content))
        data = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
        info = tarfile.TarInfo("release.json")
        info.mode, info.size = 0o644, len(data)
        archive.addfile(info, io.BytesIO(data))
    archive_hash = sha256((output / "release.tar.gz").read_bytes())
    (output / "release-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (output / "release.sha256").write_text(archive_hash + "  release.tar.gz\n")
    print(
        json.dumps(
            {"bundle": str(output / "release.tar.gz"), "sha256": archive_hash, "files": len(files)}
        )
    )


if __name__ == "__main__":
    main()
