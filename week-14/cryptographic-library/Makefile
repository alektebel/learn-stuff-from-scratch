# Makefile for SHA-256 Cryptographic Implementation

CC = gcc
CFLAGS = -Wall -Wextra -g
TARGET = sha256

all: $(TARGET)

$(TARGET): sha256.c
	$(CC) $(CFLAGS) -o $(TARGET) sha256.c

clean:
	rm -f $(TARGET)

run: $(TARGET)
	./$(TARGET)

test: $(TARGET)
	@echo "Running SHA-256 tests..."
	./$(TARGET)

.PHONY: all clean run test
