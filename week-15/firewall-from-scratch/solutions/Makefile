# Firewall Solution Makefile

CC = gcc
CFLAGS = -Wall -Wextra -std=c99 -g
TARGET = firewall
SOURCE = firewall.c

.PHONY: all clean run test help

all: $(TARGET)

$(TARGET): $(SOURCE)
	$(CC) $(CFLAGS) -o $(TARGET) $(SOURCE)

clean:
	rm -f $(TARGET)

run: $(TARGET)
	@echo "========================================="
	@echo "  Starting Firewall (Solution)"
	@echo "========================================="
	@echo "Note: Firewall requires root privileges for raw socket access"
	@echo "Press Ctrl+C to stop the firewall"
	@echo ""
	sudo ./$(TARGET)

test: $(TARGET)
	@echo "========================================="
	@echo "  Firewall Testing"
	@echo "========================================="
	@echo ""
	@echo "1. Start the firewall in one terminal:"
	@echo "   sudo ./$(TARGET)"
	@echo ""
	@echo "2. In another terminal, test with:"
	@echo "   ping 8.8.8.8"
	@echo "   curl http://example.com"
	@echo ""

help:
	@echo "Firewall Solution Makefile"
	@echo ""
	@echo "Targets:"
	@echo "  all   - Build the firewall (default)"
	@echo "  clean - Remove built files"
	@echo "  run   - Build and run the firewall (requires sudo)"
	@echo "  test  - Show testing instructions"
	@echo "  help  - Show this help message"
