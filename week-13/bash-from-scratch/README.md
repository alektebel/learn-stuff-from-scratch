# Bash From Scratch (Terminal/Shell)

This directory contains a from-scratch implementation of a command-line shell/terminal similar to Bash.

## Goal
Build a Unix shell to understand:
- Command parsing and execution
- Process management (fork, exec, wait)
- Pipes and redirection
- Signal handling
- Job control
- Shell scripting features

## Learning Path
1. **Basic REPL** - Read-eval-print loop
2. **Command Execution** - Fork and exec system calls
3. **Built-in Commands** - cd, exit, echo, etc.
4. **Pipes** - Inter-process communication
5. **Redirection** - Input/output redirection (<, >, >>)
6. **Environment Variables** - Variable expansion
7. **Job Control** - Background processes, fg, bg
8. **Signal Handling** - Ctrl+C, Ctrl+Z
9. **Scripting Features** - If statements, loops, functions
10. **Advanced Features** - Command history, tab completion

## Features to Implement
- Command line parsing
- PATH resolution
- Wildcard expansion
- Quote handling
- Command substitution
- Aliases

## Video Courses & Resources

**Systems Programming**:
- [15-213 Introduction to Computer Systems - CMU](https://scs.hosted.panopto.com/Panopto/Pages/Sessions/List.aspx#folderID=%22b96d90ae-9871-4fae-91e2-b1627b43e25e%22&maxResults=150)
- [Systems Programming Courses](https://github.com/Developer-Y/cs-video-courses#systems-programming)
- [Operating Systems Courses](https://github.com/Developer-Y/cs-video-courses#operating-systems)

**Additional Resources**:
- [Advanced Programming in the UNIX Environment](https://stevens.netmeister.org/631/)
- [Beej's Guide to Unix IPC](https://beej.us/guide/bgipc/)

## Sources

- Kerrisk, **The Linux Programming Interface** — `fork`, `exec`, `wait`, pipes and signals, chapters 24–27 and 34.
- Stevens & Rago, **Advanced Programming in the UNIX Environment** — the shorter path to the same material.

Full list: [`../../REFERENCES.md`](../../REFERENCES.md#week-1314--sockets-and-protocols)
