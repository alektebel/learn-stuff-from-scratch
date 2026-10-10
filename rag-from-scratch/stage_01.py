"""RAG From Scratch — stage 1: chunking with exact offsets

DESIGN DECISION — why offsets and not just strings?
    A chunk that cannot point back at the source cannot cite it, and a RAG
    system that cannot cite cannot be audited. Return offsets, and reconstruct
    the document from them in the check.

TODO: implement `chunk`.

    chunk(text, size, overlap) -> list[{"start", "end", "text"}]
    stride = size - overlap
    - the first chunk starts at 0; the last ends at len(text)
    - consecutive chunks overlap by exactly `overlap`
    - the last chunk may be shorter than `size`
    - text[start:end] == chunk["text"], exactly
    - raise ValueError if size <= 0 or not 0 <= overlap < size
"""


def chunk(text, size, overlap):
    raise NotImplementedError("stage 1: implement chunk()")
