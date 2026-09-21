/*
 * I2C (Inter-Integrated Circuit) Implementation - Solution
 *
 * Complete working I2C bus simulator with START/STOP, ACK/NACK,
 * and register read/write transactions.
 *
 * Compilation: gcc -Wall -o i2c i2c.c
 * Run: ./i2c
 *
 * Hardware variant: gcc -DHARDWARE -Wall -o i2c i2c.c
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

typedef struct {
    uint8_t sda;
    uint8_t scl;
} i2c_bus_t;

#define I2C_ACK   0
#define I2C_NACK  1

typedef struct {
    uint8_t address;
    uint8_t regs[256];
    uint8_t reg_ptr;
} i2c_slave_t;

/* Verbose flag for bus transaction tracing */
static int verbose = 1;

static void bus_trace(const char *event, const i2c_bus_t *bus)
{
    if (verbose)
        printf("  [BUS] %-20s  SDA=%d SCL=%d\n", event, bus->sda, bus->scl);
}

/* =========================================================================
 * i2c_start / i2c_stop
 * ========================================================================= */
void i2c_start(i2c_bus_t *bus)
{
    bus->sda = 1; bus->scl = 1;
    bus_trace("START: SDA high", bus);
    bus->sda = 0;
    bus_trace("START: SDA falls (START)", bus);
    bus->scl = 0;
    bus_trace("START: SCL low", bus);
}

void i2c_stop(i2c_bus_t *bus)
{
    bus->scl = 0; bus->sda = 0;
    bus_trace("STOP: SDA low", bus);
    bus->scl = 1;
    bus_trace("STOP: SCL rises", bus);
    bus->sda = 1;
    bus_trace("STOP: SDA rises (STOP)", bus);
}

/* =========================================================================
 * i2c_write_bit / i2c_read_bit
 * ========================================================================= */
void i2c_write_bit(i2c_bus_t *bus, uint8_t bit)
{
    bus->sda = bit;
    bus->scl = 1;   /* receiver samples here */
    bus->scl = 0;
}

uint8_t i2c_read_bit(i2c_bus_t *bus)
{
    bus->sda = 1;   /* release SDA so slave can drive it */
    bus->scl = 1;
    uint8_t bit = bus->sda;  /* sample */
    bus->scl = 0;
    return bit;
}

/* =========================================================================
 * Slave simulation helpers (internal)
 * ========================================================================= */
static uint8_t  pending_reg_addr;
static int      addr_phase = 1;

static int sim_slave_ack(i2c_slave_t *slave, uint8_t byte)
{
    if (addr_phase) {
        slave->reg_ptr   = byte;
        pending_reg_addr = byte;
        addr_phase       = 0;
    } else {
        slave->regs[slave->reg_ptr++] = byte;
    }
    return I2C_ACK;
}

static int bit_pos_slave = 7;

static uint8_t sim_slave_send_bit(i2c_slave_t *slave)
{
    uint8_t val = slave->regs[slave->reg_ptr];
    uint8_t bit = (val >> bit_pos_slave) & 1;
    if (--bit_pos_slave < 0) {
        bit_pos_slave = 7;
        slave->reg_ptr++;
    }
    return bit;
}

/* =========================================================================
 * i2c_write_byte – 8 data bits then ACK
 * ========================================================================= */
int i2c_write_byte(i2c_bus_t *bus, uint8_t byte,
                   int (*slave_ack_fn)(i2c_slave_t *slave, uint8_t byte),
                   i2c_slave_t *slave)
{
    for (int i = 7; i >= 0; i--)
        i2c_write_bit(bus, (byte >> i) & 1);

    /* ACK phase: slave drives SDA low = ACK */
    int ack;
    if (slave_ack_fn && slave)
        ack = slave_ack_fn(slave, byte);
    else
        ack = I2C_NACK;

    bus->sda = (uint8_t)ack;
    bus->scl = 1;
    bus->scl = 0;
    bus->sda = 1;

    return ack;
}

/* =========================================================================
 * i2c_read_byte – 8 data bits then send ACK/NACK
 * ========================================================================= */
uint8_t i2c_read_byte(i2c_bus_t *bus, int send_ack,
                      uint8_t (*slave_send_bit_fn)(i2c_slave_t *slave),
                      i2c_slave_t *slave)
{
    uint8_t result = 0;

    for (int i = 7; i >= 0; i--) {
        uint8_t bit;
        if (slave_send_bit_fn && slave)
            bit = slave_send_bit_fn(slave);
        else
            bit = 1;

        bus->sda = bit;
        bus->scl = 1;
        result |= (uint8_t)(bit << i);
        bus->scl = 0;
    }

    /* ACK/NACK from master */
    i2c_write_bit(bus, send_ack ? I2C_ACK : I2C_NACK);

    return result;
}

/* =========================================================================
 * i2c_write_reg – complete write transaction
 * ========================================================================= */
int i2c_write_reg(i2c_bus_t *bus, i2c_slave_t *slave,
                  uint8_t reg_addr, uint8_t value)
{
    addr_phase = 1;

    i2c_start(bus);

    /* Address byte + WRITE (R/W = 0) */
    uint8_t addr_byte = (uint8_t)((slave->address << 1) | 0);
    if (verbose) printf("  [WR] addr_byte=0x%02X\n", addr_byte);
    int ack = i2c_write_byte(bus, addr_byte, NULL, NULL);
    /* Fake ACK for matching address */
    ack = (addr_byte >> 1 == slave->address) ? I2C_ACK : I2C_NACK;
    if (ack != I2C_ACK) { i2c_stop(bus); return -1; }

    /* Register address */
    if (verbose) printf("  [WR] reg_addr=0x%02X\n", reg_addr);
    i2c_write_byte(bus, reg_addr, sim_slave_ack, slave);

    /* Value */
    if (verbose) printf("  [WR] value=0x%02X\n", value);
    i2c_write_byte(bus, value, sim_slave_ack, slave);

    i2c_stop(bus);
    return 0;
}

