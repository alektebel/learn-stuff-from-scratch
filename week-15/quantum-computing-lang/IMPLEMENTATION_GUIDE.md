# Quantum Computing Simulator Implementation Guide

This guide provides comprehensive, step-by-step instructions for implementing a quantum computing simulator from scratch in C. Each phase builds upon the previous one, creating a functional simulator that can execute quantum circuits and algorithms.

## Table of Contents

1. [Project Overview](#project-overview)
2. [Prerequisites](#prerequisites)
3. [Phase 1: Qubit Representation and Complex Numbers](#phase-1-qubit-representation)
4. [Phase 2: Single-Qubit Gates](#phase-2-single-qubit-gates)
5. [Phase 3: Multi-Qubit Systems and Entanglement](#phase-3-multi-qubit-systems)
6. [Phase 4: Measurement and State Collapse](#phase-4-measurement)
7. [Phase 5: Quantum Algorithms](#phase-5-quantum-algorithms)
8. [Testing and Validation](#testing-and-validation)
9. [Mathematical Foundations](#mathematical-foundations)
10. [Complete Examples](#complete-examples)
11. [Resources and References](#resources-and-references)

## Project Overview

### What You'll Build

A complete quantum computing simulator with these components:
- **Quantum State Management**: Multi-qubit state vectors with complex amplitudes
- **Gate Library**: Single and multi-qubit quantum gates
- **Circuit Executor**: Apply sequences of gates to quantum states
- **Measurement System**: Probabilistic measurement with state collapse
- **Algorithm Suite**: Implement famous quantum algorithms

### Quantum Computing Fundamentals

Quantum computers manipulate quantum bits (qubits) that can exist in **superposition** - simultaneously in multiple states. Key differences from classical computing:

- **Classical bit**: 0 or 1
- **Qubit**: α|0⟩ + β|1⟩ where |α|² + |β|² = 1

### Architecture

```
Quantum State (Complex Vector)
    ↓
[Apply Gates] → Transform state (unitary operations)
    ↓
[Measurement] → Classical bits (probabilistic collapse)
    ↓
Results
```

## Prerequisites

### Required Knowledge

- **C programming**: Pointers, structures, dynamic memory allocation
- **Complex numbers**: Addition, multiplication, conjugates
- **Linear algebra**: Vectors, matrices, tensor products
- **Basic quantum mechanics**: Superposition, measurement concepts
- **Probability**: Basic probability theory

### Tools Needed

- GCC compiler with math library support (`-lm` flag)
- Make build system
- Complex number library (`<complex.h>`)
- Math library (`<math.h>`)

### Setting Up

```bash
cd quantum-computing-lang/
gcc -o quantum quantum.c -lm    # Build simulator
./quantum                        # Run demo
```

## Phase 1: Qubit Representation

### Overview

Qubits are represented as complex probability amplitudes. A single qubit requires 2 complex numbers, n qubits require 2ⁿ complex numbers.

### Mathematical Background

A single qubit state is:
```
|ψ⟩ = α|0⟩ + β|1⟩
```

Where:
- α, β are complex numbers (amplitudes)
- |α|² + |β|² = 1 (normalization constraint)
- |α|² = probability of measuring 0
- |β|² = probability of measuring 1

### Implementation Steps

#### Step 1: Define Complex Number Type (5 minutes)

In C, use `<complex.h>`:

```c
#include <complex.h>
#include <math.h>

// Type alias for clarity
typedef double complex Complex;
```

Complex number operations:
- `creal(z)`: Real part
- `cimag(z)`: Imaginary part
- `cabs(z)`: Magnitude |z|
- `conj(z)`: Complex conjugate
- `z1 * z2`: Multiplication
- `z1 + z2`: Addition

#### Step 2: Define Quantum State Structure (15 minutes)

Create the main data structure:

```c
typedef struct {
    int num_qubits;        // Number of qubits
    int state_size;        // 2^num_qubits
    Complex *amplitudes;   // State vector
} QuantumState;
```

**Why this structure?**
- `num_qubits`: Track system size
- `state_size`: 2ⁿ basis states
- `amplitudes`: Complex amplitude for each basis state

**Memory layout example** (2 qubits):
```
Index | Basis State | Amplitude
------|-------------|----------
  0   |    |00⟩     |   α₀
  1   |    |01⟩     |   α₁
  2   |    |10⟩     |   α₂
  3   |    |11⟩     |   α₃
```

#### Step 3: State Initialization (20 minutes)

Create function to initialize quantum state:

```c
QuantumState* create_quantum_state(int num_qubits) {
    // Allocate structure
    QuantumState *state = malloc(sizeof(QuantumState));
    if (!state) return NULL;
    
    state->num_qubits = num_qubits;
    state->state_size = 1 << num_qubits;  // 2^num_qubits
    
    // Allocate amplitude array
    state->amplitudes = calloc(state->state_size, sizeof(Complex));
    if (!state->amplitudes) {
        free(state);
        return NULL;
    }
    
    // Initialize to |00...0⟩ state
    state->amplitudes[0] = 1.0 + 0.0*I;  // All amplitude in |0⟩^n
    
    return state;
}
```

**Key points:**
- Use `1 << num_qubits` for efficient 2ⁿ calculation
- `calloc` zeros all amplitudes
- Set first amplitude to 1 (computational basis state |0⟩)

#### Step 4: Memory Management (10 minutes)

Implement cleanup:

```c
void destroy_quantum_state(QuantumState *state) {
    if (state) {
        if (state->amplitudes) {
            free(state->amplitudes);
        }
        free(state);
    }
}
```

#### Step 5: State Visualization (30 minutes)

Print quantum state in readable format:

```c
void print_state(QuantumState *state) {
    printf("Quantum State (%d qubit%s):\n", 
           state->num_qubits, 
           state->num_qubits == 1 ? "" : "s");
    
    for (int i = 0; i < state->state_size; i++) {
        Complex amp = state->amplitudes[i];
        double real = creal(amp);
        double imag = cimag(amp);
        double prob = cabs(amp) * cabs(amp);
        
        // Skip near-zero amplitudes
        if (prob < 1e-10) continue;
        
        // Print basis state in binary
        printf("  |");
        for (int q = state->num_qubits - 1; q >= 0; q--) {
            printf("%d", (i >> q) & 1);
        }
        printf("⟩: ");
        
        // Print amplitude
        if (imag >= 0) {
            printf("%.4f + %.4fi", real, imag);
        } else {
            printf("%.4f - %.4fi", real, -imag);
        }
        
        // Print probability
        printf(" (probability: %.4f)\n", prob);
    }
}
```

**Output example:**
```
Quantum State (2 qubits):
  |00⟩: 0.7071 + 0.0000i (probability: 0.5000)
  |11⟩: 0.7071 + 0.0000i (probability: 0.5000)
```

### Testing Phase 1

Create simple test:

```c
int main() {
    // Test: Create single qubit
    QuantumState *state = create_quantum_state(1);
    printf("Initial state:\n");
    print_state(state);  // Should show |0⟩ with probability 1.0
    
    destroy_quantum_state(state);
    return 0;
}
```

**Expected output:**
```
Quantum State (1 qubit):
  |0⟩: 1.0000 + 0.0000i (probability: 1.0000)
```

## Phase 2: Single-Qubit Gates

### Overview

Quantum gates are unitary transformations that preserve normalization. Single-qubit gates operate on one qubit at a time.

### Mathematical Background

Gates are 2×2 unitary matrices (U†U = I):

**Hadamard Gate (H)**:
```
H = (1/√2) [1   1]
           [1  -1]
```

**Pauli-X Gate (NOT)**:
```
X = [0  1]
    [1  0]
```

**Pauli-Y Gate**:
```
Y = [0  -i]
    [i   0]
```

**Pauli-Z Gate**:
```
Z = [1   0]
    [0  -1]
```

**Phase Gate (S)**:
```
S = [1   0]
    [0   i]
```

**T Gate (π/8)**:
```
T = [1        0     ]
    [0   e^(iπ/4)  ]
```

### Implementation Steps

#### Step 1: Understanding Gate Application (20 minutes)

For an n-qubit system, applying a gate to qubit q means:
1. Group basis states by qubit q's value
2. Apply 2×2 matrix to grouped amplitudes
3. Handle all 2ⁿ⁻¹ pairs simultaneously

**Example:** Apply H to qubit 0 of |00⟩:
- Pair states: (|00⟩, |01⟩), where they differ only in qubit 0
- Apply H matrix to amplitudes of this pair

#### Step 2: Implement Hadamard Gate (45 minutes)

The Hadamard gate creates superposition:

```c
void hadamard(QuantumState *state, int target_qubit) {
    int n = state->num_qubits;
    
    // Validate input
    if (target_qubit < 0 || target_qubit >= n) {
        fprintf(stderr, "Invalid qubit index\n");
        return;
    }
    
    double sqrt2_inv = 1.0 / sqrt(2.0);
    
    // Iterate through all basis states
    for (int i = 0; i < state->state_size; i++) {
        // Skip if target qubit is 1 (already processed with paired state)
        if ((i >> target_qubit) & 1) continue;
        
        // Find paired state (flip target qubit bit)
        int j = i | (1 << target_qubit);
        
        // Get current amplitudes
        Complex amp_0 = state->amplitudes[i];  // Target qubit = 0
        Complex amp_1 = state->amplitudes[j];  // Target qubit = 1
        
        // Apply Hadamard matrix
        // H|0⟩ = (|0⟩ + |1⟩)/√2
        // H|1⟩ = (|0⟩ - |1⟩)/√2
        state->amplitudes[i] = sqrt2_inv * (amp_0 + amp_1);
        state->amplitudes[j] = sqrt2_inv * (amp_0 - amp_1);
    }
}
```

**How it works:**
1. Loop through states where target qubit is 0
2. Find paired state (target qubit is 1)
3. Apply transformation matrix to amplitude pair
4. Update both amplitudes

#### Step 3: Implement Pauli-X Gate (30 minutes)

Pauli-X is the quantum NOT gate:

```c
void pauli_x(QuantumState *state, int target_qubit) {
    int n = state->num_qubits;
    
    if (target_qubit < 0 || target_qubit >= n) {
        fprintf(stderr, "Invalid qubit index\n");
        return;
    }
    
    // Swap amplitudes where target qubit differs
    for (int i = 0; i < state->state_size; i++) {
        if ((i >> target_qubit) & 1) continue;
        
        int j = i | (1 << target_qubit);
        
        // Swap amplitudes
        Complex temp = state->amplitudes[i];
        state->amplitudes[i] = state->amplitudes[j];
        state->amplitudes[j] = temp;
    }
}
```

**Effect:** X|0⟩ = |1⟩, X|1⟩ = |0⟩

#### Step 4: Implement Pauli-Z Gate (25 minutes)

Pauli-Z flips the phase:

```c
void pauli_z(QuantumState *state, int target_qubit) {
    int n = state->num_qubits;
    
    if (target_qubit < 0 || target_qubit >= n) {
        fprintf(stderr, "Invalid qubit index\n");
        return;
    }
    
    // Flip phase of states where target qubit is 1
    for (int i = 0; i < state->state_size; i++) {
        if ((i >> target_qubit) & 1) {
            state->amplitudes[i] = -state->amplitudes[i];
        }
    }
}
```

**Effect:** Z|0⟩ = |0⟩, Z|1⟩ = -|1⟩

#### Step 5: Implement Pauli-Y Gate (25 minutes)

Pauli-Y is a combination of X and Z with phase:

```c
void pauli_y(QuantumState *state, int target_qubit) {
    int n = state->num_qubits;
    
    if (target_qubit < 0 || target_qubit >= n) {
        fprintf(stderr, "Invalid qubit index\n");
        return;
    }
    
    // Y = i * X * Z (or apply matrix directly)
    for (int i = 0; i < state->state_size; i++) {
        if ((i >> target_qubit) & 1) continue;
        
        int j = i | (1 << target_qubit);
        
        Complex amp_0 = state->amplitudes[i];
        Complex amp_1 = state->amplitudes[j];
        
        // Apply Y matrix: [0, -i; i, 0]
        state->amplitudes[i] = -I * amp_1;
        state->amplitudes[j] = I * amp_0;
    }
}
```

#### Step 6: Implement Phase Gates (30 minutes)

Phase gate S and T gates:

```c
void phase_s(QuantumState *state, int target_qubit) {
    int n = state->num_qubits;
    
    if (target_qubit < 0 || target_qubit >= n) {
        fprintf(stderr, "Invalid qubit index\n");
        return;
    }
    
    // Apply phase i to |1⟩ states
    for (int i = 0; i < state->state_size; i++) {
        if ((i >> target_qubit) & 1) {
            state->amplitudes[i] *= I;
        }
    }
}

void phase_t(QuantumState *state, int target_qubit) {
    int n = state->num_qubits;
    
    if (target_qubit < 0 || target_qubit >= n) {
        fprintf(stderr, "Invalid qubit index\n");
        return;
    }
    
    // e^(i*pi/4) = (1 + i) / sqrt(2)
    Complex phase = (1.0 + I) / sqrt(2.0);
    
    for (int i = 0; i < state->state_size; i++) {
        if ((i >> target_qubit) & 1) {
            state->amplitudes[i] *= phase;
        }
    }
}
```

#### Step 7: Rotation Gates (Advanced, 45 minutes)

Implement parameterized rotation gates:

```c
// Rotation around X-axis
void rx(QuantumState *state, int target_qubit, double theta) {
    double cos_half = cos(theta / 2.0);
    double sin_half = sin(theta / 2.0);
    
    for (int i = 0; i < state->state_size; i++) {
        if ((i >> target_qubit) & 1) continue;
        
        int j = i | (1 << target_qubit);
        
        Complex amp_0 = state->amplitudes[i];
        Complex amp_1 = state->amplitudes[j];
        
        // RX matrix
        state->amplitudes[i] = cos_half * amp_0 - I * sin_half * amp_1;
        state->amplitudes[j] = -I * sin_half * amp_0 + cos_half * amp_1;
    }
}

// Rotation around Z-axis
void rz(QuantumState *state, int target_qubit, double theta) {
    Complex phase_0 = cexp(-I * theta / 2.0);
    Complex phase_1 = cexp(I * theta / 2.0);
    
    for (int i = 0; i < state->state_size; i++) {
        if ((i >> target_qubit) & 1) {
            state->amplitudes[i] *= phase_1;
        } else {
            state->amplitudes[i] *= phase_0;
        }
    }
}
```

### Testing Phase 2

Test each gate:

```c
void test_hadamard() {
    QuantumState *state = create_quantum_state(1);
    printf("Before H:\n");
    print_state(state);
    
    hadamard(state, 0);
    printf("\nAfter H:\n");
    print_state(state);
    // Expected: |0⟩ and |1⟩ with 50% probability each
    
    destroy_quantum_state(state);
}

void test_pauli_x() {
    QuantumState *state = create_quantum_state(1);
    pauli_x(state, 0);
    printf("After X:\n");
    print_state(state);
    // Expected: |1⟩ with 100% probability
    
    destroy_quantum_state(state);
}
```

## Phase 3: Multi-Qubit Systems

### Overview

Multi-qubit gates create entanglement - correlations between qubits that don't exist classically.

### Mathematical Background

**CNOT (Controlled-NOT)**:
```
CNOT = [1  0  0  0]
       [0  1  0  0]
       [0  0  0  1]
       [0  0  1  0]
```

Flips target qubit if control qubit is |1⟩.

**Toffoli Gate (CCNOT)**:
3-qubit gate, flips target if both controls are |1⟩.

**SWAP Gate**:
Swaps two qubit states.

### Implementation Steps

#### Step 1: Implement CNOT Gate (60 minutes)

The CNOT gate creates entanglement:

```c
void cnot(QuantumState *state, int control_qubit, int target_qubit) {
    int n = state->num_qubits;
    
    // Validate inputs
    if (control_qubit < 0 || control_qubit >= n ||
        target_qubit < 0 || target_qubit >= n ||
        control_qubit == target_qubit) {
        fprintf(stderr, "Invalid qubit indices\n");
        return;
    }
    
    // Only apply when control qubit is 1
    for (int i = 0; i < state->state_size; i++) {
        // Check if control qubit is 1
        if (!((i >> control_qubit) & 1)) continue;
        
        // Check if target qubit is 0 (to avoid double-swapping)
        if ((i >> target_qubit) & 1) continue;
        
        // Find state with target flipped
        int j = i | (1 << target_qubit);
        
        // Swap amplitudes
        Complex temp = state->amplitudes[i];
        state->amplitudes[i] = state->amplitudes[j];
        state->amplitudes[j] = temp;
    }
}
```

**How it works:**
1. Find states where control = 1 and target = 0
2. Swap with paired state where target = 1
3. Leave other states unchanged

#### Step 2: Implement SWAP Gate (40 minutes)

```c
void swap_gate(QuantumState *state, int qubit1, int qubit2) {
    int n = state->num_qubits;
    
    if (qubit1 < 0 || qubit1 >= n ||
        qubit2 < 0 || qubit2 >= n ||
        qubit1 == qubit2) {
        fprintf(stderr, "Invalid qubit indices\n");
        return;
    }
    
    // Swap amplitudes where qubits differ
    for (int i = 0; i < state->state_size; i++) {
        int bit1 = (i >> qubit1) & 1;
        int bit2 = (i >> qubit2) & 1;
        
        // Only process if bits differ and we haven't swapped yet
        if (bit1 != bit2 && bit1 < bit2) {
            // Construct swapped index
            int j = i ^ (1 << qubit1) ^ (1 << qubit2);
            
            Complex temp = state->amplitudes[i];
            state->amplitudes[i] = state->amplitudes[j];
            state->amplitudes[j] = temp;
        }
    }
}
```

#### Step 3: Implement Toffoli Gate (60 minutes)

Three-qubit controlled gate:

```c
void toffoli(QuantumState *state, int control1, int control2, int target) {
    int n = state->num_qubits;
    
    // Validate inputs
    if (control1 < 0 || control1 >= n ||
        control2 < 0 || control2 >= n ||
        target < 0 || target >= n ||
        control1 == control2 || control1 == target || control2 == target) {
        fprintf(stderr, "Invalid qubit indices\n");
        return;
    }
    
    // Apply only when both controls are 1
    for (int i = 0; i < state->state_size; i++) {
        // Check both controls are 1
        if (!((i >> control1) & 1)) continue;
        if (!((i >> control2) & 1)) continue;
        
        // Check target is 0
        if ((i >> target) & 1) continue;
        
        // Find state with target flipped
        int j = i | (1 << target);
        
        // Swap amplitudes
        Complex temp = state->amplitudes[i];
        state->amplitudes[i] = state->amplitudes[j];
        state->amplitudes[j] = temp;
    }
}
```

#### Step 4: Controlled Phase Gates (45 minutes)

Implement controlled-Z and controlled-phase:

```c
void controlled_z(QuantumState *state, int control, int target) {
    int n = state->num_qubits;
    
    if (control < 0 || control >= n ||
        target < 0 || target >= n ||
        control == target) {
        fprintf(stderr, "Invalid qubit indices\n");
        return;
    }
    
    // Apply phase flip when both qubits are 1
    for (int i = 0; i < state->state_size; i++) {
        if (((i >> control) & 1) && ((i >> target) & 1)) {
            state->amplitudes[i] = -state->amplitudes[i];
        }
    }
}

void controlled_phase(QuantumState *state, int control, int target, double theta) {
    Complex phase = cexp(I * theta);
    
    for (int i = 0; i < state->state_size; i++) {
        if (((i >> control) & 1) && ((i >> target) & 1)) {
            state->amplitudes[i] *= phase;
        }
    }
}
```

### Testing Phase 3

Test entanglement creation:

```c
void test_bell_state() {
    QuantumState *state = create_quantum_state(2);
    
    // Create Bell state: (|00⟩ + |11⟩)/√2
    hadamard(state, 0);
    cnot(state, 0, 1);
    
    printf("Bell state:\n");
    print_state(state);
    // Expected: |00⟩ and |11⟩ with 50% probability each
    
    destroy_quantum_state(state);
}
```

## Phase 4: Measurement

### Overview

Measurement collapses the quantum state probabilistically based on amplitude magnitudes.

### Mathematical Background

Measurement probability for basis state |i⟩:
```
P(i) = |αᵢ|² = αᵢ* × αᵢ
```

After measuring outcome |i⟩:
```
|ψ⟩ → |i⟩ (complete collapse)
```

Or partial measurement (single qubit):
- Collapse measured qubit
- Renormalize remaining superposition

### Implementation Steps

#### Step 1: Full State Measurement (45 minutes)

Measure entire quantum state:

```c
int measure_all(QuantumState *state) {
    // Calculate probabilities
    double *probabilities = malloc(state->state_size * sizeof(double));
    double total = 0.0;
    
    for (int i = 0; i < state->state_size; i++) {
        probabilities[i] = cabs(state->amplitudes[i]);
        probabilities[i] *= probabilities[i];
        total += probabilities[i];
    }
    
    // Normalize (should be ~1.0 already)
    for (int i = 0; i < state->state_size; i++) {
        probabilities[i] /= total;
    }
    
    // Random selection based on probabilities
    double random = (double)rand() / RAND_MAX;
    double cumulative = 0.0;
    int result = 0;
    
    for (int i = 0; i < state->state_size; i++) {
        cumulative += probabilities[i];
        if (random < cumulative) {
            result = i;
            break;
        }
    }
    
    // Collapse to measured state
    for (int i = 0; i < state->state_size; i++) {
        state->amplitudes[i] = (i == result) ? 1.0 : 0.0;
    }
    
    free(probabilities);
    return result;
}
```

#### Step 2: Single Qubit Measurement (60 minutes)

Measure one qubit, leave others in superposition:

```c
int measure_qubit(QuantumState *state, int target_qubit) {
    int n = state->num_qubits;
    
    if (target_qubit < 0 || target_qubit >= n) {
        fprintf(stderr, "Invalid qubit index\n");
        return -1;
    }
    
    // Calculate probabilities for qubit being 0 or 1
    double prob_0 = 0.0;
    double prob_1 = 0.0;
    
    for (int i = 0; i < state->state_size; i++) {
        double prob = cabs(state->amplitudes[i]);
        prob *= prob;
        
        if ((i >> target_qubit) & 1) {
            prob_1 += prob;
        } else {
            prob_0 += prob;
        }
    }
    
    // Random measurement outcome
    double random = (double)rand() / RAND_MAX;
    int result = (random < prob_0) ? 0 : 1;
    
    // Collapse and renormalize
    double norm_factor = sqrt(result == 0 ? prob_0 : prob_1);
    
    for (int i = 0; i < state->state_size; i++) {
        int qubit_value = (i >> target_qubit) & 1;
        
        if (qubit_value == result) {
            // Renormalize surviving amplitudes
            state->amplitudes[i] /= norm_factor;
        } else {
            // Zero out non-measured amplitudes
            state->amplitudes[i] = 0.0;
        }
    }
    
    return result;
}
```

#### Step 3: Measurement Utilities (30 minutes)

Helper functions for measurement:

```c
// Measure multiple qubits
int* measure_qubits(QuantumState *state, int *qubit_indices, int count) {
    int *results = malloc(count * sizeof(int));
    
    for (int i = 0; i < count; i++) {
        results[i] = measure_qubit(state, qubit_indices[i]);
    }
    
    return results;
}

// Get measurement probabilities without collapsing
void get_probabilities(QuantumState *state, double *probs) {
    for (int i = 0; i < state->state_size; i++) {
        probs[i] = cabs(state->amplitudes[i]);
        probs[i] *= probs[i];
    }
}

// Check if state is normalized
int is_normalized(QuantumState *state) {
    double total = 0.0;
    
    for (int i = 0; i < state->state_size; i++) {
        double prob = cabs(state->amplitudes[i]);
        total += prob * prob;
    }
    
    return fabs(total - 1.0) < 1e-10;
}
```

### Testing Phase 4

Test measurement:

```c
void test_measurement() {
    QuantumState *state = create_quantum_state(1);
    hadamard(state, 0);
    
    printf("Before measurement:\n");
    print_state(state);
    
    int result = measure_qubit(state, 0);
    printf("\nMeasured: %d\n", result);
    
    printf("\nAfter measurement:\n");
    print_state(state);
    
    destroy_quantum_state(state);
}
```

## Phase 5: Quantum Algorithms

### Overview

Implement famous quantum algorithms that demonstrate quantum advantage.

### Algorithm 1: Deutsch-Jozsa Algorithm (90 minutes)

Determines if a function is constant or balanced with one query.

**Problem:** Given f: {0,1} → {0,1}, determine if f is constant or balanced.

**Classical:** Requires 2 queries in worst case
**Quantum:** Requires 1 query

```c
// Oracle for constant-0 function
void oracle_constant_0(QuantumState *state, int input_qubit, int output_qubit) {
    // Do nothing - f(x) = 0 for all x
}

// Oracle for constant-1 function
void oracle_constant_1(QuantumState *state, int input_qubit, int output_qubit) {
    // Flip output - f(x) = 1 for all x
    pauli_x(state, output_qubit);
}

// Oracle for balanced function (f(x) = x)
void oracle_balanced_identity(QuantumState *state, int input_qubit, int output_qubit) {
    // CNOT: copy input to output
    cnot(state, input_qubit, output_qubit);
}

// Oracle for balanced function (f(x) = NOT x)
void oracle_balanced_not(QuantumState *state, int input_qubit, int output_qubit) {
    // X on input, then CNOT
    pauli_x(state, input_qubit);
    cnot(state, input_qubit, output_qubit);
    pauli_x(state, input_qubit);
}

// Deutsch-Jozsa algorithm
int deutsch_jozsa(void (*oracle)(QuantumState*, int, int)) {
    // 2 qubits: input and output
    QuantumState *state = create_quantum_state(2);
    
    // Initialize output qubit to |1⟩
    pauli_x(state, 1);
    
    // Apply Hadamard to both qubits
    hadamard(state, 0);
    hadamard(state, 1);
    
    // Apply oracle
    oracle(state, 0, 1);
    
    // Apply Hadamard to input qubit
    hadamard(state, 0);
    
    // Measure input qubit
    int result = measure_qubit(state, 0);
    
    destroy_quantum_state(state);
    
    // result = 0 → constant, result = 1 → balanced
    return result;
}
```

### Algorithm 2: Grover's Search (120 minutes)

Quantum search algorithm with O(√N) complexity.

**Problem:** Find marked item in unsorted database
**Classical:** O(N) queries
**Quantum:** O(√N) queries

```c
// Oracle: marks the solution by flipping its phase
void grover_oracle(QuantumState *state, int solution) {
    // Flip phase of solution state
    state->amplitudes[solution] = -state->amplitudes[solution];
}

// Diffusion operator (inversion about average)
void grover_diffusion(QuantumState *state) {
    int n = state->num_qubits;
    
    // H⊗n
    for (int i = 0; i < n; i++) {
        hadamard(state, i);
    }
    
    // Flip all amplitudes
    for (int i = 0; i < state->state_size; i++) {
        state->amplitudes[i] = -state->amplitudes[i];
    }
    
    // Flip phase of |0⟩ state
    state->amplitudes[0] = -state->amplitudes[0];
    
    // H⊗n
    for (int i = 0; i < n; i++) {
        hadamard(state, i);
    }
}

// Grover's algorithm
int grovers_search(int num_qubits, int solution) {
    QuantumState *state = create_quantum_state(num_qubits);
    
    // Initialize to equal superposition
    for (int i = 0; i < num_qubits; i++) {
        hadamard(state, i);
    }
    
    // Number of iterations ≈ π/4 * √(2^n)
    int iterations = (int)(M_PI / 4.0 * sqrt(state->state_size));
    
    // Grover iteration
    for (int iter = 0; iter < iterations; iter++) {
        grover_oracle(state, solution);
        grover_diffusion(state);
    }
    
    // Measure
    int result = measure_all(state);
    
    destroy_quantum_state(state);
    return result;
}
```

### Algorithm 3: Quantum Teleportation (90 minutes)

Transfer quantum state using entanglement and classical communication.

```c
void quantum_teleportation() {
    // 3 qubits: 0 = state to teleport, 1 = Alice's, 2 = Bob's
    QuantumState *state = create_quantum_state(3);
    
    // Prepare state to teleport on qubit 0 (example: |+⟩)
    hadamard(state, 0);
    
    printf("State to teleport:\n");
    print_state(state);
    
    // Create Bell pair between qubits 1 and 2
    hadamard(state, 1);
    cnot(state, 1, 2);
    
    // Alice's operations (qubits 0 and 1)
    cnot(state, 0, 1);
    hadamard(state, 0);
    
    // Measurement (Alice measures qubits 0 and 1)
    int m0 = measure_qubit(state, 0);
    int m1 = measure_qubit(state, 1);
    
    printf("\nAlice's measurements: m0=%d, m1=%d\n", m0, m1);
    
    // Bob's corrections based on measurements
    if (m1 == 1) {
        pauli_x(state, 2);
    }
    if (m0 == 1) {
        pauli_z(state, 2);
    }
    
    printf("\nBob's qubit (after corrections):\n");
    print_state(state);
    
    destroy_quantum_state(state);
}
```

### Algorithm 4: Superdense Coding (60 minutes)

Send 2 classical bits using 1 qubit via entanglement.

```c
void superdense_coding(int bit0, int bit1) {
    // 2 qubits: 0 = Alice's, 1 = Bob's
    QuantumState *state = create_quantum_state(2);
    
    // Create Bell pair
    hadamard(state, 0);
    cnot(state, 0, 1);
    
    printf("Encoding bits: %d%d\n", bit0, bit1);
    
    // Alice encodes 2 bits into her qubit
    if (bit1 == 1) {
        pauli_z(state, 0);
    }
    if (bit0 == 1) {
        pauli_x(state, 0);
    }
    
    // Bob decodes
    cnot(state, 0, 1);
    hadamard(state, 0);
    
    // Measure both qubits
    int m0 = measure_qubit(state, 0);
    int m1 = measure_qubit(state, 1);
    
    printf("Decoded bits: %d%d\n", m0, m1);
    
    destroy_quantum_state(state);
}
```

### Algorithm 5: Quantum Fourier Transform (Advanced, 180 minutes)

Foundation for Shor's algorithm and other quantum algorithms.

```c
void qft(QuantumState *state) {
    int n = state->num_qubits;
    
    for (int j = 0; j < n; j++) {
        hadamard(state, j);
        
        for (int k = j + 1; k < n; k++) {
            double angle = M_PI / pow(2, k - j);
            controlled_phase(state, k, j, angle);
        }
    }
    
    // Reverse qubit order
    for (int i = 0; i < n / 2; i++) {
        swap_gate(state, i, n - 1 - i);
    }
}

void inverse_qft(QuantumState *state) {
    int n = state->num_qubits;
    
    // Reverse qubit order
    for (int i = 0; i < n / 2; i++) {
        swap_gate(state, i, n - 1 - i);
    }
    
    for (int j = n - 1; j >= 0; j--) {
        for (int k = n - 1; k > j; k--) {
            double angle = -M_PI / pow(2, k - j);
            controlled_phase(state, k, j, angle);
        }
        
        hadamard(state, j);
    }
}
```

## Testing and Validation

### Unit Tests

```c
void run_all_tests() {
    printf("=== Running Quantum Simulator Tests ===\n\n");
    
    // Phase 1 tests
    printf("Testing state initialization...\n");
    test_initialization();
    
    // Phase 2 tests
    printf("\nTesting single-qubit gates...\n");
    test_hadamard();
    test_pauli_x();
    test_pauli_z();
    
    // Phase 3 tests
    printf("\nTesting multi-qubit gates...\n");
    test_bell_state();
    test_ghz_state();
    
    // Phase 4 tests
    printf("\nTesting measurement...\n");
    test_measurement();
    test_partial_measurement();
    
    // Phase 5 tests
    printf("\nTesting quantum algorithms...\n");
    test_deutsch_jozsa();
    test_grovers();
    test_teleportation();
    
    printf("\n=== All tests completed ===\n");
}
```

### Validation Checklist

- [ ] States are properly normalized (∑|αᵢ|² = 1)
- [ ] Gates preserve normalization
- [ ] Measurement probabilities sum to 1
- [ ] Bell states show 50/50 correlation
- [ ] Grover's finds correct solution
- [ ] QFT followed by inverse QFT returns original state

## Mathematical Foundations

### Linear Algebra Essentials

**Vectors:** Quantum states are complex vectors
```
|ψ⟩ = [α₀, α₁, ..., α_{2ⁿ-1}]ᵀ
```

**Inner Product:** ⟨ψ|φ⟩ = ∑ᵢ ψᵢ* φᵢ

**Outer Product:** |ψ⟩⟨φ| creates matrix

**Tensor Product:** Combines quantum systems
```
|ψ⟩ ⊗ |φ⟩ = |ψφ⟩
```

### Quantum Mechanics Basics

**Superposition:** Linear combinations of basis states

**Entanglement:** Non-separable multi-qubit states

**Measurement:** Projects state onto basis, probabilistic

**No-Cloning:** Cannot copy unknown quantum state

**Unitary Evolution:** U†U = UU† = I

### Complex Numbers in C

```c
Complex z = 3.0 + 4.0*I;      // 3 + 4i
double re = creal(z);          // 3.0
double im = cimag(z);          // 4.0
double mag = cabs(z);          // 5.0
Complex conj = conj(z);        // 3 - 4i
Complex exp_i = cexp(I * M_PI);// e^(iπ) = -1
```

## Complete Examples

### Example 1: Creating Superposition

```c
void example_superposition() {
    QuantumState *state = create_quantum_state(1);
    
    printf("Initial state |0⟩:\n");
    print_state(state);
    
    hadamard(state, 0);
    
    printf("\nAfter Hadamard (superposition):\n");
    print_state(state);
    // Output: |0⟩ and |1⟩ each with 50% probability
    
    destroy_quantum_state(state);
}
```

### Example 2: Creating Entanglement

```c
void example_entanglement() {
    QuantumState *state = create_quantum_state(2);
    
    // Create Bell state: (|00⟩ + |11⟩)/√2
    hadamard(state, 0);
    cnot(state, 0, 1);
    
    printf("Bell state:\n");
    print_state(state);
    
    // Measure first qubit
    int m0 = measure_qubit(state, 0);
    printf("\nFirst qubit measured: %d\n", m0);
    
    // Measure second qubit (will always match first)
    int m1 = measure_qubit(state, 1);
    printf("Second qubit measured: %d\n", m1);
    printf("Qubits are correlated: %s\n", 
           m0 == m1 ? "YES" : "NO");
    
    destroy_quantum_state(state);
}
```

### Example 3: Phase Kickback

```c
void example_phase_kickback() {
    QuantumState *state = create_quantum_state(2);
    
    // Put both qubits in superposition
    hadamard(state, 0);
    hadamard(state, 1);
    
    // Apply controlled-Z
    controlled_z(state, 0, 1);
    
    printf("After controlled-Z:\n");
    print_state(state);
    // Shows phase in |11⟩ component
    
    destroy_quantum_state(state);
}
```

## Resources and References

### Books

1. **"Quantum Computation and Quantum Information"** by Nielsen & Chuang
   - The definitive textbook
   - Comprehensive coverage of all topics

2. **"Quantum Computing: A Gentle Introduction"** by Rieffel & Polak
   - More accessible introduction
   - Good for beginners

3. **"Quantum Computer Science"** by Mermin
   - Focus on computer science aspects
   - Clear explanations

### Online Resources

1. **Qiskit Textbook**: https://qiskit.org/textbook/
   - Free, interactive textbook
   - Python-based examples

2. **IBM Quantum Experience**: https://quantum-computing.ibm.com/
   - Real quantum hardware access
   - Circuit composer

3. **Microsoft Quantum Docs**: https://docs.microsoft.com/quantum/
   - Q# programming language
   - Comprehensive tutorials

4. **Quantum Country**: https://quantum.country/
   - Spaced repetition learning
   - Interactive explanations

### Papers

1. **Deutsch's Algorithm**: D. Deutsch, "Quantum theory, the Church-Turing principle and the universal quantum computer" (1985)

2. **Grover's Algorithm**: L. Grover, "A fast quantum mechanical algorithm for database search" (1996)

3. **Shor's Algorithm**: P. Shor, "Algorithms for quantum computation: discrete logarithms and factoring" (1994)

### Video Courses

1. **MIT OpenCourseWare**: Quantum Computation
2. **Coursera**: Quantum Computing courses from various universities
3. **YouTube**: "Quantum Computing for Computer Scientists" by Microsoft Research

## Performance Optimization

### Memory Management

- Pre-allocate state vectors
- Use memory pools for temporary calculations
- Free resources promptly

### Computational Optimization

- Parallelize independent gate applications
- Use sparse representations for large systems
- Cache frequently used values (like 1/√2)

### Scalability Limits

- 20 qubits: 1M complex numbers (~16 MB)
- 30 qubits: 1B complex numbers (~16 GB)
- 40 qubits: 1T complex numbers (~16 TB)

Real quantum computers scale exponentially better!

## Extensions and Advanced Topics

### 1. Noise and Decoherence

Model realistic quantum errors:
- Bit flip errors
- Phase flip errors
- Amplitude damping
- Depolarizing noise

### 2. Error Correction

Implement quantum error correction codes:
- 3-qubit bit flip code
- Shor's 9-qubit code
- Surface codes

### 3. Variational Algorithms

- VQE (Variational Quantum Eigensolver)
- QAOA (Quantum Approximate Optimization Algorithm)

### 4. Visualization

- Bloch sphere representation
- Circuit diagrams
- State evolution animation

### 5. Advanced Gates

- Arbitrary rotation gates
- Multi-controlled gates
- Approximate gate sets

### 6. Optimization

- Gate fusion
- Circuit simplification
- Transpilation

## Debugging Tips

1. **Check normalization** after every operation
2. **Print intermediate states** during algorithm execution
3. **Verify gate matrices** are unitary
4. **Test with known states** (|0⟩, |1⟩, |+⟩, |−⟩)
5. **Use assertions** to catch errors early

## Common Pitfalls

1. **Forgetting to normalize** after manual amplitude changes
2. **Incorrect qubit indexing** (0-based vs 1-based)
3. **Not handling edge cases** (0 qubits, invalid indices)
4. **Memory leaks** from not freeing states
5. **Numerical precision** issues with floating point

## Conclusion

You've now implemented a complete quantum computing simulator! This foundation enables you to:

- Understand quantum mechanics through programming
- Experiment with quantum algorithms
- Develop intuition for quantum behavior
- Prepare for real quantum hardware

Next steps:
1. Implement additional algorithms (Bernstein-Vazirani, Simon's)
2. Add more gates (U gates, controlled rotations)
3. Optimize for larger qubit counts
4. Add visualization tools
5. Implement error correction codes

Remember: Classical simulation has exponential overhead. Real quantum computers provide exponential speedup for certain problems!

Happy quantum computing! 🚀
