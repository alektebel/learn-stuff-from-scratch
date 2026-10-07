class Cache:
    def __init__(self):
        self._data = {}
        self.hits = 0
        self.misses = 0

    def get(self, key, default=None):
        if key in self._data:
            self.hits += 1
            return self._data[key]
        self.misses += 1
        return default

    def set(self, key, value) -> None:
        self._data[key] = value

    def __len__(self) -> int:
        return len(self._data)
