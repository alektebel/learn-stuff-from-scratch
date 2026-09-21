"""
Training Script for World Models

This script orchestrates the complete training pipeline:
1. Train VAE on collected observations
2. Collect episodes using random policy, encode with VAE
3. Train MDN-RNN on encoded sequences
4. Optimize controller with CMA-ES (in dream or real environment)

Paper: World Models (Ha & Schmidhuber, 2018)
Section 3: Training Procedure
"""

import os
import argparse
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import gym

# Import our models (uncomment when files are ready)
# from vae import VAE
# from rnn import MDNRNN, train_rnn_on_batch
# from controller import Controller, CMAESOptimizer, evaluate_controller, evaluate_in_dream


class EpisodeDataset(Dataset):
    """
    Dataset for storing and loading episode sequences.
    
    Stores:
    - observations: Raw images from environment
    - actions: Actions taken
    - rewards: Rewards received
    - dones: Episode termination flags
    """
    
    def __init__(self, episodes):
        """
        Args:
            episodes: List of episode dictionaries, each containing:
                - observations: (T, H, W, C) array
                - actions: (T, action_dim) array
                - rewards: (T,) array
                - dones: (T,) array
        """
        self.episodes = episodes
    
    def __len__(self):
        return len(self.episodes)
    
    def __getitem__(self, idx):
        """
        Returns:
            Dictionary with torch tensors for one episode
        """
        episode = self.episodes[idx]
        return {
            'observations': torch.FloatTensor(episode['observations']),
            'actions': torch.FloatTensor(episode['actions']),
            'rewards': torch.FloatTensor(episode['rewards']),
            'dones': torch.FloatTensor(episode['dones'])
        }


class SequenceDataset(Dataset):
    """
    Dataset for MDN-RNN training with fixed-length sequences.
    
    Takes full episodes and chunks them into sequences of fixed length.
    This is necessary because RNN training requires consistent sequence lengths.
    """
    
    def __init__(self, z_episodes, action_episodes, reward_episodes, done_episodes, 
                 seq_len=32):
        """
        Args:
            z_episodes: List of latent sequences (num_episodes, T, latent_dim)
            action_episodes: List of action sequences
            reward_episodes: List of reward sequences
            done_episodes: List of done sequences
            seq_len: Length of sequences to extract
        """
        self.seq_len = seq_len
        self.sequences = []
        
        # TODO: Implement sequence extraction
        # Guidelines:
        # 1. For each episode:
        #    - If episode length < seq_len, skip it
        #    - Otherwise, extract all possible sequences of length seq_len
        #    - Can use sliding window or non-overlapping chunks
        # 
        # 2. Store as list of dictionaries:
        #    self.sequences.append({
        #        'z': z[i:i+seq_len],
        #        'action': action[i:i+seq_len],
        #        'reward': reward[i:i+seq_len],
        #        'done': done[i:i+seq_len]
        #    })
        
        pass
    
    def __len__(self):
        return len(self.sequences)
    
    def __getitem__(self, idx):
        seq = self.sequences[idx]
        return {
            'z': torch.FloatTensor(seq['z']),
            'action': torch.FloatTensor(seq['action']),
            'reward': torch.FloatTensor(seq['reward']).unsqueeze(-1),
            'done': torch.FloatTensor(seq['done']).unsqueeze(-1)
        }


def collect_random_episodes(env_name, num_episodes, max_steps=1000):
    """
    Collect episodes using random policy.
    
    Args:
        env_name: Gym environment name (e.g., 'CarRacing-v2')
        num_episodes: Number of episodes to collect
        max_steps: Maximum steps per episode
        
    Returns:
        episodes: List of episode dictionaries
    """
    # TODO: Implement episode collection
    # Guidelines:
    # 1. Create environment: env = gym.make(env_name)
    # 2. For each episode:
    #    a) Reset: obs = env.reset()
    #    b) Initialize lists for observations, actions, rewards, dones
    #    c) For each step:
    #       - Sample random action: action = env.action_space.sample()
    #       - Step: next_obs, reward, done, info = env.step(action)
    #       - Store (obs, action, reward, done)
    #       - Update obs = next_obs
    #       - Break if done or max_steps reached
    #    d) Store episode dict
    # 3. Return list of episodes
    # 
    # Note: For CarRacing, you may want to skip the first few frames
    # where the camera is zooming in.
    
    print(f"Collecting {num_episodes} episodes from {env_name}...")
    episodes = []
    
    # Your implementation here
    
    print(f"Collected {len(episodes)} episodes")
    return episodes


