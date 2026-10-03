"""
Evaluation and Visualization for World Models

This script provides tools for:
1. Loading trained models
2. Evaluating performance in environment
3. Generating rollout videos
4. Visualizing VAE reconstructions
5. Analyzing RNN predictions

Paper: World Models (Ha & Schmidhuber, 2018)
Section 4: Experiments
"""

import os
import argparse
import numpy as np
import torch
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, FFMpegWriter
import gym
from tqdm import tqdm

from vae import VAE
from rnn import MDNRNN
from controller import Controller


def load_models(vae_path, rnn_path, controller_path, device='cpu',
                latent_dim=32, action_dim=3, hidden_dim=256, num_gaussians=5):
    """
    Load all trained models from checkpoints.
    
    Args:
        vae_path: Path to VAE checkpoint
        rnn_path: Path to RNN checkpoint
        controller_path: Path to controller checkpoint
        device: Device to load models on
        latent_dim: VAE latent dimension
        action_dim: Action dimension
        hidden_dim: RNN hidden dimension
        num_gaussians: Number of Gaussian components
        
    Returns:
        vae: Loaded VAE model
        rnn: Loaded RNN model
        controller: Loaded controller model
    """
    print("Loading models...")
    print(f"  VAE: {vae_path}")
    print(f"  RNN: {rnn_path}")
    print(f"  Controller: {controller_path}")
    
    # Load VAE
    vae = VAE(latent_dim=latent_dim)
    vae.load_state_dict(torch.load(vae_path, map_location=device))
    vae.to(device)
    vae.eval()
    
    # Load RNN
    rnn = MDNRNN(latent_dim=latent_dim, action_dim=action_dim, 
                hidden_dim=hidden_dim, num_gaussians=num_gaussians)
    rnn.load_state_dict(torch.load(rnn_path, map_location=device))
    rnn.to(device)
    rnn.eval()
    
    # Load Controller
    input_dim = latent_dim + hidden_dim
    controller = Controller(input_dim=input_dim, action_dim=action_dim)
    controller.load_state_dict(torch.load(controller_path, map_location=device))
    controller.to(device)
    controller.eval()
    
    print("✓ Models loaded successfully")
    return vae, rnn, controller


def rollout_episode(vae, rnn, controller, env, max_steps=1000, 
                   render=False, device='cpu'):
    """
    Rollout a single episode using trained models.
    
    Args:
        vae: Trained VAE model
        rnn: Trained RNN model
        controller: Trained controller model
        env: Gym environment
        max_steps: Maximum steps
        render: Whether to render environment
        device: Device to run on
        
    Returns:
        Dictionary containing trajectory data
    """
    observations = []
    actions = []
    rewards = []
    reconstructions = []
    latents = []
    
    obs = env.reset()
    if isinstance(obs, tuple):
        obs = obs[0]
    
    hidden = None
    total_reward = 0
    
    with torch.no_grad():
        for step in range(max_steps):
            if render:
                env.render()
            
            # Preprocess observation
            if isinstance(obs, np.ndarray):
                obs_tensor = torch.FloatTensor(obs).permute(2, 0, 1).unsqueeze(0) / 255.0
            else:
                obs_tensor = obs.unsqueeze(0)
            obs_tensor = obs_tensor.to(device)
            
            # Encode observation
            mu, _ = vae.encode(obs_tensor)
            z = mu  # Use mean for deterministic encoding
            
            # Get reconstruction
            recon = vae.decode(z)
            recon_np = recon.squeeze(0).cpu().permute(1, 2, 0).numpy()
            
            # Get RNN hidden state
            if hidden is not None:
                h = hidden[0].squeeze(0)
            else:
                h = torch.zeros(1, rnn.hidden_dim).to(device)
            
            # Get action from controller
            action = controller(z, h)
            action_np = action.squeeze(0).cpu().numpy()
            
            # Store data
            observations.append(obs if isinstance(obs, np.ndarray) else obs.cpu().numpy())
            actions.append(action_np)
            reconstructions.append(recon_np)
            latents.append(z.squeeze(0).cpu().numpy())
            
            # Step environment
            result = env.step(action_np)
            if len(result) == 5:
                obs, reward, terminated, truncated, info = result
                done = terminated or truncated
            else:
                obs, reward, done, info = result
            
            rewards.append(reward)
            total_reward += reward
            
            # Update RNN hidden state
            action_tensor = torch.FloatTensor(action_np).unsqueeze(0).unsqueeze(0).to(device)
            z_expanded = z.unsqueeze(1)
            outputs = rnn(z_expanded, action_tensor, hidden)
            hidden = outputs['hidden']
            
            if done:
                break
    
    trajectory = {
        'observations': observations,
        'actions': actions,
        'rewards': rewards,
        'reconstructions': reconstructions,
        'latents': np.array(latents),
        'total_reward': total_reward,
        'episode_length': len(observations)
    }
    
    return trajectory


