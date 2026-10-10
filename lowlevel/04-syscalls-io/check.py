"""
Progress checker for the syscall-I/O templates.

    python3 check.py           # run every check, stop at the first unimplemented step
    python3 check.py 2         # run only step 2
    python3 check.py 2 4       # run steps 2 through 4
    python3 check.py --all     # run everything, do not stop at the first gap

A check that raises NotImplementedError is reported as TODO (not a failure): that is
simply the next thing to write. Nothing here imports solutions/. It tests YOUR code.

The hard cases (a short read, a short write, an EOF) are forced deterministically by
wrapping ``os.read``/``os.write``: a real regular file almost always fills a read, so
random data would never exercise them.
"""

import os
import pathlib
import random
import shutil
import sys
import tempfile
import traceback

sys.dont_write_bytecode = True
shutil.rmtree(pathlib.Path(__file__).parent / "__pycache__", ignore_errors=True)

from typing import Callable, List, Tuple  # noqa: E402

PASS, FAIL, TODO, ERROR = "PASS", "FAIL", "TODO", "ERROR"
GREEN, RED, YELLOW, GREY, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[90m", "\033[1m", "\033[0m")


def tmpdir() -> str:
    return tempfile.mkdtemp(prefix="sysio-check-")


def writedata(path: str, data: bytes) -> str:
    with open(path, "wb") as fh:
        fh.write(data)
    return path


class CappedRead:
    """A ``read(2)`` that never returns more than ``limit`` bytes: a short read.

    It reads from the real fd underneath, so it is not a mock of the data, only of the
    size. ``max_calls`` stops a loop that never terminates from hanging the checker.
    """

    def __init__(self, real, limit: int = 2, max_calls: int = 500_000):
        self.real = real
        self.limit = limit
        self.max_calls = max_calls
        self.calls = 0

    def __call__(self, fd: int, n: int) -> bytes:
        self.calls += 1
        if self.calls > self.max_calls:
            raise RuntimeError(
                "read() was called unboundedly many times: a loop is spinning on it")
        return self.real(fd, min(n, self.limit))


class EofOnceRead(CappedRead):
    """Like :class:`CappedRead`, but calling it again after it returned ``b""`` is an error.

    ``read`` of 0 bytes is EOF; retrying it is the bug this encodes. Raising (instead of
    looping) keeps the limit case from hanging.
    """

    def __init__(self, real, limit: int = 2, max_calls: int = 500_000):
        super().__init__(real, limit, max_calls)
        self.eof_returned = False

    def __call__(self, fd: int, n: int) -> bytes:
        if self.eof_returned:
            raise AssertionError(
                "read() was called again after it returned 0 bytes. A read of 0 is EOF: "
                "stop and return b'', do not treat it as an error to retry.")
        data = super().__call__(fd, n)
        if data == b"":
            self.eof_returned = True
        return data


class CappedWrite:
    """A ``write(2)`` that accepts at most ``limit`` bytes per call: a short write."""

    def __init__(self, real, limit: int = 1, max_calls: int = 2_000_000):
        self.real = real
        self.limit = limit
        self.max_calls = max_calls
        self.calls = 0

    def __call__(self, fd: int, data) -> int:
        self.calls += 1
        if self.calls > self.max_calls:
            raise RuntimeError("write() was called unboundedly many times")
        return self.real(fd, bytes(data)[: self.limit])


# ---------------------------------------------------------------------------
# Step 1: copyfile.py - unbuffered copy
# ---------------------------------------------------------------------------

def check_copy_identical() -> None:
    from copyfile import copy_fd, copy_path, read_all

    rng = random.Random(2024)
    work = tmpdir()
    src = os.path.join(work, "src.bin")
    dst = os.path.join(work, "dst.bin")

    for size in (0, 1, 17, 4096, 200_000):
        data = rng.randbytes(size)
        writedata(src, data)
        for bufsize in (1, 3, 4096, 1 << 16):
            writedata(dst, b"stale bytes that a shorter source must truncate")
            copied = copy_path(src, dst, bufsize=bufsize)
            got = open(dst, "rb").read()
            assert got == data and copied == size, (
                f"copy_path is not byte-identical for size {size}, bufsize {bufsize}: "
                f"copied {copied} bytes, destination has {len(got)}, source has {len(data)}. "
                "One os.read returns at most bufsize bytes: loop reads until EOF, and open "
                "the destination with O_TRUNC.")

    # The fd-to-fd form, with a chunk smaller than the data so the loop must run.
    data = rng.randbytes(5000)
    writedata(src, data)
    src_fd = os.open(src, os.O_RDONLY)
    dst_fd = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    try:
        copied = copy_fd(src_fd, dst_fd, bufsize=7)
    finally:
        os.close(src_fd)
        os.close(dst_fd)
    assert copied == len(data) and open(dst, "rb").read() == data, (
        f"copy_fd copied {copied} of {len(data)} bytes with bufsize=7: "
        "it must loop os.read/os.write until EOF")

    src_fd = os.open(src, os.O_RDONLY)
    try:
        assert read_all(src_fd, bufsize=13) == data, "read_all(b, bufsize=13) did not return the whole file"
    finally:
        os.close(src_fd)


# ---------------------------------------------------------------------------
# Step 2: buffered.py - short reads
# ---------------------------------------------------------------------------

def check_short_reads() -> None:
    from buffered import BufferedReader
    from copyfile import read_all, read_exact

    rng = random.Random(7)
    data = rng.randbytes(1000)
    lines = b"alpha\nbeta\ngamma-no-newline"
    work = tmpdir()
    path = writedata(os.path.join(work, "data.bin"), data)
    lines_path = writedata(os.path.join(work, "lines.txt"), lines)

    real = os.read
    os.read = CappedRead(real, limit=2)          # every read returns at most 2 bytes
    try:
        # Everything to EOF: one short read must not be mistaken for the end.
        fd = os.open(path, os.O_RDONLY)
        try:
            reader = BufferedReader(fd, capacity=16)
            got = reader.read(-1)
        finally:
            os.close(fd)
        assert got == data, (
            f"BufferedReader.read(-1) returned {len(got)} of {len(data)} bytes: a short "
            "os.read is not EOF, keep filling until read returns b''")

        # read(n) must return exactly n bytes until EOF.
        fd = os.open(path, os.O_RDONLY)
        try:
            reader = BufferedReader(fd, capacity=16)
            remaining = len(data)
            collected = []
            while remaining:
                chunk = reader.read(100)
                assert len(chunk) == min(100, remaining), (
                    f"read(100) returned {len(chunk)} bytes with {remaining} left: for a "
                    "non-negative n it must loop short reads until n bytes or EOF")
                collected.append(chunk)
                remaining -= len(chunk)
            assert reader.read(10) == b"", "a read past EOF must return b''"
        finally:
            os.close(fd)
        assert b"".join(collected) == data

        # readline must keep filling through short reads too.
        fd = os.open(lines_path, os.O_RDONLY)
        try:
            reader = BufferedReader(fd, capacity=4)
            assert reader.readline() == b"alpha\n", "readline() did not survive a short read"
            assert reader.readline() == b"beta\n"
            assert reader.readline() == b"gamma-no-newline", "readline() lost the tail at EOF"
        finally:
            os.close(fd)

        fd = os.open(path, os.O_RDONLY)
        try:
            assert read_exact(fd, 997) == data[:997], "read_exact did not loop short reads"
            assert read_exact(fd, 100) == data[997:], "read_exact returned more than is left"
        finally:
            os.close(fd)

        fd = os.open(path, os.O_RDONLY)
        try:
            assert read_all(fd, bufsize=5) == data, "read_all did not loop short reads"
        finally:
            os.close(fd)
    finally:
        os.read = real


# ---------------------------------------------------------------------------
# Step 3: fdtable.py - close is reported
# ---------------------------------------------------------------------------

def check_double_close() -> None:
    from fdtable import BadFileDescriptor, FDTable

    work = tmpdir()
    a = writedata(os.path.join(work, "a.txt"), b"a-contents")
    b = writedata(os.path.join(work, "b.txt"), b"b-contents")
    c = writedata(os.path.join(work, "c.txt"), b"c-contents")

    table = FDTable()
    fa = table.open(a, os.O_RDONLY)
    fb = table.open(b, os.O_RDONLY)
    assert fa != fb and {fa, fb} <= set(table.open_fds()), "open must return distinct descriptors"
    assert table.read(fa, 64) == b"a-contents", "read through the table returned the wrong bytes"

    table.close(fa)
    assert fa not in table, "a closed descriptor must no longer be in the table"

    try:
        table.close(fa)
    except BadFileDescriptor:
        pass
    else:
        raise AssertionError(
            "closing an fd twice was not reported. A double close must raise "
            "BadFileDescriptor (EBADF), never be ignored: the number may have been reused, "
            "so ignoring it would close someone else's file.")

    try:
        table.read(fa, 1)
    except BadFileDescriptor:
        pass
    else:
        raise AssertionError("reading a closed fd must raise BadFileDescriptor, not return bytes")

    # POSIX open(2): the lowest free descriptor is reused.
    fc = table.open(c, os.O_RDONLY)
    assert fc == fa, (
        f"after closing {fa}, open returned {fc}: open(2) must reuse the LOWEST free "
        f"descriptor ({fa}), not keep counting up")

    # Writing through the table, then closing everything, then one more bad close.
    out = os.path.join(work, "out.txt")
    fw = table.open(out, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    assert table.write(fw, b"written through the table") == len(b"written through the table")
    for fd in list(table.open_fds()):
        table.close(fd)
    assert not table.open_fds(), "every descriptor should be closed"
    assert open(out, "rb").read() == b"written through the table"
    try:
        table.close(fw)
    except BadFileDescriptor:
        pass
    else:
        raise AssertionError("closing an fd after the table is emptied must still be reported")


# ---------------------------------------------------------------------------
# Step 4 (limit): copyfile.py - partial write on a pipe
# ---------------------------------------------------------------------------

def check_partial_write() -> None:
    from buffered import BufferedWriter
    from copyfile import copy_fd, write_all

    data = bytes(range(256)) * 8          # 2048 bytes
    work = tmpdir()
    dst = os.path.join(work, "out.bin")

    # A real pipe, to show write_all works on a non-seekable fd at all.
    r, w = os.pipe()
    try:
        write_all(w, b"through a real pipe")
        assert os.read(r, 64) == b"through a real pipe", "write_all corrupted a real pipe write"
    finally:
        os.close(r)
        os.close(w)

    # Now force a short write: each os.write accepts one byte.
    real = os.write
    os.write = CappedWrite(real, limit=1)
    try:
        fd = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
        try:
            written = write_all(fd, data)
        finally:
            os.close(fd)
    finally:
        os.write = real
    assert written == len(data), f"write_all reported {written} of {len(data)} bytes"
    assert open(dst, "rb").read() == data, (
        "write_all dropped bytes when write(2) returned short. write(2) may write fewer "
        "bytes than requested (a pipe with less room); the remainder must be retried, not "
        "counted as done.")

    # copy_fd's write path must survive the same.
    src = writedata(os.path.join(work, "src.bin"), data)
    os.write = CappedWrite(real, limit=3)
    try:
        src_fd = os.open(src, os.O_RDONLY)
        dst_fd = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
        try:
            copied = copy_fd(src_fd, dst_fd, bufsize=64)
        finally:
            os.close(src_fd)
            os.close(dst_fd)
    finally:
        os.write = real
    assert copied == len(data) and open(dst, "rb").read() == data, (
        "copy_fd truncated the output under a short write: each chunk must be fully written")

    # BufferedWriter.flush must deliver every buffered byte under short writes.
    os.write = CappedWrite(real, limit=1)
    try:
        fd = os.open(dst, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
        try:
            writer = BufferedWriter(fd, capacity=1 << 16)
            writer.write(data)
            writer.flush()
        finally:
            os.close(fd)
    finally:
        os.write = real
    assert open(dst, "rb").read() == data, (
        "BufferedWriter.flush lost bytes under a short write: flush must go through the "
        "retrying write_all, not a single os.write")


# ---------------------------------------------------------------------------
# Step 5 (limit): read of 0 bytes means EOF
# ---------------------------------------------------------------------------

def check_read_zero_is_eof() -> None:
    from buffered import BufferedReader
    from copyfile import read_all

    data = b"the end is not an error" * 5
    work = tmpdir()
    path = writedata(os.path.join(work, "data.bin"), data)

    real = os.read
    os.read = EofOnceRead(real, limit=2)   # b'' is EOF; asking again is the bug
    try:
        fd = os.open(path, os.O_RDONLY)
        try:
            reader = BufferedReader(fd, capacity=8)
            got = reader.read(-1)
        finally:
            os.close(fd)
        assert got == data, (
            f"read(-1) returned {len(got)} of {len(data)} bytes and stopped early: keep "
            "reading until read(2) returns 0 bytes")
        assert reader.read(10) == b"", (
            "after EOF a read must return b'' without retrying: 0 bytes is EOF, not an "
            "error to retry")

        os.read = EofOnceRead(real, limit=4)   # a fresh guard for the next reader
        fd = os.open(path, os.O_RDONLY)
        try:
            assert read_all(fd, bufsize=4) == data, "read_all must stop on the first 0-byte read"
        finally:
            os.close(fd)
    finally:
        os.read = real

    # With a real file, a read past the end is 0 bytes and is not an error.
    fd = os.open(path, os.O_RDONLY)
    try:
        assert os.read(fd, 1 << 20) == data
        assert os.read(fd, 10) == b"", "read at EOF should return b''"
        assert os.read(fd, 10) == b"", "read at EOF should keep returning b''"
    finally:
        os.close(fd)


CHECKS: List[Tuple[str, str, Callable[[], None]]] = [
    ("copyfile.py", "unbuffered copy is byte-identical on random data", check_copy_identical),
    ("buffered.py", "a short read is looped, not truncated", check_short_reads),
    ("fdtable.py", "closing an fd twice is reported", check_double_close),
    ("copyfile.py", "a partial write is retried for the remainder", check_partial_write),
    ("buffered.py", "a read of 0 bytes means EOF, not an error", check_read_zero_is_eof),
]


def run_one(check: Callable[[], None]) -> Tuple[str, str]:
    try:
        check()
        return PASS, ""
    except NotImplementedError as exc:
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if frame.filename.endswith(".py") and "check.py" not in frame.filename:
                where = f"{frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return TODO, (str(exc) or where)
    except AssertionError as exc:
        return FAIL, str(exc) or "assertion failed"
    except Exception as exc:  # noqa: BLE001
        where = ""
        for frame in reversed(traceback.extract_tb(sys.exc_info()[2])):
            if "check.py" not in frame.filename:
                where = f"\n      at {frame.filename.split('/')[-1]}:{frame.lineno} in {frame.name}()"
                break
        return ERROR, f"{type(exc).__name__}: {exc}{where}"


def main(argv: List[str]) -> int:
    keep_going = "--all" in argv
    wanted = [int(a) for a in argv if a.isdigit()]
    if len(wanted) > 1:
        wanted = list(range(min(wanted), max(wanted) + 1))
    print(f"\n{BOLD}Syscalls & I/O From Scratch — progress check{RESET}")
    print(f"{GREY}implement the templates, re-run this after each step{RESET}\n")
    passed = failed = todo = 0
    first_gap = None
    for index, (filename, title, check) in enumerate(CHECKS, start=1):
        if wanted and index not in wanted:
            continue
        status, detail = run_one(check)
        if status == PASS:
            passed += 1
            print(f"  {GREEN}✓{RESET} {index:>2}. {filename:<14} {title}")
        elif status == TODO:
            todo += 1
            first_gap = first_gap or index
            print(f"  {GREY}·{RESET} {index:>2}. {filename:<14} {title}")
            print(f"      {GREY}not implemented yet{(' — ' + detail) if detail else ''}{RESET}")
            if not keep_going and not wanted:
                remaining = len(CHECKS) - index
                if remaining:
                    print(f"\n  {GREY}({remaining} later checks not run; use --all to run them anyway){RESET}")
                break
        else:
            failed += 1
            first_gap = first_gap or index
            colour = RED if status == FAIL else YELLOW
            print(f"  {colour}✗{RESET} {index:>2}. {filename:<14} {title}")
            for line in detail.splitlines():
                print(f"      {colour}{line}{RESET}")
    total = len(wanted) if wanted else len(CHECKS)
    print(f"\n  {passed}/{total} passing", end="")
    if failed:
        print(f", {RED}{failed} failing{RESET}", end="")
    if todo:
        print(f", {GREY}{todo} to write{RESET}", end="")
    print()
    if passed == len(CHECKS):
        print(f"\n  {GREEN}{BOLD}All checks pass — you have built the I/O layer.{RESET}")
        print(f"  {GREY}Run each file's demo, then compare with solutions/.{RESET}\n")
    elif first_gap:
        filename, title, _ = CHECKS[first_gap - 1]
        print(f"\n  {BOLD}Next:{RESET} step {first_gap} — {title} ({filename})")
        print(f"  {GREY}The docstrings in that file walk through it. Stuck? solutions/{filename}{RESET}\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
