# Diffusion Models - From Scratch Implementation

A from-scratch implementation of Diffusion Models in Python for image generation, similar to Stable Diffusion and DALL-E architectures.

## Goal

Build a functional diffusion model to understand:
- **Diffusion Process**: Forward and reverse diffusion in image space
- **Noise Scheduling**: Various noise schedules (linear, cosine, etc.)
- **Denoising Networks**: U-Net architecture for noise prediction
- **Latent Diffusion**: Working in compressed latent space
- **Conditioning**: Text-to-image and class-conditional generation
- **Sampling**: DDPM, DDIM, and other sampling strategies

## What are Diffusion Models?

Diffusion models are generative models that learn to create images by reversing a gradual noising process:

1. **Forward Process**: Gradually add noise to training images
2. **Reverse Process**: Learn to remove noise step by step
3. **Generation**: Start from pure noise and denoise to create new images

This approach has become the state-of-the-art for image generation (Stable Diffusion, Midjourney, DALL-E 2).

## Project Structure

```
diffusion-models/
├── README.md                   # This file
├── IMPLEMENTATION_GUIDE.md     # Detailed implementation steps
├── requirements.txt            # Python dependencies
├── diffusion.py                # Core diffusion process
├── noise_schedule.py           # Noise scheduling strategies
├── unet.py                     # U-Net denoising model
├── train.py                    # Training script
├── sample.py                   # Image generation script
├── utils.py                    # Utility functions
├── data/                       # Dataset directory
└── solutions/                  # Complete reference implementations
    ├── README.md
    ├── diffusion.py
    ├── unet.py
    └── ...
```

## Features

### Core Components

**Diffusion Process**:
- Forward diffusion (adding noise)
- Reverse diffusion (denoising)
- Variance schedules (linear, cosine, sigmoid)
- Reparameterization trick
- Loss computation (simplified and variational)

**Neural Network**:
- U-Net architecture with attention
- Time embeddings
- Skip connections
- Residual blocks
- Self-attention layers

**Training**:
- Noise prediction objective
- Timestep sampling
- Data augmentation
- Gradient accumulation
- Exponential moving average (EMA)

**Sampling**:
- DDPM sampling (original)
- DDIM sampling (faster)
- Classifier-free guidance
- Progressive generation
- Various noise schedules

**Conditioning** (Advanced):
- Class-conditional generation
- Text-to-image with embeddings
- Classifier-free guidance
- CLIP guidance (optional)

## Quick Start

### Prerequisites

- Python 3.8+
- PyTorch 1.12+
- Basic understanding of deep learning
- GPU recommended (but CPU works for small experiments)

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Or manually:
pip install torch torchvision numpy matplotlib tqdm
```

### Dataset

Start with a simple dataset (MNIST, CIFAR-10, or custom):

```python
# Download MNIST
from torchvision.datasets import MNIST
from torchvision import transforms

dataset = MNIST(
    root='./data',
    train=True,
    download=True,
    transform=transforms.ToTensor()
)
```

### Training

```bash
# Train on MNIST (28x28 grayscale)
python train.py --dataset mnist --epochs 50 --batch-size 128

# Train on CIFAR-10 (32x32 RGB)
python train.py --dataset cifar10 --epochs 100 --batch-size 64

# Train with custom settings
python train.py --dataset custom --image-size 64 --timesteps 1000
```

### Generating Images

```bash
# Generate samples
python sample.py --checkpoint model.pt --num-samples 16

# Generate with DDIM (faster)
python sample.py --checkpoint model.pt --sampler ddim --steps 50

