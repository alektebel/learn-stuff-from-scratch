/*
 * SPI (Serial Peripheral Interface) Implementation - Template
 *
 * SPI is a synchronous, full-duplex serial protocol.  A single master drives
 * SCLK, MOSI (master-out/slave-in) and CS (chip-select, active-low).  The
 * slave drives MISO (master-in/slave-out).  Both sides shift bits on one
 * clock edge and sample on the other.
 *
 * Clock modes (CPOL = clock polarity, CPHA = clock phase):
 *   Mode 0 (CPOL=0,CPHA=0): idle LOW,  sample on rising  edge
 *   Mode 1 (CPOL=0,CPHA=1): idle LOW,  sample on falling edge
 *   Mode 2 (CPOL=1,CPHA=0): idle HIGH, sample on falling edge
 *   Mode 3 (CPOL=1,CPHA=1): idle HIGH, sample on rising  edge
 *
 * This file has two modes:
 *   SOFTWARE mode  – simulate SPI entirely in software (default)
 *   HARDWARE mode  – use Linux spidev (/dev/spidev0.0)
 *                    Compile: gcc -DHARDWARE -o spi spi.c
 *                    Run:     ./spi /dev/spidev0.0
 *
 * Compilation (software mode): gcc -Wall -o spi spi.c
 * Run: ./spi
 *
 * Learning path:
 *   TODO 1  – implement spi_transfer_byte() (software bit-bang, includes CPOL/CPHA)
 *   TODO 2  – implement spi_transfer_buffer()
 *   TODO 3  – (HARDWARE) open and configure a spidev device
 *   TODO 4  – (HARDWARE) perform a hardware SPI transfer
 *   TODO 5  – wire everything together in main()
 */

#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>

#ifdef HARDWARE
#include <unistd.h>
#include <fcntl.h>
#include <sys/ioctl.h>
#include <linux/spi/spidev.h>
#include <errno.h>
#endif

/* =========================================================================
 * SPI configuration
 * ========================================================================= */

typedef struct {
    uint8_t  mode;          /* SPI mode: 0–3 (encodes CPOL and CPHA)  */
    uint8_t  bits_per_word; /* typically 8                             */
    uint32_t speed_hz;      /* clock frequency in Hz, e.g. 1000000    */
    uint8_t  msb_first;     /* 1 = MSB first (standard), 0 = LSB first */
} spi_config_t;

/*
 * Software simulation "bus state" – shared between master and slave.
 * In a real system these are voltage levels on the wires.
 */
typedef struct {
    uint8_t sclk;   /* 0 or 1 */
    uint8_t mosi;   /* 0 or 1 */
    uint8_t miso;   /* 0 or 1 */
    uint8_t cs;     /* 0 = selected (active low) */
} spi_bus_t;

/* =========================================================================
 * TODO 1: Implement spi_transfer_byte
 *
 * Simulate a full-duplex SPI byte transfer in software (bit-bang).
 *
 * In SPI, master and slave exchange bits simultaneously:
 *   - Master shifts out `tx` bit by bit on MOSI
 *   - Slave shifts out its byte bit by bit on MISO
 *   - Both latch on the active clock edge
 *
 * Guidelines:
 *   - Determine bit order (MSB-first or LSB-first) from config->msb_first
 *   - For each of 8 bits:
 *       1. Place the current TX bit on bus->mosi
 *       2. Toggle SCLK to the "setup" edge (CPHA determines which)
 *       3. Read bus->miso and accumulate into rx_byte
 *       4. Toggle SCLK back to "sample" edge
 *   - Handle CPOL: idle clock level is config->mode's bit 1 (CPOL = mode >> 1)
 *   - Handle CPHA: data is sampled on 1st (CPHA=0) or 2nd (CPHA=1) edge
 *   - Return the received byte
 *
 * For the software simulation, the "slave" is provided as a function pointer
 * `slave_shift_bit(mosi_bit)` that returns the MISO bit for that clock cycle.
 *
 * Hint:
 *   CPOL = (config->mode >> 1) & 1;
 *   CPHA = (config->mode >> 0) & 1;
 * ========================================================================= */
uint8_t spi_transfer_byte(spi_bus_t *bus, const spi_config_t *config,
                          uint8_t tx,
                          uint8_t (*slave_shift_bit)(uint8_t mosi_bit))
{
    /* TODO: bit-bang one byte, return received byte */
    (void)bus; (void)config; (void)tx; (void)slave_shift_bit;
    return 0x00;
}

/* =========================================================================
 * TODO 2: Implement spi_transfer_buffer
 *
 * Transfer an array of bytes (full-duplex).
 *
 * Guidelines:
 *   - Assert CS low (bus->cs = 0) before the first byte
 *   - Call spi_transfer_byte() for each byte in tx_buf
 *   - Store received bytes in rx_buf
 *   - De-assert CS high (bus->cs = 1) after the last byte
 *   - `rx_buf` may be NULL if the caller does not care about received data
 * ========================================================================= */
