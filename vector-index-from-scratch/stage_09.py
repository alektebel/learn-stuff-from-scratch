"""Vector Index From Scratch — stage 9: int8 quantization, four bytes become one

DESIGN DECISION — the query is not quantized (asymmetric distance).
    Quantize the database: that is what is stored, that is what costs memory and
    bandwidth, and its error is the price of the compression. Keep the query in
    full precision. You then pay the database's quantization error alone, and
    the ranking is better than the symmetric alternative at no storage cost.
    Quantizing the query too is simpler to write and strictly worse — and the
    check recomputes the score from the exact query, so it will notice.

DESIGN DECISION — clamp, never wrap.
    A value above the fitted maximum must come back as the maximum, not as a
    small number. integer casts wrap silently in most languages (and in numpy),
    so an out-of-range vector becomes a *distant* one — plausible, wrong, and
    only visible if you test exactly the out-of-range case. The fitted range
    comes from the corpus, so the query is the usual thing that falls outside.

TODO: implement

    class ScalarQuantizer:
        .fit(vectors)        vectors: an iterable of dense unit vectors (all the
                             same length). Record, per dimension, the minimum and
                             the span (max - min; a dimension with zero span gets
                             span 1 and dequantizes to that constant).
        .quantize(vector)    -> list[int], one code 0..255 per dimension:
                             round((x - lo) / span * 255), clamped into 0..255.
        .dequantize(code)    -> list[float]: lo + code / 255 * span, per dimension
        .bytes_per_vector    int: one byte per dimension (a float32 costs four,
                             a float64 eight — this is the number the frontier
                             trades recall against)
        The reconstruction error per dimension is at most span / 510.

    class QuantizedIndex:
        .__init__(vectors)   fit the quantizer on the corpus; store one code per
                             key (a dict {key: dense unit vector} in).
        .code(key)           -> list[int] (the stored code, for inspection)
        .quantizer           the fitted ScalarQuantizer. The check recomputes
                             your ranking from it: the score of a row must be
                             exactly dot(query, quantizer.dequantize(code)),
                             which is what makes "asymmetric distance" a
                             statement about the numbers and not about intent
        .search(query, k)    -> [(key, score)] descending, ties by insertion
                             order; the score is the dot product of the EXACT
                             query with the DEQUANTIZED stored vector, and
                             nothing else. It is an approximation of the true
                             dot product; it must not silently be something
                             else, such as the quantized query's dot product.
        __len__()
"""


class ScalarQuantizer:
    def fit(self, vectors):
        raise NotImplementedError("stage 9: implement ScalarQuantizer.fit()")

    def quantize(self, vector):
        raise NotImplementedError("stage 9: implement ScalarQuantizer.quantize()")

    def dequantize(self, code):
        raise NotImplementedError("stage 9: implement ScalarQuantizer.dequantize()")


class QuantizedIndex:
    def __init__(self, vectors):
        raise NotImplementedError("stage 9: implement QuantizedIndex.__init__()")

    def code(self, key):
        raise NotImplementedError("stage 9: implement QuantizedIndex.code()")

    def search(self, query, k):
        raise NotImplementedError("stage 9: implement QuantizedIndex.search()")

    def __len__(self):
        raise NotImplementedError("stage 9: implement QuantizedIndex.__len__()")
