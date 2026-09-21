/*
 * Quantum Computing Simulator - Complete Solution
 */

#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <complex.h>
#include <time.h>

#define MAX_QUBITS 10

typedef struct {
    int num_qubits;
    double complex *amplitudes;
} QuantumState;

QuantumState* create_quantum_state(int num_qubits) {
    if (num_qubits <= 0 || num_qubits > MAX_QUBITS) {
        return NULL;
    }
    
    QuantumState *state = malloc(sizeof(QuantumState));
    state->num_qubits = num_qubits;
    
    int size = 1 << num_qubits;  // 2^num_qubits
    state->amplitudes = calloc(size, sizeof(double complex));
    
    // Initialize to |0...0⟩ state
    state->amplitudes[0] = 1.0 + 0.0*I;
    
    return state;
}

void free_quantum_state(QuantumState *state) {
    if (state) {
        free(state->amplitudes);
        free(state);
    }
}

void hadamard(QuantumState *state, int target_qubit) {
    int size = 1 << state->num_qubits;
    int target_mask = 1 << target_qubit;
    double inv_sqrt2 = 1.0 / sqrt(2.0);
    
    for (int i = 0; i < size; i++) {
        if ((i & target_mask) == 0) {
            int j = i | target_mask;
            double complex a = state->amplitudes[i];
            double complex b = state->amplitudes[j];
            state->amplitudes[i] = (a + b) * inv_sqrt2;
            state->amplitudes[j] = (a - b) * inv_sqrt2;
        }
    }
}

void pauli_x(QuantumState *state, int target_qubit) {
    int size = 1 << state->num_qubits;
    int target_mask = 1 << target_qubit;
    
    for (int i = 0; i < size; i++) {
        if ((i & target_mask) == 0) {
            int j = i | target_mask;
            double complex temp = state->amplitudes[i];
            state->amplitudes[i] = state->amplitudes[j];
            state->amplitudes[j] = temp;
        }
    }
}

void pauli_z(QuantumState *state, int target_qubit) {
    int size = 1 << state->num_qubits;
    int target_mask = 1 << target_qubit;
    
    for (int i = 0; i < size; i++) {
        if (i & target_mask) {
            state->amplitudes[i] = -state->amplitudes[i];
        }
    }
}

void cnot(QuantumState *state, int control_qubit, int target_qubit) {
    int size = 1 << state->num_qubits;
    int control_mask = 1 << control_qubit;
    int target_mask = 1 << target_qubit;
    
    for (int i = 0; i < size; i++) {
        // Only flip target if control is 1 and we haven't processed this pair
        if ((i & control_mask) && !(i & target_mask)) {
            int j = i | target_mask;
            double complex temp = state->amplitudes[i];
            state->amplitudes[i] = state->amplitudes[j];
            state->amplitudes[j] = temp;
        }
    }
}

double get_probability(QuantumState *state, int basis_state) {
    double complex amp = state->amplitudes[basis_state];
    return creal(amp) * creal(amp) + cimag(amp) * cimag(amp);
}

int measure(QuantumState *state, int target_qubit) {
    int size = 1 << state->num_qubits;
    int target_mask = 1 << target_qubit;
    
    // Calculate probability of measuring 0
    double prob_0 = 0.0;
    for (int i = 0; i < size; i++) {
        if ((i & target_mask) == 0) {
            prob_0 += get_probability(state, i);
        }
    }
    
    // Random measurement based on probability
    double random = (double)rand() / RAND_MAX;
    int result = (random < prob_0) ? 0 : 1;
    
    // Collapse the state
    double norm = 0.0;
    for (int i = 0; i < size; i++) {
        if (((i & target_mask) >> target_qubit) != result) {
            state->amplitudes[i] = 0.0;
        } else {
            norm += get_probability(state, i);
        }
    }
    
    // Renormalize
    norm = sqrt(norm);
    if (norm > 1e-10) {
        for (int i = 0; i < size; i++) {
            state->amplitudes[i] /= norm;
        }
    }
    
    return result;
}

void print_state(QuantumState *state) {
    int size = 1 << state->num_qubits;
    printf("Quantum state with %d qubit(s):\n", state->num_qubits);
    
    for (int i = 0; i < size; i++) {
        double prob = get_probability(state, i);
        if (prob > 1e-10) {
            // Print basis state in binary
            printf("|");
            for (int q = state->num_qubits - 1; q >= 0; q--) {
                printf("%d", (i >> q) & 1);
            }
            printf("⟩: %.6f%+.6fi (prob: %.4f)\n", 
                   creal(state->amplitudes[i]), 
                   cimag(state->amplitudes[i]), 
                   prob);
        }
    }
    printf("\n");
}

int main() {
    srand(time(NULL));
    
    printf("Quantum Computing Simulator - Complete Solution\n\n");
    
    // Example 1: Single qubit superposition
    printf("=== Example 1: Superposition ===\n");
    QuantumState *state1 = create_quantum_state(1);
    printf("Initial state:\n");
    print_state(state1);
    
    hadamard(state1, 0);
    printf("After Hadamard:\n");
    print_state(state1);
    free_quantum_state(state1);
    
    // Example 2: Bell state (entanglement)
    printf("=== Example 2: Bell State (Entanglement) ===\n");
    QuantumState *state2 = create_quantum_state(2);
    
    hadamard(state2, 0);
    printf("After H on qubit 0:\n");
    print_state(state2);
    
    cnot(state2, 0, 1);
    printf("After CNOT(0,1) - Bell state:\n");
    print_state(state2);
    
    printf("Measuring qubit 0...\n");
    int result = measure(state2, 0);
    printf("Measured: %d\n", result);
    printf("State after measurement (collapsed):\n");
    print_state(state2);
    
    free_quantum_state(state2);
    
    // Example 3: GHZ state (3-qubit entanglement)
    printf("=== Example 3: GHZ State ===\n");
    QuantumState *state3 = create_quantum_state(3);
    
    hadamard(state3, 0);
    cnot(state3, 0, 1);
    cnot(state3, 1, 2);
    printf("GHZ state: (|000⟩ + |111⟩)/√2\n");
    print_state(state3);
    
    free_quantum_state(state3);
    
    return 0;
}
