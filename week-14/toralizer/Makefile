# Makefile for Toralizer

CC = gcc
CFLAGS = -Wall -Wextra -std=c99 -g
LDFLAGS = 

# Source files
SOURCES = toralizer.c socks.c network.c
OBJECTS = $(SOURCES:.c=.o)
TARGET = toralizer

# Default target
all: $(TARGET)

# Build the toralizer executable
$(TARGET): $(OBJECTS)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

# Compile individual object files
%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

# Clean build artifacts
clean:
	rm -f $(OBJECTS) $(TARGET)

# Phony targets
.PHONY: all clean

# Dependencies
toralizer.o: toralizer.c socks.h network.h
socks.o: socks.c socks.h
network.o: network.c network.h
