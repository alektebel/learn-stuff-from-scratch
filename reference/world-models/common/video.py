"""
Video Generation Utilities for World Models

This module provides utilities for saving environment rollouts and model
predictions as videos. Visualization is crucial for debugging and understanding
world model behavior.

Key Features:
- Save environment rollouts as videos
- Visualize model predictions (reconstructions, imaginations)
- Compare real vs predicted observations
- Support for various video formats
- Handle both RGB and grayscale images

Common use cases:
- Record agent behavior during evaluation
- Visualize VAE reconstructions
- Show world model predictions vs reality
- Create training progress videos

References:
- World Models (Ha & Schmidhuber, 2018): Video of agent in environment
- DreamerV1/V2: Visualization of imagined trajectories
"""

import numpy as np
import cv2
import os
from typing import List, Optional, Tuple


class VideoRecorder:
    """
    Record sequences of images as video files.
    
    Handles frame collection and video encoding. Supports various
    output formats and frame rates.
    
    Args:
        save_path: Path to save video file
        fps: Frames per second (default: 30)
        codec: FourCC codec code (default: 'mp4v')
        frame_size: Optional tuple (width, height) to resize frames
    """
    
    def __init__(
        self,
        save_path: str,
        fps: int = 30,
        codec: str = 'mp4v',
        frame_size: Optional[Tuple[int, int]] = None
    ):
        self.save_path = save_path
        self.fps = fps
        self.codec = codec
        self.frame_size = frame_size
        
        self.frames = []
        self.writer = None
        
        # Create directory if needed
        os.makedirs(os.path.dirname(save_path) if os.path.dirname(save_path) else '.', exist_ok=True)
    
    def add_frame(self, frame: np.ndarray):
        """
        Add a frame to the video.
        
        Args:
            frame: Image frame as numpy array
                  Can be (H, W), (H, W, C), or (C, H, W)
                  Values should be in [0, 1] or [0, 255]
        """
        # TODO: Implement frame addition
        # Guidelines:
        # 1. Normalize frame to [0, 255] uint8
        # 2. Handle different input formats (channels first/last, grayscale)
        # 3. Resize if frame_size is specified
        # 4. Convert grayscale to RGB if needed (cv2 requires RGB)
        # 5. Store processed frame
        
        # Convert to numpy array if needed
        if not isinstance(frame, np.ndarray):
            frame = np.array(frame)
        
        # Handle channels-first format (C, H, W) -> (H, W, C)
        if len(frame.shape) == 3 and frame.shape[0] in [1, 3, 4]:
            frame = np.transpose(frame, (1, 2, 0))
        
        # Normalize to [0, 255] if needed
        if frame.dtype == np.float32 or frame.dtype == np.float64:
            if frame.max() <= 1.0:
                frame = (frame * 255).astype(np.uint8)
            else:
                frame = frame.astype(np.uint8)
        elif frame.dtype != np.uint8:
            frame = frame.astype(np.uint8)
        
        # Convert grayscale to RGB
        if len(frame.shape) == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
        elif frame.shape[2] == 1:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
        
        # Resize if needed
        if self.frame_size is not None:
            frame = cv2.resize(frame, self.frame_size)
        
        # Convert RGB to BGR for OpenCV
        if frame.shape[2] == 3:
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        
        self.frames.append(frame)
    
    def save(self):
        """
        Save collected frames to video file.
        
        Encodes all frames into video format and writes to disk.
        """
        # TODO: Implement video saving
        # Guidelines:
        # 1. Check if frames exist
        # 2. Initialize VideoWriter with codec and fps
        # 3. Write all frames
        # 4. Release writer
        # 5. Handle errors gracefully
        
        if len(self.frames) == 0:
            print(f"Warning: No frames to save for {self.save_path}")
            return
        
        # Get frame dimensions from first frame
        height, width = self.frames[0].shape[:2]
        
        # Initialize video writer
        fourcc = cv2.VideoWriter_fourcc(*self.codec)
        self.writer = cv2.VideoWriter(self.save_path, fourcc, self.fps, (width, height))
        
        if not self.writer.isOpened():
            raise RuntimeError(f"Failed to open video writer for {self.save_path}")
        
        # Write all frames
        for frame in self.frames:
            self.writer.write(frame)
        
        # Release writer
        self.writer.release()
        
        print(f"Video saved to {self.save_path} ({len(self.frames)} frames, {self.fps} fps)")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - saves video."""
        self.save()
    
    def __len__(self):
        """Return number of frames collected."""
        return len(self.frames)


def save_video(
    frames: List[np.ndarray],
    path: str,
    fps: int = 30,
    codec: str = 'mp4v'
):
    """
    Save a list of frames as a video file.
    
    Convenience function for simple video saving.
    
    Args:
        frames: List of image frames
        path: Output file path
        fps: Frames per second
        codec: Video codec
        
    Example:
        >>> frames = [env.render() for _ in range(100)]
        >>> save_video(frames, 'rollout.mp4', fps=30)
    """
    # TODO: Implement video saving
    # Guidelines:
    # 1. Create VideoRecorder
    # 2. Add all frames
    # 3. Save video
    
    with VideoRecorder(path, fps=fps, codec=codec) as recorder:
        for frame in frames:
            recorder.add_frame(frame)


def save_comparison_video(
    real_frames: List[np.ndarray],
    pred_frames: List[np.ndarray],
    path: str,
    fps: int = 30,
    labels: Tuple[str, str] = ("Real", "Predicted")
):
    """
    Save side-by-side comparison of real and predicted frames.
    
    Useful for visualizing world model prediction quality.
    
    Args:
        real_frames: List of real observation frames
        pred_frames: List of predicted observation frames
        path: Output file path
        fps: Frames per second
        labels: Tuple of (real_label, pred_label) for display
        
    Example:
        >>> save_comparison_video(real_obs, reconstructed_obs, 'comparison.mp4')
    """
    # TODO: Implement comparison video
    # Guidelines:
    # 1. Check that frame lists have same length
    # 2. For each pair of frames:
    #    a. Normalize both to same size and format
    #    b. Add text labels
    #    c. Concatenate horizontally
    # 3. Save combined frames as video
    
    if len(real_frames) != len(pred_frames):
        raise ValueError(f"Frame count mismatch: {len(real_frames)} vs {len(pred_frames)}")
    
    combined_frames = []
    
    for real_frame, pred_frame in zip(real_frames, pred_frames):
        # Convert to numpy and normalize
        real_frame = np.array(real_frame)
        pred_frame = np.array(pred_frame)
        
        # Handle channels-first format
        if len(real_frame.shape) == 3 and real_frame.shape[0] in [1, 3, 4]:
            real_frame = np.transpose(real_frame, (1, 2, 0))
        if len(pred_frame.shape) == 3 and pred_frame.shape[0] in [1, 3, 4]:
            pred_frame = np.transpose(pred_frame, (1, 2, 0))
        
        # Normalize to [0, 255] uint8
        for frame_list, frame in [(real_frames, real_frame), (pred_frames, pred_frame)]:
            if frame.dtype in [np.float32, np.float64]:
                if frame.max() <= 1.0:
                    frame = (frame * 255).astype(np.uint8)
                else:
                    frame = frame.astype(np.uint8)
        
        # Ensure same size
        if real_frame.shape[:2] != pred_frame.shape[:2]:
            target_size = real_frame.shape[:2]
            pred_frame = cv2.resize(pred_frame, (target_size[1], target_size[0]))
        
        # Convert grayscale to RGB if needed
        if len(real_frame.shape) == 2:
            real_frame = cv2.cvtColor(real_frame, cv2.COLOR_GRAY2RGB)
        if len(pred_frame.shape) == 2:
            pred_frame = cv2.cvtColor(pred_frame, cv2.COLOR_GRAY2RGB)
        
        # Add text labels
        real_with_label = real_frame.copy()
        pred_with_label = pred_frame.copy()
        
        cv2.putText(real_with_label, labels[0], (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.putText(pred_with_label, labels[1], (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        
        # Concatenate horizontally
        combined = np.concatenate([real_with_label, pred_with_label], axis=1)
        combined_frames.append(combined)
    
    # Save combined video
    save_video(combined_frames, path, fps=fps)


def save_grid_video(
    frame_groups: List[List[np.ndarray]],
    path: str,
    fps: int = 30,
    grid_shape: Optional[Tuple[int, int]] = None,
    labels: Optional[List[str]] = None
):
    """
    Save multiple frame sequences in a grid layout.
    
    Useful for comparing multiple models or rollouts.
    
    Args:
        frame_groups: List of frame sequences, one per grid cell
        path: Output file path
        fps: Frames per second
        grid_shape: Optional (rows, cols) for grid layout
        labels: Optional labels for each group
        
    Example:
        >>> sequences = [rollout1, rollout2, rollout3, rollout4]
        >>> save_grid_video(sequences, 'grid.mp4', grid_shape=(2, 2))
    """
    # TODO: Implement grid video
    # Guidelines:
    # 1. Determine grid shape if not provided
    # 2. Check all sequences have same length
    # 3. For each time step:
    #    a. Normalize all frames to same size
    #    b. Add labels if provided
    #    c. Arrange in grid layout
    # 4. Save combined frames as video
    
    if len(frame_groups) == 0:
        raise ValueError("No frame groups provided")
    
    # Check all sequences have same length
    seq_len = len(frame_groups[0])
    for i, group in enumerate(frame_groups):
        if len(group) != seq_len:
            raise ValueError(f"Sequence {i} has length {len(group)}, expected {seq_len}")
    
    # Determine grid shape
    if grid_shape is None:
        n = len(frame_groups)
        cols = int(np.ceil(np.sqrt(n)))
        rows = int(np.ceil(n / cols))
        grid_shape = (rows, cols)
    
    rows, cols = grid_shape
    if rows * cols < len(frame_groups):
        raise ValueError(f"Grid shape {grid_shape} too small for {len(frame_groups)} groups")
    
    combined_frames = []
    
    for t in range(seq_len):
        # Collect frames at time t
        frames_t = [group[t] for group in frame_groups]
        
        # Normalize all frames
        normalized = []
        max_h, max_w = 0, 0
        
        for frame in frames_t:
            frame = np.array(frame)
            
            # Handle channels-first
            if len(frame.shape) == 3 and frame.shape[0] in [1, 3, 4]:
                frame = np.transpose(frame, (1, 2, 0))
            
            # Normalize to uint8
            if frame.dtype in [np.float32, np.float64]:
                if frame.max() <= 1.0:
                    frame = (frame * 255).astype(np.uint8)
                else:
                    frame = frame.astype(np.uint8)
            
            # Convert grayscale to RGB
            if len(frame.shape) == 2:
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
            elif frame.shape[2] == 1:
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
            
            normalized.append(frame)
            max_h = max(max_h, frame.shape[0])
            max_w = max(max_w, frame.shape[1])
        
        # Resize all to same size and add labels
        resized = []
        for i, frame in enumerate(normalized):
            frame = cv2.resize(frame, (max_w, max_h))
            
            if labels is not None and i < len(labels):
                cv2.putText(frame, labels[i], (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            
            resized.append(frame)
        
        # Pad with blank frames if needed
        while len(resized) < rows * cols:
            blank = np.zeros((max_h, max_w, 3), dtype=np.uint8)
            resized.append(blank)
        
        # Arrange in grid
        grid_rows = []
        for r in range(rows):
            row_frames = resized[r * cols:(r + 1) * cols]
            grid_row = np.concatenate(row_frames, axis=1)
            grid_rows.append(grid_row)
        
        grid_frame = np.concatenate(grid_rows, axis=0)
        combined_frames.append(grid_frame)
    
    # Save grid video
    save_video(combined_frames, path, fps=fps)


def record_episode(env, agent, max_steps=1000, render_mode='rgb_array'):
    """
    Record a full episode with an agent.
    
    Args:
        env: Gym environment
        agent: Agent with act(obs) method
        max_steps: Maximum episode length
        render_mode: Render mode for environment
        
    Returns:
        frames: List of rendered frames
        episode_return: Total episode return
        episode_length: Episode length
        
    Example:
        >>> frames, ret, length = record_episode(env, agent)
        >>> save_video(frames, f'episode_return_{ret:.0f}.mp4')
    """
    # TODO: Implement episode recording
    # Guidelines:
    # 1. Reset environment
    # 2. Run episode loop:
    #    a. Get action from agent
    #    b. Step environment
    #    c. Render and collect frame
    #    d. Track return and length
    # 3. Return frames and statistics
    
    frames = []
    obs = env.reset()
    done = False
    episode_return = 0.0
    episode_length = 0
    
    while not done and episode_length < max_steps:
        # Render frame
        if hasattr(env, 'render'):
            frame = env.render(mode=render_mode)
            if frame is not None:
                frames.append(frame)
        
        # Get action from agent
        if hasattr(agent, 'act'):
            action = agent.act(obs)
        elif callable(agent):
            action = agent(obs)
        else:
            raise ValueError("Agent must have act() method or be callable")
        
        # Step environment
        obs, reward, done, info = env.step(action)
        episode_return += reward
        episode_length += 1
    
    return frames, episode_return, episode_length


def visualize_reconstructions(
    original: np.ndarray,
    reconstructed: np.ndarray,
    save_path: str,
    n_samples: int = 8
):
    """
    Visualize VAE or autoencoder reconstructions.
    
    Creates a grid showing original images and their reconstructions.
    
    Args:
        original: Original images (B, C, H, W) or (B, H, W, C)
        reconstructed: Reconstructed images (same shape as original)
        save_path: Path to save visualization
        n_samples: Number of samples to visualize
        
    Example:
        >>> visualize_reconstructions(test_obs, vae_output, 'recon.png')
    """
    # TODO: Implement reconstruction visualization
    # Guidelines:
    # 1. Select n_samples from batch
    # 2. Interleave original and reconstructed (orig1, recon1, orig2, recon2, ...)
    # 3. Create grid image
    # 4. Save as image file
    
    import matplotlib.pyplot as plt
    
    n_samples = min(n_samples, len(original))
    
    # Convert to numpy if needed
    original = np.array(original)
    reconstructed = np.array(reconstructed)
    
    # Handle channels-first format
    if original.shape[1] in [1, 3, 4]:
        original = np.transpose(original, (0, 2, 3, 1))
        reconstructed = np.transpose(reconstructed, (0, 2, 3, 1))
    
    # Normalize to [0, 1] for display
    if original.max() > 1.0:
        original = original / 255.0
    if reconstructed.max() > 1.0:
        reconstructed = reconstructed / 255.0
    
    # Create figure
    fig, axes = plt.subplots(2, n_samples, figsize=(n_samples * 2, 4))
    
    for i in range(n_samples):
        # Original
        axes[0, i].imshow(original[i].squeeze(), cmap='gray' if original.shape[-1] == 1 else None)
        axes[0, i].axis('off')
        if i == 0:
            axes[0, i].set_title('Original', fontsize=10)
        
        # Reconstructed
        axes[1, i].imshow(reconstructed[i].squeeze(), cmap='gray' if reconstructed.shape[-1] == 1 else None)
        axes[1, i].axis('off')
        if i == 0:
            axes[1, i].set_title('Reconstructed', fontsize=10)
    
    plt.tight_layout()
    plt.savefig(save_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    print(f"Reconstruction visualization saved to {save_path}")


# Example usage and testing
if __name__ == "__main__":
    print("Testing video utilities...")
    
    # Test VideoRecorder
    print("\n=== Testing VideoRecorder ===")
    try:
        with VideoRecorder('/tmp/test_video.mp4', fps=10) as recorder:
            # Generate test frames
            for i in range(30):
                frame = np.random.rand(64, 64, 3).astype(np.float32)
                recorder.add_frame(frame)
        print(f"✓ VideoRecorder created video with 30 frames")
    except Exception as e:
        print(f"✗ VideoRecorder error: {e}")
    
    # Test save_video
    print("\n=== Testing save_video ===")
    try:
        frames = [np.random.rand(32, 32, 3) for _ in range(20)]
        save_video(frames, '/tmp/test_save_video.mp4', fps=10)
        print(f"✓ save_video created video with 20 frames")
    except Exception as e:
        print(f"✗ save_video error: {e}")
    
    # Test save_comparison_video
    print("\n=== Testing save_comparison_video ===")
    try:
        real = [np.random.rand(32, 32, 3) for _ in range(15)]
        pred = [np.random.rand(32, 32, 3) for _ in range(15)]
        save_comparison_video(real, pred, '/tmp/test_comparison.mp4', fps=10)
        print(f"✓ save_comparison_video created comparison video")
    except Exception as e:
        print(f"✗ save_comparison_video error: {e}")
    
    # Test save_grid_video
    print("\n=== Testing save_grid_video ===")
    try:
        groups = [
            [np.random.rand(32, 32, 3) for _ in range(10)],
            [np.random.rand(32, 32, 3) for _ in range(10)],
            [np.random.rand(32, 32, 3) for _ in range(10)],
            [np.random.rand(32, 32, 3) for _ in range(10)],
        ]
        save_grid_video(groups, '/tmp/test_grid.mp4', fps=10, 
                       grid_shape=(2, 2), labels=['A', 'B', 'C', 'D'])
        print(f"✓ save_grid_video created 2x2 grid video")
    except Exception as e:
        print(f"✗ save_grid_video error: {e}")
    
    print("\nAll tests completed!")
