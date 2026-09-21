# DNS Server Makefile

CC = gcc
CFLAGS = -Wall -Wextra -std=c99
TARGET = dns_server
SOURCE = dns_server.c

.PHONY: all clean run test

all: $(TARGET)

$(TARGET): $(SOURCE)
	$(CC) $(CFLAGS) -o $(TARGET) $(SOURCE)

clean:
	rm -f $(TARGET)

run: $(TARGET)
	@echo "Note: DNS server requires root privileges to bind to port 53"
	@echo "Run with: sudo ./$(TARGET)"
	sudo ./$(TARGET)

test: $(TARGET)
	@echo "Testing DNS server..."
	@echo "Start the server with 'make run' in another terminal"
	@echo "Then test with:"
	@echo "  dig @127.0.0.1 example.com"
	@echo "  nslookup example.com 127.0.0.1"
	@echo "  host example.com 127.0.0.1"

help:
	@echo "DNS Server Makefile"
	@echo ""
	@echo "Targets:"
	@echo "  all   - Build the DNS server (default)"
	@echo "  clean - Remove built files"
	@echo "  run   - Build and run the DNS server (requires sudo)"
	@echo "  test  - Show testing instructions"
	@echo "  help  - Show this help message"