def train_vae_phase(vae, episodes, num_epochs=10, batch_size=32, lr=1e-3,
                    save_path='checkpoints/vae.pt'):
    """
    Phase 1: Train VAE on collected observations.
    
    Args:
        vae: VAE model
        episodes: List of episode dictionaries
        num_epochs: Number of training epochs
        batch_size: Batch size
        lr: Learning rate
        save_path: Path to save trained model
        
    Returns:
        vae: Trained VAE model
    """
    # TODO: Implement VAE training
    # Guidelines:
    # 1. Extract all observations from episodes and create dataset
    #    All observations: [episode['observations'] for episode in episodes]
    # 
    # 2. Create DataLoader for batching
    # 
    # 3. Setup optimizer (Adam is a good choice)
    # 
    # 4. Training loop:
    #    for epoch in range(num_epochs):
    #        for batch in dataloader:
    #            - Forward pass: recon, mu, logvar = vae(batch)
    #            - Compute loss: loss, recon_loss, kl_loss = vae.loss_function(...)
    #            - Backward and optimize
    #            - Log progress
    # 
    # 5. Save trained model: torch.save(vae.state_dict(), save_path)
    # 
    # 6. Return trained VAE
    
    print("Training VAE...")
    print(f"  Episodes: {len(episodes)}")
    print(f"  Epochs: {num_epochs}")
    print(f"  Batch size: {batch_size}")
    
    # Your implementation here
    
    print(f"✓ VAE training complete. Saved to {save_path}")
    return vae


def encode_episodes_with_vae(vae, episodes, device='cpu'):
    """
    Encode all observations in episodes using trained VAE.
    
    Args:
        vae: Trained VAE model
        episodes: List of episode dictionaries
        device: Device to run on
        
    Returns:
        z_episodes: List of encoded latent sequences
    """
    # TODO: Implement encoding
    # Guidelines:
    # 1. Set VAE to eval mode
    # 2. For each episode:
    #    a) Get observations
    #    b) Encode in batches: mu, logvar = vae.encode(obs_batch)
    #    c) Use mu (not sampling) for deterministic encoding
    #    d) Store encoded sequence
    # 3. Return list of encoded episodes
    
    print("Encoding episodes with VAE...")
    vae.eval()
    z_episodes = []
    
    # Your implementation here
    
    print(f"✓ Encoded {len(z_episodes)} episodes")
    return z_episodes


def train_rnn_phase(rnn, z_episodes, action_episodes, reward_episodes, done_episodes,
                    num_epochs=20, batch_size=32, seq_len=32, lr=1e-3,
                    save_path='checkpoints/rnn.pt'):
    """
    Phase 2: Train MDN-RNN on encoded sequences.
    
    Args:
        rnn: MDN-RNN model
        z_episodes: List of latent sequences
        action_episodes: List of action sequences
        reward_episodes: List of reward sequences
        done_episodes: List of done sequences
        num_epochs: Number of training epochs
        batch_size: Batch size
        seq_len: Sequence length for RNN
        lr: Learning rate
        save_path: Path to save trained model
        
    Returns:
        rnn: Trained RNN model
    """
    # TODO: Implement RNN training
    # Guidelines:
    # 1. Create SequenceDataset from episodes
    #    dataset = SequenceDataset(z_episodes, action_episodes, ...)
    # 
    # 2. Create DataLoader
    # 
    # 3. Setup optimizer
    # 
    # 4. Training loop:
    #    for epoch in range(num_epochs):
    #        for batch in dataloader:
    #            - Use train_rnn_on_batch() function from rnn.py
    #            - Log losses
    # 
    # 5. Save trained model
    # 
    # 6. Return trained RNN
    
    print("Training MDN-RNN...")
    print(f"  Episodes: {len(z_episodes)}")
    print(f"  Epochs: {num_epochs}")
    print(f"  Sequence length: {seq_len}")
    
    # Your implementation here
    
    print(f"✓ RNN training complete. Saved to {save_path}")
    return rnn


def train_controller_phase(controller, vae, rnn, env_name, use_dream=True,
                          generations=100, population_size=64,
                          save_path='checkpoints/controller.pt'):
    """
    Phase 3: Optimize controller with CMA-ES.
    
    Args:
        controller: Controller model
        vae: Trained VAE model
        rnn: Trained MDN-RNN model
        env_name: Environment name
        use_dream: If True, train in dream; if False, train in real env
        generations: Number of CMA-ES generations
        population_size: Population size for CMA-ES
        save_path: Path to save trained controller
        
    Returns:
        controller: Optimized controller
    """
    # TODO: Implement controller optimization
    # Guidelines:
    # 1. Create CMA-ES optimizer:
    #    from controller import CMAESOptimizer
    #    optimizer = CMAESOptimizer(controller, population_size=population_size)
    # 
    # 2. For each generation:
    #    a) Sample candidates: candidates = optimizer.ask()
    #    b) Evaluate each candidate:
    #       - Set controller parameters: controller.set_parameters_from_vector(candidate)
    #       - If use_dream:
    #           fitness = evaluate_in_dream(controller, rnn, ...)
    #         Else:
    #           fitness = evaluate_controller(controller, vae, rnn, env, ...)
    #    c) Update optimizer: optimizer.tell(candidates, fitnesses)
    #    d) Log best fitness
    #    e) Check stopping criteria: if optimizer.should_stop(): break
    # 
    # 3. Get best solution: best_params, best_fitness = optimizer.result()
    # 
    # 4. Set controller to best parameters and save
    # 
    # 5. Return optimized controller
    
    print("Optimizing controller with CMA-ES...")
    print(f"  Use dream: {use_dream}")
    print(f"  Generations: {generations}")
    print(f"  Population size: {population_size}")
    
    # Your implementation here
    
    print(f"✓ Controller optimization complete. Saved to {save_path}")
    return controller