def evaluate_multiple_episodes(vae, rnn, controller, env_name, num_episodes=10,
                               max_steps=1000, device='cpu'):
    """
    Evaluate models over multiple episodes.
    
    Args:
        vae: Trained VAE model
        rnn: Trained RNN model
        controller: Trained controller model
        env_name: Environment name
        num_episodes: Number of episodes to run
        max_steps: Maximum steps per episode
        device: Device to run on
        
    Returns:
        Dictionary with statistics
    """
    print(f"Evaluating over {num_episodes} episodes...")
    
    env = gym.make(env_name)
    all_rewards = []
    all_lengths = []
    
    for episode in tqdm(range(num_episodes), desc="Evaluating"):
        trajectory = rollout_episode(vae, rnn, controller, env, max_steps, 
                                    render=False, device=device)
        all_rewards.append(trajectory['total_reward'])
        all_lengths.append(trajectory['episode_length'])
    
    env.close()
    
    results = {
        'mean_reward': np.mean(all_rewards),
        'std_reward': np.std(all_rewards),
        'mean_length': np.mean(all_lengths),
        'all_rewards': all_rewards
    }
    
    print(f"  Mean reward: {results['mean_reward']:.2f} ± {results['std_reward']:.2f}")
    print(f"  Mean length: {results['mean_length']:.2f}")
    
    return results


def visualize_reconstruction(observations, reconstructions, num_samples=5,
                            save_path='visualizations/reconstructions.png'):
    """
    Visualize VAE reconstructions alongside original observations.
    
    Args:
        observations: List/array of original observations
        reconstructions: List/array of VAE reconstructions
        num_samples: Number of samples to visualize
        save_path: Path to save figure
    """
    print(f"Creating reconstruction visualization...")
    
    # Select evenly spaced samples
    indices = np.linspace(0, len(observations) - 1, num_samples, dtype=int)
    
    fig, axes = plt.subplots(2, num_samples, figsize=(15, 6))
    
    for i, idx in enumerate(indices):
        # Original
        obs = observations[idx]
        if obs.shape[0] == 3:  # CHW format
            obs = np.transpose(obs, (1, 2, 0))
        axes[0, i].imshow(obs)
        axes[0, i].set_title('Original')
        axes[0, i].axis('off')
        
        # Reconstruction
        recon = reconstructions[idx]
        axes[1, i].imshow(recon)
        axes[1, i].set_title('Reconstruction')
        axes[1, i].axis('off')
    
    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"✓ Saved to {save_path}")


