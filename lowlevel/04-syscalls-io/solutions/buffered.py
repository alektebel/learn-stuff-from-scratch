"""A buffered reader over a raw file descriptor, built to survive short reads.

Sources
-------
* OSTEP, ch. 36 *I/O Devices*: the chapter's central cost is the request. A buffered
  reader amortises many small logical reads over few syscalls: pull ``capacity`` bytes per
  ``read(2)`` and serve ``read(n)``/``readline`` from what was already fetched.
* POSIX.1-2017 / Linux man-pages, section 2: ``read(2)``. Restated: a ``read`` may return
  fewer bytes than asked for *without* it being EOF, and only ``0`` means EOF. A buffered
  reader that assumes "short read == end of data" silently truncates its output.

DESIGN DECISION - is a short read EOF?

Treating a short read as EOF is the classic buffering bug: it works on local regular files
(where ``read`` usually fills the request) and loses data on pipes, sockets and terminals.
**Chosen:** a short read is *not* EOF; the fill loop repeats until the request is met or
``read`` returns ``0``. It costs one extra comparison per fill and removes a whole class of
data loss.

DESIGN DECISION - one buffer, or a read/peek cursor pair?

A cursor over a growable ``bytearray`` (peek without consuming) supports ``readline`` and
lookahead at the cost of occasionally copying the buffer down. Consuming by slicing
``del`` after each read is simpler and allocates one bytes object per read. **Chosen:**
consume-by-slice; ``readline`` looks at the whole buffer each call, which is fine because
the buffer is bounded by ``capacity``.
"""

import os

from copyfile import write_all

DEFAULT_CAPACITY = 1 << 16


class BufferedReader:
    """Read from ``fd`` in ``capacity``-byte syscalls, handing out exact-size reads."""

    def __init__(self, fd: int, capacity: int = DEFAULT_CAPACITY):
        self.fd = fd
        self.capacity = capacity
        self._buf = bytearray()
        self._eof = False
        #: Number of underlying ``read(2)`` calls made. A measurement, not bookkeeping.
        self.reads = 0

    def _fill(self) -> bool:
        """Pull one chunk from the fd into the buffer.

        Returns ``False`` once ``read(2)`` has reported EOF (``b""``); that result is
        remembered so a later call does not ask again. A non-empty short read returns
        ``True``: it is more data, not the end.
        """
        if self._eof:
            return False
        chunk = os.read(self.fd, self.capacity)
        self.reads += 1
        if chunk == b"":
            self._eof = True
            return False
        self._buf.extend(chunk)
        return True

    def read(self, n: int = -1) -> bytes:
        """Return up to ``n`` bytes, or everything to EOF when ``n`` is negative.

        For a non-negative ``n`` the result is exactly ``n`` bytes unless EOF was
        reached, so a short underlying read must be looped over, not returned as-is.
        """
        if n is None or n < 0:
            while self._fill():
                pass
            data = bytes(self._buf)
            self._buf.clear()
            return data
        while len(self._buf) < n and self._fill():
            pass
        take = min(n, len(self._buf))
        data = bytes(self._buf[:take])
        del self._buf[:take]
        return data

    def readline(self) -> bytes:
        """Return one line including its trailing newline, or the tail at EOF.

        Keeps filling - through short reads - until a newline is buffered or EOF.
        """
        while b"\n" not in self._buf and not self._eof:
            self._fill()
        idx = self._buf.find(b"\n")
        take = len(self._buf) if idx == -1 else idx + 1
        data = bytes(self._buf[:take])
        del self._buf[:take]
        return data


class BufferedWriter:
    """Buffer writes and flush them with every byte delivered (via ``write_all``)."""

    def __init__(self, fd: int, capacity: int = DEFAULT_CAPACITY):
        self.fd = fd
        self.capacity = capacity
        self._buf = bytearray()
        #: Number of underlying write batches flushed.
        self.writes = 0

    def write(self, data: bytes) -> int:
        """Append to the buffer, flushing whole ``capacity`` blocks as they fill."""
        self._buf.extend(data)
        while len(self._buf) >= self.capacity:
            self._flush_chunk(self.capacity)
        return len(data)

    def _flush_chunk(self, n: int) -> None:
        chunk = bytes(self._buf[:n])
        del self._buf[:n]
        write_all(self.fd, chunk)
        self.writes += 1

    def flush(self) -> None:
        """Deliver whatever is buffered. Uses ``write_all``: a short write is retried."""
        if self._buf:
            write_all(self.fd, bytes(self._buf))
            self._buf.clear()
            self.writes += 1


if __name__ == "__main__":
    import tempfile

    size = 200_000
    data = bytes(range(256)) * (size // 256) + b"tail"
    work = tempfile.mkdtemp(prefix="buffered-demo-")
    path = os.path.join(work, "data.bin")
    with open(path, "wb") as fh:
        fh.write(data)

    print(f"buffered: {len(data)} bytes")
    for capacity in (16, 64, DEFAULT_CAPACITY):
        fd = os.open(path, os.O_RDONLY)
        try:
            reader = BufferedReader(fd, capacity=capacity)
            got = reader.read(-1)
        finally:
            os.close(fd)
        print(f"  capacity {capacity:>6}: {len(got)} bytes, identical={got == data}, "
              f"{reader.reads} read() syscalls")

    fd = os.open(os.path.join(work, "out.bin"), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    try:
        writer = BufferedWriter(fd, capacity=64)
        for i in range(0, len(data), 1000):
            writer.write(data[i:i + 1000])
        writer.flush()
    finally:
        os.close(fd)
    print(f"  writer: {writer.writes} flush batches, identical="
          f"{open(os.path.join(work, 'out.bin'), 'rb').read() == data}")
