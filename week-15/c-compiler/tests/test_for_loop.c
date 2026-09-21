/*
 * Test: For Loop
 * 
 * Tests for loop functionality.
 * Tests:
 * - For loop
 * - Initialization, condition, increment
 * - Variable modification in loop
 * 
 * Expected: Returns 15 (sum of 0+1+2+3+4+5)
 */

int main() {
    int sum = 0;
    int i;
    
    for (i = 0; i < 6; i = i + 1) {
        sum = sum + i;
    }
    
    return sum;
}