def visualize_latent_space(latents, rewards=None, save_path='visualizations/latent_space.png'):
    """
    Visualize latent space using PCA dimensionality reduction.
    
    Args:
        latents: Array of latent vectors (N, latent_dim)
        rewards: Optional array of rewards for coloring points
        save_path: Path to save figure
    """
    print(f"Creating latent space visualization...")
    
    from sklearn.decomposition import PCA
    
    # Apply PCA
    pca = PCA(n_components=2)
    latents_2d = pca.fit_transform(latents)
    
    # Create scatter plot
    fig, ax = plt.subplots(figsize=(10, 8))
    
    if rewards is not None:
        scatter = ax.scatter(latents_2d[:, 0], latents_2d[:, 1], 
                           c=rewards, cmap='viridis', alpha=0.6)
        plt.colorbar(scatter, label='Reward')
    else:
        ax.scatter(latents_2d[:, 0], latents_2d[:, 1], alpha=0.6)
    
    ax.set_xlabel('PC 1')
    ax.set_ylabel('PC 2')
    ax.set_title('Latent Space Visualization (PCA)')
    ax.grid(True, alpha=0.3)
    
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"✓ Saved to {save_path}")


def create_rollout_video(observations, reconstructions, actions, rewards,
                         save_path='visualizations/rollout.mp4', fps=30):
    """
    Create a video showing episode rollout with visualizations.
    
    Args:
        observations: List of observations
        reconstructions: List of VAE reconstructions
        actions: List of actions
        rewards: List of rewards
        save_path: Path to save video
        fps: Frames per second
    """
    print(f"Creating rollout video...")
    
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
    
    cumulative_rewards = np.cumsum(rewards)
    
    def update(frame):
        ax1.clear()
        ax2.clear()
        
        # Original observation
        obs = observations[frame]
        if obs.shape[0] == 3:  # CHW format
            obs = np.transpose(obs, (1, 2, 0))
        ax1.imshow(obs)
        ax1.set_title('Original Observation')
        ax1.axis('off')
        
        # Reconstruction
        recon = reconstructions[frame]
        ax2.imshow(recon)
        ax2.set_title('VAE Reconstruction')
        ax2.axis('off')
        
        # Overall title with stats
        action_str = f"[{actions[frame][0]:.2f}, {actions[frame][1]:.2f}, {actions[frame][2]:.2f}]"
        fig.suptitle(f'Step {frame} | Action: {action_str} | Total Reward: {cumulative_rewards[frame]:.2f}',
                    fontsize=12)
    
    anim = FuncAnimation(fig, update, frames=len(observations), interval=1000//fps)
    
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    writer = FFMpegWriter(fps=fps)
    anim.save(save_path, writer=writer)
    plt.close()
    
    print(f"✓ Saved to {save_path}")


def analyze_rnn_predictions(vae, rnn, env_name, num_steps=100, device='cpu',
                           save_path='visualizations/rnn_predictions.png'):
    """
    Analyze RNN prediction accuracy by comparing predicted vs actual next states.
    
    Args:
        vae: Trained VAE model
        rnn: Trained RNN model
        env_name: Environment name
        num_steps: Number of steps to analyze
        device: Device to run on
        save_path: Path to save analysis figure
    """
    print(f"Analyzing RNN predictions over {num_steps} steps...")
    
    env = gym.make(env_name)
    obs = env.reset()
    if isinstance(obs, tuple):
        obs = obs[0]
    
    prediction_errors = []
    hidden = None
    
    with torch.no_grad():
        for step in range(num_steps):
            # Encode current observation
            if isinstance(obs, np.ndarray):
                obs_tensor = torch.FloatTensor(obs).permute(2, 0, 1).unsqueeze(0) / 255.0
            else:
                obs_tensor = obs.unsqueeze(0)
            obs_tensor = obs_tensor.to(device)
            
            mu_curr, _ = vae.encode(obs_tensor)
            z_curr = mu_curr
            
            # Random action
            action = env.action_space.sample()
            action_tensor = torch.FloatTensor(action).unsqueeze(0).unsqueeze(0).to(device)
            
            # Step environment
            result = env.step(action)
            if len(result) == 5:
                obs, reward, terminated, truncated, info = result
                done = terminated or truncated
            else:
                obs, reward, done, info = result
            
            if done:
                break
            
            # Encode next observation
            if isinstance(obs, np.ndarray):
                obs_next_tensor = torch.FloatTensor(obs).permute(2, 0, 1).unsqueeze(0) / 255.0
            else:
                obs_next_tensor = obs.unsqueeze(0)
            obs_next_tensor = obs_next_tensor.to(device)
            
            mu_next_true, _ = vae.encode(obs_next_tensor)
            z_next_true = mu_next_true
            
            # Predict next state with RNN
            z_curr_expanded = z_curr.unsqueeze(1)
            outputs = rnn(z_curr_expanded, action_tensor, hidden)
            
            # Get predicted next state (use mean of most likely Gaussian)
            pi = outputs['pi'].squeeze(1)
            mu = outputs['mu'].squeeze(1)
            
            # Use mixture mean as prediction
            z_next_pred = (pi.unsqueeze(-1) * mu).sum(dim=1)
            
            # Compute prediction error
            error = torch.mean((z_next_pred - z_next_true) ** 2).item()
            prediction_errors.append(error)
            
            # Update hidden state
            hidden = outputs['hidden']
    
    env.close()
    
    # Create visualization
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    
    # Error over time
    ax1.plot(prediction_errors)
    ax1.set_xlabel('Step')
    ax1.set_ylabel('MSE')
    ax1.set_title('RNN Prediction Error Over Time')
    ax1.grid(True, alpha=0.3)
    
    # Error distribution
    ax2.hist(prediction_errors, bins=30, edgecolor='black')
    ax2.set_xlabel('MSE')
    ax2.set_ylabel('Frequency')
    ax2.set_title('Distribution of Prediction Errors')
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"✓ Saved to {save_path}")
    print(f"  Mean prediction error: {np.mean(prediction_errors):.6f}")
    print(f"  Std prediction error: {np.std(prediction_errors):.6f}")


