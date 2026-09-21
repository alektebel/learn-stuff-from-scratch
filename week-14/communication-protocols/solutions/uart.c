/*
 * UART / USART Implementation - Solution
 *
 * Complete working implementation of UART frame encoding/decoding.
 *
 * Compilation: gcc -Wall -o uart uart.c
 * Run: ./uart
 *
 * Hardware variant: gcc -DHARDWARE -Wall -o uart uart.c
 */

#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>

#ifdef HARDWARE
#include <unistd.h>
#include <fcntl.h>
#include <termios.h>
#include <errno.h>
#endif

typedef enum {
    PARITY_NONE = 0,
    PARITY_ODD,
    PARITY_EVEN
} uart_parity_t;

typedef struct {
    uint32_t baud_rate;
    uint8_t  data_bits;
    uart_parity_t parity;
    uint8_t  stop_bits;
} uart_config_t;

#define MAX_FRAME_BITS 12

typedef struct {
    uint8_t bits[MAX_FRAME_BITS];
    int     length;
} uart_frame_t;

/* =========================================================================
 * uart_calc_parity
 * ========================================================================= */
int uart_calc_parity(uint8_t byte, int data_bits, uart_parity_t type)
{
    if (type == PARITY_NONE) return 0;

    int ones = 0;
    for (int i = 0; i < data_bits; i++)
        ones += (byte >> i) & 1;

    if (type == PARITY_EVEN)
        return (ones % 2 != 0) ? 1 : 0;   /* make total even */
    else /* ODD */
        return (ones % 2 == 0) ? 1 : 0;   /* make total odd  */
}

/* =========================================================================
 * uart_frame_byte
 * ========================================================================= */
void uart_frame_byte(uint8_t byte, const uart_config_t *config, uart_frame_t *frame)
{
    int pos = 0;

    /* Start bit */
    frame->bits[pos++] = 0;

    /* Data bits, LSB first */
    for (int i = 0; i < config->data_bits; i++)
        frame->bits[pos++] = (byte >> i) & 1;

    /* Parity bit */
    if (config->parity != PARITY_NONE)
        frame->bits[pos++] = (uint8_t)uart_calc_parity(byte, config->data_bits, config->parity);

    /* Stop bit(s) */
    for (int s = 0; s < config->stop_bits; s++)
        frame->bits[pos++] = 1;

    frame->length = pos;
}

/* =========================================================================
 * uart_deframe_byte  – returns decoded byte (0-255) or negative error code
 * ========================================================================= */
int uart_deframe_byte(const uart_frame_t *frame, const uart_config_t *config)
{
    if (frame->bits[0] != 0)
        return -1; /* bad start bit */

    /* Reconstruct byte from data bits (LSB first) */
    uint8_t result = 0;
    for (int i = 0; i < config->data_bits; i++)
        result |= (uint8_t)(frame->bits[1 + i] << i);

    int pos = 1 + config->data_bits;

    /* Check parity */
    if (config->parity != PARITY_NONE) {
        uint8_t expected = (uint8_t)uart_calc_parity(result, config->data_bits, config->parity);
        if (frame->bits[pos] != expected)
            return -2; /* parity error */
        pos++;
    }

    /* Check stop bit(s) */
    for (int s = 0; s < config->stop_bits; s++) {
        if (frame->bits[pos++] != 1)
            return -3; /* framing error */
    }

    return (int)result;
}

/* =========================================================================
 * uart_baud_delay_us
 * ========================================================================= */
uint32_t uart_baud_delay_us(uint32_t baud_rate)
{
    return 1000000U / baud_rate;
}

/* =========================================================================
 * Hardware: open and configure serial port
 * ========================================================================= */
#ifdef HARDWARE
static speed_t baud_to_termios(uint32_t baud)
{
    switch (baud) {
        case    9600: return B9600;
        case   19200: return B19200;
        case   38400: return B38400;
        case   57600: return B57600;
        case  115200: return B115200;
        case  230400: return B230400;
        case  460800: return B460800;
        case  921600: return B921600;
        default:      return B115200;
    }
}