/* =========================================================================
 * i2c_read_reg – combined write-read transaction
 * ========================================================================= */
int i2c_read_reg(i2c_bus_t *bus, i2c_slave_t *slave, uint8_t reg_addr)
{
    addr_phase = 1;

    /* Write phase: set register pointer */
    i2c_start(bus);
    uint8_t addr_wr = (uint8_t)((slave->address << 1) | 0);
    if (verbose) printf("  [RD] addr_byte(WR)=0x%02X\n", addr_wr);
    i2c_write_byte(bus, addr_wr, NULL, NULL);   /* address (fake ACK) */
    i2c_write_byte(bus, reg_addr, sim_slave_ack, slave);  /* reg pointer */

    /* Repeated START then read */
    i2c_start(bus);
    uint8_t addr_rd = (uint8_t)((slave->address << 1) | 1);
    if (verbose) printf("  [RD] addr_byte(RD)=0x%02X\n", addr_rd);
    i2c_write_byte(bus, addr_rd, NULL, NULL);

    bit_pos_slave = 7;
    uint8_t val = i2c_read_byte(bus, 0 /* NACK = last byte */, sim_slave_send_bit, slave);
    if (verbose) printf("  [RD] value=0x%02X\n", val);

    i2c_stop(bus);
    return (int)val;
}

/* =========================================================================
 * Hardware: i2c-dev interface
 * ========================================================================= */
#ifdef HARDWARE
int i2c_open_device(const char *device, uint8_t addr7bit)
{
    int fd = open(device, O_RDWR);
    if (fd < 0) { perror("open"); return -1; }
    if (ioctl(fd, I2C_SLAVE, (long)addr7bit) < 0) {
        perror("I2C_SLAVE"); close(fd); return -1;
    }
    return fd;
}

int i2c_hw_write_reg(int fd, uint8_t reg_addr, uint8_t value)
{
    uint8_t buf[2] = { reg_addr, value };
    return (write(fd, buf, 2) == 2) ? 0 : -1;
}

int i2c_hw_read_reg(int fd, uint8_t reg_addr)
{
    if (write(fd, &reg_addr, 1) != 1) return -1;
    uint8_t val;
    if (read(fd, &val, 1) != 1) return -1;
    return (int)val;
}
#endif  /* HARDWARE */

/* =========================================================================
 * main
 * ========================================================================= */
int main(int argc, char *argv[])
{
    (void)argc; (void)argv;

    i2c_bus_t   bus   = { .sda = 1, .scl = 1 };
    i2c_slave_t slave = { .address = 0x48 };
    memset(slave.regs, 0, sizeof(slave.regs));
    slave.regs[0x00] = 0xAB;
    slave.regs[0x01] = 0xCD;
    slave.regs[0x02] = 0xEF;

    printf("=== I2C Simulator ===\n");
    printf("Slave address: 0x%02X\n\n", slave.address);

    /* Write to register 0x00 */
    printf("--- Writing 0x42 to register 0x00 ---\n");
    i2c_write_reg(&bus, &slave, 0x00, 0x42);
    printf("\n");

    /* Read register 0x00 */
    printf("--- Reading register 0x00 ---\n");
    int val = i2c_read_reg(&bus, &slave, 0x00);
    printf("  → read 0x%02X  %s\n", val, (val == 0x42) ? "✓" : "✗ MISMATCH");
    printf("\n");

    /* Read register 0x01 (unchanged) */
    printf("--- Reading register 0x01 (should be 0xCD) ---\n");
    val = i2c_read_reg(&bus, &slave, 0x01);
    printf("  → read 0x%02X  %s\n", val, (val == 0xCD) ? "✓" : "✗ MISMATCH");
    printf("\n");

    /* Write multiple registers */
    printf("--- Writing pattern to registers 0x10..0x13 ---\n");
    uint8_t pattern[] = { 0x11, 0x22, 0x33, 0x44 };
    for (int i = 0; i < 4; i++)
        i2c_write_reg(&bus, &slave, (uint8_t)(0x10 + i), pattern[i]);

    printf("\n--- Reading back registers 0x10..0x13 ---\n");
    int ok = 1;
    for (int i = 0; i < 4; i++) {
        val = i2c_read_reg(&bus, &slave, (uint8_t)(0x10 + i));
        printf("  reg[0x%02X] = 0x%02X  %s\n",
               0x10 + i, val,
               ((uint8_t)val == pattern[i]) ? "✓" : "✗");
        if ((uint8_t)val != pattern[i]) ok = 0;
    }
    printf("\nResult: %s\n", ok ? "ALL PASSED" : "ERRORS FOUND");

#ifdef HARDWARE
    if (argc >= 3) {
        uint8_t addr = (uint8_t)strtoul(argv[2], NULL, 16);
        int fd = i2c_open_device(argv[1], addr);
        if (fd < 0) return 1;
        printf("\nHardware: reading reg 0x00 from device 0x%02X on %s\n",
               addr, argv[1]);
        int hwval = i2c_hw_read_reg(fd, 0x00);
        if (hwval < 0) perror("read");
        else printf("  → 0x%02X\n", hwval);
        close(fd);
    }
#endif

    return 0;
}
