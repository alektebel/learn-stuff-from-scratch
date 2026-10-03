/*
 * Test: Function Call
 * 
 * Tests function definitions and calls.
 * Tests:
 * - Multiple function definitions
 * - Function parameters
 * - Function calls
 * - Return values
 * 
 * Expected: Returns 15 (add(5, 10))
 */

int add(int a, int b) {
    return a + b;
}

int main() {
    int result = add(5, 10);
    return result;
}