def dream_rollout(rnn, controller, initial_z, num_steps=1000, device='cpu'):
    """
    Rollout in dream (using only the learned world model).
    
    Args:
        rnn: Trained RNN model
        controller: Trained controller model
        initial_z: Initial latent state (latent_dim,)
        num_steps: Number of steps to imagine
        device: Device to run on
        
    Returns:
        Dictionary containing dream trajectory
    """
    print(f"Dreaming for {num_steps} steps...")
    
    latents = []
    actions = []
    rewards = []
    dones = []
    
    z = initial_z.unsqueeze(0).to(device)  # Add batch dimension
    hidden = None
    total_reward = 0
    
    with torch.no_grad():
        for step in range(num_steps):
            # Get hidden state
            if hidden is not None:
                h = hidden[0].squeeze(0)
            else:
                h = torch.zeros(1, rnn.hidden_dim).to(device)
            
            # Get action
            action = controller(z, h)
            
            # Predict next state
            z_expanded = z.unsqueeze(1)
            action_expanded = action.unsqueeze(1)
            
            outputs = rnn(z_expanded, action_expanded, hidden)
            
            # Sample next latent state
            pi = outputs['pi'].squeeze(1)
            mu = outputs['mu'].squeeze(1)
            sigma = outputs['sigma'].squeeze(1)
            
            z_next = rnn.sample(pi, mu, sigma)
            
            # Get predictions
            reward = outputs['reward'].squeeze().item()
            done = outputs['done'].squeeze().item() > 0.5
            
            # Store
            latents.append(z.squeeze(0).cpu().numpy())
            actions.append(action.squeeze(0).cpu().numpy())
            rewards.append(reward)
            dones.append(done)
            
            total_reward += reward
            
            # Update
            hidden = outputs['hidden']
            z = z_next
            
            if done:
                break
    
    dream_trajectory = {
        'latents': np.array(latents),
        'actions': np.array(actions),
        'rewards': np.array(rewards),
        'dones': np.array(dones),
        'total_reward': total_reward
    }
    
    print(f"  Dream total reward: {total_reward:.2f}")
    print(f"  Dream length: {len(latents)}")
    
    return dream_trajectory


