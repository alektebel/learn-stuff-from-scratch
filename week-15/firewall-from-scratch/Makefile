# Firewall Makefile

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
	@echo "  Starting Firewall"
	@echo "========================================="
	@echo "Note: Firewall requires root privileges for raw socket access"
	@echo "Press Ctrl+C to stop the firewall"
	@echo ""
	sudo ./$(TARGET)

test: $(TARGET)
	@echo "========================================="
	@echo "  Firewall Testing Guide"
	@echo "========================================="
	@echo ""
	@echo "1. Start the firewall in one terminal:"
	@echo "   sudo ./$(TARGET)"
	@echo ""
	@echo "2. In another terminal, test with these commands:"
	@echo ""
	@echo "   # Test ICMP (ping) blocking:"
	@echo "   ping 8.8.8.8"
	@echo ""
	@echo "   # Test HTTP traffic:"
	@echo "   curl http://example.com"
	@echo ""
	@echo "   # View packets with tcpdump:"
	@echo "   sudo tcpdump -i eth0 -n"
	@echo ""
	@echo "   # Scan ports with nmap:"
	@echo "   nmap -sS localhost"
	@echo ""
	@echo "For detailed testing instructions, see TESTING_GUIDE.md"
	@echo ""

debug: CFLAGS += -DDEBUG -g
debug: clean $(TARGET)
	@echo "Built with debug symbols"

valgrind: $(TARGET)
	sudo valgrind --leak-check=full --show-leak-kinds=all --track-origins=yes ./$(TARGET)

help:
	@echo "Firewall Makefile"
	@echo ""
	@echo "Targets:"
	@echo "  all      - Build the firewall (default)"
	@echo "  clean    - Remove built files"
	@echo "  run      - Build and run the firewall (requires sudo)"
	@echo "  test     - Show testing instructions"
	@echo "  debug    - Build with debug symbols"
	@echo "  valgrind - Run with valgrind memory checker"
	@echo "  help     - Show this help message"
	@echo ""
	@echo "Usage examples:"
	@echo "  make              # Build the firewall"
	@echo "  make run          # Build and run with default settings"
	@echo "  sudo ./firewall   # Run manually"
	@echo "  make clean        # Clean build artifacts"
