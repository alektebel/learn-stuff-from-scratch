/*
 * Test: Nested Blocks
 * 
 * Tests nested scopes and variable shadowing.
 * Tests:
 * - Nested blocks (compound statements)
 * - Variable scoping
 * - Variable shadowing (inner variable hides outer)
 * 
 * Expected: Returns 10 (outer x is 5, inner x is 10, returns inner x)
 */

int main() {
    int x = 5;
    {
        int x = 10;
        return x;  // Returns inner x (10)
    }
    return x;  // Unreachable
}
