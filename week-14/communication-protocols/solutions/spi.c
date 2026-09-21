/*
 * SPI (Serial Peripheral Interface) Implementation - Solution
 *
 * Complete working implementation of SPI bit-bang simulator.
 *
 * Compilation: gcc -Wall -o spi spi.c
 * Run: ./spi
 *
 * Hardware variant: gcc -DHARDWARE -Wall -o spi spi.c
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

typedef struct {
    uint8_t  mode;
    uint8_t  bits_per_word;
    uint32_t speed_hz;
    uint8_t  msb_first;
} spi_config_t;

typedef struct {
    uint8_t sclk;
    uint8_t mosi;
    uint8_t miso;
    uint8_t cs;
} spi_bus_t;

/* =========================================================================
 * spi_transfer_byte – bit-bang one byte, return received byte
 * ========================================================================= */
uint8_t spi_transfer_byte(spi_bus_t *bus, const spi_config_t *config,
                          uint8_t tx,
                          uint8_t (*slave_shift_bit)(uint8_t mosi_bit))
{
    uint8_t cpol = (config->mode >> 1) & 1;
    uint8_t cpha = (config->mode >> 0) & 1;
    uint8_t rx   = 0;

    /* Set clock to idle state */
    bus->sclk = cpol;

    for (int i = 7; i >= 0; i--) {
        int bit_index = config->msb_first ? i : (7 - i);

        /* Place TX bit on MOSI */
        bus->mosi = (tx >> bit_index) & 1;

        if (cpha == 0) {
            /* CPHA=0: sample on first (active) edge, shift on second */
            bus->sclk = cpol ^ 1;                   /* first edge  */
            bus->miso = slave_shift_bit(bus->mosi);  /* slave responds */
            rx |= (uint8_t)(bus->miso << bit_index); /* sample       */
            bus->sclk = cpol;                        /* second edge  */
        } else {
            /* CPHA=1: shift on first edge, sample on second */
            bus->sclk = cpol ^ 1;                   /* first edge  */
            bus->sclk = cpol;                        /* second edge */
            bus->miso = slave_shift_bit(bus->mosi);  /* slave responds */
            rx |= (uint8_t)(bus->miso << bit_index); /* sample       */
        }
    }

    return rx;
}

/* =========================================================================
 * spi_transfer_buffer
 * ========================================================================= */
void spi_transfer_buffer(spi_bus_t *bus, const spi_config_t *config,
                         const uint8_t *tx_buf, uint8_t *rx_buf, size_t len,
                         uint8_t (*slave_shift_bit)(uint8_t mosi_bit))
{
    bus->cs = 0;  /* assert CS (active low) */

    for (size_t i = 0; i < len; i++) {
        uint8_t rx = spi_transfer_byte(bus, config, tx_buf[i], slave_shift_bit);
        if (rx_buf)
            rx_buf[i] = rx;
    }

    bus->cs = 1;  /* de-assert CS */
}

/* =========================================================================
 * Hardware: open spidev device
 * ========================================================================= */
#ifdef HARDWARE
int spi_open_device(const char *device, const spi_config_t *config)
{
    int fd = open(device, O_RDWR);
    if (fd < 0) { perror("open"); return -1; }

    uint8_t mode = config->mode;
    if (ioctl(fd, SPI_IOC_WR_MODE, &mode) < 0) {
        perror("SPI_IOC_WR_MODE"); close(fd); return -1;
    }

    uint8_t bits = config->bits_per_word;
    if (ioctl(fd, SPI_IOC_WR_BITS_PER_WORD, &bits) < 0) {
        perror("SPI_IOC_WR_BITS_PER_WORD"); close(fd); return -1;
    }

    uint32_t speed = config->speed_hz;
    if (ioctl(fd, SPI_IOC_WR_MAX_SPEED_HZ, &speed) < 0) {
        perror("SPI_IOC_WR_MAX_SPEED_HZ"); close(fd); return -1;
    }

    return fd;
}

int spi_hw_transfer(int fd, const spi_config_t *config,
                    const uint8_t *tx_buf, uint8_t *rx_buf, size_t len)
{
    struct spi_ioc_transfer tr = {
        .tx_buf        = (unsigned long)tx_buf,
        .rx_buf        = (unsigned long)rx_buf,
        .len           = (uint32_t)len,
        .speed_hz      = config->speed_hz,
        .bits_per_word = config->bits_per_word,
        .delay_usecs   = 0,
    };

    if (ioctl(fd, SPI_IOC_MESSAGE(1), &tr) < 0) {
        perror("SPI_IOC_MESSAGE"); return -1;
    }
    return 0;
}
#endif  /* HARDWARE */

/* =========================================================================
 * Slave simulation: simple loopback (returns previous TX byte on MISO)
 * ========================================================================= */
static uint8_t slave_buf  = 0xA5;
static int     slave_bpos = 7;

static uint8_t loopback_slave(uint8_t mosi_bit)
{
    uint8_t miso_bit = (slave_buf >> slave_bpos) & 1;
    slave_buf = (uint8_t)((slave_buf << 1) | mosi_bit);
    if (--slave_bpos < 0) slave_bpos = 7;
    return miso_bit;
}

/* =========================================================================
 * main
 * ========================================================================= */
int main(int argc, char *argv[])
{
    (void)argc; (void)argv;

    printf("=== SPI Simulator ===\n\n");

    uint8_t tx[] = { 0xDE, 0xAD, 0xBE, 0xEF, 0xCA, 0xFE };
    uint8_t rx[sizeof(tx)];

    /* Test all 4 SPI modes */
    for (int mode = 0; mode <= 3; mode++) {
        spi_config_t config = {
            .mode          = (uint8_t)mode,
            .bits_per_word = 8,
            .speed_hz      = 1000000,
            .msb_first     = 1,
        };
        spi_bus_t bus = { .sclk = (uint8_t)((mode >> 1) & 1),
                          .mosi = 0, .miso = 0, .cs = 1 };

        memset(rx, 0, sizeof(rx));
        slave_buf  = 0xA5;
        slave_bpos = 7;

        spi_transfer_buffer(&bus, &config, tx, rx, sizeof(tx), loopback_slave);

        printf("Mode %d (CPOL=%d,CPHA=%d):\n", mode, (mode>>1)&1, mode&1);
        printf("  TX: ");
        for (size_t i = 0; i < sizeof(tx); i++) printf("%02X ", tx[i]);
        printf("\n");
        printf("  RX: ");
        for (size_t i = 0; i < sizeof(rx); i++) printf("%02X ", rx[i]);
        printf("\n\n");
    }

#ifdef HARDWARE
    if (argc > 1) {
        spi_config_t hw_cfg = { .mode=0, .bits_per_word=8,
                                 .speed_hz=500000, .msb_first=1 };
        int fd = spi_open_device(argv[1], &hw_cfg);
        if (fd < 0) return 1;
        memset(rx, 0, sizeof(rx));
        spi_hw_transfer(fd, &hw_cfg, tx, rx, sizeof(tx));
        printf("Hardware TX: ");
        for (size_t i = 0; i < sizeof(tx); i++) printf("%02X ", tx[i]);
        printf("\nHardware RX: ");
        for (size_t i = 0; i < sizeof(rx); i++) printf("%02X ", rx[i]);
        printf("\n");
        close(fd);
    }
#endif

    return 0;
}
