# Phase 4: Production Video Analysis System - Implementation Guide

This guide provides comprehensive instructions for building a production-grade real-time video analysis system optimized for edge devices and GPU servers.

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Design](#architecture-design)
3. [Edge Device Deployment](#edge-device-deployment)
4. [Server Deployment](#server-deployment)
5. [Multi-Model Pipeline](#multi-model-pipeline)
6. [Adaptive Inference](#adaptive-inference)
7. [Monitoring and Scaling](#monitoring-and-scaling)

## System Overview

### What You'll Build

A complete production system that:
- Processes video streams in real-time (30+ FPS)
- Deploys on edge devices (Raspberry Pi, Jetson Nano)
- Scales on GPU servers (100+ concurrent streams)
- Implements multi-model pipeline (detection → tracking → classification)
- Adapts to hardware capabilities
- Monitors performance metrics

### System Requirements

**Edge Deployment:**
- <50ms p99 latency per frame
- 30+ FPS processing
- <10W power consumption
- Offline operation capability

**Server Deployment:**
- 100+ concurrent video streams
- 1000+ FPS total throughput
- <100ms end-to-end latency
- Auto-scaling based on load

### Technology Stack

**Edge:**
- NVIDIA Jetson (Nano, Xavier, Orin)
- Raspberry Pi 4
- TensorRT for optimization
- OpenCV for video processing

**Server:**
- NVIDIA Triton Inference Server
- Docker/Kubernetes for orchestration
- Prometheus/Grafana for monitoring
- gRPC for high-performance serving

## Architecture Design

### 2.1 System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Video Input                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │ Camera 1 │  │ Camera 2 │  │ Stream N │                  │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘                  │
│       │             │             │                          │
│       └─────────────┴─────────────┘                          │
│                     │                                        │
└─────────────────────┼────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│               Video Ingestion Service                        │
│  - Frame extraction                                          │
│  - Preprocessing                                             │
│  - Buffering                                                 │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│             Inference Pipeline                               │
│                                                              │
│  ┌────────────────┐  ┌────────────────┐  ┌──────────────┐  │
│  │  Detection     │→ │   Tracking     │→ │Classification│  │
│  │  (YOLOv8)      │  │   (DeepSORT)   │  │  (ResNet)    │  │
│  └────────────────┘  └────────────────┘  └──────────────┘  │
│                                                              │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│             Post-Processing                                  │
│  - Result aggregation                                        │
│  - Visualization                                             │
│  - Alerting                                                  │
└────────────┬────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────┐
│                Output/Storage                                │
│  - Display                                                   │
│  - Database                                                  │
│  - Analytics                                                 │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Core Components

**1. Video Capture Module:**
```python
import cv2
import threading
from queue import Queue

class VideoCapture:
    """
    Efficiently capture video frames from multiple sources.
    
    Features:
    - Non-blocking frame capture
    - Buffer management
    - Frame dropping under load
    """
    
    def __init__(self, source, buffer_size=10):
        """
        Initialize video capture.
        
        Args:
            source: Video source (camera index, file path, RTSP URL)
            buffer_size: Maximum frames to buffer
        """
        self.source = source
        self.buffer = Queue(maxsize=buffer_size)
        self.cap = cv2.VideoCapture(source)
        
        # Capture thread
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.running = False
    
    def start(self):
        """Start capture thread."""
        self.running = True
        self.thread.start()
    
    def _capture_loop(self):
        """
        Background capture loop.
        
        Continuously reads frames and adds to buffer.
        Drops oldest frame if buffer is full.
        """
        while self.running:
            ret, frame = self.cap.read()
            
            if not ret:
                print(f"Failed to read frame from {self.source}")
                continue
            
            # Add to buffer (drop oldest if full)
            if self.buffer.full():
                try:
                    self.buffer.get_nowait()  # Remove oldest
                except:
                    pass
            
            self.buffer.put(frame)
    
    def read(self):
        """
        Get next frame from buffer.
        
        Returns:
            Frame if available, None otherwise
        """
        if not self.buffer.empty():
            return self.buffer.get()
        return None
    
    def stop(self):
        """Stop capture."""
        self.running = False
        self.thread.join()
        self.cap.release()
```

**2. Preprocessing Pipeline:**
```python
class FramePreprocessor:
    """
    Preprocess frames for inference.
    
    Optimized for real-time performance.
    """
    
    def __init__(self, target_size=(640, 640), normalize=True):
        """
        Initialize preprocessor.
        
        Args:
            target_size: Target frame size (width, height)
            normalize: Apply normalization
        """
        self.target_size = target_size
        self.normalize = normalize
    
    def process(self, frame):
        """
        Preprocess single frame.
        
        Steps:
        1. Resize to target size
        2. Convert BGR to RGB
        3. Normalize to [0, 1]
        4. Transpose to CHW format
        5. Add batch dimension
        
        Optimizations:
        - Use OpenCV for fast resize
        - Minimize memory copies
        - Use NumPy for efficiency
        """
        # Resize (OpenCV is faster than PIL)
        resized = cv2.resize(frame, self.target_size)
        
        # BGR to RGB
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        
        # Normalize
        if self.normalize:
            normalized = rgb.astype(np.float32) / 255.0
        else:
            normalized = rgb.astype(np.float32)
        
        # HWC to CHW
        transposed = np.transpose(normalized, (2, 0, 1))
        
        # Add batch dimension
        batched = np.expand_dims(transposed, axis=0)
        
        return batched
    
    def process_batch(self, frames):
        """
        Process batch of frames efficiently.
        
        Vectorized operations for better performance.
        """
        processed = [self.process(frame) for frame in frames]
        return np.concatenate(processed, axis=0)
```

## Edge Device Deployment

### 3.1 Jetson Nano Setup

**Step-by-Step Deployment:**

```python
class JetsonInferenceEngine:
    """
    Optimized inference engine for Jetson devices.
    
    Uses TensorRT for maximum performance on Jetson.
    """
    
    def __init__(self, engine_path, input_shape=(640, 640)):
        """
        Initialize Jetson inference engine.
        
        Args:
            engine_path: Path to TensorRT engine file
            input_shape: Input image size
        """
        import pycuda.driver as cuda
        import pycuda.autoinit
        import tensorrt as trt
        
        self.input_shape = input_shape
        
        # Load TensorRT engine
        self.logger = trt.Logger(trt.Logger.WARNING)
        
        with open(engine_path, 'rb') as f:
            runtime = trt.Runtime(self.logger)
            self.engine = runtime.deserialize_cuda_engine(f.read())
        
        self.context = self.engine.create_execution_context()
        
        # Allocate GPU memory
        self._allocate_buffers()
    
    def _allocate_buffers(self):
        """
        Pre-allocate GPU memory for inference.
        
        Avoids allocation overhead during inference.
        """
        import pycuda.driver as cuda
        
        # Input buffer
        input_size = np.prod(self.input_shape) * 3 * 4  # RGB, FP32
        self.input_buffer = cuda.mem_alloc(input_size)
        
        # Output buffer (adjust based on model)
        output_size = 1000 * 4  # Example: 1000 classes, FP32
        self.output_buffer = cuda.mem_alloc(output_size)
    
    def infer(self, frame):
        """
        Run inference on single frame.
        
        Optimized for low latency.
        """
        import pycuda.driver as cuda
        
        # Preprocess
        preprocessed = self._preprocess(frame)
        
        # Copy to GPU
        cuda.memcpy_htod_async(
            self.input_buffer,
            preprocessed,
            stream=None
        )
        
        # Run inference
        self.context.execute_async_v2(
            bindings=[int(self.input_buffer), int(self.output_buffer)],
            stream_handle=0
        )
        
        # Copy result back
        output = np.empty((1000,), dtype=np.float32)
        cuda.memcpy_dtoh_async(output, self.output_buffer, stream=None)
        
        # Synchronize
        cuda.Context.synchronize()
        
        return output
    
    def _preprocess(self, frame):
        """Fast preprocessing on Jetson."""
        # Use Jetson-optimized libraries when available
        resized = cv2.resize(frame, self.input_shape)
        normalized = resized.astype(np.float32) / 255.0
        transposed = np.transpose(normalized, (2, 0, 1))
        return transposed
```

**Power Management:**
```python
class PowerOptimizer:
    """
    Optimize power consumption on edge devices.
    
    Balances performance and power usage.
    """
    
    def __init__(self, device_type='jetson_nano'):
        self.device_type = device_type
        self.power_modes = {
            'jetson_nano': {
                'max_performance': '0',  # 10W
                'balanced': '1',         # 5W
                'power_save': '2'        # 2.5W
            }
        }
    
    def set_power_mode(self, mode='balanced'):
        """
        Set device power mode.
        
        Args:
            mode: 'max_performance', 'balanced', or 'power_save'
        """
        if self.device_type == 'jetson_nano':
            mode_id = self.power_modes['jetson_nano'][mode]
            os.system(f'sudo nvpmodel -m {mode_id}')
            print(f"Set power mode to: {mode}")
    
    def get_power_consumption(self):
        """
        Read current power consumption.
        
        Returns:
            Power in watts
        """
        # Read from Jetson power sensors
        try:
            with open('/sys/bus/i2c/drivers/ina3221x/1-0040/iio:device0/in_power0_input', 'r') as f:
                power_mw = int(f.read().strip())
                return power_mw / 1000.0  # Convert to watts
        except:
            return None
```

### 3.2 Adaptive Resolution

**Dynamic Resolution Scaling:**
```python
class AdaptiveResolution:
    """
    Adapt input resolution based on performance.
    
    Reduces resolution when FPS drops below target.
    """
    
    def __init__(self, target_fps=30, base_resolution=(640, 640)):
        self.target_fps = target_fps
        self.base_resolution = base_resolution
        self.current_resolution = base_resolution
        
        # Resolution options (descending)
        self.resolutions = [
            (640, 640),
            (512, 512),
            (416, 416),
            (320, 320)
        ]
        self.current_index = 0
        
        # FPS tracking
        self.fps_history = deque(maxlen=30)
    
    def update_fps(self, fps):
        """Update FPS measurement."""
        self.fps_history.append(fps)
    
    def adjust_resolution(self):
        """
        Adjust resolution based on FPS.
        
        Returns:
            New resolution tuple
        """
        if len(self.fps_history) < 10:
            return self.current_resolution
        
        avg_fps = sum(self.fps_history) / len(self.fps_history)
        
        # Decrease resolution if FPS too low
        if avg_fps < self.target_fps * 0.8:
            if self.current_index < len(self.resolutions) - 1:
                self.current_index += 1
                self.current_resolution = self.resolutions[self.current_index]
                print(f"Decreased resolution to {self.current_resolution}")
        
        # Increase resolution if FPS allows
        elif avg_fps > self.target_fps * 1.2:
            if self.current_index > 0:
                self.current_index -= 1
                self.current_resolution = self.resolutions[self.current_index]
                print(f"Increased resolution to {self.current_resolution}")
        
        return self.current_resolution
```

## Server Deployment

### 4.1 Triton Inference Server

**Model Configuration:**
```python
# config.pbtxt for Triton Server
"""
name: "yolov8_detection"
platform: "tensorrt_plan"
max_batch_size: 32

input [
  {
    name: "input"
    data_type: TYPE_FP32
    dims: [3, 640, 640]
  }
]

output [
  {
    name: "output"
    data_type: TYPE_FP32
    dims: [25200, 85]  # Detection outputs
  }
]

dynamic_batching {
  preferred_batch_size: [1, 2, 4, 8, 16, 32]
  max_queue_delay_microseconds: 5000  # 5ms
}

instance_group [
  {
    count: 2
    kind: KIND_GPU
    gpus: [0]
  }
]
"""

class TritonClient:
    """
    Client for NVIDIA Triton Inference Server.
    
    Provides high-level API for inference requests.
    """
    
    def __init__(self, server_url='localhost:8000', model_name='yolov8_detection'):
        """
        Initialize Triton client.
        
        Args:
            server_url: Triton server URL
            model_name: Model name on server
        """
        import tritonclient.http as httpclient
        
        self.server_url = server_url
        self.model_name = model_name
        self.client = httpclient.InferenceServerClient(url=server_url)
        
        # Check server health
        if not self.client.is_server_live():
            raise RuntimeError("Triton server not responding")
        
        # Get model metadata
        self.metadata = self.client.get_model_metadata(model_name)
    
    def infer(self, input_data):
        """
        Run inference request.
        
        Args:
            input_data: Input numpy array
        
        Returns:
            Inference results
        """
        import tritonclient.http as httpclient
        
        # Create input
        inputs = []
        inputs.append(
            httpclient.InferInput(
                'input',
                input_data.shape,
                datatype='FP32'
            )
        )
        inputs[0].set_data_from_numpy(input_data)
        
        # Create output request
        outputs = []
        outputs.append(httpclient.InferRequestedOutput('output'))
        
        # Inference request
        response = self.client.infer(
            model_name=self.model_name,
            inputs=inputs,
            outputs=outputs
        )
        
        # Get results
        output_data = response.as_numpy('output')
        
        return output_data
    
    async def infer_async(self, input_data):
        """
        Asynchronous inference request.
        
        Better for high-throughput scenarios.
        """
        # Similar to infer() but async
        pass
```

### 4.2 Multi-Stream Processing

**Concurrent Stream Handler:**
```python
class MultiStreamProcessor:
    """
    Process multiple video streams concurrently.
    
    Manages resources across streams efficiently.
    """
    
    def __init__(self, inference_client, max_streams=100):
        """
        Initialize multi-stream processor.
        
        Args:
            inference_client: Client for inference service
            max_streams: Maximum concurrent streams
        """
        self.client = inference_client
        self.max_streams = max_streams
        
        # Stream management
        self.active_streams = {}
        self.stream_queue = asyncio.Queue(maxsize=max_streams)
    
    async def add_stream(self, stream_id, source):
        """
        Add new video stream.
        
        Args:
            stream_id: Unique stream identifier
            source: Video source (URL, camera, file)
        """
        if len(self.active_streams) >= self.max_streams:
            raise RuntimeError("Maximum streams reached")
        
        # Create stream processor
        processor = StreamProcessor(stream_id, source, self.client)
        self.active_streams[stream_id] = processor
        
        # Start processing
        asyncio.create_task(processor.process())
    
    async def remove_stream(self, stream_id):
        """Remove stream from processing."""
        if stream_id in self.active_streams:
            processor = self.active_streams[stream_id]
            await processor.stop()
            del self.active_streams[stream_id]
    
    def get_stats(self):
        """
        Get statistics for all streams.
        
        Returns:
            Dictionary with per-stream stats
        """
        stats = {}
        for stream_id, processor in self.active_streams.items():
            stats[stream_id] = processor.get_stats()
        return stats

class StreamProcessor:
    """Process single video stream."""
    
    def __init__(self, stream_id, source, client):
        self.stream_id = stream_id
        self.source = source
        self.client = client
        self.running = False
        
        # Performance tracking
        self.frame_count = 0
        self.fps = 0
        self.latency = 0
    
    async def process(self):
        """
        Main processing loop for stream.
        
        Steps:
        1. Capture frame
        2. Preprocess
        3. Inference
        4. Post-process
        5. Update metrics
        """
        self.running = True
        cap = cv2.VideoCapture(self.source)
        
        while self.running:
            start_time = time.time()
            
            # Capture frame
            ret, frame = cap.read()
            if not ret:
                break
            
            # Preprocess
            preprocessed = preprocess_frame(frame)
            
            # Inference
            result = await self.client.infer_async(preprocessed)
            
            # Post-process
            detections = postprocess_detections(result)
            
            # Update metrics
            self.frame_count += 1
            self.latency = (time.time() - start_time) * 1000  # ms
            
            # Calculate FPS
            if self.frame_count % 30 == 0:
                self.fps = 30 / ((time.time() - start_time) * 30)
        
        cap.release()
    
    async def stop(self):
        """Stop processing."""
        self.running = False
    
    def get_stats(self):
        """Get stream statistics."""
        return {
            'frame_count': self.frame_count,
            'fps': self.fps,
            'latency_ms': self.latency
        }
```

## Multi-Model Pipeline

### 5.1 Pipeline Implementation

**Detection → Tracking → Classification:**
```python
class VideoPipeline:
    """
    Multi-model inference pipeline.
    
    Chains multiple models for complete video analysis.
    """
    
    def __init__(self, detector, tracker, classifier):
        """
        Initialize pipeline.
        
        Args:
            detector: Object detection model
            tracker: Object tracking model
            classifier: Classification model
        """
        self.detector = detector
        self.tracker = tracker
        self.classifier = classifier
    
    async def process_frame(self, frame, frame_id):
        """
        Process single frame through pipeline.
        
        Args:
            frame: Input frame (numpy array)
            frame_id: Sequential frame identifier
        
        Returns:
            Dictionary with all results
        """
        results = {'frame_id': frame_id}
        
        # Stage 1: Detection
        detections = await self._detect(frame)
        results['detections'] = detections
        
        # Stage 2: Tracking
        if detections:
            tracks = await self._track(frame, detections, frame_id)
            results['tracks'] = tracks
            
            # Stage 3: Classification (for each track)
            classifications = []
            for track in tracks:
                bbox = track['bbox']
                crop = self._crop_object(frame, bbox)
                cls = await self._classify(crop)
                classifications.append(cls)
            
            results['classifications'] = classifications
        
        return results
    
    async def _detect(self, frame):
        """
        Run object detection.
        
        Returns:
            List of detections with bounding boxes
        """
        # Preprocess for detector
        input_tensor = self._preprocess_for_detection(frame)
        
        # Inference
        output = await self.detector.infer_async(input_tensor)
        
        # Post-process
        detections = self._postprocess_detections(output)
        
        return detections
    
    async def _track(self, frame, detections, frame_id):
        """
        Update object tracks.
        
        Associates detections across frames.
        """
        # Update tracker with new detections
        tracks = self.tracker.update(detections, frame_id)
        
        return tracks
    
    async def _classify(self, crop):
        """
        Classify cropped object.
        
        Returns:
            Classification result
        """
        # Preprocess crop
        input_tensor = self._preprocess_for_classification(crop)
        
        # Inference
        output = await self.classifier.infer_async(input_tensor)
        
        # Get class
        class_id = np.argmax(output)
        confidence = output[class_id]
        
        return {'class_id': class_id, 'confidence': confidence}
```

## Monitoring and Scaling

### 7.1 Performance Monitoring

**Metrics Collection:**
```python
class PerformanceMonitor:
    """
    Monitor inference system performance.
    
    Tracks metrics for observability.
    """
    
    def __init__(self):
        from prometheus_client import Counter, Histogram, Gauge
        
        # Metrics
        self.requests_total = Counter(
            'inference_requests_total',
            'Total inference requests'
        )
        
        self.latency = Histogram(
            'inference_latency_seconds',
            'Inference latency distribution'
        )
        
        self.throughput = Gauge(
            'inference_throughput_fps',
            'Current throughput in FPS'
        )
        
        self.gpu_utilization = Gauge(
            'gpu_utilization_percent',
            'GPU utilization percentage'
        )
    
    def record_inference(self, latency):
        """Record single inference."""
        self.requests_total.inc()
        self.latency.observe(latency)
    
    def update_throughput(self, fps):
        """Update throughput metric."""
        self.throughput.set(fps)
    
    def update_gpu_util(self, utilization):
        """Update GPU utilization."""
        self.gpu_utilization.set(utilization)
```

## Expected Outcomes

After completing Phase 4, you should have:

### System Capabilities
- ✅ Real-time video analysis at 30+ FPS
- ✅ Edge deployment on Jetson/RPi
- ✅ Server deployment handling 100+ streams
- ✅ Multi-model pipeline working end-to-end
- ✅ Adaptive inference based on hardware
- ✅ Production monitoring and alerting

### Performance Targets
- **Edge**: <50ms p99 latency, 30+ FPS
- **Server**: 100+ streams, 1000+ total FPS
- **Accuracy**: >90% of original model
- **Uptime**: 99.9%+ availability

### Understanding
- ✅ Design production inference systems
- ✅ Deploy on various hardware platforms
- ✅ Optimize for real-time constraints
- ✅ Monitor and debug production issues
- ✅ Scale inference infrastructure

## Completion Criteria

You've mastered ML inference when you can:
1. ✅ Build complete production inference systems
2. ✅ Deploy on edge devices and servers
3. ✅ Achieve real-time performance requirements
4. ✅ Implement complex multi-model pipelines
5. ✅ Monitor and maintain production systems
6. ✅ Make informed optimization decisions

**Congratulations!** You've completed the ML Inference learning path!
