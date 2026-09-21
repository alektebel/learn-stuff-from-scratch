# Communication Protocols Makefile

CC     = gcc
CFLAGS = -Wall -Wextra -std=c99 -g
TARGETS = uart spi i2c can rs485

.PHONY: all clean run help $(TARGETS)

all: $(TARGETS)

uart: uart.c
	$(CC) $(CFLAGS) -o uart uart.c

spi: spi.c
	$(CC) $(CFLAGS) -o spi spi.c

i2c: i2c.c
	$(CC) $(CFLAGS) -o i2c i2c.c

can: can.c
	$(CC) $(CFLAGS) -o can can.c

rs485: rs232_485.c
	$(CC) $(CFLAGS) -o rs485 rs232_485.c

clean:
	rm -f $(TARGETS)

help:
	@echo "Communication Protocols Makefile"
	@echo ""
	@echo "Targets:"
	@echo "  all    - Build all protocol simulators (default)"
	@echo "  uart   - Build UART/USART simulator"
	@echo "  spi    - Build SPI simulator"
	@echo "  i2c    - Build I2C simulator"
	@echo "  can    - Build CAN bus simulator"
	@echo "  rs485  - Build RS-232/RS-485 simulator"
	@echo "  clean  - Remove built binaries"
	@echo "  help   - Show this help message"
	@echo ""
	@echo "Usage:"
	@echo "  make          # Build everything"
	@echo "  make uart     # Build only UART"
	@echo "  ./uart        # Run UART simulator (software mode)"
	@echo "  make clean    # Clean binaries"
