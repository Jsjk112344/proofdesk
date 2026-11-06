"""Clearly labelled synthetic fault injection, never live research or model output."""

import json

from .controller import ROOT
from .runner import Task

FAILURES = {
    "incorrect": "artifact_schema_or_content_mismatch",
    "oversized": "artifact_too_large_or_empty",
    "symlink": "unsafe_artifact_type",
    "fifo": "unsafe_artifact_type",
    "extra-path": "unexpected_artifact_path",
    "timeout": "task_deadline_exceeded",
    "output-flood": "output_limit",
    "archive-flood": "output_limit",
    "nonzero": "task_nonzero_exit",
    "memory": "task_nonzero_exit",
}
PROBES = [*FAILURES, "network", "host-file", "credentials", "filesystem", "processes"]


def scenario(name: str, canary=None):
    fixture = ROOT / "fixtures/extraction"
    document = (fixture / "document.txt").read_bytes()
    expected = json.loads((fixture / "expected.json").read_text())
    script = (fixture / "extract.py").read_text()
    if name == "fixture":
        return Task(script.encode(), document), expected
    prefix = "# SYNTHETIC CONTAINMENT PROBE; not model-generated.\n"
    prefix += "import errno, json, os, pathlib, socket, subprocess\n"
    suffix = "\npathlib.Path('/work/out/result.json').write_text(json.dumps({'blocked': True}))\n"
    cases = {
        "incorrect": "pathlib.Path('/work/out/result.json').write_text('{}')",
        "oversized": "pathlib.Path('/work/out/result.json').write_bytes(b'x' * 16385)",
        "symlink": "pathlib.Path('/work/out/result.json').symlink_to('/etc/passwd')",
        "fifo": "os.mkfifo('/work/out/result.json')",
        "extra-path": "pathlib.Path('/work/out/unexpected.txt').write_text('synthetic')",
        "timeout": "while True: pass",
        "output-flood": "os.write(1, b'x' * 65536)",
        "archive-flood": "pathlib.Path('/work/out/result.json').write_bytes(b'x' * 131072)",
        "nonzero": "raise SystemExit(7)",
        "memory": "data = bytearray(256 * 1024 * 1024)",
        "network": """
assert socket.if_nameindex() == [(1, 'lo')]
for address in ('192.0.2.1', '169.254.169.254'):
    try:
        connection = socket.create_connection((address, 80), timeout=0.3)
    except OSError:
        pass
    else:
        connection.close()
        raise AssertionError('unexpected network access')
""",
        "host-file": f"""
for name in ({str(canary)!r}, '/var/run/docker.sock'):
    try:
        pathlib.Path(name).read_bytes()
    except (FileNotFoundError, PermissionError):
        pass
    else:
        raise AssertionError('unexpected host file access')
try:
    pathlib.Path({str(canary)!r}).write_text('SYNTHETIC PROBE CHANGE')
except (FileNotFoundError, PermissionError, OSError):
    pass
else:
    raise AssertionError('unexpected host file write')
""",
        "credentials": """
assert dict(os.environ) == {
    'PATH': '/usr/local/bin:/usr/bin:/bin', 'LANG': 'C.UTF-8', 'HOME': '/nonexistent'
}
for path in ('/root/.aws/credentials', '/root/.docker/config.json', '/work/.env'):
    assert not os.access(path, os.R_OK)
""",
        "filesystem": """
try:
    pathlib.Path('/root-write-probe').write_text('synthetic')
except OSError:
    pass
else:
    raise AssertionError('root filesystem writable')
blocked = False
try:
    for i in range(12):
        pathlib.Path('/work/fill-' + str(i)).write_bytes(b'x' * 1048576)
except OSError as error:
    assert error.errno == errno.ENOSPC
    blocked = True
finally:
    for path in pathlib.Path('/work').glob('fill-*'):
        path.unlink()
assert blocked
""",
        "processes": """
children = []
blocked = False
try:
    for i in range(40):
        children.append(subprocess.Popen(['sleep', '10']))
except OSError as error:
    assert error.errno == errno.EAGAIN
    blocked = True
finally:
    for child in children:
        child.terminate()
    for child in children:
        child.wait()
assert blocked
""",
    }
    code = prefix + cases[name]
    if name not in FAILURES:
        code += suffix
        expected = {"blocked": True}
    return Task(code.encode(), document), expected
