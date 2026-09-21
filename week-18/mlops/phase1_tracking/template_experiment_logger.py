"""
Template: Experiment Logger

GOAL: Build a simple experiment tracking system to log ML experiments.

GUIDELINES:
1. Track hyperparameters, metrics, and artifacts
2. Store experiments with unique IDs
3. Enable comparison between experiments
4. Support saving and loading experiment data

YOUR TASKS:
- Implement experiment logging to disk
- Track parameters, metrics, and artifacts
- Create comparison utilities
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, List
import pickle
from pathlib import Path


class Experiment:
    """
    Represents a single ML experiment.
    
    TODO: Implement experiment tracking
    """
    
    def __init__(self, experiment_name: str, run_id: str = None):
        """
        Initialize an experiment.
        
        Args:
            experiment_name: Name of the experiment
            run_id: Unique identifier for this run (generated if not provided)
        
        TODO: 
        1. Generate or use provided run_id
        2. Initialize storage for params, metrics, artifacts
        3. Record start time
        """
        self.experiment_name = experiment_name
        self.run_id = run_id or self._generate_run_id()
        self.start_time = datetime.now()
        
        # TODO: Initialize storage dictionaries
        # self.params = {}
        # self.metrics = {}
        # self.artifacts = {}
        
    def _generate_run_id(self) -> str:
        """
        Generate a unique run ID.
        
        TODO: Create a unique identifier
        HINT: Use timestamp + random string
        """
        pass  # TODO: Implement
    
    def log_param(self, key: str, value: Any):
        """
        Log a parameter (hyperparameter, config value).
        
        Args:
            key: Parameter name
            value: Parameter value
        
        TODO: Store the parameter
        HINT: Parameters are typically set once and don't change
        """
        pass  # TODO: Implement
    
    def log_params(self, params: Dict[str, Any]):
        """
        Log multiple parameters at once.
        
        Args:
            params: Dictionary of parameters
        
        TODO: Log all parameters from the dictionary
        """
        pass  # TODO: Implement
    
    def log_metric(self, key: str, value: float, step: int = None):
        """
        Log a metric value.
        
        Args:
            key: Metric name (e.g., 'train_loss', 'val_accuracy')
            value: Metric value
            step: Training step/epoch (optional)
        
        TODO: Store the metric
        HINT: Metrics can be logged multiple times (e.g., loss per epoch)
        HINT: Store as a list of (step, value) tuples
        """
        pass  # TODO: Implement
    
    def log_artifact(self, artifact_name: str, artifact_path: str):
        """
        Log an artifact (model file, plot, etc.).
        
        Args:
            artifact_name: Name for the artifact
            artifact_path: Path to the artifact file
        
        TODO: Copy or reference the artifact
        HINT: You might want to copy files to experiment directory
        """
        pass  # TODO: Implement


class ExperimentLogger:
    """
    Manages multiple experiments and provides comparison utilities.
    
    TODO: Implement experiment management
    """
    
    def __init__(self, base_path: str = "./experiments"):
        """
        Initialize the experiment logger.
        
        Args:
            base_path: Base directory for storing experiments
        
        TODO: 
        1. Create base directory if it doesn't exist
        2. Initialize tracking of active experiments
        """
        self.base_path = Path(base_path)
        # TODO: Create directory
        # TODO: Initialize experiment tracking
    
    def create_experiment(self, experiment_name: str) -> Experiment:
        """
        Create a new experiment.
        
        Args:
            experiment_name: Name of the experiment
        
        Returns:
            Experiment object
        
        TODO: 
        1. Create Experiment instance
        2. Create directory for experiment
        3. Return experiment object
        """
        pass  # TODO: Implement
    
    def save_experiment(self, experiment: Experiment):
        """
        Save experiment data to disk.
        
        Args:
            experiment: Experiment to save
        
        TODO: 
        1. Create experiment directory
        2. Save params, metrics, artifacts as JSON
        3. Include metadata (start_time, run_id, etc.)
        
        HINT: Structure the saved data for easy loading
        """
        pass  # TODO: Implement
    
    def load_experiment(self, run_id: str) -> Experiment:
        """
        Load an experiment from disk.
        
        Args:
            run_id: Run ID of the experiment to load
        
        Returns:
            Loaded Experiment object
        
        TODO: 
        1. Find experiment directory
        2. Load saved data
        3. Reconstruct Experiment object
        """
        pass  # TODO: Implement
    
    def list_experiments(self, experiment_name: str = None) -> List[Dict[str, Any]]:
        """
        List all experiments, optionally filtered by name.
        
        Args:
            experiment_name: Filter by experiment name (optional)
        
        Returns:
            List of experiment summaries
        
        TODO: 
        1. Scan experiment directories
        2. Load metadata for each
        3. Return as list of dictionaries
        """
        pass  # TODO: Implement
    
    def compare_experiments(self, run_ids: List[str]) -> Dict[str, Any]:
        """
        Compare multiple experiments.
        
        Args:
            run_ids: List of run IDs to compare
        
        Returns:
            Comparison data (params, metrics for each run)
        
        TODO: 
        1. Load all experiments
        2. Extract params and metrics
        3. Format for easy comparison
        
        HINT: Return a structure that's easy to display as a table
        """
        pass  # TODO: Implement


# TESTING CODE
if __name__ == "__main__":
    print("Experiment Logger Template")
    print("=" * 50)
    
    # Example usage (once implemented):
    print("\nExample usage:")
    print("""
    # Create logger
    logger = ExperimentLogger()
    
    # Start experiment
    exp = logger.create_experiment("mnist_training")
    
    # Log hyperparameters
    exp.log_params({
        "learning_rate": 0.001,
        "batch_size": 32,
        "epochs": 10
    })
    
    # Log metrics during training
    for epoch in range(10):
        train_loss = train_one_epoch()  # Your training code
        exp.log_metric("train_loss", train_loss, step=epoch)
        
        val_acc = validate()  # Your validation code
        exp.log_metric("val_accuracy", val_acc, step=epoch)
    
    # Save experiment
    logger.save_experiment(exp)
    
    # Compare experiments
    comparison = logger.compare_experiments(["run_1", "run_2", "run_3"])
    """)
    
    print("\n" + "=" * 50)
    print("Key features to implement:")
    print("- Unique run IDs")
    print("- Persistent storage (JSON files)")
    print("- Parameter and metric tracking")
    print("- Experiment comparison")
    print("=" * 50)
