/*
 * I2C (Inter-Integrated Circuit) Implementation - Template
 *
 * I2C uses two open-drain wires shared by all devices on the bus:
 *   SDA – Serial Data (bidirectional)
 *   SCL – Serial Clock (driven by master, may be stretched by slave)
 *
 * Transaction structure:
 *   START → [7-bit address + R/W̄] → ACK → [data byte] → ACK → … → STOP
 *
 * Key concepts:
 *   - START condition:  SDA falls while SCL is HIGH
 *   - STOP  condition:  SDA rises  while SCL is HIGH
 *   - Data bit:         SDA stable while SCL is HIGH; changes when SCL is LOW
 *   - ACK:              receiver pulls SDA LOW on the 9th clock (after 8 data bits)
 *   - NACK:             SDA remains HIGH on the 9th clock
 *   - Clock stretching: slave holds SCL LOW to pause the master
 *
 * Addresses:
 *   - 7-bit (standard):    0x03–0x77 (reserved: 0x00–0x02, 0x78–0x7F)
 *   - 10-bit (extended):   two-byte addressing, first byte starts 0b11110xx
 *
 * This file has two modes:
 *   SOFTWARE mode  – simulate I2C bus in software (default)
 *   HARDWARE mode  – use Linux i2c-dev (/dev/i2c-N)
 *                    Compile: gcc -DHARDWARE -o i2c i2c.c
 *                    Run:     ./i2c /dev/i2c-1 0x48
 *
 * Compilation (software mode): gcc -Wall -o i2c i2c.c
 * Run: ./i2c
 *
 * Learning path:
 *   TODO 1  – implement i2c_start() and i2c_stop()
 *   TODO 2  – implement i2c_write_bit() and i2c_read_bit()
 *   TODO 3  – implement i2c_write_byte()  (returns ACK/NACK)
 *   TODO 4  – implement i2c_read_byte()   (sends ACK/NACK)
 *   TODO 5  – implement i2c_write_reg() and i2c_read_reg()
 *   TODO 6  – (HARDWARE) open i2c-dev and use ioctl/read/write
 *   TODO 7  – wire everything together in main()
 */

#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>

#ifdef HARDWARE
#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <linux/i2c-dev.h>
#include <linux/i2c.h>
#include <errno.h>
#endif

/* =========================================================================
 * I2C bus simulation state
 * ========================================================================= */

typedef struct {
    uint8_t sda;   /* 0 or 1 (open-drain: 0 = driven low, 1 = released/high) */
    uint8_t scl;   /* 0 or 1 */
} i2c_bus_t;

#define I2C_ACK   0
#define I2C_NACK  1

/*
 * A simulated I2C slave device:
 *   address  – 7-bit I2C address
 *   regs[]   – 256-byte register file
 *   reg_ptr  – current register pointer (auto-incremented on multi-byte reads)
 */
typedef struct {
    uint8_t address;
    uint8_t regs[256];
    uint8_t reg_ptr;
} i2c_slave_t;

/* =========================================================================
 * TODO 1: Implement i2c_start() and i2c_stop()
 *
 * START condition: SDA transitions HIGH→LOW while SCL is HIGH
 *   - Ensure SCL = 1 and SDA = 1 first (idle)
 *   - Pull SDA LOW (SDA = 0) while SCL stays HIGH
 *   - Then pull SCL LOW to begin clocking data
 *
 * STOP condition: SDA transitions LOW→HIGH while SCL is HIGH
 *   - Ensure SCL = 0 first
 *   - Pull SDA LOW (SDA = 0) while SCL is LOW
 *   - Raise SCL HIGH
 *   - Raise SDA HIGH (while SCL is HIGH) → this is the STOP
 *
 * Guidelines:
 *   - Update bus->sda and bus->scl to reflect each transition
 *   - Print each state change for visibility in the simulator
 * ========================================================================= */
void i2c_start(i2c_bus_t *bus)
{
    /* TODO: generate I2C START condition */
    (void)bus;
}

void i2c_stop(i2c_bus_t *bus)
{
    /* TODO: generate I2C STOP condition */
    (void)bus;
}

