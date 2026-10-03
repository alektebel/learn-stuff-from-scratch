"""
Template: Distributed Data Loader

GOAL: Implement a data loader that distributes data across multiple GPUs for parallel training.

GUIDELINES:
1. Each GPU should receive a unique subset of the data (no overlap)
2. Ensure all GPUs process roughly equal amounts of data
3. Handle cases where dataset size isn't perfectly divisible by number of GPUs
4. Implement proper batching and shuffling

YOUR TASKS:
- Implement the DistributedDataLoader class
- Ensure proper data sharding across processes
- Add data shuffling while maintaining reproducibility
"""

import torch
from torch.utils.data import Dataset, DataLoader, Sampler
from typing import Iterator


class DistributedSampler(Sampler):
    """
    Sampler that distributes data across multiple processes.
    
    TODO: Implement the logic to:
    1. Calculate which samples belong to this process
    2. Handle uneven distribution (when len(dataset) % num_processes != 0)
    3. Support shuffling with a seed for reproducibility
    """
    
    def __init__(self, dataset: Dataset, num_replicas: int, rank: int, shuffle: bool = True, seed: int = 0):
        """
        Args:
            dataset: Dataset to sample from
            num_replicas: Number of processes (GPUs)
            rank: Rank of current process (0 to num_replicas-1)
            shuffle: Whether to shuffle data
            seed: Random seed for shuffling
        
        TODO: Initialize necessary attributes
        HINT: You'll need to track:
        - Total samples in dataset
        - Samples per replica (with padding for even distribution)
        - Which indices belong to this rank
        """
        pass  # TODO: Implement initialization
    
    def __iter__(self) -> Iterator[int]:
        """
        Generate indices for this process.
        
        TODO: Implement the logic to:
        1. Optionally shuffle all indices
        2. Pad indices if needed to make distribution even
        3. Select indices for this rank
        4. Return an iterator over these indices
        
        HINT: Use torch.randperm() for shuffling
        HINT: Padding can be done by repeating some indices
        """
        pass  # TODO: Implement iteration
    
    def __len__(self) -> int:
        """Return the number of samples for this process."""
        pass  # TODO: Return samples per replica


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
    
    TODO: Create and return a DataLoader that uses DistributedSampler
    
    HINT: Use the DistributedSampler you implemented above
    HINT: Set pin_memory=True for GPU training efficiency
    """
    pass  # TODO: Implement


# TESTING CODE (Don't modify, but use to test your implementation)
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
    for rank in range(4):
        sampler = DistributedSampler(dataset, num_replicas=4, rank=rank, shuffle=False)
        indices = list(sampler)
        print(f"Rank {rank}: {len(indices)} samples, indices: {indices[:5]}... (showing first 5)")
    
    print("\n" + "=" * 50)
    print("Expected: Each rank should have 25 samples with no overlap")
    print("Total samples across all ranks should equal or slightly exceed dataset size")
