"""
Solution: Basic Data Parallel Trainer

This is the complete implementation of a data parallel trainer.
"""

import torch
import torch.nn as nn
import torch.distributed as dist
from typing import Optional
import os


class DataParallelTrainer:
    """
    Simple data parallel trainer for multiple GPUs.
    """
    
    def __init__(
        self,
        model: nn.Module,
        optimizer: torch.optim.Optimizer,
        rank: int,
        world_size: int,
        device: torch.device
    ):
        """
        Initialize the trainer.
        
        Args:
            model: The neural network model
            optimizer: Optimizer for training
            rank: Current process rank
            world_size: Total number of processes
            device: Device to train on (e.g., cuda:0)
        """
        self.model = model.to(device)
        self.optimizer = optimizer
        self.rank = rank
        self.world_size = world_size
        self.device = device
        
        # Broadcast initial model parameters to ensure all processes start the same
        self.broadcast_model()
    
    def all_reduce_gradients(self):
        """
        Aggregate gradients across all GPUs using all-reduce.
        
        This averages the gradients computed on each GPU, which is mathematically
        equivalent to computing gradients on the full batch.
        """
        for param in self.model.parameters():
            if param.grad is not None:
                # Sum gradients across all processes
                dist.all_reduce(param.grad.data, op=dist.ReduceOp.SUM)
                # Average by dividing by world size
                param.grad.data /= self.world_size
    
    def train_step(self, batch_data, batch_labels):
        """
        Perform one training step.
        
        Args:
            batch_data: Input data for this batch
            batch_labels: Labels for this batch
        
        Returns:
            loss: The loss value for this batch
        """
        # Move data to device
        batch_data = batch_data.to(self.device)
        batch_labels = batch_labels.to(self.device)
        
        # Zero gradients from previous step
        self.optimizer.zero_grad()
        
        # Forward pass
        outputs = self.model(batch_data)
        
        # Compute loss
        loss = nn.functional.cross_entropy(outputs, batch_labels)
        
        # Backward pass
        loss.backward()
        
        # Synchronize gradients across all GPUs
        self.all_reduce_gradients()
        
        # Update weights
        self.optimizer.step()
        
        return loss.item()
    
    def broadcast_model(self):
        """
        Broadcast model parameters from rank 0 to all other ranks.
        This ensures all processes start with the same model weights.
        """
        for param in self.model.parameters():
            dist.broadcast(param.data, src=0)


def setup_distributed(rank: int, world_size: int, backend: str = 'nccl'):
    """
    Initialize the distributed process group.
    
    Args:
        rank: Rank of current process
        world_size: Total number of processes
        backend: Backend to use ('nccl' for GPU, 'gloo' for CPU)
    """
    # Set up environment variables if not already set
    if 'MASTER_ADDR' not in os.environ:
        os.environ['MASTER_ADDR'] = 'localhost'
    if 'MASTER_PORT' not in os.environ:
        os.environ['MASTER_PORT'] = '12355'
    
    # Initialize process group
    dist.init_process_group(
        backend=backend,
        init_method='env://',
        world_size=world_size,
        rank=rank
    )
    
    # Set device for this process
    if backend == 'nccl':
        torch.cuda.set_device(rank)


def cleanup_distributed():
    """
    Clean up the distributed process group.
    """
    dist.destroy_process_group()


# EXAMPLE USAGE
def train_example(rank: int, world_size: int):
    """
    Example training function showing how to use the DataParallelTrainer.
    """
    print(f"Running on rank {rank}/{world_size}")
    
    # Setup distributed training
    setup_distributed(rank, world_size, backend='nccl' if torch.cuda.is_available() else 'gloo')
    
    # Create a simple model
    device = torch.device(f'cuda:{rank}' if torch.cuda.is_available() else 'cpu')
    model = nn.Sequential(
        nn.Linear(784, 128),
        nn.ReLU(),
        nn.Linear(128, 10)
    )
    
    # Create optimizer
    optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
    
    # Create trainer
    trainer = DataParallelTrainer(model, optimizer, rank, world_size, device)
    
    # Dummy training data (in real scenario, use distributed data loader)
    for step in range(10):
        # Generate random data
        batch_data = torch.randn(32, 784)
        batch_labels = torch.randint(0, 10, (32,))
        
        # Training step
        loss = trainer.train_step(batch_data, batch_labels)
        
        if rank == 0:  # Only print from rank 0 to avoid duplicate output
            print(f"Step {step}, Loss: {loss:.4f}")
    
    # Cleanup
    cleanup_distributed()
    print(f"Rank {rank} finished training")


if __name__ == "__main__":
    import torch.multiprocessing as mp
    
    print("Data Parallel Trainer - Complete Implementation")
    print("=" * 50)
    
    # Check if CUDA is available
    if torch.cuda.is_available():
        world_size = torch.cuda.device_count()
        print(f"Found {world_size} CUDA devices")
        
        if world_size > 1:
            print("Starting distributed training...")
            # Spawn processes for each GPU
            mp.spawn(train_example, args=(world_size,), nprocs=world_size, join=True)
        else:
            print("Only 1 GPU found. For testing, will use rank 0 only.")
            train_example(0, 1)
    else:
        print("CUDA not available. Running on CPU with 1 process.")
        train_example(0, 1)
    
    print("\n" + "=" * 50)
    print("Key features implemented:")
    print("- Gradient all-reduce (averaging across GPUs)")
    print("- Model broadcasting (sync initial weights)")
    print("- Proper device placement")
    print("- Complete training loop")
