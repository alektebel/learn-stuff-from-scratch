/*
 * Simple Shell Implementation - Complete Solution
 * 
 * This is a complete implementation of a basic Unix shell.
 * It demonstrates all the concepts needed to build a working shell.
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
#include <fcntl.h>

#define MAX_INPUT_SIZE 1024
#define MAX_ARGS 64
#define MAX_PATH_SIZE 256

void display_prompt() {
    char cwd[MAX_PATH_SIZE];
    if (getcwd(cwd, sizeof(cwd)) != NULL) {
        printf("%s $ ", cwd);
    } else {
        printf("$ ");
    }
    fflush(stdout);
}

char* read_input() {
    char* input = malloc(MAX_INPUT_SIZE);
    if (input == NULL) {
        fprintf(stderr, "Allocation error\n");
        exit(EXIT_FAILURE);
    }

    if (fgets(input, MAX_INPUT_SIZE, stdin) == NULL) {
        free(input);
        return NULL;
    }

    // Remove trailing newline
    size_t len = strlen(input);
    if (len > 0 && input[len - 1] == '\n') {
        input[len - 1] = '\0';
    }

    return input;
}

char** parse_input(char* input) {
    char** tokens = malloc(MAX_ARGS * sizeof(char*));
    if (tokens == NULL) {
        fprintf(stderr, "Allocation error\n");
        exit(EXIT_FAILURE);
    }

    int position = 0;
    char* token = strtok(input, " \t\n\r");
    
    while (token != NULL && position < MAX_ARGS - 1) {
        tokens[position] = token;
        position++;
        token = strtok(NULL, " \t\n\r");
    }
    
    tokens[position] = NULL;
    return tokens;
}

int builtin_cd(char** args) {
    if (args[1] == NULL) {
        // No argument, go to home directory
        char* home = getenv("HOME");
        if (home == NULL) {
            fprintf(stderr, "cd: HOME not set\n");
            return 0;
        }
        if (chdir(home) != 0) {
            perror("cd");
            return 0;
        }
    } else {
        // Change to specified directory
        if (chdir(args[1]) != 0) {
            perror("cd");
            return 0;
        }
    }
    return 1;
}

int builtin_exit(char** args) {
    int exit_code = 0;
    if (args[1] != NULL) {
        exit_code = atoi(args[1]);
    }
    exit(exit_code);
    return 1;
}

int builtin_pwd(char** args) {
    char cwd[MAX_PATH_SIZE];
    if (getcwd(cwd, sizeof(cwd)) != NULL) {
        printf("%s\n", cwd);
        return 1;
    } else {
        perror("pwd");
        return 0;
    }
}

int execute_builtin(char** args) {
    if (args[0] == NULL) {
        return 0;
    }

    if (strcmp(args[0], "cd") == 0) {
        return builtin_cd(args);
    } else if (strcmp(args[0], "exit") == 0) {
        return builtin_exit(args);
    } else if (strcmp(args[0], "pwd") == 0) {
        return builtin_pwd(args);
    }

    return 0;
}

int execute_command(char** args) {
    if (args[0] == NULL) {
        return 1;
    }

    pid_t pid = fork();
    
    if (pid < 0) {
        // Fork failed
        perror("fork");
        return 0;
    } else if (pid == 0) {
        // Child process
        if (execvp(args[0], args) == -1) {
            perror("shell");
        }
        exit(EXIT_FAILURE);
    } else {
        // Parent process
        int status;
        waitpid(pid, &status, 0);
        return 1;
    }
}

int find_pipe(char** args) {
    for (int i = 0; args[i] != NULL; i++) {
        if (strcmp(args[i], "|") == 0) {
            return i;
        }
    }
    return -1;
}

int execute_with_pipes(char** args) {
    int pipe_pos = find_pipe(args);
    
    if (pipe_pos == -1) {
        // No pipe found, execute normally
        return execute_command(args);
    }

    // Split commands at pipe
    args[pipe_pos] = NULL;
    char** cmd1 = args;
    char** cmd2 = args + pipe_pos + 1;

    int pipefd[2];
    if (pipe(pipefd) == -1) {
        perror("pipe");
        return 0;
    }

    pid_t pid1 = fork();
    if (pid1 == 0) {
        // First command - write to pipe
        close(pipefd[0]); // Close read end
        dup2(pipefd[1], STDOUT_FILENO);
        close(pipefd[1]);
        
        if (execvp(cmd1[0], cmd1) == -1) {
            perror("shell");
            exit(EXIT_FAILURE);
        }
    }

    pid_t pid2 = fork();
    if (pid2 == 0) {
        // Second command - read from pipe
        close(pipefd[1]); // Close write end
        dup2(pipefd[0], STDIN_FILENO);
        close(pipefd[0]);
        
        if (execvp(cmd2[0], cmd2) == -1) {
            perror("shell");
            exit(EXIT_FAILURE);
        }
    }

    // Parent closes both ends and waits
    close(pipefd[0]);
    close(pipefd[1]);
    waitpid(pid1, NULL, 0);
    waitpid(pid2, NULL, 0);

    return 1;
}

int handle_redirection(char** args) {
    for (int i = 0; args[i] != NULL; i++) {
        if (strcmp(args[i], ">") == 0 && args[i + 1] != NULL) {
            // Output redirection
            args[i] = NULL;
            int fd = open(args[i + 1], O_WRONLY | O_CREAT | O_TRUNC, 0644);
            if (fd < 0) {
                perror("open");
                return 0;
            }
            dup2(fd, STDOUT_FILENO);
            close(fd);
            return 1;
        } else if (strcmp(args[i], ">>") == 0 && args[i + 1] != NULL) {
            // Append redirection
            args[i] = NULL;
            int fd = open(args[i + 1], O_WRONLY | O_CREAT | O_APPEND, 0644);
            if (fd < 0) {
                perror("open");
                return 0;
            }
            dup2(fd, STDOUT_FILENO);
            close(fd);
            return 1;
        } else if (strcmp(args[i], "<") == 0 && args[i + 1] != NULL) {
            // Input redirection
            args[i] = NULL;
            int fd = open(args[i + 1], O_RDONLY);
            if (fd < 0) {
                perror("open");
                return 0;
            }
            dup2(fd, STDIN_FILENO);
            close(fd);
            return 1;
        }
    }
    return 0;
}

int main(int argc, char** argv) {
    char* input;
    char** args;
    int status = 1;

    printf("Simple Shell - Type 'exit' to quit\n");

    while (status) {
        display_prompt();
        input = read_input();
        
        if (input == NULL) {
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

        if (!execute_builtin(args)) {
            execute_with_pipes(args);
        }

        free(input);
        free(args);
    }

    return 0;
}
