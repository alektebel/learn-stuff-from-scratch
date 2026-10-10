# Syscalls & I/O From Scratch

File descriptors, `read`/`write`, short reads, short writes and buffering — in pure Python
(standard library only), built one mechanism at a time on top of `os.read`/`os.write`.

This is the OS-boundary node of the `lowlevel` track. It sits between
`lowlevel-02-memory-layout` (what a buffer is) and the rest of systems work: once you have
seen how a *short read* and a *short write* are not errors, every socket, pipe and
blocking-I/O bug later in the tree has a name.

Sources:

- OSTEP, ch. 36 *I/O Devices* (Arpaci-Dusseau & Arpaci-Dusseau, 2018) — a user `read`/
  `write` becomes an OS request, and the cost is per request, which is why buffers exist.
- POSIX.1-2017 / Linux man-pages, section 2 — `open(2)`, `close(2)`, `read(2)`,
  `write(2)`, `pipe(2)`. `read` returns *up to* the count; `0` is EOF. `write` may write
  fewer bytes than requested, and that is not an error.

## What you build

| Concept | Mechanism | File | Checks |
|---|---|---|---|
| Unbuffered copy | `os.read`/`os.write` loop, `O_TRUNC`, fd lifetime | `copyfile.py` | 1 |
| Short reads | a buffered reader that fills until the request is met or EOF | `buffered.py` | 2 |
| Descriptor table | small integers → handles, lowest-free allocation, `EBADF` | `fdtable.py` | 3 |
| Short writes (limit) | retry the remainder of a partial `write(2)` | `copyfile.py` | 4 |
| EOF (limit) | `read` returning `0` is EOF, never an error to retry | `buffered.py` | 5 |

Every `accept`/`limit_case` in the skill tree is one check step.

## How to use this directory

The top-level files are **templates**: each function you write keeps its signature and
docstring, has a `TODO` with a hint, and raises `NotImplementedError`. `solutions/` holds
working versions for when you are stuck, or to compare afterwards.

```bash
cd lowlevel/04-syscalls-io
python3 check.py        # what to build next; stops at the first gap
python3 check.py 2      # one step
python3 check.py 2 4    # a range
python3 check.py --all  # everything
```

`check.py` runs 5 checks against **your** code and never imports `solutions/`.

**The checker was itself tested.** Seven classic bugs were planted in copies of the
solutions; each one has to be caught by its check:

| Planted bug | Caught by |
|---|---|
| the copy stops after the first `read` (truncation) | step 1 |
| `write_all` does not retry a short write | step 4 |
| a short read is treated as EOF (truncation) | step 2 |
| a `0`-byte read is retried instead of treated as EOF | step 5 |
| `BufferedWriter.flush` writes once, no short-write retry | step 4 |
| `close` silently ignores a bad descriptor | step 3 |
| descriptor numbers are never reused | step 3 |

The limit cases do not rely on luck. A regular file almost always fills a `read`, so random
data would never produce a short read; the checker wraps `os.read`/`os.write` to cap each
call deterministically, and wraps EOF so that asking again raises instead of hanging.

## Design decisions, named

Each file opens with its decisions and what they cost. In short:

- **A fixed, caller-overridable chunk, not the whole file** (`copyfile.py`). A streaming
  copy has a constant footprint; the cost is more syscalls and a copy per chunk. The loop
  is the mechanism.
- **A short read is not EOF** (`buffered.py`). Treating it as the end works on local
  regular files and loses data on pipes, sockets and terminals. The fill loop repeats
  until the request is met or `read` returns `0`.
- **Consume-by-slice buffer** (`buffered.py`). Simpler than a peek cursor; `readline`
  scans the bounded buffer on each call.
- **The table numbers descriptors itself** (`fdtable.py`). It costs a lookup per operation
  and buys a table you can inspect, reuse and teach with; passing the kernel fd straight
  through would hide the lowest-free rule and the double-close hazard.
- **Store the raw `os.open` fd, call `os.read`/`os.write` directly** (`fdtable.py`).
  Holding a Python file object would hide the syscall the module is about.

## Questions to answer before reading the solutions

1. **Why is a short read not EOF, and on which kinds of descriptor does the difference
   actually show?** On a local file you will rarely see it; name the fd types where you
   will, and say what a reader that assumes "short read == done" prints.
2. `write(2)` returning `n < len(data)` is not an error. Under what condition does a pipe
   return a partial write rather than blocking or failing, and where does the retry belong
   — in the caller or in the kernel?
3. Closing an fd twice is harmless if the number was not reused, and catastrophic if it
   was. Describe the exact interleaving in which a double close shuts an unrelated file.
4. Why does `open(2)` promise the *lowest* free descriptor, and what breaks in a shell or a
   server if it hands out a fresh high number instead?
5. A buffer amortises syscall count. The demo prints the syscall count for three
   capacities. At what capacity does the kernel's own per-request work stop dominating,
   and what does the curve look like past that point?

## Limits

- Regular files and pipes only. There is no `select`/`poll`/`epoll`, no non-blocking mode
  and no `EINTR` handling; a real event loop is the subject of `lowlevel-05-concurrency`.
- No `pread`/`pwrite`/`readv`/`writev`/`sendfile`. Each would remove a copy or a loop; the
  byte-by-byte loop is the lesson here.
- `BufferedReader` never seeks and has no `tell`; it is a forward-only stream.
- `FDTable` is single-threaded and has no `dup`/`fcntl`. It models the descriptor table,
  not the full `open-file-description` layer.
- The demos print wall-clock times, which vary by machine; the byte counts, syscall counts
  and identity flags are the reproducible part.
