"""Docker-only runner. All subprocesses on the host are Docker client commands."""

import json
import os
import selectors
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass
from typing import Protocol

from .artifacts import ARCHIVE_LIMIT

LABEL = "org.proofdesk.execution"
ENV = ["PATH=/usr/local/bin:/usr/bin:/bin", "LANG=C.UTF-8", "HOME=/nonexistent"]


class RunError(RuntimeError):
    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(reason)


@dataclass(frozen=True)
class Limits:
    wall_seconds: int = 5
    memory_bytes: int = 128 * 1024 * 1024
    nano_cpus: int = 500_000_000
    pids: int = 32
    work_bytes: int = 8 * 1024 * 1024
    tmp_bytes: int = 1024 * 1024
    shm_bytes: int = 1024 * 1024
    log_bytes: int = 16 * 1024
    archive_bytes: int = ARCHIVE_LIMIT


@dataclass(frozen=True)
class Task:
    script: bytes
    input: bytes


@dataclass
class Execution:
    exit_code: int
    logs: bytes
    archive: bytes
    evidence: dict


class Runner(Protocol):
    def execute(self, name: str, task: Task, limits: Limits) -> Execution: ...
    def cleanup(self, name: str) -> dict: ...


def command(args, *, timeout=15, cap=128 * 1024, payload=None):
    """Bound both streams together, including Docker error output; never use a shell.

    Payloads are small controller-owned JSON; nonblocking writes avoid pipe stalls.
    Killing the client alone does NOT kill a task: the controller always removes
    the container in its finalizer after any exception here.
    """
    deadline = time.monotonic() + max(0, timeout)
    output = {"stdout": bytearray(), "stderr": bytearray()}
    total = 0
    try:
        process = subprocess.Popen(
            args,
            stdin=subprocess.PIPE if payload is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        raise RunError("docker_unavailable") from exc
    try:
        with selectors.DefaultSelector() as selector:
            for key in output:
                stream = getattr(process, key)
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, key)
            pending = memoryview(payload or b"")
            if payload is not None:
                os.set_blocking(process.stdin.fileno(), False)
                selector.register(process.stdin, selectors.EVENT_WRITE, "stdin")
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise RunError("command_timeout")
                for key, _ in selector.select(min(remaining, 0.1)):
                    if key.data == "stdin":
                        try:
                            count = os.write(key.fd, pending[:4096]) if pending else 0
                            pending = pending[count:]
                        except BrokenPipeError:
                            pending = pending[:0]
                        if not pending:
                            selector.unregister(key.fileobj)
                            key.fileobj.close()
                        continue
                    chunk = os.read(key.fd, min(4096, cap - total + 1))
                    if not chunk:
                        selector.unregister(key.fileobj)
                        continue
                    total += len(chunk)
                    if total > cap:
                        raise RunError("output_limit")
                    output[key.data].extend(chunk)
            code = process.wait(timeout=max(0.001, deadline - time.monotonic()))
            return code, bytes(output["stdout"]), bytes(output["stderr"])
    except subprocess.TimeoutExpired as exc:
        raise RunError("command_timeout") from exc
    finally:
        if process.poll() is None:
            process.kill()
        process.wait()
        for stream in (process.stdin, process.stdout, process.stderr):
            if stream is not None:
                stream.close()


BOOTSTRAP = """
import json, pathlib, sys
p = json.load(sys.stdin)
pathlib.Path('/work/out').mkdir()
pathlib.Path('/work/input.txt').write_text(p['input'])
exec(compile(p['script'], '<deterministic-fixture>', 'exec'), {'__name__': '__main__'})
"""

# Runs before task input is sent. Values come from the kernel, not task claims.
PREFLIGHT = """
import json, os, pathlib
c = pathlib.Path('/sys/fs/cgroup')
print(json.dumps({
  'uid': os.getuid(), 'env': dict(os.environ),
  'cpu': (c/'cpu.max').read_text().strip(),
  'memory': (c/'memory.max').read_text().strip(),
  'swap': (c/'memory.swap.max').read_text().strip(),
  'pids': (c/'pids.max').read_text().strip(),
  'work_bytes': os.statvfs('/work').f_blocks * os.statvfs('/work').f_frsize,
  'tmp_bytes': os.statvfs('/tmp').f_blocks * os.statvfs('/tmp').f_frsize,
  'shm_bytes': os.statvfs('/dev/shm').f_blocks * os.statvfs('/dev/shm').f_frsize,
}))
"""


