/*
 * Test: Comparison Operators
 * 
 * Tests all comparison operators.
 * Tests:
 * - ==, !=, <, >, <=, >=
 * - Boolean logic (result of comparison used in if)
 * 
 * Expected: Returns 6 (all conditions are true, count increments 6 times)
 */

int main() {
    int count = 0;
    
    if (5 == 5) count = count + 1;
    if (5 != 3) count = count + 1;
    if (3 < 5) count = count + 1;
    if (5 > 3) count = count + 1;
    if (5 <= 5) count = count + 1;
    if (5 >= 5) count = count + 1;
    
    return count;
}