def main(args):
    """
    Main evaluation script.
    """
    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Set device
    device = torch.device('cuda' if torch.cuda.is_available() and args.use_gpu else 'cpu')
    print(f"Using device: {device}")
    
    # Load models
    vae, rnn, controller = load_models(
        args.vae_path, args.rnn_path, args.controller_path,
        device=device, latent_dim=args.latent_dim,
        action_dim=args.action_dim, hidden_dim=args.hidden_dim,
        num_gaussians=args.num_gaussians
    )
    
    # Evaluate performance
    results = evaluate_multiple_episodes(
        vae, rnn, controller, args.env_name,
        num_episodes=args.num_episodes, device=device
    )
    
    # Create visualizations
    if args.visualize:
        print("\nCreating visualizations...")
        
        # Rollout single episode for detailed visualization
        env = gym.make(args.env_name)
        trajectory = rollout_episode(vae, rnn, controller, env, device=device)
        env.close()
        
        # Reconstruction comparison
        visualize_reconstruction(
            trajectory['observations'],
            trajectory['reconstructions'],
            save_path=os.path.join(args.output_dir, 'reconstructions.png')
        )
        
        # Latent space
        visualize_latent_space(
            trajectory['latents'],
            rewards=np.array(trajectory['rewards']),
            save_path=os.path.join(args.output_dir, 'latent_space.png')
        )
        
        # Rollout video
        if args.create_video:
            try:
                create_rollout_video(
                    trajectory['observations'],
                    trajectory['reconstructions'],
                    trajectory['actions'],
                    trajectory['rewards'],
                    save_path=os.path.join(args.output_dir, 'rollout.mp4')
                )
            except Exception as e:
                print(f"  Warning: Video creation failed: {e}")
        
        # RNN prediction analysis
        analyze_rnn_predictions(
            vae, rnn, args.env_name, device=device,
            save_path=os.path.join(args.output_dir, 'rnn_predictions.png')
        )
        
        # Dream rollout
        if args.dream_rollout:
            initial_z = torch.FloatTensor(trajectory['latents'][0])
            dream_traj = dream_rollout(rnn, controller, initial_z, device=device)
    
    # Print summary
    print("\n" + "="*50)
    print("Evaluation Summary")
    print("="*50)
    print(f"Mean reward: {results['mean_reward']:.2f} ± {results['std_reward']:.2f}")
    print(f"Mean length: {results['mean_length']:.2f}")
    print(f"Visualizations saved to: {args.output_dir}")
    print("="*50)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Evaluate World Models')
    
    # Model paths
    parser.add_argument('--vae_path', type=str, required=True,
                       help='Path to trained VAE checkpoint')
    parser.add_argument('--rnn_path', type=str, required=True,
                       help='Path to trained RNN checkpoint')
    parser.add_argument('--controller_path', type=str, required=True,
                       help='Path to trained controller checkpoint')
    
    # Environment
    parser.add_argument('--env_name', type=str, default='CarRacing-v2',
                       help='Gym environment name')
    
    # Model dimensions
    parser.add_argument('--latent_dim', type=int, default=32,
                       help='VAE latent dimension')
    parser.add_argument('--action_dim', type=int, default=3,
                       help='Action space dimension')
    parser.add_argument('--hidden_dim', type=int, default=256,
                       help='RNN hidden dimension')
    parser.add_argument('--num_gaussians', type=int, default=5,
                       help='Number of Gaussian components')
    
    # Evaluation settings
    parser.add_argument('--num_episodes', type=int, default=10,
                       help='Number of episodes for evaluation')
    parser.add_argument('--max_steps', type=int, default=1000,
                       help='Maximum steps per episode')
    
    # Visualization
    parser.add_argument('--visualize', action='store_true',
                       help='Create visualizations')
    parser.add_argument('--create_video', action='store_true',
                       help='Create rollout video (requires ffmpeg)')
    parser.add_argument('--dream_rollout', action='store_true',
                       help='Perform dream rollout')
    parser.add_argument('--output_dir', type=str, default='visualizations',
                       help='Directory for outputs')
    
    # Device
    parser.add_argument('--use_gpu', action='store_true',
                       help='Use GPU if available')
    
    args = parser.parse_args()
    main(args)
