"""
Template: Model Server with REST API

GOAL: Build a basic REST API server that serves ML model predictions.

GUIDELINES:
1. Use FastAPI or Flask for the REST API
2. Load a trained model on server startup
3. Create endpoints for health checks and predictions
4. Handle input validation and preprocessing
5. Return predictions with proper error handling

YOUR TASKS:
- Implement the ModelServer class
- Create prediction endpoint with proper validation
- Add error handling
- Include basic logging
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, validator
import torch
import torch.nn as nn
from typing import List, Dict, Any
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PredictionRequest(BaseModel):
    """
    Input schema for prediction requests.
    
    TODO: Define the input schema for your model
    HINT: Use Pydantic validators to ensure data quality
    """
    data: List[List[float]]  # Example: 2D array for batch predictions
    
    @validator('data')
    def validate_data(cls, v):
        """
        TODO: Add validation logic
        - Check data dimensions
        - Check for NaN or infinite values
        - Check value ranges if applicable
        """
        pass  # TODO: Implement validation


class PredictionResponse(BaseModel):
    """
    Output schema for prediction responses.
    
    TODO: Define what your API returns
    """
    predictions: List[float]
    model_version: str
    inference_time_ms: float


class ModelServer:
    """
    ML Model serving class.
    
    TODO: Implement model loading and inference
    """
    
    def __init__(self, model_path: str, model_version: str = "1.0.0"):
        """
        Initialize the model server.
        
        Args:
            model_path: Path to the trained model file
            model_version: Version of the model
        
        TODO: 
        1. Load the model from disk
        2. Set model to evaluation mode
        3. Move model to appropriate device (CPU/GPU)
        4. Initialize any preprocessing objects
        
        HINT: Use torch.load() for PyTorch models
        HINT: Call model.eval() to set evaluation mode
        """
        self.model_version = model_version
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # TODO: Load model
        # self.model = ...
        
        logger.info(f"Model loaded: version {model_version}, device: {self.device}")
    
    def preprocess(self, data: List[List[float]]) -> torch.Tensor:
        """
        Preprocess input data.
        
        Args:
            data: Raw input data
        
        Returns:
            Preprocessed tensor ready for model input
        
        TODO: Implement preprocessing
        - Convert to tensor
        - Normalize if needed
        - Reshape if needed
        - Move to correct device
        """
        pass  # TODO: Implement
    
    def predict(self, data: List[List[float]]) -> Dict[str, Any]:
        """
        Run inference on input data.
        
        Args:
            data: Input data as list of lists
        
        Returns:
            Dictionary with predictions and metadata
        
        TODO: Implement inference
        STEPS:
        1. Preprocess input data
        2. Run model inference (with torch.no_grad())
        3. Postprocess outputs
        4. Measure inference time
        5. Return results
        
        HINT: Use time.time() to measure latency
        HINT: Use torch.no_grad() for inference
        """
        pass  # TODO: Implement


# Create FastAPI app
app = FastAPI(
    title="ML Model Server",
    description="REST API for ML model inference",
    version="1.0.0"
)

# Global model server instance
model_server = None


@app.on_event("startup")
async def startup_event():
    """
    Load model on server startup.
    
    TODO: Initialize the ModelServer with your model
    
    HINT: Use a global variable to store the model server
    """
    global model_server
    # TODO: Initialize model_server
    logger.info("Server started successfully")


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    TODO: Return server status
    - Check if model is loaded
    - Return model version
    - Return device info
    """
    pass  # TODO: Implement


@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    """
    Prediction endpoint.
    
    Args:
        request: PredictionRequest with input data
    
    Returns:
        PredictionResponse with predictions
    
    TODO: Implement prediction endpoint
    STEPS:
    1. Validate that model is loaded
    2. Call model_server.predict()
    3. Handle exceptions gracefully
    4. Return PredictionResponse
    
    HINT: Use HTTPException for errors
    HINT: Log all predictions for monitoring
    """
    pass  # TODO: Implement


# TESTING CODE
if __name__ == "__main__":
    import uvicorn
    
    print("Model Server Template")
    print("=" * 50)
    print("\nTo test this implementation:")
    print("1. Complete all TODO sections")
    print("2. Place your trained model in the expected path")
    print("3. Run: uvicorn template_model_server:app --reload")
    print("4. Test with: curl -X POST http://localhost:8000/predict -H 'Content-Type: application/json' -d '{\"data\": [[1,2,3]]}'")
    print("\nKey features to implement:")
    print("- Model loading and initialization")
    print("- Input validation with Pydantic")
    print("- Preprocessing and postprocessing")
    print("- Error handling")
    print("- Logging")
    print("=" * 50)
    
    # For development, run with:
    # uvicorn.run(app, host="0.0.0.0", port=8000)