class DockerRunner:
    def __init__(self, image: str, namespace: str):
        self.image = image
        self.namespace = namespace
        self.docker = shutil.which("docker") or "docker"
        self.evidence = {}

    def call(self, *args, **kwargs):
        code, out, _ = command([self.docker, *args], **kwargs)
        if code:
            # Do not put arbitrary daemon diagnostics or host settings into records.
            raise RunError(f"docker_{args[0]}_failed")
        return out

    def execute(self, name: str, task: Task, limits: Limits) -> Execution:
        self.evidence = {}
        info = json.loads(self.call("info", "--format", "{{json .}}"))
        security = info.get("SecurityOptions", [])
        if (
            info.get("OSType") != "linux"
            or info.get("CgroupVersion") != "2"
            or not any("name=seccomp" in entry for entry in security)
        ):
            raise RunError("required_linux_cgroup_v2_seccomp_unavailable")
        self.evidence["runtime"] = {
            key: info.get(key)
            for key in ("ServerVersion", "OSType", "Architecture", "CgroupVersion")
        }
        if self.call("ps", "-aq", "--filter", f"label={LABEL}={self.namespace}").strip():
            raise RunError("abandoned_containers_require_cleanup")
        image = json.loads(self.call("image", "inspect", self.image))[0]
        if image["Config"].get("Volumes"):
            raise RunError("image_declares_volumes")
        self.evidence["image_id"] = image["Id"]
        self.call(
            "create",
            "--pull=never",
            "--name",
            name,
            "--label",
            f"{LABEL}={self.namespace}",
            "--network=none",
            "--ipc=private",
            "--cgroupns=private",
            "--user=65532:65532",
            "--read-only",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges:true",
            "--restart=no",
            "--log-driver=none",
            f"--memory={limits.memory_bytes}",
            f"--memory-swap={limits.memory_bytes}",
            "--cpu-period=100000",
            f"--cpu-quota={limits.nano_cpus // 10000}",
            f"--pids-limit={limits.pids}",
            f"--shm-size={limits.shm_bytes}",
            "--ulimit=nofile=64:64",
            "--ulimit=core=0:0",
            "--ulimit=fsize=1048576:1048576",
            "--tmpfs",
            f"/work:rw,noexec,nosuid,nodev,size={limits.work_bytes},mode=1777",
            "--tmpfs",
            f"/tmp:rw,noexec,nosuid,nodev,size={limits.tmp_bytes},mode=1777",
            "--workdir=/work",
            "--entrypoint=/usr/bin/env",
            self.image,
            "-i",
            *ENV,
            "python",
            "-I",
            "-B",
            "-c",
            "import time; time.sleep(60)",
        )
        inspection = json.loads(self.call("inspect", name))[0]
        host = inspection["HostConfig"]
        if (
            host["Privileged"]
            or host.get("Binds")
            or host.get("Devices")
            or inspection["Mounts"]
            or host["NetworkMode"] != "none"
            or host["PidMode"] not in ("", "private")
            or host["IpcMode"] != "private"
            or host["CgroupnsMode"] != "private"
            or not host["ReadonlyRootfs"]
            or host["CapDrop"] != ["ALL"]
            or inspection["Config"]["User"] != "65532:65532"
        ):
            raise RunError("container_policy_mismatch")
        self.evidence["policy"] = {
            key: host[key]
            for key in (
                "NetworkMode",
                "ReadonlyRootfs",
                "Privileged",
                "CapDrop",
                "SecurityOpt",
                "Memory",
                "MemorySwap",
                "CpuPeriod",
                "CpuQuota",
                "PidsLimit",
                "Tmpfs",
                "ShmSize",
                "LogConfig",
                "Ulimits",
                "Binds",
                "PidMode",
                "IpcMode",
            )
        }
        self.call("start", name)
        preflight = json.loads(
            self.call(
                "exec", name, "/usr/bin/env", "-i", *ENV, "python", "-I", "-B", "-c", PREFLIGHT
            )
        )
        expected = {
            "uid": 65532,
            "env": dict(entry.split("=", 1) for entry in ENV),
            "cpu": f"{limits.nano_cpus // 10000} 100000",
            "memory": str(limits.memory_bytes),
            "swap": "0",
            "pids": str(limits.pids),
            "work_bytes": limits.work_bytes,
            "tmp_bytes": limits.tmp_bytes,
            "shm_bytes": limits.shm_bytes,
        }
        self.evidence["preflight"] = preflight
        if preflight != expected:
            raise RunError("kernel_limit_or_environment_mismatch")
        deadline = time.monotonic() + limits.wall_seconds
        payload = json.dumps(
            {"script": task.script.decode(), "input": task.input.decode()}
        ).encode()
        try:
            code, out, err = command(
                [
                    self.docker,
                    "exec",
                    "-i",
                    name,
                    "/usr/bin/env",
                    "-i",
                    *ENV,
                    "python",
                    "-I",
                    "-B",
                    "-c",
                    BOOTSTRAP,
                ],
                timeout=deadline - time.monotonic(),
                cap=limits.log_bytes,
                payload=payload,
            )
            self.evidence["task_exit_code"] = code
            if code:
                return Execution(code, out + err, b"", self.evidence)
            # Docker cp cannot read task tmpfs on all supported local daemons.
            # Stream from inside the mount namespace instead. The task may still
            # have descendants: the archive is untrusted, not an atomic snapshot.
            # Host validation accepts only the exact bytes it checks and saves.
            archive = self.call(
                "exec",
                name,
                "/usr/bin/env",
                "-i",
                *ENV,
                "/bin/tar",
                "--format=ustar",
                "-cf",
                "-",
                "-C",
                "/work",
                "out",
                timeout=deadline - time.monotonic(),
                cap=limits.archive_bytes,
            )
            return Execution(code, out + err, archive, self.evidence)
        except RunError as exc:
            if exc.reason == "command_timeout":
                raise RunError("task_deadline_exceeded") from exc
            raise
        finally:
            self.evidence["task_elapsed_seconds"] = round(
                time.monotonic() - (deadline - limits.wall_seconds), 3
            )

    def cleanup(self, name: str) -> dict:
        try:
            # Name is reserved and persisted before create. Removal also works
            # after a client timeout where create may have reached the daemon.
            command([self.docker, "rm", "--force", "--volumes", name], timeout=10)
            remaining = self.call("ps", "-aq", "--filter", f"name=^/{name}$", timeout=10).strip()
            return {"removed": not remaining, "reason": None if not remaining else "still_present"}
        except (RunError, OSError):
            return {"removed": False, "reason": "docker_unavailable_or_cleanup_failed"}


def limits_record(limits: Limits) -> dict:
    return asdict(limits)
