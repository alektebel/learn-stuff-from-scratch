# Solutions

This directory contains complete implementations of the lexer for a C compiler.

## Files

- **lexer.c** - Complete lexical analyzer (tokenizer) for C

## Building and Running

```bash
gcc -o lexer lexer.c
./lexer
```

## Features

The lexer implementation includes:

1. **Keyword Recognition**: int, return, if, else, while, for
2. **Operators**: +, -, *, /, =, ==, !=, <, >, <=, >=
3. **Delimiters**: ;, ,, (, ), {, }
4. **Identifiers**: Variable and function names
5. **Number Literals**: Integer constants
6. **Position Tracking**: Line and column numbers for error reporting

## Usage

The lexer converts source code into a stream of tokens:

```c
const char* source = "int x = 42;";
Token** tokens = tokenize(source);

// Process tokens
for (int i = 0; tokens[i] != NULL; i++) {
    print_token(tokens[i]);
    free(tokens[i]);
}
free(tokens);
```

## Example Output

Input:
```c
int main() {
    int x = 42;
    return x;
}
```

Output:
```
INT        'int' (line 1, col 1)
IDENT      'main' (line 1, col 5)
LPAREN     '(' (line 1, col 9)
RPAREN     ')' (line 1, col 10)
LBRACE     '{' (line 1, col 12)
INT        'int' (line 2, col 5)
IDENT      'x' (line 2, col 9)
ASSIGN     '=' (line 2, col 11)
NUMBER     '42' (line 2, col 13)
SEMI       ';' (line 2, col 15)
...
```

## Learning Points

- Lexical analysis fundamentals
- Character-by-character parsing
- State machines for tokenization
- Keyword vs identifier discrimination
- Multi-character operator recognition
- Error detection and reporting

## Next Steps

After completing the lexer, the next phase is:

1. **Parser**: Build an abstract syntax tree (AST) from tokens
2. **Semantic Analysis**: Type checking and validation
3. **Code Generation**: Produce assembly or intermediate code
4. **Optimization**: Improve generated code

## Extensions to Explore

- String literals with escape sequences
- Character literals
- Floating-point numbers
- Preprocessor directives (#include, #define)
- Comments (// and /* */)
- Additional operators (++, --, &, |, ^, <<, >>)
- Additional keywords (struct, typedef, const, etc.)

## Resources

- "Compilers: Principles, Techniques, and Tools" (Dragon Book)
- "Engineering a Compiler" by Cooper & Torczon
- ANSI C Specification (ISO/IEC 9899)
