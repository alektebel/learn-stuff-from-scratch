"""RAG From Scratch — stage 1 solution: chunking with exact offsets.

Reference implementation. Compare against stage_01.py.
"""


def chunk(text, size, overlap):
    if size <= 0:
        raise ValueError("size must be positive")
    if not 0 <= overlap < size:
        raise ValueError("overlap must satisfy 0 <= overlap < size")
    if not text:
        return []
    stride = size - overlap
    out = []
    i = 0
    n = len(text)
    while i < n:
        end = min(i + size, n)
        out.append({"start": i, "end": end, "text": text[i:end]})
        if end == n:
            break
        i += stride
    return out
