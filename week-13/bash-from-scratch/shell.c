/*
 * Simple Shell Implementation - Template
 * 
 * This is a template file to help you build a Unix shell from scratch.
 * Follow the TODOs and implement each section step by step.
 * 
 * Compilation: gcc -o shell shell.c
 * Usage: ./shell
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>
#include <sys/types.h>

#define MAX_INPUT_SIZE 1024
#define MAX_ARGS 64
#define MAX_PATH_SIZE 256

/*
 * TODO 1: Implement the display_prompt function
 * 
 * Guidelines:
 * - Display the current working directory
 * - Use getcwd() to get the current directory
 * - Add a prompt symbol like "$ " or "> "
 * - Make it visually clear where user should type
 */
void display_prompt() {
    // TODO: Implement prompt display
    printf("> ");
    fflush(stdout);
}

/*
 * TODO 2: Implement read_input function
 * 
 * Guidelines:
 * - Read a line of input from stdin
 * - Use fgets() for safe input reading
 * - Remove the trailing newline character
 * - Handle empty input gracefully
 * - Return NULL on EOF (Ctrl+D)
 */
char* read_input() {
    // TODO: Implement input reading
    return NULL;
}

/*
 * TODO 3: Implement parse_input function
 * 
 * Guidelines:
 * - Split the input string into tokens (arguments)
 * - Use strtok() to tokenize the string
 * - Handle spaces, tabs as delimiters
 * - Store tokens in an array
 * - NULL-terminate the array (required for execvp)
 * - Handle quoted strings as single arguments (advanced)
 */
char** parse_input(char* input) {
    // TODO: Implement input parsing
    return NULL;
}

/*
 * TODO 4: Implement built-in command: cd
 * 
 * Guidelines:
 * - Use chdir() system call to change directory
 * - Handle "cd" (go to home directory)
 * - Handle "cd <path>"
 * - Print error message if directory doesn't exist
 * - Return 1 on success, 0 on failure
 */
int builtin_cd(char** args) {
    // TODO: Implement cd command
    return 0;
}

/*
 * TODO 5: Implement built-in command: exit
 * 
 * Guidelines:
 * - Simply call exit(0) to terminate the shell
 * - Optionally support "exit <code>" for custom exit codes
 */
int builtin_exit(char** args) {
    // TODO: Implement exit command
    return 0;
}

/*
 * TODO 6: Implement execute_builtin function
 * 
 * Guidelines:
 * - Check if the command is a built-in (cd, exit, pwd, etc.)
 * - Call the appropriate built-in function
 * - Return 1 if command was a built-in, 0 otherwise
 */
int execute_builtin(char** args) {
    // TODO: Check and execute built-in commands
    return 0;
}

/*
 * TODO 7: Implement execute_command function
 * 
 * Guidelines:
 * - Fork a new process using fork()
 * - In child process: use execvp() to execute the command
 * - In parent process: wait for child to complete using waitpid()
 * - Handle fork errors
 * - Handle execvp errors (command not found)
 * - Return the exit status of the command
 */
int execute_command(char** args) {
    // TODO: Implement command execution with fork/exec
    return 0;
}

/*
 * TODO 8 (Advanced): Implement pipe support
 * 
 * Guidelines:
 * - Detect pipe character '|' in the command
 * - Split command into segments
 * - Use pipe() system call to create pipe
 * - Fork processes for each segment
 * - Connect stdout of one process to stdin of next
 * - Close unused file descriptors
 */
int execute_with_pipes(char** args) {
    // TODO: Implement pipe support (Advanced)
    return 0;
}

/*
 * TODO 9 (Advanced): Implement redirection support
 * 
 * Guidelines:
 * - Detect redirection operators: <, >, >>
 * - Use open() to open files
 * - Use dup2() to redirect file descriptors
 * - Handle input redirection (<)
 * - Handle output redirection (>)
 * - Handle append mode (>>)
 */
int handle_redirection(char** args) {
    // TODO: Implement redirection support (Advanced)
    return 0;
}

/*
 * Main shell loop
 * 
 * This is the main function that runs the shell loop.
 * You should not need to modify this much.
 */
int main(int argc, char** argv) {
    char* input;
    char** args;
    int status = 1;

    // Main shell loop
    while (status) {
        display_prompt();
        input = read_input();
        
        if (input == NULL) {
            // EOF reached (Ctrl+D)
            printf("\n");
            break;
        }

        if (strlen(input) == 0) {
            free(input);
            continue;
        }

        args = parse_input(input);
        
        if (args == NULL || args[0] == NULL) {
            free(input);
            continue;
        }

        // Try built-in commands first
        if (!execute_builtin(args)) {
            // If not a built-in, execute as external command
            execute_command(args);
        }

        free(input);
        free(args);
    }

    return 0;
}

/*
 * IMPLEMENTATION GUIDE:
 * 
 * Step 1: Start with display_prompt() and read_input()
 *         Test that you can read and display user input
 * 
 * Step 2: Implement parse_input() to split commands into arguments
 *         Test with printf to see if parsing works correctly
 * 
 * Step 3: Implement basic built-ins (exit, cd)
 *         Test that you can exit and change directories
 * 
 * Step 4: Implement execute_command() with fork/exec
 *         Test with simple commands like "ls", "echo hello"
 * 
 * Step 5 (Advanced): Add pipe support
 *         Test with commands like "ls | grep .c"
 * 
 * Step 6 (Advanced): Add redirection support
 *         Test with commands like "ls > output.txt"
 * 
 * Testing Tips:
 * - Test each function independently
 * - Start with simple cases, then add complexity
 * - Use printf for debugging
 * - Test error cases (invalid commands, missing files, etc.)
 */
