# Makefile for Quantum Computing Simulator

CC = gcc
CFLAGS = -Wall -Wextra -g
LDFLAGS = -lm
TARGET = quantum

all: $(TARGET)

$(TARGET): quantum.c
	$(CC) $(CFLAGS) -o $(TARGET) quantum.c $(LDFLAGS)

clean:
	rm -f $(TARGET)

run: $(TARGET)
	./$(TARGET)

test: $(TARGET)
	@echo "Running quantum simulator tests..."
	./$(TARGET)

.PHONY: all clean run test
