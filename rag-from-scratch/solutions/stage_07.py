"""RAG From Scratch — stage 7 solution: claim support from chunks."""


def _coverage(claim, chunk):
    c = set(claim)
    if not c:
        return 0.0
    return len(c & set(chunk)) / len(c)


def find_support(claim_tokens, chunks_tokens, threshold=0.6):
    return [i for i, ch in enumerate(chunks_tokens)
            if _coverage(claim_tokens, ch) >= threshold]


def unsupported(claim_tokens, chunks_tokens, threshold=0.6):
    return not find_support(claim_tokens, chunks_tokens, threshold)
