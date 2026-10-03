# Makefile for Simple Shell
# TODO: Update this makefile as needed

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

.PHONY: all clean run
