"""
Solution: Model Server with REST API

This is a complete implementation of a model serving API.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, validator
import torch
import torch.nn as nn
from typing import List, Dict, Any
import logging
import time
import numpy as np
import os

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PredictionRequest(BaseModel):
    """Input schema for prediction requests."""
    data: List[List[float]]
    
    @validator('data')
    def validate_data(cls, v):
        """Validate input data."""
        if not v:
            raise ValueError("Input data cannot be empty")
        
        # Check for consistent dimensions
        if len(v) > 0:
            first_len = len(v[0])
            if not all(len(row) == first_len for row in v):
                raise ValueError("All input rows must have the same length")
        
        # Check for NaN or infinite values
        arr = np.array(v)
        if np.any(np.isnan(arr)) or np.any(np.isinf(arr)):
            raise ValueError("Input contains NaN or infinite values")
        
        return v


class PredictionResponse(BaseModel):
    """Output schema for prediction responses."""
    predictions: List[float]
    model_version: str
    inference_time_ms: float


class SimpleModel(nn.Module):
    """A simple neural network for demonstration."""
    def __init__(self, input_size: int = 10, hidden_size: int = 50, output_size: int = 1):
        super().__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(hidden_size, output_size)
    
    def forward(self, x):
        x = self.fc1(x)
        x = self.relu(x)
        x = self.fc2(x)
        return x


class ModelServer:
    """ML Model serving class."""
    
    def __init__(self, model_path: str = None, model_version: str = "1.0.0"):
        """Initialize the model server."""
        self.model_version = model_version
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Load or create model
        if model_path and os.path.exists(model_path):
            self.model = torch.load(model_path, map_location=self.device)
            logger.info(f"Loaded model from {model_path}")
        else:
            # Create a dummy model for demonstration
            self.model = SimpleModel(input_size=10)
            logger.warning("Created dummy model (no model path provided)")
        
        self.model.to(self.device)
        self.model.eval()
        
        logger.info(f"Model loaded: version {model_version}, device: {self.device}")
    
    def preprocess(self, data: List[List[float]]) -> torch.Tensor:
        """Preprocess input data."""
        # Convert to tensor
        tensor = torch.tensor(data, dtype=torch.float32)
        
        # Move to device
        tensor = tensor.to(self.device)
        
        return tensor
    
    def predict(self, data: List[List[float]]) -> Dict[str, Any]:
        """Run inference on input data."""
        start_time = time.time()
        
        try:
            # Preprocess
            input_tensor = self.preprocess(data)
            
            # Inference
            with torch.no_grad():
                outputs = self.model(input_tensor)
            
            # Postprocess
            predictions = outputs.cpu().numpy().flatten().tolist()
            
            # Calculate inference time
            inference_time_ms = (time.time() - start_time) * 1000
            
            return {
                "predictions": predictions,
                "model_version": self.model_version,
                "inference_time_ms": round(inference_time_ms, 2)
            }
        
        except Exception as e:
            logger.error(f"Prediction error: {str(e)}")
            raise


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
    """Load model on server startup."""
    global model_server
    model_server = ModelServer(model_version="1.0.0")
    logger.info("Server started successfully")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    if model_server is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    return {
        "status": "healthy",
        "model_version": model_server.model_version,
        "device": str(model_server.device)
    }


@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    """Prediction endpoint."""
    if model_server is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        # Log request
        logger.info(f"Received prediction request with {len(request.data)} samples")
        
        # Make prediction
        result = model_server.predict(request.data)
        
        # Log response
        logger.info(f"Prediction completed in {result['inference_time_ms']:.2f}ms")
        
        return PredictionResponse(**result)
    
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Prediction error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "name": "ML Model Server",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "predict": "/predict (POST)",
            "docs": "/docs"
        }
    }


if __name__ == "__main__":
    import uvicorn
    import os
    
    print("Starting ML Model Server...")
    print("=" * 50)
    print("Endpoints:")
    print("  - GET  /         : API information")
    print("  - GET  /health   : Health check")
    print("  - POST /predict  : Make predictions")
    print("  - GET  /docs     : Interactive API documentation")
    print("=" * 50)
    
    # Run server
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