/* =========================================================================
 * TODO 2: Implement i2c_write_bit() and i2c_read_bit()
 *
 * i2c_write_bit(bus, bit):
 *   - Set SDA = bit (data must be stable before SCL rises)
 *   - Raise SCL HIGH  (receiver samples here)
 *   - Lower SCL LOW
 *
 * i2c_read_bit(bus):
 *   - Release SDA (SDA = 1, let the slave drive it)
 *   - Raise SCL HIGH
 *   - Sample SDA → this is the received bit
 *   - Lower SCL LOW
 *   - Return the sampled bit
 *
 * Hint: in a real system you'd also check for clock stretching
 *       (wait until SCL is actually HIGH before sampling).
 * ========================================================================= */
void i2c_write_bit(i2c_bus_t *bus, uint8_t bit)
{
    /* TODO: clock one bit out */
    (void)bus; (void)bit;
}

uint8_t i2c_read_bit(i2c_bus_t *bus)
{
    /* TODO: clock one bit in, return it */
    (void)bus;
    return 1; /* default: NACK / line high */
}

/* =========================================================================
 * TODO 3: Implement i2c_write_byte
 *
 * Send 8 data bits (MSB first) then read the ACK/NACK bit.
 *
 * Guidelines:
 *   - Loop 8 times, starting from bit 7 down to bit 0
 *   - Call i2c_write_bit() for each bit
 *   - After the 8 data bits, call i2c_read_bit() to get ACK (0) or NACK (1)
 *   - Return I2C_ACK (0) or I2C_NACK (1)
 *
 * In the simulation, the slave's response is provided by slave_ack():
 *   slave_ack(slave, byte_sent) → returns I2C_ACK or I2C_NACK
 * ========================================================================= */
int i2c_write_byte(i2c_bus_t *bus, uint8_t byte,
                   int (*slave_ack)(i2c_slave_t *slave, uint8_t byte),
                   i2c_slave_t *slave)
{
    /* TODO: send 8 bits MSB-first, return ACK/NACK */
    (void)bus; (void)byte; (void)slave_ack; (void)slave;
    return I2C_NACK;
}

/* =========================================================================
 * TODO 4: Implement i2c_read_byte
 *
 * Receive 8 data bits (MSB first) then send ACK or NACK.
 *
 * Guidelines:
 *   - Loop 8 times, calling i2c_read_bit() each time (bit 7 first)
 *   - Reconstruct the byte
 *   - Call i2c_write_bit(send_ack ? I2C_ACK : I2C_NACK) to acknowledge
 *   - Return the received byte
 *
 * `slave_send_bit(slave)` provides the next MISO bit from the slave.
 * ========================================================================= */
uint8_t i2c_read_byte(i2c_bus_t *bus, int send_ack,
                      uint8_t (*slave_send_bit)(i2c_slave_t *slave),
                      i2c_slave_t *slave)
{
    /* TODO: receive 8 bits MSB-first, send ACK/NACK, return byte */
    (void)bus; (void)send_ack; (void)slave_send_bit; (void)slave;
    return 0xFF;
}

/* =========================================================================
 * TODO 5: Implement i2c_write_reg and i2c_read_reg
 *
 * i2c_write_reg(bus, slave, reg_addr, value):
 *   Full write transaction:
 *   START → [addr | WRITE(0)] → ACK → [reg_addr] → ACK → [value] → ACK → STOP
 *
 * i2c_read_reg(bus, slave, reg_addr):
 *   Combined write-then-read (repeated START):
 *   START → [addr | WRITE] → ACK → [reg_addr] → ACK →
 *   RESTART → [addr | READ(1)] → ACK → [value] → NACK → STOP
 *   Return the received value.
 *
 * The 8-bit address byte on the wire = (7-bit address << 1) | R/W̄
 *   R/W̄ = 0 for write, 1 for read
 *
 * Guidelines:
 *   - Use i2c_start(), i2c_write_byte(), i2c_read_byte(), i2c_stop()
 *   - Return -1 if the slave NACKs the address (device not found)
 * ========================================================================= */
int i2c_write_reg(i2c_bus_t *bus, i2c_slave_t *slave,
                  uint8_t reg_addr, uint8_t value);    /* forward decl */

int i2c_read_reg(i2c_bus_t *bus, i2c_slave_t *slave, uint8_t reg_addr);

/* =========================================================================
 * Slave simulation helpers
 *
 * These simulate a simple I2C slave with a 256-byte register file.
 * You do NOT need to modify these for the basic exercises.
 * ========================================================================= */
