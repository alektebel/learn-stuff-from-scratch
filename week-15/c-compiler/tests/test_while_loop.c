/*
 * Test: While Loop
 * 
 * Tests while loop functionality.
 * Tests:
 * - While loop
 * - Loop condition
 * - Variable modification in loop
 * - Comparison operators
 * 
 * Expected: Returns 10 (sum of 1+2+3+4)
 */

int main() {
    int i = 1;
    int sum = 0;
    
    while (i < 5) {
        sum = sum + i;
        i = i + 1;
    }
    
    return sum;
}
