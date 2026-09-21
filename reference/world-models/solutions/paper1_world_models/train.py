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
from tqdm import tqdm

from vae import VAE
from rnn import MDNRNN, train_rnn_on_batch
from controller import Controller, CMAESOptimizer, evaluate_controller, evaluate_in_dream


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
        
        # Extract sequences from episodes
        for z, action, reward, done in zip(z_episodes, action_episodes, reward_episodes, done_episodes):
            episode_len = len(z)
            
            # Skip episodes that are too short
            if episode_len < seq_len:
                continue
            
            # Extract non-overlapping sequences
            for start_idx in range(0, episode_len - seq_len, seq_len // 2):
                end_idx = start_idx + seq_len
                if end_idx <= episode_len:
                    self.sequences.append({
                        'z': z[start_idx:end_idx],
                        'action': action[start_idx:end_idx],
                        'reward': reward[start_idx:end_idx],
                        'done': done[start_idx:end_idx]
                    })
    
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
    print(f"Collecting {num_episodes} episodes from {env_name}...")
    episodes = []
    
    env = gym.make(env_name)
    
    for episode_idx in tqdm(range(num_episodes), desc="Collecting episodes"):
        obs = env.reset()
        if isinstance(obs, tuple):
            obs = obs[0]  # Handle new gym API
        
        observations = []
        actions = []
        rewards = []
        dones = []
        
        for step in range(max_steps):
            # Store observation (normalize to [0, 1])
            if isinstance(obs, np.ndarray):
                obs_normalized = obs.astype(np.float32) / 255.0
                # Transpose to (C, H, W) format
                obs_normalized = np.transpose(obs_normalized, (2, 0, 1))
            else:
                obs_normalized = obs
            
            observations.append(obs_normalized)
            
            # Sample random action
            action = env.action_space.sample()
            actions.append(action)
            
            # Step environment
            result = env.step(action)
            if len(result) == 5:
                obs, reward, terminated, truncated, info = result
                done = terminated or truncated
            else:
                obs, reward, done, info = result
            
            rewards.append(reward)
            dones.append(float(done))
            
            if done:
                break
        
        # Store episode
        episodes.append({
            'observations': np.array(observations),
            'actions': np.array(actions),
            'rewards': np.array(rewards),
            'dones': np.array(dones)
        })
    
    env.close()
    print(f"Collected {len(episodes)} episodes")
    return episodes


def train_vae_phase(vae, episodes, num_epochs=10, batch_size=32, lr=1e-3,
                    save_path='checkpoints/vae.pt', device='cpu'):
    """
    Phase 1: Train VAE on collected observations.
    
    Args:
        vae: VAE model
        episodes: List of episode dictionaries
        num_epochs: Number of training epochs
        batch_size: Batch size
        lr: Learning rate
        save_path: Path to save trained model
        device: Device to train on
        
    Returns:
        vae: Trained VAE model
    """
    print("Training VAE...")
    print(f"  Episodes: {len(episodes)}")
    print(f"  Epochs: {num_epochs}")
    print(f"  Batch size: {batch_size}")
    
    vae = vae.to(device)
    
    # Extract all observations from episodes
    all_observations = []
    for episode in episodes:
        all_observations.append(episode['observations'])
    all_observations = np.concatenate(all_observations, axis=0)
    
    # Create dataset and dataloader
    obs_tensor = torch.FloatTensor(all_observations)
    dataset = torch.utils.data.TensorDataset(obs_tensor)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    
    # Setup optimizer
    optimizer = optim.Adam(vae.parameters(), lr=lr)
    
    # Training loop
    for epoch in range(num_epochs):
        vae.train()
        epoch_loss = 0
        epoch_recon_loss = 0
        epoch_kl_loss = 0
        
        for batch_idx, (batch,) in enumerate(dataloader):
            batch = batch.to(device)
            
            # Forward pass
            recon, mu, logvar = vae(batch)
            
            # Compute loss
            loss, recon_loss, kl_loss = vae.loss_function(recon, batch, mu, logvar)
            
            # Backward pass
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            epoch_loss += loss.item()
            epoch_recon_loss += recon_loss.item()
            epoch_kl_loss += kl_loss.item()
        
        # Print epoch statistics
        num_batches = len(dataloader)
        print(f"Epoch {epoch+1}/{num_epochs}: "
              f"Loss={epoch_loss/num_batches:.4f}, "
              f"Recon={epoch_recon_loss/num_batches:.4f}, "
              f"KL={epoch_kl_loss/num_batches:.4f}")
    
    # Save trained model
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    torch.save(vae.state_dict(), save_path)
    print(f"✓ VAE training complete. Saved to {save_path}")
    
    return vae


def encode_episodes_with_vae(vae, episodes, device='cpu', batch_size=128):
    """
    Encode all observations in episodes using trained VAE.
    
    Args:
        vae: Trained VAE model
        episodes: List of episode dictionaries
        device: Device to run on
        batch_size: Batch size for encoding
        
    Returns:
        z_episodes: List of encoded latent sequences
    """
    print("Encoding episodes with VAE...")
    vae.eval()
    vae = vae.to(device)
    z_episodes = []
    
    with torch.no_grad():
        for episode in tqdm(episodes, desc="Encoding"):
            observations = episode['observations']
            obs_tensor = torch.FloatTensor(observations).to(device)
            
            # Encode in batches
            z_list = []
            for i in range(0, len(obs_tensor), batch_size):
                batch = obs_tensor[i:i+batch_size]
                mu, _ = vae.encode(batch)
                z_list.append(mu.cpu().numpy())
            
            z_episode = np.concatenate(z_list, axis=0)
            z_episodes.append(z_episode)
    
    print(f"✓ Encoded {len(z_episodes)} episodes")
    return z_episodes


def train_rnn_phase(rnn, z_episodes, action_episodes, reward_episodes, done_episodes,
                    num_epochs=20, batch_size=32, seq_len=32, lr=1e-3,
                    save_path='checkpoints/rnn.pt', device='cpu'):
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
        device: Device to train on
        
    Returns:
        rnn: Trained RNN model
    """
    print("Training MDN-RNN...")
    print(f"  Episodes: {len(z_episodes)}")
    print(f"  Epochs: {num_epochs}")
    print(f"  Sequence length: {seq_len}")
    
    rnn = rnn.to(device)
    
    # Create sequence dataset
    dataset = SequenceDataset(z_episodes, action_episodes, reward_episodes, 
                             done_episodes, seq_len=seq_len)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    
    # Setup optimizer
    optimizer = optim.Adam(rnn.parameters(), lr=lr)
    
    # Training loop
    for epoch in range(num_epochs):
        rnn.train()
        epoch_loss = 0
        epoch_mdn_loss = 0
        epoch_reward_loss = 0
        epoch_done_loss = 0
        
        for batch in dataloader:
            z_seq = batch['z'].to(device)
            action_seq = batch['action'].to(device)
            reward_seq = batch['reward'].to(device)
            done_seq = batch['done'].to(device)
            
            # Train on batch
            losses = train_rnn_on_batch(rnn, optimizer, z_seq, action_seq, 
                                       reward_seq, done_seq)
            
            epoch_loss += losses['loss']
            epoch_mdn_loss += losses['mdn_loss']
            epoch_reward_loss += losses['reward_loss']
            epoch_done_loss += losses['done_loss']
        
        # Print epoch statistics
        num_batches = len(dataloader)
        print(f"Epoch {epoch+1}/{num_epochs}: "
              f"Loss={epoch_loss/num_batches:.4f}, "
              f"MDN={epoch_mdn_loss/num_batches:.4f}, "
              f"Reward={epoch_reward_loss/num_batches:.4f}, "
              f"Done={epoch_done_loss/num_batches:.4f}")
    
    # Save trained model
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    torch.save(rnn.state_dict(), save_path)
    print(f"✓ RNN training complete. Saved to {save_path}")
    
    return rnn


def train_controller_phase(controller, vae, rnn, env_name, use_dream=True,
                          generations=100, population_size=64,
                          save_path='checkpoints/controller.pt', device='cpu'):
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
        device: Device to run on
        
    Returns:
        controller: Optimized controller
    """
    print("Optimizing controller with CMA-ES...")
    print(f"  Use dream: {use_dream}")
    print(f"  Generations: {generations}")
    print(f"  Population size: {population_size}")
    
    vae = vae.to(device)
    rnn = rnn.to(device)
    controller = controller.to(device)
    
    # Create CMA-ES optimizer
    optimizer = CMAESOptimizer(controller, population_size=population_size, sigma=0.5)
    
    # Create environment (for real evaluation)
    if not use_dream:
        env = gym.make(env_name)
    
    best_fitness = -np.inf
    
    for generation in range(generations):
        # Sample candidate solutions
        candidates = optimizer.ask()
        
        # Evaluate each candidate
        fitnesses = []
        for candidate in candidates:
            # Set controller parameters
            controller.set_parameters_from_vector(candidate)
            
            # Evaluate fitness
            if use_dream:
                # Evaluate in learned world model
                fitness = evaluate_in_dream(controller, rnn, num_rollouts=16, 
                                          max_steps=1000)
            else:
                # Evaluate in real environment
                fitness, _ = evaluate_controller(controller, vae, rnn, env, 
                                                num_episodes=3, max_steps=1000)
            
            fitnesses.append(fitness)
        
        # Update optimizer with fitnesses
        optimizer.tell(candidates, fitnesses)
        
        # Track best fitness
        max_fitness = max(fitnesses)
        if max_fitness > best_fitness:
            best_fitness = max_fitness
        
        print(f"Generation {generation+1}/{generations}: "
              f"Max={max_fitness:.2f}, Best={best_fitness:.2f}, "
              f"Mean={np.mean(fitnesses):.2f}")
        
        # Check stopping criteria
        if optimizer.should_stop():
            print("Optimization converged.")
            break
    
    # Get best solution
    best_params, best_fitness = optimizer.result()
    controller.set_parameters_from_vector(best_params)
    
    # Save trained controller
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    torch.save(controller.state_dict(), save_path)
    print(f"✓ Controller optimization complete. Saved to {save_path}")
    print(f"  Best fitness: {best_fitness:.2f}")
    
    if not use_dream:
        env.close()
    
    return controller


def main(args):
    """
    Main training pipeline.
    """
    # Set random seeds for reproducibility
    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    
    # Set device
    device = torch.device('cuda' if torch.cuda.is_available() and args.use_gpu else 'cpu')
    print(f"Using device: {device}")
    
    # Create checkpoint directory
    os.makedirs(args.checkpoint_dir, exist_ok=True)
    
    # Step 1: Collect random episodes (if not already collected)
    if not os.path.exists(args.episodes_path):
        episodes = collect_random_episodes(args.env_name, args.num_episodes, 
                                          max_steps=args.max_steps)
        os.makedirs(os.path.dirname(args.episodes_path), exist_ok=True)
        torch.save(episodes, args.episodes_path)
    else:
        print(f"Loading episodes from {args.episodes_path}")
        episodes = torch.load(args.episodes_path)
        print(f"Loaded {len(episodes)} episodes")
    
    # Step 2: Train VAE
    vae = VAE(latent_dim=args.latent_dim)
    if not os.path.exists(args.vae_path):
        vae = train_vae_phase(vae, episodes, num_epochs=args.vae_epochs,
                             batch_size=args.batch_size, save_path=args.vae_path,
                             device=device)
    else:
        vae.load_state_dict(torch.load(args.vae_path, map_location=device))
        print(f"Loaded VAE from {args.vae_path}")
    
    # Step 3: Encode episodes
    z_episodes = encode_episodes_with_vae(vae, episodes, device=device)
    action_episodes = [ep['actions'] for ep in episodes]
    reward_episodes = [ep['rewards'] for ep in episodes]
    done_episodes = [ep['dones'] for ep in episodes]
    
    # Step 4: Train RNN
    rnn = MDNRNN(latent_dim=args.latent_dim, action_dim=args.action_dim,
                hidden_dim=args.rnn_hidden_dim, num_gaussians=args.num_gaussians)
    if not os.path.exists(args.rnn_path):
        rnn = train_rnn_phase(rnn, z_episodes, action_episodes, reward_episodes,
                             done_episodes, num_epochs=args.rnn_epochs,
                             seq_len=args.seq_len, save_path=args.rnn_path,
                             device=device)
    else:
        rnn.load_state_dict(torch.load(args.rnn_path, map_location=device))
        print(f"Loaded RNN from {args.rnn_path}")
    
    # Step 5: Optimize controller
    input_dim = args.latent_dim + args.rnn_hidden_dim
    controller = Controller(input_dim=input_dim, action_dim=args.action_dim)
    if not os.path.exists(args.controller_path) or args.retrain_controller:
        controller = train_controller_phase(
            controller, vae, rnn, args.env_name,
            use_dream=args.use_dream,
            generations=args.generations,
            population_size=args.population_size,
            save_path=args.controller_path,
            device=device
        )
    else:
        controller.load_state_dict(torch.load(args.controller_path, map_location=device))
        print(f"Loaded controller from {args.controller_path}")
    
    # Step 6: Final evaluation in real environment
    if args.final_eval:
        print("\nFinal evaluation in real environment...")
        env = gym.make(args.env_name)
        final_reward, final_steps = evaluate_controller(
            controller, vae, rnn, env, num_episodes=args.eval_episodes
        )
        env.close()
        
        print(f"\n{'='*50}")
        print(f"Final evaluation:")
        print(f"  Average reward: {final_reward:.2f}")
        print(f"  Average steps: {final_steps:.2f}")
        print(f"{'='*50}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Train World Models')
    
    # Environment
    parser.add_argument('--env_name', type=str, default='CarRacing-v2',
                       help='Gym environment name')
    parser.add_argument('--max_steps', type=int, default=1000,
                       help='Maximum steps per episode')
    
    # Data collection
    parser.add_argument('--num_episodes', type=int, default=1000,
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
    parser.add_argument('--num_gaussians', type=int, default=5,
                       help='Number of Gaussian components in MDN')
    parser.add_argument('--seq_len', type=int, default=32,
                       help='Sequence length for RNN training')
    
    # Training hyperparameters
    parser.add_argument('--vae_epochs', type=int, default=10,
                       help='Number of VAE training epochs')
    parser.add_argument('--rnn_epochs', type=int, default=20,
                       help='Number of RNN training epochs')
    parser.add_argument('--batch_size', type=int, default=32,
                       help='Batch size for training')
    parser.add_argument('--generations', type=int, default=100,
                       help='Number of CMA-ES generations')
    parser.add_argument('--population_size', type=int, default=64,
                       help='CMA-ES population size')
    
    # Optimization
    parser.add_argument('--use_dream', action='store_true',
                       help='Train controller in dream (learned model)')
    parser.add_argument('--use_gpu', action='store_true',
                       help='Use GPU if available')
    parser.add_argument('--seed', type=int, default=42,
                       help='Random seed')
    
    # Evaluation
    parser.add_argument('--final_eval', action='store_true',
                       help='Run final evaluation')
    parser.add_argument('--eval_episodes', type=int, default=10,
                       help='Number of episodes for final evaluation')
    parser.add_argument('--retrain_controller', action='store_true',
                       help='Retrain controller even if checkpoint exists')
    
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
