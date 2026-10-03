# Communication Protocols From Scratch

This directory contains from-scratch implementations of serial and parallel communication protocols in C, simulated on Linux using software emulation and Linux kernel interfaces (spidev, i2c-dev, SocketCAN, serial ports).

## Goal

Build protocol implementations to understand:
- How signals are encoded, framed, and transmitted at the bit level
- Clocking, synchronization, and timing requirements
- Master/slave, multi-master, and point-to-point bus topologies
- Error detection and correction techniques
- Real-world trade-offs between speed, robustness, pin count, and distance

## Projects in This Directory

| File            | Protocol      | Type     | Key Concepts                                             |
|-----------------|---------------|----------|----------------------------------------------------------|
| `uart.c`        | UART / USART  | Serial   | Async framing, baud rate, parity, flow control           |
| `spi.c`         | SPI           | Serial   | Synchronous, MOSI/MISO/SCLK/CS, clock polarity & phase  |
| `i2c.c`         | I2C           | Serial   | Multi-drop, 7-bit addressing, ACK/NACK, clock stretching |
| `can.c`         | CAN           | Serial   | Differential signaling, arbitration, CRC, error frames   |
| `rs232_485.c`   | RS-232 / RS-485 | Serial | Voltage levels, half-duplex, multi-drop, bias resistors  |

## Learning Path

### Phase 1 – Fundamentals
1. **UART** – Start here. Asynchronous framing is the foundation for all other protocols.
2. **RS-232 / RS-485** – Understand voltage standards and multi-drop extensions of UART.

### Phase 2 – Synchronous Protocols
3. **SPI** – Fast, simple, full-duplex communication with a shared clock.
4. **I2C** – Two-wire multi-device bus with software addressing.

### Phase 3 – Robust Industrial Protocols
5. **CAN** – The gold standard for noise-immune, arbitrated bus communication.

### Phase 4 – Bonus Topics (research only, no code templates)
- **Parallel buses** – PCI, PATA/IDE, FSMC (STM32 flexible static memory controller)
- **VGA DDC/EDID** – The hidden I2C bus inside every VGA connector (read monitor EDID data!)
- **USB** – Differential signaling, enumeration, descriptors
- **Ethernet** – CSMA/CD, MAC framing, PHY layer

---

## Protocol Quick Reference

### UART (Universal Asynchronous Receiver/Transmitter)
```
 Idle  Start  D0  D1  D2  D3  D4  D5  D6  D7  Parity  Stop
  ───┐  ┌──┐  ...bit stream...                         ┌───
     └──┘  └──────────────────────────────────────────┘
```
- **No shared clock** – both sides must agree on baud rate beforehand
- **Frame**: 1 start bit + 5–9 data bits + optional parity + 1–2 stop bits
- **Common baud rates**: 9600, 115200, 460800, 921600
- **Full-duplex**: separate TX and RX lines

### SPI (Serial Peripheral Interface)
```
Master          Slave
  SCLK ──────────────────►
  MOSI ──────────────────►
  MISO ◄──────────────────
  CS   ──────────────────► (active low)
```
- **Synchronous**: data sampled on SCLK edge
- **CPOL/CPHA** define clock idle state and sampling edge (4 modes: 0–3)
- **Full-duplex**: MOSI and MISO transfer simultaneously
- **Multiple slaves**: one CS line per device

### I2C (Inter-Integrated Circuit)
```
Master / Slave(s)
  SDA ────┤pull-up├──── (open drain, bidirectional)
  SCL ────┤pull-up├──── (open drain, clock)
```
- **Two wires** (SDA + SCL) shared by up to 127 devices (7-bit address)
- **Start / Stop conditions** mark transaction boundaries
- **ACK/NACK** after every byte (receiver pulls SDA low = ACK)
- **Clock stretching**: slave may hold SCL low to pause master
- **VGA DDC**: EDID data on VGA pins 12 (SDA) and 15 (SCL) — real I2C!

### CAN (Controller Area Network)
```
CAN_H ─── twisted pair ─── differential signaling
CAN_L ─── twisted pair ───
       120Ω                120Ω  (termination resistors)
```
- **Multi-master**: any node can start transmission
- **Arbitration**: bitwise OR on bus; lower ID wins without collision
- **Frame**: SOF + 11/29-bit ID + RTR + DLC + 0–8 data bytes + CRC + ACK + EOF
- **Error confinement**: error counters, bus-off state
- **Speeds**: 125 kbps (automotive) to 1 Mbps standard; CAN FD up to 8 Mbps

### RS-232 / RS-485
```
RS-232 (point-to-point)   RS-485 (multi-drop, differential)
  +3V…+15V = logic 0        +200mV differential = logic 1
  -3V…-15V = logic 1        -200mV differential = logic 0
  (inverted logic!)         Up to 32 nodes, 1200 m at 100 kbps
```
- **RS-232**: ±12V single-ended, up to ~15 m, point-to-point only
- **RS-485**: differential, noise-immune, 32+ nodes, industrial standard