int uart_open_port(const char *device, const uart_config_t *config)
{
    int fd = open(device, O_RDWR | O_NOCTTY | O_SYNC);
    if (fd < 0) { perror("open"); return -1; }

    struct termios tty;
    if (tcgetattr(fd, &tty) != 0) { perror("tcgetattr"); close(fd); return -1; }

    cfmakeraw(&tty);
    cfsetispeed(&tty, baud_to_termios(config->baud_rate));
    cfsetospeed(&tty, baud_to_termios(config->baud_rate));

    /* Data bits */
    tty.c_cflag &= ~CSIZE;
    switch (config->data_bits) {
        case 5: tty.c_cflag |= CS5; break;
        case 6: tty.c_cflag |= CS6; break;
        case 7: tty.c_cflag |= CS7; break;
        default: tty.c_cflag |= CS8; break;
    }

    /* Parity */
    if (config->parity == PARITY_NONE) {
        tty.c_cflag &= ~PARENB;
    } else {
        tty.c_cflag |= PARENB;
        if (config->parity == PARITY_ODD)
            tty.c_cflag |= PARODD;
        else
            tty.c_cflag &= ~PARODD;
    }

    /* Stop bits */
    if (config->stop_bits == 2)
        tty.c_cflag |= CSTOPB;
    else
        tty.c_cflag &= ~CSTOPB;

    tty.c_cflag |= (CLOCAL | CREAD);
    tty.c_cc[VMIN]  = 1;
    tty.c_cc[VTIME] = 5;

    if (tcsetattr(fd, TCSANOW, &tty) != 0) {
        perror("tcsetattr"); close(fd); return -1;
    }
    return fd;
}

int uart_send_byte(int fd, uint8_t byte)
{
    return (write(fd, &byte, 1) == 1) ? 0 : -1;
}

int uart_recv_byte(int fd)
{
    uint8_t byte;
    ssize_t n = read(fd, &byte, 1);
    return (n == 1) ? (int)byte : -1;
}
#endif  /* HARDWARE */

/* =========================================================================
 * Helper: print a UART frame
 * ========================================================================= */
static void print_frame(const uart_frame_t *frame, const uart_config_t *config)
{
    printf("  Frame [%d bits]: ", frame->length);
    printf("START(%d) ", frame->bits[0]);
    for (int i = 1; i <= config->data_bits; i++)
        printf("D%d(%d) ", i - 1, frame->bits[i]);
    int pos = 1 + config->data_bits;
    if (config->parity != PARITY_NONE)
        printf("PAR(%d) ", frame->bits[pos++]);
    for (int s = 0; s < config->stop_bits; s++)
        printf("STOP(%d) ", frame->bits[pos++]);
    printf("\n");
}

/* =========================================================================
 * main
 * ========================================================================= */
int main(int argc, char *argv[])
{
    (void)argc; (void)argv;

    uart_config_t configs[] = {
        { 115200, 8, PARITY_NONE, 1 },  /* 8N1 */
        { 9600,   8, PARITY_EVEN, 1 },  /* 8E1 */
        { 9600,   8, PARITY_ODD,  1 },  /* 8O1 */
        { 9600,   7, PARITY_EVEN, 2 },  /* 7E2 */
    };
    const char *config_names[] = { "8N1", "8E1", "8O1", "7E2" };
    const char *test_str = "Hi!";

    printf("=== UART Simulator ===\n\n");

    for (int c = 0; c < 4; c++) {
        uart_config_t *cfg = &configs[c];
        printf("Config: %u baud %s  (bit period: %u µs)\n",
               cfg->baud_rate, config_names[c],
               uart_baud_delay_us(cfg->baud_rate));

        int errors = 0;
        for (int i = 0; test_str[i] != '\0'; i++) {
            uint8_t orig = (uint8_t)test_str[i];
            uart_frame_t frame;
            uart_frame_byte(orig, cfg, &frame);
            print_frame(&frame, cfg);

            int decoded = uart_deframe_byte(&frame, cfg);
            if (decoded < 0) {
                printf("  ERROR decoding byte '%c' (code %d)\n", orig, decoded);
                errors++;
            } else if ((uint8_t)decoded != orig) {
                printf("  MISMATCH: sent 0x%02X, got 0x%02X\n", orig, (uint8_t)decoded);
                errors++;
            } else {
                printf("  '%c' (0x%02X) → frame → '%c' (0x%02X) ✓\n",
                       orig, orig, (char)decoded, (uint8_t)decoded);
            }
        }
        printf("  Result: %s\n\n", errors == 0 ? "ALL PASSED" : "ERRORS FOUND");
    }

#ifdef HARDWARE
    if (argc > 1) {
        uart_config_t hw_cfg = { 115200, 8, PARITY_NONE, 1 };
        int fd = uart_open_port(argv[1], &hw_cfg);
        if (fd < 0) { fprintf(stderr, "Cannot open %s\n", argv[1]); return 1; }
        printf("Hardware mode on %s at 115200 8N1\n", argv[1]);
        for (int i = 0; test_str[i]; i++)
            uart_send_byte(fd, (uint8_t)test_str[i]);
        printf("Sent: %s\n", test_str);
        close(fd);
    }
#endif

    return 0;
}
