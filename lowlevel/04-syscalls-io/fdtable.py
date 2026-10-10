"""A process file-descriptor table: small integers to open handles.

Sources
-------
* POSIX.1-2017 / Linux man-pages, section 2: ``open(2)``, ``close(2)``, ``read(2)``,
  ``write(2)``. Restated: a descriptor is a small non-negative integer, unique within the
  process. ``open`` returns the *lowest unused* descriptor (a guarantee programs rely on:
  the standard streams are 0, 1, 2). ``close`` on a descriptor that is not open fails with
  ``EBADF`` - which is precisely why closing twice must be *reported*: if the number was
  recycled in between, the second close would shut an unrelated file.
* OSTEP, ch. 36 *I/O Devices*: the descriptor table is the per-process map the kernel
  walks on every I/O call to turn a small integer into an open file. Keeping the mapping
  explicit in user space is a miniature of the kernel's own table.

DESIGN DECISION - is the descriptor the OS fd, or an index the table owns?

Passing the kernel's own fd number straight through is a thin wrapper, and closing it is
just ``os.close``. But then "close twice" is caught only by the kernel, and a logical fd
that coincides with 0/1/2 is a footgun. **Chosen:** the table numbers handles itself,
starting at the lowest free integer, and keeps the kernel fd private. It costs a lookup per
operation and buys a table you can inspect, reuse and teach with.

DESIGN DECISION - what does a handle hold?

The alternative is to hold a Python file object and call its ``.read``/``.write``. That
hides the raw syscall this module is about. **Chosen:** store the raw integer returned by
``os.open`` and call ``os.read``/``os.write`` directly, so the table's jobs (allocate,
look up, release) are the only thing layered on top.
"""

import os


class BadFileDescriptor(OSError):
    """Raised for an operation on a descriptor that is not open (POSIX ``EBADF``)."""

    def __init__(self, fd: int):
        super().__init__(9, f"bad file descriptor: {fd}")  # errno.EBADF == 9
        self.fd = fd


class FDTable:
    """A process descriptor table. Logical fds are small integers; the OS fd is private."""

    def __init__(self) -> None:
        self._handles: dict[int, int] = {}   # logical fd -> raw os fd
        self._paths: dict[int, str] = {}

    def _lowest_free(self) -> int:
        """The smallest non-negative integer not currently open (POSIX ``open(2)``).

        Starting the scan at 0 each time - rather than handing out a counter - is what
        makes a freed descriptor number get reused, matching the kernel and making
        double-close dangerous in exactly the way the check demonstrates.
        """
        # TODO: Scan from 0 for the first integer that is not in the table. open(2) returns the LOWEST unused descriptor, so a freed number is reused.
        raise NotImplementedError("FDTable._lowest_free")

    def open(self, path: str, flags: int, mode: int = 0o644) -> int:
        """Open ``path`` and install the handle, returning its lowest free descriptor."""
        # TODO: os.open for the raw fd, allocate the lowest free logical number, store both maps, and close the raw fd if allocation raises. Return the logical number.
        raise NotImplementedError("FDTable.open")

    def _handle(self, fd: int) -> int:
        """Look up the raw os fd for ``fd``, or raise :class:`BadFileDescriptor`."""
        # TODO: Return the raw os fd for a logical fd, or raise BadFileDescriptor (POSIX EBADF) if it is not open.
        raise NotImplementedError("FDTable._handle")

    def read(self, fd: int, n: int) -> bytes:
        """``read(2)`` through the table; an unopened fd is an error, not an empty read."""
        # TODO: os.read the handle for fd; a descriptor that is not open must raise BadFileDescriptor, not read nothing.
        raise NotImplementedError("FDTable.read")

    def write(self, fd: int, data: bytes) -> int:
        """``write(2)`` through the table; an unopened fd is an error."""
        # TODO: os.write the handle for fd; a descriptor that is not open must raise BadFileDescriptor.
        raise NotImplementedError("FDTable.write")

    def close(self, fd: int) -> None:
        """Close ``fd``. A descriptor that is not open is an error, never ignored.

        Silently ignoring it is the bug: the number may already have been handed to a new
        ``open``, and a repeated close would then shut *that* file.
        """
        # TODO: Look up the handle (raises BadFileDescriptor if absent), delete both map entries, then os.close the raw fd. Never silently ignore an unknown fd.
        raise NotImplementedError("FDTable.close")

    def __contains__(self, fd: int) -> bool:
        return fd in self._handles

    def __len__(self) -> int:
        return len(self._handles)

    def open_fds(self) -> list[int]:
        """The logical descriptors currently open, in numeric order (for inspection)."""
        return sorted(self._handles)


if __name__ == "__main__":
    import tempfile

    work = tempfile.mkdtemp(prefix="fdtable-demo-")
    paths = []
    for name in ("a", "b", "c"):
        p = os.path.join(work, name + ".txt")
        with open(p, "w") as fh:
            fh.write(f"{name}: contents\n")
        paths.append(p)

    table = FDTable()
    opened = [table.open(p, os.O_RDONLY) for p in paths]
    print(f"fdtable: opened {opened} -> {len(table)} descriptors")
    print(f"  read(fd={opened[0]}) = {table.read(opened[0], 64)!r}")

    table.close(opened[0])
    print(f"  after close {opened[0]}: open_fds = {table.open_fds()}")
    try:
        table.close(opened[0])
    except BadFileDescriptor as exc:
        print(f"  double close reported: {exc}")

    reused = table.open(paths[1], os.O_RDONLY)
    print(f"  open reused the lowest free number: {opened[0]} -> {reused}")
    for fd in list(table.open_fds()):
        table.close(fd)
    print(f"  all closed: open_fds = {table.open_fds()}")
