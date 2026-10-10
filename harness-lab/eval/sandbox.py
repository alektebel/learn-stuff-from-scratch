"""Throwaway Docker containers for agents and verifiers.

DESIGN DECISION — copy the repo in, or bind-mount it?
A bind mount is faster and lets the host see edits live, but anything the agent does
to /work lands directly on the host filesystem, and a symlink planted in the repo can
point a later host-side step at a host path. Copying in with `docker cp` and copying
out at the end keeps the host's copy untouched until the runner decides to read it.
Chosen: copy in, copy out. Cost: a second or two per run on large repos.

DESIGN DECISION — verify in the agent's container, or a fresh one?
Verifying in place lets the agent's leftovers (background processes, files outside
/work, a patched site-packages) influence the verdict. A fresh container sees only
the exported /work. Chosen: fresh container (see eval/verify.py).
"""

from __future__ import annotations

import os
import shlex
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

DEFAULT_IMAGE = "harness-lab-sandbox:0"
OUTPUT_CAP = 1_000_000  # bytes kept per stream; the rest is dropped and flagged


@dataclass(frozen=True)
class ExecResult:
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool
    truncated: bool
    duration_s: float


def _docker(*args: str, input: bytes | None = None, timeout: float | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["docker", *args], input=input, capture_output=True, timeout=timeout)


def _check(proc: subprocess.CompletedProcess, what: str) -> None:
    if proc.returncode != 0:
        raise RuntimeError(f"{what} failed: {proc.stderr.decode(errors='replace').strip()}")


@dataclass
class DockerSandbox:
    """One container, network disabled, running as an unprivileged user.

    Picklable on purpose: the runner hands it to the agent's child process, which
    only needs the container id to talk to Docker.
    """

    image: str = DEFAULT_IMAGE
    memory: str = "2g"
    cpus: str = "1"
    pids: int = 512
    container_id: str | None = None

    def start(self, repo_dir: Path) -> "DockerSandbox":
        proc = _docker(
            "create", "--network", "none", "--memory", self.memory, "--cpus", self.cpus,
            "--pids-limit", str(self.pids), "--user", "agent", "--workdir", "/work",
            # CHOWN only so root can hand /work to the agent user below. The agent itself
            # runs as uid 1000 with no-new-privileges, so it never holds capabilities.
            "--security-opt", "no-new-privileges", "--cap-drop", "ALL", "--cap-add", "CHOWN",
            self.image, "sleep", "infinity",
        )
        _check(proc, "docker create")
        self.container_id = proc.stdout.decode().strip()
        # Start before copying. On rootless Docker the daemon can only mount a
        # container's rootfs while it runs: `docker cp` into a container that is
        # merely `create`d fails with "device or resource busy". The entrypoint is
        # `sleep infinity`, so nothing touches /work before the copy lands.
        _check(_docker("start", self.container_id), "docker start")
        _check(_docker("cp", f"{repo_dir}/.", f"{self.container_id}:/work"), "docker cp in")
        # docker cp writes files as root; hand them to the agent user.
        _check(_docker("exec", "--user", "root", self.container_id, "chown", "-R", "agent:agent", "/work"),
               "chown /work")
        return self

    def _require(self) -> str:
        if self.container_id is None:
            raise RuntimeError("sandbox not started")
        return self.container_id

    def exec(self, command: str, timeout: float = 120.0, user: str = "agent") -> ExecResult:
        """Run `command` through sh in /work. The in-container `timeout` kills the
        process tree; the host-side timeout is a backstop if Docker itself hangs."""
        cid = self._require()
        t0 = time.monotonic()
        wrapped = f"timeout -s KILL {int(max(1, timeout))} sh -c {shlex.quote(command)}"
        try:
            proc = _docker("exec", "--user", user, cid, "sh", "-c", wrapped, timeout=timeout + 15)
        except subprocess.TimeoutExpired:
            return ExecResult(-1, "", "host-side timeout", True, False, time.monotonic() - t0)
        out, err = proc.stdout, proc.stderr
        truncated = len(out) > OUTPUT_CAP or len(err) > OUTPUT_CAP
        return ExecResult(
            exit_code=proc.returncode,
            stdout=out[:OUTPUT_CAP].decode(errors="replace"),
            stderr=err[:OUTPUT_CAP].decode(errors="replace"),
            timed_out=proc.returncode == 137,  # SIGKILL from `timeout -s KILL`
            truncated=truncated,
            duration_s=time.monotonic() - t0,
        )

    def write_file(self, path: str, content: bytes, user: str = "agent") -> None:
        cid = self._require()
        script = f"mkdir -p \"$(dirname {shlex.quote(path)})\" && cat > {shlex.quote(path)}"
        _check(_docker("exec", "-i", "--user", user, cid, "sh", "-c", script, input=content), f"write {path}")

    def read_file(self, path: str) -> bytes:
        cid = self._require()
        proc = _docker("exec", "--user", "agent", cid, "cat", "--", path)
        _check(proc, f"read {path}")
        return proc.stdout

    def put_dir(self, src: Path, dest: str) -> None:
        """Copy a host directory into the container as root (used for hidden tests)."""
        cid = self._require()
        _check(_docker("cp", f"{src}/.", f"{cid}:{dest}"), f"docker cp {dest}")
        # `docker cp` preserves the host uid/gid. Normalise ownership to the agent
        # user (the one that runs the tests): chown needs CAP_CHOWN, which the
        # container has, while chmod as root would need CAP_FOWNER, which it drops
        # (root is not the owner), so the chmod runs as the new owner instead.
        _check(_docker("exec", "--user", "root", cid, "chown", "-R", "agent:agent", dest),
               f"chown {dest}")
        _check(_docker("exec", "--user", "agent", cid, "chmod", "-R", "a+rX", dest),
               f"chmod {dest}")

    def export(self, dest_dir: Path, src: str = "/work") -> None:
        """Copy `src` out of the container. Works on a stopped container too.
        Symlinks come out as symlinks: host-side readers must not follow them."""
        cid = self._require()
        dest_dir.mkdir(parents=True, exist_ok=True)
        _check(_docker("cp", f"{cid}:{src}/.", str(dest_dir)), f"docker cp out {src}")

    def stop(self) -> None:
        """Stop the container, killing every process the agent left running, so what
        is exported afterwards cannot change underneath the reader."""
        _check(_docker("stop", "--time", "1", self._require()), "docker stop")

    def close(self) -> None:
        if self.container_id is not None:
            _docker("rm", "-f", self.container_id)
            self.container_id = None

    def __enter__(self) -> "DockerSandbox":
        return self

    def __exit__(self, *exc) -> None:
        self.close()


def build_image(tag: str = DEFAULT_IMAGE, ca_bundle: Path | None = None) -> None:
    """Build sandbox/Dockerfile. `ca_bundle` is only for TLS-intercepting proxies."""
    root = Path(__file__).resolve().parent.parent / "sandbox"
    args = ["build", "-q", "-t", tag]
    if ca_bundle is not None:
        args += ["--network", "host", "--secret", f"id=ca,src={ca_bundle}"]
        if proxy := os.environ.get("HTTPS_PROXY"):
            args += ["--build-arg", f"HTTPS_PROXY={proxy}"]
    _check(_docker(*args, str(root)), "docker build")


def docker_available(image: str = DEFAULT_IMAGE) -> bool:
    try:
        return _docker("image", "inspect", image, timeout=20).returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False
