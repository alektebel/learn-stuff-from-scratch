# Syscalls & I/O From Scratch — Solutions

Complete versions of every template in the parent directory. Pure Python 3, standard
library only. Run them from inside this directory (they import each other by name):

```bash
python3 copyfile.py    # one copy at four buffer sizes: syscalls vs time
python3 buffered.py    # one file at three capacities: read() syscalls to read it all
python3 fdtable.py     # open/read/close, a reported double close, and fd reuse
```

Expected output (`copyfile.py`; wall-clock times vary by machine):

```
copyfile: 65536 bytes, unbuffered os.read/os.write
  bufsize      1: 65536 bytes, ~65536 read() calls,    46.6 ms, identical=True
  bufsize      7: 65536 bytes, ~9363 read() calls,     6.7 ms, identical=True
  bufsize   4096: 65536 bytes, ~16 read() calls,     0.0 ms, identical=True
  bufsize  65536: 65536 bytes, ~1 read() calls,     0.0 ms, identical=True
  pipe: echoed 38 bytes back through the same helpers
```

`buffered.py`:

```
buffered: 199940 bytes
  capacity     16: 199940 bytes, identical=True, 12498 read() syscalls
  capacity     64: 199940 bytes, identical=True, 3126 read() syscalls
  capacity  65536: 199940 bytes, identical=True, 5 read() syscalls
  writer: 3125 flush batches, identical=True
```

`fdtable.py`:

```
fdtable: opened [0, 1, 2] -> 3 descriptors
  read(fd=0) = b'a: contents\n'
  after close 0: open_fds = [1, 2]
  double close reported: [Errno 9] bad file descriptor: 0
  open reused the lowest free number: 0 -> 0
  all closed: open_fds = []
```

To grade yourself, run the checker against these files in a scratch directory:

```bash
cd lowlevel/04-syscalls-io
tmp=$(mktemp -d)
cp solutions/*.py check.py "$tmp"/
(cd "$tmp" && python3 check.py --all)   # 5/5 passing
```

The one number worth predicting before you look is the `read()` count in `buffered.py`:
`ceil(199940 / capacity)` syscalls, plus the final `0`-byte read that signals EOF. If your
buffer were unbuffered on a pipe, each logical read would be one syscall — that gap is the
reason a buffer exists.
