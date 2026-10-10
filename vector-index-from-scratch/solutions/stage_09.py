"""Vector Index From Scratch — stage 9: int8 quantization, four bytes become one

SOLUTION. Per-dimension min/max over the corpus becomes a linear map to 0..255,
clamped on the way in. The query stays in full precision: the score is the exact
query against the reconstructed database vector, so the only error in the
ranking is the compression's.
"""


class ScalarQuantizer:
    def __init__(self):
        self.lo = []
        self.span = []

    def fit(self, vectors):
        rows = [tuple(v) for v in vectors]
        if not rows:
            raise ValueError("fit() needs at least one vector")
        dim = len(rows[0])
        for r in rows:
            if len(r) != dim:
                raise ValueError("fit() got vectors of different dimensions")
        self.lo = [min(r[d] for r in rows) for d in range(dim)]
        self.span = []
        for d in range(dim):
            hi = max(r[d] for r in rows)
            self.span.append((hi - self.lo[d]) or 1.0)
        return self

    @property
    def bytes_per_vector(self):
        return len(self.lo)

    def quantize(self, vector):
        if len(vector) != len(self.lo):
            raise ValueError(
                f"quantize() got {len(vector)} dimensions, the fit saw "
                f"{len(self.lo)}")
        codes = []
        for x, lo, span in zip(vector, self.lo, self.span):
            code = int(round((x - lo) / span * 255.0))
            if code < 0:
                code = 0
            elif code > 255:
                code = 255
            codes.append(code)
        return codes

    def dequantize(self, code):
        return [lo + c / 255.0 * span
                for c, lo, span in zip(code, self.lo, self.span)]


class QuantizedIndex:
    def __init__(self, vectors):
        self._keys = list(vectors)
        self._vectors = {k: tuple(v) for k, v in vectors.items()}
        self._order = {k: i for i, k in enumerate(self._keys)}
        self._quantizer = ScalarQuantizer().fit(self._vectors.values())
        self._codes = {k: self._quantizer.quantize(v)
                       for k, v in self._vectors.items()}

    @property
    def quantizer(self):
        return self._quantizer

    def code(self, key):
        return list(self._codes[key])

    def __len__(self):
        return len(self._keys)

    def search(self, query, k):
        q = tuple(query)
        rows = []
        for key in self._keys:
            # the query is exact, the database vector is reconstructed: the
            # asymmetry is the point, and it costs nothing
            restored = self._quantizer.dequantize(self._codes[key])
            rows.append((key, sum(x * y for x, y in zip(q, restored))))
        rows.sort(key=lambda kv: (-kv[1], self._order[kv[0]]))
        return rows[:max(0, k)]
