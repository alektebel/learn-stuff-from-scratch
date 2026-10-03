# Solutions

This directory contains a complete implementation of a quantum computing simulator.

## Files

- **quantum.c** - Complete quantum circuit simulator with qubits, gates, and measurement

## Building and Running

```bash
gcc -o quantum quantum.c -lm
./quantum
```

Note: The `-lm` flag links the math library for complex number support.

## Features

The simulator implements:

1. **Quantum State Management**
   - Multi-qubit state representation
   - State vector with complex amplitudes
   - Proper normalization

2. **Single-Qubit Gates**
   - Hadamard (H): Creates superposition
   - Pauli-X: Quantum NOT gate
   - Pauli-Z: Phase flip gate

3. **Two-Qubit Gates**
   - CNOT: Controlled-NOT (creates entanglement)

4. **Measurement**
   - Probabilistic measurement with collapse
   - Proper state renormalization

5. **State Visualization**
   - Display amplitudes and probabilities
   - Binary notation for basis states

## Examples Demonstrated

### 1. Superposition

```c
QuantumState *state = create_quantum_state(1);
hadamard(state, 0);
// Creates: (|0⟩ + |1⟩)/√2
```

### 2. Bell State (Entanglement)

```c
QuantumState *state = create_quantum_state(2);
hadamard(state, 0);
cnot(state, 0, 1);
// Creates: (|00⟩ + |11⟩)/√2
```

### 3. GHZ State

```c
QuantumState *state = create_quantum_state(3);
hadamard(state, 0);
cnot(state, 0, 1);
cnot(state, 1, 2);
// Creates: (|000⟩ + |111⟩)/√2
```

## Understanding Quantum States

### State Representation

For n qubits, we store 2^n complex amplitudes:

```
|ψ⟩ = α₀|00...0⟩ + α₁|00...1⟩ + ... + α_{2ⁿ-1}|11...1⟩
```

Where: Σ|αᵢ|² = 1 (normalization)

### Gate Operations

Gates are unitary transformations that preserve normalization:

**Hadamard**: H = (1/√2) [[1, 1], [1, -1]]
- H|0⟩ = (|0⟩ + |1⟩)/√2
- H|1⟩ = (|0⟩ - |1⟩)/√2

**Pauli-X**: X = [[0, 1], [1, 0]]
- X|0⟩ = |1⟩
- X|1⟩ = |0⟩

**CNOT**: Flips target if control is |1⟩

### Measurement

Measurement is probabilistic:
- Probability of outcome = |amplitude|²
- After measurement, state collapses
- Unmeasured qubits may remain in superposition

## Learning Points

1. **Quantum Superposition**
   - States can be in multiple states simultaneously
   - Represented by complex probability amplitudes

2. **Quantum Entanglement**
   - Correlations between qubits
   - Measurement of one affects the other
   - Created by two-qubit gates like CNOT

3. **Measurement and Collapse**
   - Destroys superposition
   - Probabilistic outcome
   - State collapses to measured value

4. **Complex Numbers**
   - Quantum amplitudes are complex
   - Probabilities are |amplitude|²
   - C complex.h library usage

## Quantum Algorithms to Implement

Using this simulator, you can implement:

1. **Deutsch's Algorithm**: Determine if function is constant or balanced
2. **Grover's Algorithm**: Quantum search
3. **Quantum Teleportation**: Transfer quantum state
4. **Superdense Coding**: Send 2 classical bits using 1 qubit
5. **Bernstein-Vazirani Algorithm**: Find hidden bit string

## Extensions to Explore

- More gates (Y, S, T, Toffoli)
- Phase gates and rotation gates
- Quantum Fourier Transform
- Error correction codes
- Noise and decoherence modeling
- Visualization of Bloch sphere
- Circuit optimization

## Resources

- "Quantum Computation and Quantum Information" by Nielsen & Chuang
- Qiskit Textbook: https://qiskit.org/textbook/
- IBM Quantum Experience: https://quantum-computing.ibm.com/
- Microsoft Quantum: https://azure.microsoft.com/en-us/products/quantum/

## Mathematical Background

Key concepts:
- Linear algebra (vectors, matrices, tensor products)
- Complex numbers
- Probability theory
- Quantum mechanics basics
- Group theory (for gates)

## Performance Notes

- State vector size grows as 2^n (exponential in qubit count)
- 20 qubits requires 2^20 = 1M complex numbers
- Real quantum computers: exponential speedup for certain problems
- Classical simulation: exponential slowdown
