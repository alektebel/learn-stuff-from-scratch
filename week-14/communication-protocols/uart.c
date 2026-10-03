/*
 * UART / USART Implementation - Template
 *
 * UART (Universal Asynchronous Receiver/Transmitter) is the simplest serial
 * protocol: no shared clock, both sides agree on a baud rate in advance.
 *
 * This file has two modes:
 *   SOFTWARE mode  – simulate UART framing entirely in software (default)
 *   HARDWARE mode  – open a real serial port via POSIX termios
 *                    Compile: gcc -DHARDWARE -o uart uart.c
 *                    Run:     ./uart /dev/ttyUSB0
 *
 * Compilation (software mode): gcc -Wall -o uart uart.c
 * Run: ./uart
 *
 * Learning path:
 *   TODO 1  – understand and fill in uart_frame_byte()
 *   TODO 2  – implement uart_deframe_byte() (including parity validation)
 *   TODO 3  – add parity calculation (uart_calc_parity)
 *   TODO 4  – implement the baud-rate timing helper
 *   TODO 5  – (HARDWARE) open and configure a real serial port
 *   TODO 6  – (HARDWARE) send/receive bytes over the serial port
 *   TODO 7  – wire everything together in main()
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

/* =========================================================================
 * UART frame configuration
 * ========================================================================= */

typedef enum {
    PARITY_NONE = 0,
    PARITY_ODD,
    PARITY_EVEN
} uart_parity_t;

typedef struct {
    uint32_t baud_rate;     /* e.g. 9600, 115200 */
    uint8_t  data_bits;     /* 5, 6, 7, or 8     */
    uart_parity_t parity;   /* NONE, ODD, EVEN   */
    uint8_t  stop_bits;     /* 1 or 2            */
} uart_config_t;

/*
 * A "frame" in software simulation is just an array of bits.
 * Index 0 = start bit, 1..data_bits = data, next = optional parity,
 * last 1 or 2 = stop bit(s).
 * Maximum frame size: 1 + 8 + 1 + 2 = 12 bits.
 */
#define MAX_FRAME_BITS 12

typedef struct {
    uint8_t bits[MAX_FRAME_BITS];  /* each element is 0 or 1 */
    int     length;                /* total number of bits    */
} uart_frame_t;

/* =========================================================================
 * TODO 1: Implement uart_frame_byte
 *
 * Convert a single byte into a UART frame (array of bits).
 *
 * Frame structure (LSB first for data bits):
 *   [0]          start bit   = 0  (line pulled LOW to signal start)
 *   [1..data_bits] data bits  = LSB first
 *   [next]       parity bit  (only if config->parity != PARITY_NONE)
 *   [last 1–2]   stop bit(s) = 1  (line returns HIGH)
 *
 * Guidelines:
 *   - Set frame->bits[0] = 0  (start bit)
 *   - Loop through data_bits, extracting each bit from `byte` LSB-first
 *   - If parity is not NONE, compute and append the parity bit
 *     (use uart_calc_parity defined below)
 *   - Append stop_bits * 1 at the end
 *   - Set frame->length to the total number of bits written
 *
 * Hint: to extract bit i from byte: (byte >> i) & 1
 * ========================================================================= */
int uart_calc_parity(uint8_t byte, int data_bits, uart_parity_t type);  /* forward decl */

void uart_frame_byte(uint8_t byte, const uart_config_t *config, uart_frame_t *frame)
{
    /* TODO: build the frame bit-by-bit */
    (void)byte; (void)config; (void)frame;
}

/* =========================================================================
 * TODO 2: Implement uart_deframe_byte
 *
 * Decode a UART frame back to a byte, checking start and stop bits.
 *
 * Guidelines:
 *   - Verify frame->bits[0] == 0 (start bit); return -1 on error
 *   - Reconstruct the byte from bits[1..data_bits] (LSB first)
 *   - If parity is not NONE, read the parity bit and verify it
 *     (return -2 on parity error)
 *   - Verify stop bit(s) == 1; return -3 on framing error
 *   - Return the decoded byte (0–255) on success
 *
 * Hint: to set bit i in result: result |= (bit << i)
 * ========================================================================= */
int uart_deframe_byte(const uart_frame_t *frame, const uart_config_t *config)
{
    /* TODO: decode the frame, return byte value or negative error code */
    (void)frame; (void)config;
    return -1;
}

/* =========================================================================
 * TODO 3: Implement uart_calc_parity
 *
 * Calculate the parity bit for `byte` using the given scheme.
 *
 * Guidelines:
 *   - Count the number of 1-bits in the lower `data_bits` bits of `byte`
 *   - EVEN parity: parity bit = 1 if count is odd  (makes total 1s even)
 *   - ODD  parity: parity bit = 1 if count is even (makes total 1s odd)
 *   - NONE:        return 0
 *
 * Hint: use __builtin_popcount() or count manually with a loop
 * ========================================================================= */
