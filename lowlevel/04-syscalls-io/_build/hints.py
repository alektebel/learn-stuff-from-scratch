"""Hints for .claude/skills/graded-module/scripts/make_templates.py.

Every function that carries a mechanism is listed, so make_templates stubs it and puts a
graded hint in its body. ``BufferedWriter._flush_chunk`` is left implemented: it is one
line of plumbing around ``write_all``, not the lesson.
"""
HINTS = {
 "copyfile.py": {
  "write_all": "Loop until every byte is written: write(2) may return fewer bytes than len(data) (a short write) and that is NOT an error. Pass a memoryview slice of the remainder each time.",
  "read_all": "Loop os.read until it returns b'' (EOF), appending the non-empty chunks. A short read is more data, not the end.",
  "read_exact": "Loop until n bytes read or EOF: os.read may return fewer than requested (pipe, signal). Stop on b'' and let the caller compare len(result) with n.",
  "copy_fd": "Read one chunk with os.read; if it is b'' break (EOF); otherwise write_all it to the destination. Return the total bytes written.",
  "copy_path": "os.open the source O_RDONLY and the destination O_WRONLY|O_CREAT|O_TRUNC, call copy_fd, and close both in finally so no descriptor leaks.",
 },
 "buffered.py": {
  "BufferedReader._fill": "One os.read(fd, capacity). b'' is EOF: set a flag and return False, and never call read again. A non-empty (even short) chunk extends the buffer and returns True.",
  "BufferedReader.read": "n < 0: fill until EOF, return the whole buffer. n >= 0: fill while len(buf) < n and not EOF, then take min(n, len(buf)). A short fill is not the end.",
  "BufferedReader.readline": "Fill until b'\\n' is in the buffer or EOF; return through the newline if present, else the remaining tail.",
  "BufferedWriter.write": "Append to the buffer, and while it holds at least `capacity` bytes flush one whole block. Return len(data).",
  "BufferedWriter.flush": "If anything is buffered, hand it to write_all (which retries short writes), then clear the buffer.",
 },
 "fdtable.py": {
  "FDTable._lowest_free": "Scan from 0 for the first integer that is not in the table. open(2) returns the LOWEST unused descriptor, so a freed number is reused.",
  "FDTable.open": "os.open for the raw fd, allocate the lowest free logical number, store both maps, and close the raw fd if allocation raises. Return the logical number.",
  "FDTable._handle": "Return the raw os fd for a logical fd, or raise BadFileDescriptor (POSIX EBADF) if it is not open.",
  "FDTable.read": "os.read the handle for fd; a descriptor that is not open must raise BadFileDescriptor, not read nothing.",
  "FDTable.write": "os.write the handle for fd; a descriptor that is not open must raise BadFileDescriptor.",
  "FDTable.close": "Look up the handle (raises BadFileDescriptor if absent), delete both map entries, then os.close the raw fd. Never silently ignore an unknown fd.",
 },
}
