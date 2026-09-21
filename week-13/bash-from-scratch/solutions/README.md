# Solutions

This directory contains complete, working implementations of the shell project.

## Files

- **shell.c** - Complete implementation of a Unix shell with:
  - Command parsing and execution
  - Built-in commands (cd, exit, pwd)
  - Fork/exec for external commands
  - Pipe support for command chaining
  - Input/output redirection
  - Error handling

- **Makefile** - Build configuration for the shell

## Building and Running

```bash
make
./shell
```

## Features Demonstrated

1. **Basic REPL**: Read-Eval-Print Loop for interactive command execution
2. **Process Management**: Using fork(), exec(), and waitpid()
3. **Built-in Commands**: cd, exit, pwd implemented directly
4. **External Commands**: Execution of system commands via PATH resolution
5. **Pipes**: Command chaining with | operator
6. **Redirection**: Input (<), output (>), and append (>>)
7. **Error Handling**: Graceful handling of invalid commands and system errors

## Usage Examples

```bash
# Basic commands
$ ls
$ pwd
$ cd /tmp

# Pipes
$ ls | grep .c
$ cat file.txt | wc -l

# Redirection
$ ls > output.txt
$ cat < input.txt
$ echo "hello" >> log.txt

# Exit
$ exit
```

## Learning Points

- System calls: fork(), exec(), pipe(), dup2(), chdir()
- Process creation and management
- File descriptor manipulation
- String parsing and tokenization
- Memory management in C
- Error handling with errno and perror()

## Notes

This is a simplified shell for educational purposes. A production shell would include:
- Job control (bg, fg, jobs)
- Signal handling (Ctrl+C, Ctrl+Z)
- Command history
- Tab completion
- Environment variable expansion
- Alias support
- Scripting features (if, while, functions)