int uart_calc_parity(uint8_t byte, int data_bits, uart_parity_t type)
{
    /* TODO: return parity bit value (0 or 1) */
    (void)byte; (void)data_bits; (void)type;
    return 0;
}

/* =========================================================================
 * TODO 4: Implement uart_baud_delay_us
 *
 * Return the duration of one bit period in microseconds.
 *
 * Guidelines:
 *   - One bit period = 1 / baud_rate seconds
 *   - Convert to microseconds: 1,000,000 / baud_rate
 *   - Use integer arithmetic; avoid floating point if possible
 *
 * Example: baud_rate = 9600 → 104 µs per bit
 * ========================================================================= */
uint32_t uart_baud_delay_us(uint32_t baud_rate)
{
    /* TODO: return bit period in microseconds */
    (void)baud_rate;
    return 0;
}

/* =========================================================================
 * TODO 5 (HARDWARE): Implement uart_open_port
 *
 * Open and configure a real serial port using POSIX termios.
 *
 * Guidelines (only relevant when compiled with -DHARDWARE):
 *   - Open the device file (e.g. /dev/ttyUSB0) with O_RDWR | O_NOCTTY
 *   - Use tcgetattr() to read current settings into a struct termios
 *   - Call cfmakeraw() to disable all special processing
 *   - Set baud rate with cfsetispeed() and cfsetospeed()
 *     (use B9600, B115200, etc. constants)
 *   - Configure data bits (CS5–CS8), parity (PARENB/PARODD), stop bits (CSTOPB)
 *   - Apply settings with tcsetattr(..., TCSANOW, ...)
 *   - Return the file descriptor, or -1 on error
 *
 * Hint: See `man 3 termios` for full documentation
 * ========================================================================= */
#ifdef HARDWARE
int uart_open_port(const char *device, const uart_config_t *config)
{
    /* TODO: open and configure the serial port */
    (void)device; (void)config;
    return -1;
}
#endif

/* =========================================================================
 * TODO 6 (HARDWARE): Implement uart_send_byte and uart_recv_byte
 *
 * Send / receive one byte over an open serial port file descriptor.
 *
 * Guidelines:
 *   - uart_send_byte: call write(fd, &byte, 1); return 0 on success, -1 on error
 *   - uart_recv_byte: call read(fd, &byte, 1);  return byte value, -1 on error
 * ========================================================================= */
#ifdef HARDWARE
int uart_send_byte(int fd, uint8_t byte)
{
    /* TODO: write one byte to fd */
    (void)fd; (void)byte;
    return -1;
}

int uart_recv_byte(int fd)
{
    /* TODO: read one byte from fd, return it or -1 */
    (void)fd;
    return -1;
}
#endif

/* =========================================================================
 * Helper: print a UART frame as a string of bits
 * ========================================================================= */
static void print_frame(const uart_frame_t *frame, const uart_config_t *config)
{
    printf("Frame [%d bits]: ", frame->length);
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
 * TODO 7: Wire everything together in main()
 *
 * Software mode:
 *   1. Define a uart_config_t (e.g. 9600 8N1)
 *   2. For each byte in a test string:
 *      a. Call uart_frame_byte() to encode it
 *      b. Print the resulting frame
 *      c. Call uart_deframe_byte() to decode it
 *      d. Verify decoded byte matches original
 *   3. Print a summary
 *
 * Hardware mode (when compiled with -DHARDWARE):
 *   1. Parse argv[1] as the serial device path
 *   2. Open the port with uart_open_port()
 *   3. Send a test string byte by byte with uart_send_byte()
 *   4. Read it back with uart_recv_byte() (requires loopback cable)
 *   5. Print each received byte
 * ========================================================================= */
int main(int argc, char *argv[])
{
    (void)argc; (void)argv;

    uart_config_t config = {
        .baud_rate = 115200,
        .data_bits = 8,
        .parity    = PARITY_NONE,
        .stop_bits = 1,
    };

    const char *test_str = "Hello UART!";
    printf("=== UART Simulator ===\n");
    printf("Config: %u baud, %d%s%d\n",
           config.baud_rate, config.data_bits,
           config.parity == PARITY_NONE ? "N" :
           config.parity == PARITY_ODD  ? "O" : "E",
           config.stop_bits);
    printf("Bit period: %u µs\n\n", uart_baud_delay_us(config.baud_rate));

    /* TODO: iterate over test_str, frame each byte, deframe, and verify */

    return 0;
}
