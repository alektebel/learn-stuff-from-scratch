/*
 * Quantum Computing Simulator - Template
 * 
 * This template guides you through building a basic quantum computing simulator.
 * It will simulate qubits, quantum gates, and basic quantum circuits.
 * 
 * Compilation: gcc -o quantum quantum.c -lm
 * (Note: -lm links the math library for complex number operations)
 */

#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <complex.h>

#define MAX_QUBITS 10

/*
 * TODO 1: Define quantum state structure
 * 
 * Guidelines:
 * - A qubit is represented by a state vector: α|0⟩ + β|1⟩
 * - Where α and β are complex numbers with |α|² + |β|² = 1
 * - For n qubits, we need 2^n complex amplitudes
 * - Store number of qubits and state vector
 */
typedef struct {
    int num_qubits;
    double complex *amplitudes;  // Array of 2^num_qubits complex numbers
} QuantumState;

/*
 * TODO 2: Implement quantum state initialization
 * 
 * Guidelines:
 * - Allocate memory for 2^num_qubits complex amplitudes
 * - Initialize all qubits to |0⟩ state
 * - This means amplitude[0] = 1, all others = 0
 */
QuantumState* create_quantum_state(int num_qubits) {
    // TODO: Allocate and initialize quantum state
    return NULL;
}

/*
 * TODO 3: Implement state cleanup
 */
void free_quantum_state(QuantumState *state) {
    // TODO: Free allocated memory
}

/*
 * TODO 4: Implement Hadamard gate
 * 
 * Guidelines:
 * - H = (1/√2) * [[1, 1], [1, -1]]
 * - Creates superposition: H|0⟩ = (|0⟩ + |1⟩)/√2
 * - Apply to a specific qubit in multi-qubit system
 * - Use tensor product for multi-qubit states
 */
void hadamard(QuantumState *state, int target_qubit) {
    // TODO: Apply Hadamard gate to target qubit
}

/*
 * TODO 5: Implement Pauli-X gate (NOT gate)
 * 
 * Guidelines:
 * - X = [[0, 1], [1, 0]]
 * - Flips qubit: X|0⟩ = |1⟩, X|1⟩ = |0⟩
 */
void pauli_x(QuantumState *state, int target_qubit) {
    // TODO: Apply Pauli-X gate
}

/*
 * TODO 6: Implement Pauli-Z gate
 * 
 * Guidelines:
 * - Z = [[1, 0], [0, -1]]
 * - Phase flip: Z|0⟩ = |0⟩, Z|1⟩ = -|1⟩
 */
void pauli_z(QuantumState *state, int target_qubit) {
    // TODO: Apply Pauli-Z gate
}

/*
 * TODO 7: Implement CNOT gate (Controlled-NOT)
 * 
 * Guidelines:
 * - Two-qubit gate: control and target
 * - If control qubit is |1⟩, flip target qubit
 * - CNOT creates entanglement
 * - Matrix: [[1,0,0,0], [0,1,0,0], [0,0,0,1], [0,0,1,0]]
 */
void cnot(QuantumState *state, int control_qubit, int target_qubit) {
    // TODO: Apply CNOT gate
}

/*
 * TODO 8: Implement measurement
 * 
 * Guidelines:
 * - Measure a specific qubit
 * - Probability of |0⟩ is sum of |α_i|² where qubit is 0
 * - Probability of |1⟩ is sum of |α_i|² where qubit is 1
 * - Collapse state after measurement
 * - Return 0 or 1
 */
int measure(QuantumState *state, int target_qubit) {
    // TODO: Implement measurement with collapse
    return 0;
}

/*
 * TODO 9: Implement state printing
 * 
 * Guidelines:
 * - Print all non-zero amplitudes
 * - Show basis states in binary notation
 * - Show probability for each basis state
 */
void print_state(QuantumState *state) {
    // TODO: Print quantum state
    printf("Quantum state with %d qubits:\n", state->num_qubits);
}

/*
 * Helper function to calculate probability of a basis state
 */
double get_probability(QuantumState *state, int basis_state) {
    double complex amp = state->amplitudes[basis_state];
    return creal(amp) * creal(amp) + cimag(amp) * cimag(amp);
}

int main() {
    printf("Quantum Computing Simulator\n\n");
    
    // Example: Create Bell state (maximally entangled state)
    printf("Creating Bell state:\n");
    QuantumState *state = create_quantum_state(2);
    
    if (state) {
        // Apply H to first qubit
        hadamard(state, 0);
        printf("After Hadamard on qubit 0:\n");
        print_state(state);
        
        // Apply CNOT with control=0, target=1
        cnot(state, 0, 1);
        printf("\nAfter CNOT(0,1) - Bell state created:\n");
        print_state(state);
        
        // Measure
        printf("\nMeasuring qubit 0: %d\n", measure(state, 0));
        printf("State after measurement:\n");
        print_state(state);
        
        free_quantum_state(state);
    }
    
    return 0;
}

/*
 * IMPLEMENTATION GUIDE:
 * 
 * Step 1: Implement create_quantum_state and free_quantum_state
 *         Test with simple state creation
 * 
 * Step 2: Implement print_state
 *         Verify initial state is correct
 * 
 * Step 3: Implement single-qubit gates (H, X, Z)
 *         Start with 1-qubit system, then extend to multi-qubit
 * 
 * Step 4: Implement CNOT gate
 *         Test with 2-qubit system
 * 
 * Step 5: Implement measurement
 *         Test probability calculations
 * 
 * Step 6: Test with quantum algorithms
 *         Create Bell states, GHZ states
 * 
 * Learning Resources:
 * - Nielsen & Chuang: "Quantum Computation and Quantum Information"
 * - Qiskit tutorials: https://qiskit.org/textbook/
 * - Complex numbers in C: use <complex.h>
 * 
 * Mathematical Notes:
 * - Qubit: α|0⟩ + β|1⟩ where |α|² + |β|² = 1
 * - 2-qubit basis: |00⟩, |01⟩, |10⟩, |11⟩
 * - Bell state: (|00⟩ + |11⟩)/√2
 */
