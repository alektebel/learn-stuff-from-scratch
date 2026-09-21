# Communication Protocols – Solutions

This directory contains complete, working implementations of the communication
protocol simulators.  Use these as a reference after attempting the templates,
or to verify your approach.

## Files

| File              | Description                                                      |
|-------------------|------------------------------------------------------------------|
| `uart.c`          | Full UART framer/deframer with parity, baud-rate calc, and demo  |
| `spi.c`           | Full SPI bit-bang simulator with all 4 CPOL/CPHA modes           |
| `i2c.c`           | Full I2C bus simulator with START/STOP, ACK/NACK, r/w registers  |
| `can.c`           | Full CAN 2.0A encoder/decoder with CRC-15 and arbitration        |
| `rs232_485.c`     | Full RS-232 voltage model + RS-485 differential + packet protocol |

## Building

```bash
# Build all solutions
make -f Makefile.solutions

# Or build individually
gcc -Wall -o uart    uart.c
gcc -Wall -o spi     spi.c
gcc -Wall -o i2c     i2c.c
gcc -Wall -o can     can.c
gcc -Wall -o rs485   rs232_485.c

# Hardware variants (requires Linux with appropriate kernel interfaces)
gcc -DHARDWARE -Wall -o uart_hw  uart.c
gcc -DHARDWARE -Wall -o spi_hw   spi.c
gcc -DHARDWARE -Wall -o i2c_hw   i2c.c
gcc -DHARDWARE -Wall -o can_hw   can.c
gcc -DHARDWARE -Wall -o rs485_hw rs232_485.c
```

## Running

```bash
./uart    # UART framing demo with all parity modes
./spi     # SPI byte-transfer demo with all 4 CPOL/CPHA modes
./i2c     # I2C write/read register transactions
./can     # CAN frame encode/decode + arbitration simulation
./rs485   # RS-232 voltage + RS-485 differential + packet protocol demo
```

## Key Takeaways

### UART
- Framing is purely time-based: start/stop bits pace the receiver
- Parity adds a single-bit error-detection capability
- At 115200 baud each bit lasts only 8.68 µs

### SPI
- CPOL and CPHA must match between master and slave or data is garbled
- Full-duplex: every clock cycle both master and slave shift out one bit
- Speed is only limited by the slowest device and trace capacitance

### I2C
- The pull-up resistor value is a critical design parameter:
  too weak → slow rise time; too strong → excessive current
- Clock stretching allows slow peripherals to participate
- The VGA DDC bus uses I2C at 100 kHz to transfer the EDID ROM

### CAN
- The CRC-15 polynomial (0x4599) is specifically chosen for Hamming distance
  guarantees over automotive cable lengths at typical speeds
- Bit stuffing ensures clock synchronisation by preventing long runs of
  identical bits (max 5 in a row before a complementary stuff bit is inserted)
- Error confinement prevents one broken node from taking down the whole bus

### RS-485
- Differential signaling rejects common-mode noise (e.g., ground differences
  between nodes tens of meters apart)
- The 200 mV minimum differential threshold is deliberately conservative –
  real transceivers (e.g., MAX485) guarantee operation down to ±200 mV
- TX enable (DE) timing is critical: assert before first bit, release after
  last stop bit stops – or a half-bit-time after the last stop bit finishes
