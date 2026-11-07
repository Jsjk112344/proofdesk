"""Direct browser check in a bounded disposable container, no host mounts or mocked API."""

import argparse
import io
import json
import tarfile
import uuid
from pathlib import Path

from backend.app.execution.controller import ROOT
from backend.app.execution.runner import command


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://host.docker.internal:8011")
    parser.add_argument("--screen", choices=["group", "store", "handoff", "journey"], default="group")
    parser.add_argument("--output", default=".local/dealer-browser")
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    name = "salesdesk-browser-" + uuid.uuid4().hex
    try:
        code, _, _ = command(
            [
                "docker",
                "run",
                "-d",
                "--name",
                name,
                "--init",
                "--read-only",
                "--cap-drop=ALL",
                "--security-opt=no-new-privileges:true",
                "--ipc=private",
                "--shm-size=256m",
                "--memory=1g",
                "--memory-swap=1g",
                "--cpus=1",
                "--pids-limit=128",
                "--log-driver=none",
                "--tmpfs",
                "/tmp:rw,nosuid,nodev,size=256m,mode=1777",
                "--tmpfs",
                "/work:rw,noexec,nosuid,nodev,size=32m,mode=1777",
                "-e",
                "CHECK_BASE=" + args.base_url,
                "-e",
                "CHECK_SCREEN=" + args.screen,
                "proofdesk-ui-check",
                "sleep",
                "600",
            ]
        )
        assert code == 0, "browser start failed"
        raw = (ROOT / "frontend/tests/dealer.mjs").read_bytes()
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w") as archive:
            info = tarfile.TarInfo("dealer.mjs")
            info.size = len(raw)
            info.mode = 0o644
            archive.addfile(info, io.BytesIO(raw))
        code, _, _ = command(
            ["docker", "exec", "-i", name, "tar", "-xf", "-", "-C", "/work"], payload=buf.getvalue()
        )
        assert code == 0, "browser script input failed"
        code, out, err = command(
            ["docker", "exec", name, "node", "/work/dealer.mjs"], timeout=360, cap=32768
        )
        (output / "browser.log").write_bytes(out + err)
        print((out + err).decode())
        assert code == 0, "dealer browser check failed"
        code, raw, _ = command(
            ["docker", "exec", name, "tar", "-cf", "-", "-C", "/work", "."], cap=24 * 1024 * 1024
        )
        assert code == 0, "browser collection failed"
        with tarfile.open(fileobj=io.BytesIO(raw), mode="r:") as archive:
            for info in archive:
                leaf = info.name.removeprefix("./")
                if not (
                    leaf.startswith("salesdesk-")
                    and leaf.endswith(".png")
                    or leaf == "dealer-browser-check.json"
                ):
                    continue
                assert info.isfile() and not info.linkname and not info.issparse()
                assert "/" not in leaf and 0 < info.size <= 4 * 1024 * 1024
                data = archive.extractfile(info).read(4 * 1024 * 1024 + 1)
                assert len(data) == info.size
                if leaf.endswith(".png"):
                    assert data.startswith(b"\x89PNG\r\n\x1a\n")
                (output / leaf).write_bytes(data)
        print(json.dumps({"output": str(output), "container_removed_in_finalizer": name}))
    finally:
        command(["docker", "rm", "-f", name])
        code, out, _ = command(["docker", "ps", "-aq", "--filter", "name=^/" + name + "$"])
        assert code == 0 and not out.strip(), "browser cleanup unverified"


if __name__ == "__main__":
    main()
