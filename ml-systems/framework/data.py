"""
Datasets and batching
=====================
Book: Vol I ch. 4 (Data engineering). TinyTorch module 05.

A DataLoader turns a dataset into mini-batches. Shuffling each epoch matters (ordered
data, e.g. sorted by label, makes every batch one class and training oscillates), and it
must be reproducible: the same seed gives the same order, or no experiment can be rerun.
"""

from __future__ import annotations

import numpy as np


class TensorDataset:
    def __init__(self, X, y):
        self.X, self.y = np.asarray(X, dtype=float), np.asarray(y)
        if len(self.X) != len(self.y):
            raise ValueError(f"X has {len(self.X)} rows but y has {len(self.y)}")

    def __len__(self) -> int:
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]


class DataLoader:
    def __init__(self, dataset, batch_size: int = 32, shuffle: bool = True, seed: int = 0,
                 drop_last: bool = False):
        if batch_size < 1:
            raise ValueError("batch_size must be >= 1")
        self.dataset, self.batch_size = dataset, batch_size
        self.shuffle, self.drop_last = shuffle, drop_last
        self._rng = np.random.default_rng(seed)

    def __len__(self) -> int:
        # TODO: Number of batches: floor(n / batch) with drop_last, ceil otherwise.
        raise NotImplementedError("DataLoader.__len__")

    def __iter__(self):
        # TODO: Permutation from self._rng when shuffling (seeded: reproducible), arange otherwise. Yield dataset[index slice] per batch; skip a short last batch if drop_last.
        raise NotImplementedError("DataLoader.__iter__")