static uint8_t pending_write_addr;
static int     addr_phase = 1;   /* 1 = next byte is register address */

static int sim_slave_ack(i2c_slave_t *slave, uint8_t byte)
{
    if (addr_phase) {
        /* First byte after address: treat as register pointer */
        slave->reg_ptr = byte;
        pending_write_addr = byte;
        addr_phase = 0;
    } else {
        /* Subsequent bytes: write to register */
        slave->regs[slave->reg_ptr++] = byte;
    }
    return I2C_ACK;
}

static uint8_t sim_slave_send_bit(i2c_slave_t *slave)
{
    /* Return next bit of current register value, MSB first */
    static int bit_pos = 7;
    uint8_t val = slave->regs[slave->reg_ptr];
    uint8_t bit = (val >> bit_pos) & 1;
    if (--bit_pos < 0) {
        bit_pos = 7;
        slave->reg_ptr++;
    }
    return bit;
}

int i2c_write_reg(i2c_bus_t *bus, i2c_slave_t *slave,
                  uint8_t reg_addr, uint8_t value)
{
    /* TODO: implement full write transaction */
    (void)bus; (void)slave; (void)reg_addr; (void)value;
    return -1;
}

int i2c_read_reg(i2c_bus_t *bus, i2c_slave_t *slave, uint8_t reg_addr)
{
    /* TODO: implement combined write-read transaction */
    (void)bus; (void)slave; (void)reg_addr;
    return -1;
}

/* =========================================================================
 * TODO 6 (HARDWARE): Implement i2c_open_device, i2c_hw_write_reg,
 *                     i2c_hw_read_reg
 *
 * i2c_open_device(device, addr7bit):
 *   - open(device, O_RDWR)  e.g. device = "/dev/i2c-1"
 *   - ioctl(fd, I2C_SLAVE, addr7bit)  to set the target slave address
 *   - Return fd or -1 on error
 *
 * i2c_hw_write_reg(fd, reg_addr, value):
 *   - Write two bytes: { reg_addr, value } using write(fd, buf, 2)
 *   - Return 0 on success, -1 on error
 *
 * i2c_hw_read_reg(fd, reg_addr):
 *   - Write one byte (reg_addr) with write(fd, &reg_addr, 1)
 *   - Read one byte with read(fd, &value, 1)
 *   - Return the value or -1 on error
 *
 * Hint: for SMBus protocol use smbus_read/write helpers from <linux/i2c.h>
 * ========================================================================= */
#ifdef HARDWARE
int i2c_open_device(const char *device, uint8_t addr7bit)
{
    /* TODO: open i2c-dev and set slave address */
    (void)device; (void)addr7bit;
    return -1;
}

int i2c_hw_write_reg(int fd, uint8_t reg_addr, uint8_t value)
{
    /* TODO: write register over i2c-dev */
    (void)fd; (void)reg_addr; (void)value;
    return -1;
}

int i2c_hw_read_reg(int fd, uint8_t reg_addr)
{
    /* TODO: read register over i2c-dev */
    (void)fd; (void)reg_addr;
    return -1;
}
#endif

/* =========================================================================
 * TODO 7: Wire everything together in main()
 *
 * Software mode:
 *   1. Create an i2c_bus_t and an i2c_slave_t (address e.g. 0x48)
 *   2. Pre-populate a few slave registers with known values
 *   3. Write a value to register 0x00 using i2c_write_reg()
 *   4. Read it back using i2c_read_reg() and verify
 *   5. Print a summary of the bus transactions
 *
 * Hardware mode (compiled with -DHARDWARE):
 *   1. Parse argv[1] (device path) and argv[2] (hex address)
 *   2. Open with i2c_open_device()
 *   3. Write and read a register; print result
 * ========================================================================= */
int main(int argc, char *argv[])
{
    (void)argc; (void)argv;

    i2c_bus_t  bus   = { .sda = 1, .scl = 1 };
    i2c_slave_t slave = { .address = 0x48 };
    memset(slave.regs, 0, sizeof(slave.regs));
    slave.regs[0x00] = 0xAB;
    slave.regs[0x01] = 0xCD;

    printf("=== I2C Simulator ===\n");
    printf("Slave address: 0x%02X\n\n", slave.address);

    /* TODO: demonstrate write and read register transactions */

    return 0;
}
