# C Compiler Test Suite

This directory contains test programs for the C compiler implementation.

## Test Categories

### Basic Tests
- `test_simple_return.c`: Minimal program (return 0)
- `test_arithmetic.c`: Basic arithmetic operations
- `test_variables.c`: Variable declaration and usage

### Control Flow Tests
- `test_if_else.c`: If-else statements
- `test_while_loop.c`: While loops
- `test_for_loop.c`: For loops
- `test_nested_scopes.c`: Nested blocks and scoping

### Function Tests
- `test_function_call.c`: Function definition and calling

### Operator Tests
- `test_comparisons.c`: Comparison operators (==, !=, <, >, <=, >=)

## Running Tests

### Manual Testing

Test individual programs:

```bash
# Compile with your compiler
./codegen tests/test_simple_return.c -o output.s
gcc output.s -o test_prog
./test_prog
echo $?  # Should print expected return value

# Compare with GCC
gcc tests/test_simple_return.c -o gcc_prog
./gcc_prog
echo $?  # Should match
```

### Automated Testing

Create a test script (`run_tests.sh`):

```bash
#!/bin/bash

PASSED=0
FAILED=0

for test in tests/*.c; do
    echo "Testing: $test"
    
    # Get expected result from GCC
    gcc "$test" -o gcc_prog 2>/dev/null
    ./gcc_prog
    expected=$?
    
    # Get result from our compiler
    ./codegen "$test" -o output.s 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "  ✗ FAIL: Compilation error"
        FAILED=$((FAILED + 1))
        continue
    fi
    
    gcc output.s -o test_prog 2>/dev/null
    ./test_prog
    actual=$?
    
    if [ $expected -eq $actual ]; then
        echo "  ✓ PASS (returned $actual)"
        PASSED=$((PASSED + 1))
    else
        echo "  ✗ FAIL (got $actual, expected $expected)"
        FAILED=$((FAILED + 1))
    fi
    
    # Cleanup
    rm -f gcc_prog test_prog output.s
done

echo ""
echo "Results: $PASSED passed, $FAILED failed"
```

Make it executable and run:

```bash
chmod +x run_tests.sh
./run_tests.sh
```

## Expected Results

| Test File | Expected Return Value | Description |
|-----------|----------------------|-------------|
| `test_simple_return.c` | 0 | Returns 0 |
| `test_arithmetic.c` | 14 | 2 + 3 * 4 = 14 |
| `test_variables.c` | 15 | 5 + 10 = 15 |
| `test_if_else.c` | 1 | 5 > 3 is true |
| `test_while_loop.c` | 10 | Sum of 1+2+3+4 |
| `test_for_loop.c` | 15 | Sum of 0+1+2+3+4+5 |
| `test_function_call.c` | 15 | add(5, 10) = 15 |
| `test_nested_scopes.c` | 10 | Returns inner x |
| `test_comparisons.c` | 6 | All 6 comparisons true |

## Writing New Tests

### Test Template

```c
/*
 * Test: [Test Name]
 * 
 * Tests [what features are being tested].
 * Tests:
 * - Feature 1
 * - Feature 2
 * 
 * Expected: [Expected behavior and return value]
 */

int main() {
    // Test code here
    return expected_value;
}
```

### Guidelines

1. **One concept per test**: Each test should focus on one feature or aspect
2. **Clear expected behavior**: Document what should happen
3. **Deterministic**: Tests should always produce the same result
4. **Simple return values**: Use return values to indicate success (easy to check)
5. **Incremental complexity**: Start simple, gradually add complexity

### Example: Adding a New Test

```c
/*
 * Test: Logical Operators
 * 
 * Tests logical AND (&&) and OR (||) operators.
 * Tests:
 * - && operator
 * - || operator
 * - Short-circuit evaluation (if implemented)
 * 
 * Expected: Returns 3
 */

int main() {
    int result = 0;
    
    // Test AND (both true)
    if (1 && 1) {
        result = result + 1;  // Should execute
    }
    
    // Test AND (one false)
    if (1 && 0) {
        result = result + 1;  // Should NOT execute
    }
    
    // Test OR (one true)
    if (1 || 0) {
        result = result + 1;  // Should execute
    }
    
    // Test OR (both false)
    if (0 || 0) {
        result = result + 1;  // Should NOT execute
    }
    
    // Test combined
    if ((1 && 1) || 0) {
        result = result + 1;  // Should execute
    }
    
    return result;  // Expected: 3
}
```

## Error Tests

Create tests that should fail compilation (for semantic analyzer):

```c
// test_error_undeclared.c
int main() {
    return x;  // Error: x not declared
}

// test_error_type_mismatch.c
int main() {
    int x = 5;
    return x + "hello";  // Error: can't add int and string
}

// test_error_wrong_args.c
int foo(int a) {
    return a;
}

int main() {
    return foo(1, 2);  // Error: too many arguments
}
```

These should be tested differently:

```bash
# Should fail compilation
./semantic tests/test_error_undeclared.c
if [ $? -ne 0 ]; then
    echo "✓ Correctly detected error"
else
    echo "✗ Should have failed"
fi
```

## Debugging Failed Tests

When a test fails:

1. **Check tokens**: Run lexer on the test file
   ```bash
   ./lexer tests/test_name.c
   ```

2. **Check AST**: Run parser and print AST
   ```bash
   ./parser tests/test_name.c
   ```

3. **Check types**: Run semantic analyzer
   ```bash
   ./semantic tests/test_name.c
   ```

4. **Check assembly**: Inspect generated code
   ```bash
   ./codegen tests/test_name.c -o output.s
   cat output.s
   ```

5. **Compare with GCC**: See what GCC generates
   ```bash
   gcc -S tests/test_name.c -o gcc_output.s
   diff output.s gcc_output.s
   ```

## Performance Tests

For measuring optimization effectiveness:

```c
// test_optimization.c
int main() {
    // Should be optimized to: return 5;
    return 2 + 3;
}
```

Check if constant folding works:
```bash
./optimizer tests/test_optimization.c
# Inspect optimized AST - should show LITERAL(5) not ADD(2,3)
```

## Coverage

Ensure tests cover:
- ✓ All token types
- ✓ All statement types
- ✓ All expression types
- ✓ All operators
- ✓ Function calls with various argument counts
- ✓ Nested scopes
- ✓ Control flow (if, loops)
- ✓ Edge cases (empty blocks, single statements, etc.)
- ✓ Error cases (for semantic analyzer)

## Continuous Testing

As you implement each compiler phase:
1. Write tests for that phase
2. Run tests frequently
3. Keep all previous tests passing
4. Add regression tests for bugs you fix

## Resources

- Test-driven development (TDD) for compilers
- GCC test suite for inspiration
- LLVM test suite examples
