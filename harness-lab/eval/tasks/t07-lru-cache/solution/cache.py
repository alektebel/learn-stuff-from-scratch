from collections import OrderedDict


class Cache:
    def __init__(self, capacity: int = 128):
        if not isinstance(capacity, int) or isinstance(capacity, bool) or capacity <= 0:
            raise ValueError("capacity must be a positive int")
        self.capacity = capacity
        self._data: OrderedDict = OrderedDict()
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def get(self, key, default=None):
        if key in self._data:
            self.hits += 1
            self._data.move_to_end(key)
            return self._data[key]
        self.misses += 1
        return default

    def set(self, key, value) -> None:
        if key in self._data:
            self._data.move_to_end(key)
        elif len(self._data) >= self.capacity:
            self._data.popitem(last=False)
            self.evictions += 1
        self._data[key] = value

    def __len__(self) -> int:
        return len(self._data)