---

## Features to Implement

### Basic Features
- Software frame encoder/decoder for each protocol
- Timing/baud rate calculation
- Basic error detection (parity, CRC)
- Linux hardware interface setup (where applicable)

### Intermediate Features
- Multi-device addressing (I2C, SPI with multiple CS)
- ACK/NACK handling (I2C)
- CAN message arbitration simulation
- RS-485 direction control (TX enable pin)

### Advanced Features
- CAN error frame injection and error counter simulation
- I2C clock stretching and multi-master arbitration
- SPI DMA-style buffer transfers
- UART hardware flow control (RTS/CTS)
- CAN FD extended frame format

---

## Building and Testing

```bash
# Build all protocol simulators
make

# Build a specific protocol
make uart
make spi
make i2c
make can
make rs485

# Run a simulator
./uart
./spi
./i2c
./can
./rs485

# Clean build artifacts
make clean
```

### Hardware Testing (optional, requires real hardware)
```bash
# UART via USB-serial adapter
# Connect /dev/ttyUSB0 ↔ /dev/ttyUSB1 with null-modem cable
./uart /dev/ttyUSB0

# SPI via Linux spidev
# Requires SPI-enabled board (Raspberry Pi, BeagleBone, etc.)
./spi /dev/spidev0.0

# I2C via Linux i2c-dev
# Requires I2C-enabled board + connected device
./i2c /dev/i2c-1 0x48   # Example: TMP102 temperature sensor

# CAN via SocketCAN
# sudo ip link set can0 type can bitrate 500000
# sudo ip link set can0 up
./can can0

# RS-485 via USB-RS485 adapter
./rs485 /dev/ttyUSB0
```

---

## Security Considerations

- Validate all incoming frame lengths before accessing buffers
- Sanitize I2C/SPI device addresses (7-bit: 0x03–0x77, 10-bit: 0x000–0x3FF)
- Avoid unbounded reads when framing is lost; implement sync recovery
- CAN: validate DLC (0–8 bytes) before accessing data array
- RS-485: bound the maximum packet length; reject oversized frames

## Common Pitfalls

1. **UART baud mismatch** – Even 1% difference causes framing errors at high speeds
2. **SPI CPOL/CPHA** – Wrong mode means reading on the wrong clock edge (garbled data)
3. **I2C pull-ups** – Too weak = slow edges; too strong = signal integrity issues
4. **CAN termination** – Missing 120Ω terminators cause reflections and bus errors
5. **RS-485 direction** – Must drive TX enable *before* sending and release *after* last bit
6. **Endianness** – Many protocols are big-endian (CAN ID, I2C register addresses)

---

## Interesting Facts

- **VGA has a hidden I2C bus**: pins 12 (SDA) and 15 (SCL) carry the DDC (Display Data Channel) bus. Your GPU reads the monitor's EDID ROM over I2C at boot — you can attach sensors to a spare VGA port!
- **CAN was designed by Bosch for automotive** – every modern car has dozens of CAN nodes (ECU, ABS, airbag, dashboard…) all sharing a single twisted pair
- **I2C was invented by Philips** – the patent expired in 2006; before that, competitors had to use "TWI" (Two Wire Interface) as the name (hence Atmel AVR TWI)
- **RS-232 dates to 1960** – yet it still appears on industrial equipment, test instruments, and even some modern microcontrollers

---

## Resources

### Standards & RFCs
- **UART**: POSIX termios man page (`man 3 termios`); 16550 UART datasheet
- **SPI**: Motorola SPI specification; Linux `spidev` documentation
- **I2C**: NXP I2C-bus specification (UM10204); Linux `i2c-dev` documentation
- **CAN**: Bosch CAN specification 2.0; ISO 11898-1; Linux SocketCAN documentation
- **RS-485**: TIA/EIA-485-A standard; RS-232: TIA/EIA-232-F

### Linux Kernel Interfaces
- [Linux SPI userspace API](https://www.kernel.org/doc/html/latest/spi/spidev.html)
- [Linux I2C/SMBus userspace API](https://www.kernel.org/doc/html/latest/i2c/dev-interface.html)
- [Linux SocketCAN](https://www.kernel.org/doc/html/latest/networking/can.html)
- [Linux serial/termios](https://man7.org/linux/man-pages/man3/termios.3.html)

### Video Courses & Further Reading
- [Embedded Systems courses](https://github.com/Developer-Y/cs-video-courses#computer-organization-and-architecture)
- [Ben Eater's SPI/I2C/UART series on YouTube](https://www.youtube.com/@BenEater)
- [Computer Networks Courses](https://github.com/Developer-Y/cs-video-courses#computer-networks)

## Sources

- **NXP UM10204** — the I²C specification, and the only authority on it.
- **Bosch CAN 2.0 specification** — arbitration and the bit-stuffing rules.
- Each MCU's own datasheet for UART framing; there is no single RFC.

Full list: [`../../REFERENCES.md`](../../REFERENCES.md#week-1314--sockets-and-protocols)