def main(args):
    """
    Main training pipeline.
    """
    # Set random seeds for reproducibility
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    
    # Create checkpoint directory
    os.makedirs(args.checkpoint_dir, exist_ok=True)
    
    # TODO: Implement full training pipeline
    # Guidelines:
    # 
    # Step 1: Collect random episodes (if not already collected)
    # if not os.path.exists(args.episodes_path):
    #     episodes = collect_random_episodes(args.env_name, args.num_episodes)
    #     # Save episodes for reuse
    #     torch.save(episodes, args.episodes_path)
    # else:
    #     episodes = torch.load(args.episodes_path)
    # 
    # Step 2: Train VAE
    # vae = VAE(latent_dim=args.latent_dim)
    # if not os.path.exists(args.vae_path):
    #     vae = train_vae_phase(vae, episodes, num_epochs=args.vae_epochs,
    #                          save_path=args.vae_path)
    # else:
    #     vae.load_state_dict(torch.load(args.vae_path))
    #     print(f"Loaded VAE from {args.vae_path}")
    # 
    # Step 3: Encode episodes
    # z_episodes = encode_episodes_with_vae(vae, episodes)
    # action_episodes = [ep['actions'] for ep in episodes]
    # reward_episodes = [ep['rewards'] for ep in episodes]
    # done_episodes = [ep['dones'] for ep in episodes]
    # 
    # Step 4: Train RNN
    # rnn = MDNRNN(latent_dim=args.latent_dim, action_dim=args.action_dim)
    # if not os.path.exists(args.rnn_path):
    #     rnn = train_rnn_phase(rnn, z_episodes, action_episodes, reward_episodes,
    #                          done_episodes, num_epochs=args.rnn_epochs,
    #                          save_path=args.rnn_path)
    # else:
    #     rnn.load_state_dict(torch.load(args.rnn_path))
    #     print(f"Loaded RNN from {args.rnn_path}")
    # 
    # Step 5: Optimize controller
    # input_dim = args.latent_dim + args.rnn_hidden_dim
    # controller = Controller(input_dim=input_dim, action_dim=args.action_dim)
    # controller = train_controller_phase(
    #     controller, vae, rnn, args.env_name,
    #     use_dream=args.use_dream,
    #     generations=args.generations,
    #     save_path=args.controller_path
    # )
    # 
    # Step 6: Final evaluation in real environment
    # env = gym.make(args.env_name)
    # final_reward, final_steps = evaluate_controller(
    #     controller, vae, rnn, env, num_episodes=10
    # )
    # print(f"\n{'='*50}")
    # print(f"Final evaluation:")
    # print(f"  Average reward: {final_reward:.2f}")
    # print(f"  Average steps: {final_steps:.2f}")
    # print(f"{'='*50}")
    
    print("Training pipeline not implemented yet. Follow TODOs above.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Train World Models')
    
    # Environment
    parser.add_argument('--env_name', type=str, default='CarRacing-v2',
                       help='Gym environment name')
    
    # Data collection
    parser.add_argument('--num_episodes', type=int, default=10000,
                       help='Number of episodes to collect')
    parser.add_argument('--episodes_path', type=str, 
                       default='data/episodes.pt',
                       help='Path to save/load episodes')
    
    # Model dimensions
    parser.add_argument('--latent_dim', type=int, default=32,
                       help='VAE latent dimension')
    parser.add_argument('--action_dim', type=int, default=3,
                       help='Action space dimension')
    parser.add_argument('--rnn_hidden_dim', type=int, default=256,
                       help='RNN hidden dimension')
    
    # Training hyperparameters
    parser.add_argument('--vae_epochs', type=int, default=10,
                       help='Number of VAE training epochs')
    parser.add_argument('--rnn_epochs', type=int, default=20,
                       help='Number of RNN training epochs')
    parser.add_argument('--generations', type=int, default=100,
                       help='Number of CMA-ES generations')
    parser.add_argument('--population_size', type=int, default=64,
                       help='CMA-ES population size')
    
    # Optimization
    parser.add_argument('--use_dream', action='store_true',
                       help='Train controller in dream (learned model)')
    parser.add_argument('--seed', type=int, default=42,
                       help='Random seed')
    
    # Checkpoints
    parser.add_argument('--checkpoint_dir', type=str, default='checkpoints',
                       help='Directory for checkpoints')
    parser.add_argument('--vae_path', type=str, default='checkpoints/vae.pt',
                       help='Path to VAE checkpoint')
    parser.add_argument('--rnn_path', type=str, default='checkpoints/rnn.pt',
                       help='Path to RNN checkpoint')
    parser.add_argument('--controller_path', type=str, 
                       default='checkpoints/controller.pt',
                       help='Path to controller checkpoint')
    
    args = parser.parse_args()
    main(args)
