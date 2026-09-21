"""
Solution: Distributed Data Loader

This is the complete implementation of a distributed data loader.
"""

import torch
from torch.utils.data import Dataset, DataLoader, Sampler
from typing import Iterator
import math


class DistributedSampler(Sampler):
    """
    Sampler that distributes data across multiple processes.
    """
    
    def __init__(self, dataset: Dataset, num_replicas: int, rank: int, shuffle: bool = True, seed: int = 0):
        """
        Args:
            dataset: Dataset to sample from
            num_replicas: Number of processes (GPUs)
            rank: Rank of current process (0 to num_replicas-1)
            shuffle: Whether to shuffle data
            seed: Random seed for shuffling
        """
        self.dataset = dataset
        self.num_replicas = num_replicas
        self.rank = rank
        self.shuffle = shuffle
        self.seed = seed
        self.epoch = 0
        
        # Calculate samples per replica (with padding for even distribution)
        self.num_samples = math.ceil(len(self.dataset) / self.num_replicas)
        self.total_size = self.num_samples * self.num_replicas
    
    def __iter__(self) -> Iterator[int]:
        """Generate indices for this process."""
        # Generate all indices
        if self.shuffle:
            # Deterministic shuffling based on seed and epoch
            g = torch.Generator()
            g.manual_seed(self.seed + self.epoch)
            indices = torch.randperm(len(self.dataset), generator=g).tolist()
        else:
            indices = list(range(len(self.dataset)))
        
        # Pad indices to make total_size
        # This ensures all replicas have the same number of samples
        indices += indices[:(self.total_size - len(indices))]
        assert len(indices) == self.total_size
        
        # Subsample for this rank
        indices = indices[self.rank:self.total_size:self.num_replicas]
        assert len(indices) == self.num_samples
        
        return iter(indices)
    
    def __len__(self) -> int:
        """Return the number of samples for this process."""
        return self.num_samples
    
    def set_epoch(self, epoch: int):
        """
        Set the epoch for shuffling.
        Call this at the beginning of each epoch for proper shuffling.
        """
        self.epoch = epoch


def create_distributed_dataloader(
    dataset: Dataset,
    batch_size: int,
    rank: int,
    world_size: int,
    shuffle: bool = True,
    num_workers: int = 4
) -> DataLoader:
    """
    Create a DataLoader with distributed sampling.
    
    Args:
        dataset: The dataset to load
        batch_size: Batch size per GPU
        rank: Current process rank
        world_size: Total number of processes
        shuffle: Whether to shuffle data
        num_workers: Number of data loading workers
    
    Returns:
        DataLoader configured for distributed training
    """
    sampler = DistributedSampler(
        dataset,
        num_replicas=world_size,
        rank=rank,
        shuffle=shuffle
    )
    
    dataloader = DataLoader(
        dataset,
        batch_size=batch_size,
        sampler=sampler,
        num_workers=num_workers,
        pin_memory=True,  # Faster data transfer to GPU
        drop_last=False  # Keep all samples
    )
    
    return dataloader


# TESTING CODE
if __name__ == "__main__":
    # Create a simple dataset for testing
    class SimpleDataset(Dataset):
        def __init__(self, size):
            self.size = size
        
        def __len__(self):
            return self.size
        
        def __getitem__(self, idx):
            return torch.tensor(idx)
    
    # Test with 100 samples and 4 processes
    dataset = SimpleDataset(100)
    
    print("Testing DistributedSampler:")
    print("=" * 50)
    
    # Simulate 4 processes
    all_indices = []
    for rank in range(4):
        sampler = DistributedSampler(dataset, num_replicas=4, rank=rank, shuffle=False)
        indices = list(sampler)
        all_indices.extend(indices[:25])  # Only take original samples (excluding padding)
        print(f"Rank {rank}: {len(indices)} samples, indices: {indices[:5]}... (showing first 5)")
    
    print("\n" + "=" * 50)
    print(f"Total unique samples covered: {len(set(all_indices))}")
    print("Expected: Each rank should have 25 samples")
    print("Total samples across all ranks: 100 (some may be duplicated due to padding)")
    
    # Test with shuffling
    print("\n" + "=" * 50)
    print("Testing with shuffle=True:")
    for rank in range(4):
        sampler = DistributedSampler(dataset, num_replicas=4, rank=rank, shuffle=True, seed=42)
        indices = list(sampler)
        print(f"Rank {rank}: indices: {indices[:5]}... (showing first 5)")
    
    print("\n" + "=" * 50)
    print("Note: With shuffling, indices should be randomized but deterministic")
    print("Running again with same seed should give same results")
