# Makefile for Simple Shell - Solution

CC = gcc
CFLAGS = -Wall -Wextra -g
TARGET = shell

all: $(TARGET)

$(TARGET): shell.c
	$(CC) $(CFLAGS) -o $(TARGET) shell.c

clean:
	rm -f $(TARGET)

run: $(TARGET)
	./$(TARGET)

test: $(TARGET)
	@echo "Testing built-in commands..."
	@echo "exit" | ./$(TARGET)
	@echo "Test completed!"

.PHONY: all clean run test
