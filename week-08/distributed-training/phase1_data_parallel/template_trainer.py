"""
Template: Basic Data Parallel Trainer

GOAL: Implement a simple data parallel training loop that distributes training across multiple GPUs.

GUIDELINES:
1. Each GPU maintains a copy of the model
2. Forward and backward passes happen independently on each GPU
3. Gradients are averaged across all GPUs before updating weights
4. All GPUs should stay synchronized

YOUR TASKS:
- Implement gradient aggregation across GPUs
- Ensure proper synchronization
- Handle model replication
"""

import torch
import torch.nn as nn
import torch.distributed as dist
from typing import Optional


class DataParallelTrainer:
    """
    Simple data parallel trainer for multiple GPUs.
    
    TODO: Implement distributed training logic
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
        
        TODO: 
        1. Move model to the correct device
        2. Store necessary attributes
        3. Initialize any tracking variables
        """
        pass  # TODO: Implement
    
    def all_reduce_gradients(self):
        """
        Aggregate gradients across all GPUs using all-reduce.
        
        TODO: Implement gradient aggregation
        
        STEPS:
        1. Iterate through all model parameters
        2. For each parameter with gradients:
           - Use dist.all_reduce() to sum gradients across GPUs
           - Divide by world_size to get average
        
        HINT: Use dist.all_reduce(tensor, op=dist.ReduceOp.SUM)
        HINT: Make sure to only reduce parameters that have gradients
        """
        pass  # TODO: Implement
    
    def train_step(self, batch_data, batch_labels):
        """
        Perform one training step.
        
        Args:
            batch_data: Input data for this batch
            batch_labels: Labels for this batch
        
        Returns:
            loss: The loss value for this batch
        
        TODO: Implement the training step
        
        STEPS:
        1. Move data and labels to device
        2. Zero gradients
        3. Forward pass
        4. Compute loss
        5. Backward pass
        6. All-reduce gradients
        7. Optimizer step
        8. Return loss value
        
        HINT: Use self.all_reduce_gradients() after backward()
        """
        pass  # TODO: Implement
    
    def broadcast_model(self):
        """
        Broadcast model parameters from rank 0 to all other ranks.
        This ensures all processes start with the same model weights.
        
        TODO: Implement model broadcasting
        
        STEPS:
        1. Iterate through all model parameters
        2. Use dist.broadcast() to send each parameter from rank 0
        
        HINT: dist.broadcast(tensor, src=0)
        """
        pass  # TODO: Implement


def setup_distributed(rank: int, world_size: int, backend: str = 'nccl'):
    """
    Initialize the distributed process group.
    
    Args:
        rank: Rank of current process
        world_size: Total number of processes
        backend: Backend to use ('nccl' for GPU, 'gloo' for CPU)
    
    TODO: Initialize the process group using dist.init_process_group()
    
    HINT: You may need to set environment variables:
    - MASTER_ADDR: Address of rank 0 (e.g., 'localhost')
    - MASTER_PORT: Port for communication (e.g., '12355')
    
    For testing on single machine, use:
    - backend='nccl' for GPU
    - init_method='tcp://localhost:12355'
    """
    pass  # TODO: Implement


def cleanup_distributed():
    """
    Clean up the distributed process group.
    
    TODO: Call dist.destroy_process_group()
    """
    pass  # TODO: Implement


# TESTING CODE
if __name__ == "__main__":
    print("Data Parallel Trainer Template")
    print("=" * 50)
    print("\nTo test this implementation:")
    print("1. Complete all TODO sections")
    print("2. Run with: python -m torch.distributed.launch --nproc_per_node=NUM_GPUS template_trainer.py")
    print("3. Or use: torchrun --nproc_per_node=NUM_GPUS template_trainer.py")
    print("\nKey concepts to implement:")
    print("- Gradient all-reduce (averaging gradients across GPUs)")
    print("- Model broadcasting (sync initial weights)")
    print("- Proper device placement")
    print("=" * 50)
