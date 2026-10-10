"""Unbuffered file copying with ``os.read``/``os.write``.

Sources
-------
* OSTEP, ch. 36 *I/O Devices* (Arpaci-Dusseau & Arpaci-Dusseau, 2018): a user-level
  ``read``/``write`` becomes an OS request that travels down to a device. The chapter's
  point is the *cost per request*: one syscall per byte is catastrophically slow, which
  is exactly why code loops over a buffer rather than calling the kernel for every byte.
* POSIX.1-2017 / Linux man-pages, section 2: ``read(2)``, ``write(2)``, ``open(2)``,
  ``close(2)``, ``pipe(2)``. Restated: ``read`` returns *up to* the requested count; a
  return of ``0`` means end-of-file, not an error. ``write`` returns the number of bytes
  actually written, which *may be less* than the count handed to it (a pipe with less
  room than the request; a signal between bytes). Neither short case is an error.

DESIGN DECISION - buffer size: one big buffer, or chunked reads?

A buffer as large as the file is simple and fast: allocate once and read. It also dies on
a file larger than RAM. A fixed chunk (the classic 4 KiB page, here 64 KiB) copies files
of any size with a constant footprint; the cost is more syscalls and a memcpy per chunk.
**Chosen:** a fixed, caller-overridable chunk. The whole point of this module is that the
*loop* is the mechanism, not the buffer size.

DESIGN DECISION - who owns the returned bytes?

``copy_fd`` writes each chunk to the destination and drops it, so peak memory is one
chunk regardless of file size (a *streaming* copy). The alternative - read everything
then write everything - needs the whole file in memory and is the bug this module is
meant to make you avoid.
"""

import errno
import os

#: Default chunk. 64 KiB matches the block size of most modern filesystems closely
#: enough that a copy issues a handful of syscalls per megabyte, not thousands.
DEFAULT_BUFSIZE = 1 << 16


def write_all(fd: int, data: bytes) -> int:
    """Write every byte of ``data`` to ``fd``, retrying a short write.

    ``write(2)`` is allowed to write fewer bytes than requested and still return success
    (a pipe with less free space than the request, or an interruption after some bytes).
    Treating that ``n < len(data)`` as success silently truncates the output; the
    remainder must be written. Returns the number of bytes written (always ``len(data)``
    on success) and raises only if the kernel reports zero progress.
    """
    # TODO: Loop until every byte is written: write(2) may return fewer bytes than len(data) (a short write) and that is NOT an error. Pass a memoryview slice of the remainder each time.
    raise NotImplementedError("write_all")


def read_all(fd: int, bufsize: int = DEFAULT_BUFSIZE) -> bytes:
    """Read ``fd`` to end-of-file and return everything.

    ``read(2)`` returning ``b""`` is EOF (POSIX ``read(2)``); retrying it would spin
    forever, so the loop stops there. A non-empty short read is simply appended and the
    loop continues.
    """
    # TODO: Loop os.read until it returns b'' (EOF), appending the non-empty chunks. A short read is more data, not the end.
    raise NotImplementedError("read_all")


def read_exact(fd: int, n: int) -> bytes:
    """Read exactly ``n`` bytes, or fewer only at EOF.

    A single ``os.read`` may return less than ``n`` on a pipe, a terminal or after a
    signal; loops until ``n`` bytes or EOF. The caller distinguishes truncation from a
    complete read by the length of the return value.
    """
    # TODO: Loop until n bytes read or EOF: os.read may return fewer than requested (pipe, signal). Stop on b'' and let the caller compare len(result) with n.
    raise NotImplementedError("read_exact")


def copy_fd(src_fd: int, dst_fd: int, bufsize: int = DEFAULT_BUFSIZE) -> int:
    """Copy from ``src_fd`` to ``dst_fd`` until EOF; return the number of bytes copied.

    Unbuffered and streaming: read one chunk, hand it to :func:`write_all`, repeat. The
    read loop ends only on ``b""`` (EOF), never on a short read. The write loop is inside
    ``write_all`` because a short *write* is not the end of anything.
    """
    # TODO: Read one chunk with os.read; if it is b'' break (EOF); otherwise write_all it to the destination. Return the total bytes written.
    raise NotImplementedError("copy_fd")


def copy_path(src: str, dst: str, bufsize: int = DEFAULT_BUFSIZE) -> int:
    """Copy a file by path using only ``os.open``/``os.read``/``os.write``/``os.close``.

    Owns both descriptors so they are released even if the copy raises; ``O_TRUNC`` makes
    the destination match the source exactly, including a shorter source over a longer
    destination. No Python file object, no buffering: this is the raw syscall path.
    """
    # TODO: os.open the source O_RDONLY and the destination O_WRONLY|O_CREAT|O_TRUNC, call copy_fd, and close both in finally so no descriptor leaks.
    raise NotImplementedError("copy_path")


if __name__ == "__main__":
    import random
    import tempfile
    import time

    size = 1 << 16
    data = random.Random(1).randbytes(size)
    work = tempfile.mkdtemp(prefix="copyfile-demo-")
    src = os.path.join(work, "src.bin")
    dst = os.path.join(work, "dst.bin")
    with open(src, "wb") as fh:
        fh.write(data)

    print(f"copyfile: {size} bytes, unbuffered os.read/os.write")
    for bufsize in (1, 7, 4096, DEFAULT_BUFSIZE):
        start = time.perf_counter()
        copied = copy_path(src, dst, bufsize=bufsize)
        elapsed = time.perf_counter() - start
        identical = open(dst, "rb").read() == data
        reads = -(-size // bufsize)
        print(f"  bufsize {bufsize:>6}: {copied} bytes, ~{reads} read() calls, "
              f"{elapsed * 1000:7.1f} ms, identical={identical}")

    # A real pipe, to show the same code works on a non-seekable fd.
    r, w = os.pipe()
    try:
        write_all(w, b"pipe: ")
        write_all(w, data[:32])
        print(f"  pipe: echoed {len(read_exact(r, 38))} bytes back through the same helpers")
    finally:
        os.close(r)
        os.close(w)
