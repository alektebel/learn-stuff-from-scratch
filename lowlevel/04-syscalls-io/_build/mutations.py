"""Planted bugs for .claude/skills/graded-module/scripts/mutate.py.

Each is a classic mistake for this mechanism, and each must be caught by the named step.
"""
MUTATIONS = [
    # copyfile.py -----------------------------------------------------------------
    ("copy stops after the first read (truncation)", "copyfile.py",
     "    total = 0\n"
     "    while True:\n"
     "        chunk = os.read(src_fd, bufsize)\n"
     "        if chunk == b\"\":\n"
     "            break\n"
     "        total += write_all(dst_fd, chunk)\n"
     "    return total\n",
     "    chunk = os.read(src_fd, bufsize)\n"
     "    if chunk == b\"\":\n"
     "        return 0\n"
     "    return write_all(dst_fd, chunk)\n",
     "1"),

    ("write_all does not retry a short write", "copyfile.py",
     "    view = memoryview(data)\n"
     "    written = 0\n"
     "    while written < len(view):\n"
     "        n = os.write(fd, view[written:])\n"
     "        if n == 0:\n"
     "            raise OSError(errno.EIO, \"write(2) returned 0 without making progress\")\n"
     "        written += n\n"
     "    return written\n",
     "    return os.write(fd, data)\n",
     "4"),

    # buffered.py -----------------------------------------------------------------
    ("a short read is treated as EOF (truncation)", "buffered.py",
     "        while len(self._buf) < n and self._fill():\n"
     "            pass\n"
     "        take = min(n, len(self._buf))\n",
     "        self._fill()\n"
     "        take = min(n, len(self._buf))\n",
     "2"),

    ("a 0-byte read is retried instead of treated as EOF", "buffered.py",
     "        if chunk == b\"\":\n"
     "            self._eof = True\n"
     "            return False\n",
     "        if chunk == b\"\":\n"
     "            return True\n",
     "5"),

    ("BufferedWriter.flush writes once, no short-write retry", "buffered.py",
     "            write_all(self.fd, bytes(self._buf))\n",
     "            os.write(self.fd, bytes(self._buf))\n",
     "4"),

    # fdtable.py ------------------------------------------------------------------
    ("close silently ignores a bad descriptor", "fdtable.py",
     "        real = self._handle(fd)\n"
     "        del self._handles[fd]\n"
     "        del self._paths[fd]\n"
     "        os.close(real)\n",
     "        real = self._handles.pop(fd, None)\n"
     "        self._paths.pop(fd, None)\n"
     "        if real is not None:\n"
     "            os.close(real)\n",
     "3"),

    ("descriptor numbers are never reused", "fdtable.py",
     "        fd = 0\n"
     "        while fd in self._handles:\n"
     "            fd += 1\n"
     "        return fd\n",
     "        self._counter = getattr(self, \"_counter\", 0)\n"
     "        fd = self._counter\n"
     "        self._counter += 1\n"
     "        return fd\n",
     "3"),
]