# Class-conditional generation
python sample.py --checkpoint model.pt --class-id 5 --num-samples 10
```

## Learning Path

### Phase 1: Understand Diffusion (2-3 hours)
**Goal**: Grasp the mathematical foundation

1. Study forward diffusion process
2. Understand noise schedules
3. Learn reverse diffusion
4. Implement basic forward process
5. Visualize noising steps

**Skills learned**:
- Gaussian noise addition
- Variance schedules
- Reparameterization trick
- Markov chain process

### Phase 2: Build U-Net Architecture (3-4 hours)
**Goal**: Implement the denoising network

1. Understand U-Net structure
2. Implement residual blocks
3. Add time embeddings
4. Implement attention layers
5. Build complete U-Net
6. Test forward pass

**Skills learned**:
- U-Net architecture
- Time conditioning
- Attention mechanisms
- Skip connections
- PyTorch modules

### Phase 3: Training Loop (2-3 hours)
**Goal**: Train the model to denoise

1. Implement training step
2. Sample random timesteps
3. Add noise to images
4. Predict noise with network
5. Compute loss (MSE)
6. Add validation
7. Save checkpoints

**Skills learned**:
- Training diffusion models
- Loss functions
- Optimization strategies
- Checkpointing
- Monitoring training

### Phase 4: Sampling (2-3 hours)
**Goal**: Generate new images

1. Implement DDPM sampling
2. Start from random noise
3. Iteratively denoise
4. Generate complete images
5. Implement DDIM (faster)
6. Add progress visualization

**Skills learned**:
- Sampling algorithms
- DDPM vs DDIM
- Generation strategies
- Speed vs quality tradeoffs

### Phase 5: Advanced Features (3-4 hours)
**Goal**: Add conditioning and improvements

1. Implement class conditioning
2. Add classifier-free guidance
3. Improve sampling speed
4. Add text embeddings (optional)
5. Implement latent diffusion (optional)
6. Experiment with schedules

**Skills learned**:
- Conditional generation
- Guidance techniques
- Advanced architectures
- Latent space diffusion

**Total Time**: ~12-17 hours for complete implementation

## Implementation Details

### Forward Diffusion

At each timestep t, add noise according to:

```
x_t = √(α_t) * x_0 + √(1 - α_t) * ε
```

Where:
- x_0 is the original image
- x_t is the noisy image at timestep t
- α_t is the noise schedule coefficient
- ε ~ N(0, I) is Gaussian noise

### Reverse Diffusion

Learn to predict the noise:

```
ε_θ(x_t, t) ≈ ε
```

Then denoise:

```
x_{t-1} = 1/√(α_t) * (x_t - (1-α_t)/√(1-ᾱ_t) * ε_θ(x_t, t)) + σ_t * z
```

### U-Net Architecture

```
┌──────────────────────────────────────────┐
│              Input (x_t, t)              │
└────────────────┬─────────────────────────┘
                 │
      ┌──────────▼──────────┐
      │   Time Embedding    │
      └──────────┬──────────┘
                 │
      ┌──────────▼──────────┐
      │   Down Block 1      │────┐
      └──────────┬──────────┘    │
                 │                │
      ┌──────────▼──────────┐    │
      │   Down Block 2      │──┐ │
      └──────────┬──────────┘  │ │
                 │              │ │
      ┌──────────▼──────────┐  │ │
      │   Bottleneck +      │  │ │
      │   Attention         │  │ │
      └──────────┬──────────┘  │ │
                 │              │ │
      ┌──────────▼──────────┐  │ │
      │   Up Block 2        │◄─┘ │
      └──────────┬──────────┘    │
                 │                │
      ┌──────────▼──────────┐    │
      │   Up Block 1        │◄───┘
      └──────────┬──────────┘
                 │
      ┌──────────▼──────────┐
      │   Output (noise)    │
      └─────────────────────┘
```

## Testing

### Visual Inspection

Monitor training progress:

```python
# Generate samples during training
if epoch % 10 == 0:
    model.eval()
    samples = sample(model, num_images=16)
    save_image_grid(samples, f'epoch_{epoch}.png')
```

### Metrics

Evaluate generation quality:

```python
# FID Score (Fréchet Inception Distance)
from pytorch_fid import fid_score
fid = fid_score.calculate_fid_given_paths([real_path, generated_path])

