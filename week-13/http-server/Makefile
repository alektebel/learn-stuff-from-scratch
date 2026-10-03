# Makefile for HTTP Server

CC = gcc
CFLAGS = -Wall -Wextra -g
TARGET = http_server

all: $(TARGET)

$(TARGET): http_server.c
	$(CC) $(CFLAGS) -o $(TARGET) http_server.c

clean:
	rm -f $(TARGET)

run: $(TARGET)
	./$(TARGET) 8080

test: $(TARGET)
	@echo "Starting server on port 8080..."
	@echo "Open http://localhost:8080 in your browser"
	@echo "Or use: curl http://localhost:8080"
	./$(TARGET) 8080

.PHONY: all clean run test
