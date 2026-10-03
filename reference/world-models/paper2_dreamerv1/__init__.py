"""
DreamerV1: Dream to Control - Learning Behaviors by Latent Imagination

This package implements DreamerV1, which learns behaviors by imagining
trajectories in a learned world model.

Paper: Hafner et al., 2020
https://arxiv.org/abs/1912.01603
"""

__version__ = "1.0.0"
__author__ = "Your Name"

# Import main components
try:
    from .rssm import RSSM
    from .networks import (
        ConvEncoder,
        ConvDecoder,
        RewardPredictor,
        ContinuePredictor,
        DenseDecoder
    )
    from .actor_critic import (
        Actor,
        Critic,
        compute_lambda_returns,
        compute_actor_loss,
        compute_critic_loss
    )
    from .buffer import ReplayBuffer, SimpleBuffer
    from .train import DreamerV1, train, evaluate
    
    __all__ = [
        'RSSM',
        'ConvEncoder',
        'ConvDecoder',
        'RewardPredictor',
        'ContinuePredictor',
        'DenseDecoder',
        'Actor',
        'Critic',
        'compute_lambda_returns',
        'compute_actor_loss',
        'compute_critic_loss',
        'ReplayBuffer',
        'SimpleBuffer',
        'DreamerV1',
        'train',
        'evaluate'
    ]
except ImportError:
    # Components not yet implemented or dependencies not installed
    __all__ = []