# Inception Score
from torchmetrics.image.inception import InceptionScore
inception = InceptionScore()
score = inception(generated_images)
```

### Ablation Studies

Test different configurations:
- Timesteps: 100, 500, 1000
- Schedules: linear, cosine, sigmoid
- Architectures: U-Net sizes
- Samplers: DDPM, DDIM with different steps

## Troubleshooting

### Common Issues

**"NaN loss during training"**:
- Reduce learning rate
- Add gradient clipping
- Check for exploding gradients
- Verify noise schedule

**"Generated images are blurry"**:
- Train longer
- Increase model capacity
- Use better noise schedule
- Implement guidance

**"Slow sampling"**:
- Use DDIM instead of DDPM
- Reduce number of timesteps
- Use fewer sampling steps
- Consider latent diffusion

**"Out of memory"**:
- Reduce batch size
- Use gradient accumulation
- Reduce image resolution
- Use mixed precision training

### Debug Visualization

```python
# Visualize forward diffusion
def visualize_forward_process(image, timesteps=[0, 250, 500, 750, 999]):
    noisy_images = []
    for t in timesteps:
        noisy_img = q_sample(image, torch.tensor([t]))
        noisy_images.append(noisy_img)
    plot_images(noisy_images)

# Visualize reverse process
def visualize_sampling(model, steps=10):
    x = torch.randn(1, 3, 32, 32)
    images = [x]
    for t in reversed(range(0, 1000, 1000//steps)):
        x = p_sample(model, x, t)
        images.append(x)
    plot_images(images)
```

## Advanced Topics

After completing the basic diffusion model, explore:

### Architecture Improvements
- Transformer-based denoising (DiT)
- Better attention mechanisms
- Efficient U-Net variants
- Cascaded diffusion models

### Latent Diffusion
- VAE encoder/decoder
- Diffusion in latent space
- Reduced memory usage
- Faster training

### Conditioning Methods
- CLIP text encoders
- Cross-attention conditioning
- Classifier guidance
- Classifier-free guidance

### Advanced Sampling
- Progressive distillation
- Consistency models
- Few-step samplers
- Guided diffusion

### Applications
- Image super-resolution
- Image inpainting
- Image-to-image translation
- Video generation

## Documentation

### Papers

**Core Papers**:
- [DDPM](https://arxiv.org/abs/2006.11239): Denoising Diffusion Probabilistic Models
- [DDIM](https://arxiv.org/abs/2010.02502): Denoising Diffusion Implicit Models
- [Improved DDPM](https://arxiv.org/abs/2102.09672): Improved techniques
- [Latent Diffusion](https://arxiv.org/abs/2112.10752): High-Resolution Image Synthesis

**Advanced**:
- [Classifier-Free Guidance](https://arxiv.org/abs/2207.12598)
- [Stable Diffusion](https://arxiv.org/abs/2112.10752)
- [Imagen](https://arxiv.org/abs/2205.11487)

### Resources

- [The Annotated Diffusion Model](https://huggingface.co/blog/annotated-diffusion)
- [Diffusion Models Tutorial](https://lilianweng.github.io/posts/2021-07-11-diffusion-models/)
- [Hugging Face Diffusers Library](https://github.com/huggingface/diffusers)
- [PyTorch Implementation Examples](https://github.com/CompVis/stable-diffusion)

### Video Courses

**Deep Learning Foundations**:
- [CS231n - Convolutional Neural Networks for Visual Recognition - Stanford](http://cs231n.stanford.edu/)
- [6.S191 - Introduction to Deep Learning - MIT](http://introtodeeplearning.com/)
- [Deep Learning Specialization - deeplearning.ai](https://www.deeplearning.ai/courses/deep-learning-specialization/)

**Generative Models & Computer Vision**:
- [Generative AI and LLMs Courses](https://github.com/Developer-Y/cs-video-courses#generative-ai-and-llms)
- [Computer Vision Courses](https://github.com/Developer-Y/cs-video-courses#computer-vision)
- [Deep Learning Courses](https://github.com/Developer-Y/cs-video-courses#deep-learning)

**Advanced Topics**:
- [Full list of ML/AI video courses](https://github.com/Developer-Y/cs-video-courses#machine-learning)

## Performance Tips

### Training
- Use mixed precision (torch.cuda.amp)
- Implement gradient checkpointing
- Use efficient data loading
- Enable cudnn.benchmark

### Inference
- Use DDIM with fewer steps (50-100 instead of 1000)
- Implement model quantization
- Use TorchScript compilation
- Batch generation when possible

## License

Educational purposes. Use freely for learning.

## Acknowledgments

Inspired by:
- DDPM and DDIM papers
- Stable Diffusion by Stability AI
- Hugging Face Diffusers library
- OpenAI's DALL-E 2
- The broader diffusion models research community