void spi_transfer_buffer(spi_bus_t *bus, const spi_config_t *config,
                         const uint8_t *tx_buf, uint8_t *rx_buf, size_t len,
                         uint8_t (*slave_shift_bit)(uint8_t mosi_bit))
{
    /* TODO: transfer len bytes, assert/de-assert CS */
    (void)bus; (void)config; (void)tx_buf; (void)rx_buf;
    (void)len; (void)slave_shift_bit;
}

/* =========================================================================
 * TODO 3 (HARDWARE): Implement spi_open_device
 *
 * Open a Linux spidev device and configure it.
 *
 * Guidelines (only relevant when compiled with -DHARDWARE):
 *   - open(device, O_RDWR) to open /dev/spidevX.Y
 *   - Use ioctl(fd, SPI_IOC_WR_MODE, &config->mode) to set mode
 *   - Use ioctl(fd, SPI_IOC_WR_BITS_PER_WORD, &config->bits_per_word)
 *   - Use ioctl(fd, SPI_IOC_WR_MAX_SPEED_HZ, &config->speed_hz)
 *   - Return fd, or -1 on error
 *
 * Hint: check errno and perror() on ioctl failure
 * ========================================================================= */
#ifdef HARDWARE
int spi_open_device(const char *device, const spi_config_t *config)
{
    /* TODO: open and configure the spidev device */
    (void)device; (void)config;
    return -1;
}
#endif

/* =========================================================================
 * TODO 4 (HARDWARE): Implement spi_hw_transfer
 *
 * Perform a full-duplex SPI transfer using the kernel spidev interface.
 *
 * Guidelines:
 *   - Fill a struct spi_ioc_transfer with tx_buf, rx_buf, len, speed_hz,
 *     bits_per_word
 *   - Call ioctl(fd, SPI_IOC_MESSAGE(1), &transfer)
 *   - Return 0 on success, -1 on error
 * ========================================================================= */
#ifdef HARDWARE
int spi_hw_transfer(int fd, const spi_config_t *config,
                    const uint8_t *tx_buf, uint8_t *rx_buf, size_t len)
{
    /* TODO: use SPI_IOC_MESSAGE ioctl to transfer len bytes */
    (void)fd; (void)config; (void)tx_buf; (void)rx_buf; (void)len;
    return -1;
}
#endif

/* =========================================================================
 * Simple slave simulation
 *
 * A trivial "loopback" slave that echoes back whatever MOSI bit it receives,
 * delayed by one byte (it outputs the previous byte's bits on MISO).
 * Replace this with a real device model (e.g., a shift register or an ADC).
 * ========================================================================= */
static uint8_t slave_register = 0xA5;  /* slave's internal byte to send */
static int     slave_bit_pos  = 7;     /* current bit position (MSB first) */

static uint8_t loopback_slave(uint8_t mosi_bit)
{
    /* Return current bit of slave_register, shift in mosi_bit for next byte */
    uint8_t miso_bit = (slave_register >> slave_bit_pos) & 1;
    slave_register = (slave_register << 1) | mosi_bit;
    slave_bit_pos--;
    if (slave_bit_pos < 0) slave_bit_pos = 7;
    return miso_bit;
}

/* =========================================================================
 * TODO 5: Wire everything together in main()
 *
 * Software mode:
 *   1. Define an spi_config_t (e.g. mode=0, 8 bits, 1 MHz, MSB-first)
 *   2. Prepare a tx_buf with some test bytes and an rx_buf for results
 *   3. Call spi_transfer_buffer() with the loopback_slave function
 *   4. Print TX and RX bytes side by side
 *   5. Demonstrate each of the 4 SPI modes by changing config.mode
 *
 * Hardware mode (compiled with -DHARDWARE):
 *   1. Parse argv[1] as the spidev device path
 *   2. Open with spi_open_device()
 *   3. Transfer a test buffer with spi_hw_transfer()
 *   4. Print results and close fd
 * ========================================================================= */
int main(int argc, char *argv[])
{
    (void)argc; (void)argv;

    spi_config_t config = {
        .mode          = 0,    /* CPOL=0, CPHA=0 */
        .bits_per_word = 8,
        .speed_hz      = 1000000,
        .msb_first     = 1,
    };

    uint8_t tx[] = { 0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80 };
    uint8_t rx[sizeof(tx)];
    memset(rx, 0, sizeof(rx));

    spi_bus_t bus = { .sclk = 0, .mosi = 0, .miso = 0, .cs = 1 };

    printf("=== SPI Simulator ===\n");
    printf("Mode: %d (CPOL=%d, CPHA=%d), %u Hz, %s\n",
           config.mode,
           (config.mode >> 1) & 1,
           (config.mode >> 0) & 1,
           config.speed_hz,
           config.msb_first ? "MSB-first" : "LSB-first");
    printf("\n");

    /* TODO: call spi_transfer_buffer() and print results */

    return 0;
}
