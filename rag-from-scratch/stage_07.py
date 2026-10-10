"""RAG From Scratch — stage 7: citations and unsupported claims

An answer nobody can check is a liability. A claim is supported when some
retrieved chunk covers enough of its tokens; everything else must be flagged,
not quietly printed.

TODO: implement `find_support` and `unsupported`.

    _coverage(claim, chunk) = |claim ∩ chunk| / |claim|
    find_support(claim_tokens, chunks_tokens, threshold=0.6)
        -> indices of chunks whose coverage >= threshold
    unsupported(...) -> True when find_support would return []
"""


def find_support(claim_tokens, chunks_tokens, threshold=0.6):
    raise NotImplementedError("stage 7: implement find_support()")


def unsupported(claim_tokens, chunks_tokens, threshold=0.6):
    raise NotImplementedError("stage 7: implement unsupported()")
