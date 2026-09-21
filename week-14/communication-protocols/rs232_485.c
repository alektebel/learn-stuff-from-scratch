/*
 * RS-232 / RS-485 Implementation - Template
 *
 * RS-232 and RS-485 are electrical standards for serial communication,
 * typically layered beneath a UART framing protocol.
 *
 * RS-232 (EIA/TIA-232):
 *   - Single-ended signaling: logic 0 = +3V…+15V, logic 1 = -3V…-15V (inverted!)
 *   - Point-to-point only (one driver, one receiver)
 *   - Max distance ~15 m at 9600 baud; ~1.5 m at 115200 baud
 *   - DB-9 / DB-25 connector; common signals: TX, RX, RTS, CTS, DTR, DSR
 *   - Hardware flow control: RTS/CTS (hardware) or XON/XOFF (software)
 *
 * RS-485 (EIA/TIA-485):
 *   - Differential signaling: (A-B) > +200mV = logic 1, < -200mV = logic 0
 *   - Multi-drop: up to 32 nodes on one bus (with 1/8-unit-load transceivers: 256+)
 *   - Max distance 1200 m at 100 kbps; ~12 m at 10 Mbps
 *   - Half-duplex: direction controlled by a TX-enable (DE) pin
 *   - Requires 120Ω termination at both ends; bias resistors to define idle state
 *
 * This file has two modes:
 *   SOFTWARE mode  – simulate RS-232/RS-485 framing in software (default)
 *   HARDWARE mode  – use Linux termios for real RS-232 or RS-485
 *                    Compile: gcc -DHARDWARE -o rs485 rs232_485.c
 *                    Run:     ./rs485 /dev/ttyUSB0
 *
 * Compilation (software mode): gcc -Wall -o rs485 rs232_485.c
 * Run: ./rs485
 *
 * Learning path:
 *   TODO 1  – implement rs232_encode_voltage() and rs232_decode_voltage()
 *   TODO 2  – implement rs485_encode_differential() and rs485_decode_differential()
 *   TODO 3  – implement a simple framed packet protocol on top of RS-485
 *   TODO 4  – implement rs485_send_packet() with TX-enable simulation
 *   TODO 5  – implement rs485_recv_packet() with collision detection
 *   TODO 6  – (HARDWARE) open serial port and configure RS-485 mode
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
#include <sys/ioctl.h>
#include <linux/serial.h>
#include <errno.h>
#endif

/* =========================================================================
 * RS-232 voltage levels
 * ========================================================================= */

/*
 * In RS-232 the voltage polarity is INVERTED compared to logic levels:
 *   Data 0 (SPACE) = +3V … +15V
 *   Data 1 (MARK)  = -3V … -15V
 *   Idle line      = MARK (-V)
 */
typedef struct {
    int millivolts;   /* voltage × 1000, e.g. 12000 = +12V, -12000 = -12V */
} rs232_voltage_t;

/* =========================================================================
 * TODO 1: Implement rs232_encode_voltage and rs232_decode_voltage
 *
 * rs232_encode_voltage(logic_bit):
 *   - logic_bit == 0 → return +12000 mV  (SPACE = positive voltage)
 *   - logic_bit == 1 → return -12000 mV  (MARK  = negative voltage)
 *   - This is the physical layer encoding of RS-232
 *
 * rs232_decode_voltage(v):
 *   - v->millivolts > +3000  → return 0 (logic 0 / SPACE)
 *   - v->millivolts < -3000  → return 1 (logic 1 / MARK)
 *   - otherwise              → return -1 (undefined / transition region)
 *
 * These functions model the RS-232 transceiver chip (e.g. MAX232).
 * ========================================================================= */
rs232_voltage_t rs232_encode_voltage(uint8_t logic_bit)
{
    /* TODO: convert logic bit to RS-232 voltage */
    (void)logic_bit;
    rs232_voltage_t v = { .millivolts = 0 };
    return v;
}

int rs232_decode_voltage(const rs232_voltage_t *v)
{
    /* TODO: convert RS-232 voltage to logic bit, or -1 if undefined */
    (void)v;
    return -1;
}

/* =========================================================================
 * RS-485 differential pair
 * ========================================================================= */

typedef struct {
    int a_mv;   /* voltage on A line in millivolts */
    int b_mv;   /* voltage on B line in millivolts */
} rs485_pair_t;

/* =========================================================================
 * TODO 2: Implement rs485_encode_differential and rs485_decode_differential
 *
 * RS-485 uses differential signaling:
 *   logic 1: A > B  (typically A=+2.5V, B=+0.5V → differential = +2.0V)
 *   logic 0: A < B  (typically A=+0.5V, B=+2.5V → differential = -2.0V)
 *   Receiver detects |V_A - V_B| > 200mV as a valid signal
 *
 * rs485_encode_differential(logic_bit):
 *   - logic_bit == 1 → a_mv = 2500, b_mv = 500   (A-B = +2000 mV)
 *   - logic_bit == 0 → a_mv = 500,  b_mv = 2500  (A-B = -2000 mV)
 *
 * rs485_decode_differential(pair):
 *   - (a_mv - b_mv) >  200 → return 1
 *   - (a_mv - b_mv) < -200 → return 0
 *   - otherwise            → return -1 (undefined / bus idle / noise)
 *
 * Note: RS-485 logic is NOT inverted (unlike RS-232).
 * ========================================================================= */
rs485_pair_t rs485_encode_differential(uint8_t logic_bit)
{
    /* TODO: convert logic bit to RS-485 differential pair */
    (void)logic_bit;
    rs485_pair_t p = { .a_mv = 0, .b_mv = 0 };
    return p;
}

int rs485_decode_differential(const rs485_pair_t *pair)
{
    /* TODO: convert RS-485 differential pair to logic bit */
    (void)pair;
    return -1;
}

/* =========================================================================
 * RS-485 framed packet protocol
 *
 * A minimal application-layer protocol on top of RS-485 UART framing:
 *
 *   [PREAMBLE(1)] [DEST_ADDR(1)] [SRC_ADDR(1)] [LENGTH(1)] [DATA(0–255)] [CRC8(1)]
 *
 *   PREAMBLE  = 0xAA  (sync byte, easy to detect)
 *   DEST_ADDR = destination node address (0xFF = broadcast)
 *   SRC_ADDR  = sender's node address
 *   LENGTH    = number of data bytes that follow (0–255)
 *   DATA      = payload
 *   CRC8      = XOR of all bytes from DEST_ADDR through last DATA byte
 * ========================================================================= */

#define RS485_PREAMBLE     0xAA
#define RS485_BROADCAST    0xFF
#define RS485_MAX_PAYLOAD  255
#define RS485_HEADER_SIZE  4    /* PREAMBLE + DEST + SRC + LENGTH */
#define RS485_PACKET_MAX   (RS485_HEADER_SIZE + RS485_MAX_PAYLOAD + 1)

typedef struct {
    uint8_t dest_addr;
    uint8_t src_addr;
    uint8_t length;
    uint8_t data[RS485_MAX_PAYLOAD];
} rs485_packet_t;

/* =========================================================================
 * TODO 3: Implement rs485_calc_crc8
 *
 * Compute a simple 8-bit CRC (XOR of all bytes from dest_addr through
 * the last data byte).
 *
 * Guidelines:
 *   - XOR together: dest_addr, src_addr, length, data[0..length-1]
 *   - Return the result
 * ========================================================================= */
uint8_t rs485_calc_crc8(const rs485_packet_t *pkt)
{
    /* TODO: compute and return the 8-bit CRC */
    (void)pkt;
    return 0;
}

/* =========================================================================
 * TODO 4: Implement rs485_encode_packet and rs485_decode_packet
 *
 * rs485_encode_packet(pkt, buf, buf_max):
 *   Build the on-wire byte stream from an rs485_packet_t:
 *   1. Write PREAMBLE (0xAA)
 *   2. Write DEST_ADDR
 *   3. Write SRC_ADDR
 *   4. Write LENGTH
 *   5. Write LENGTH bytes of data
 *   6. Write CRC8 (call rs485_calc_crc8)
 *   Return total bytes written, or -1 if buf_max too small.
 *
 * rs485_decode_packet(buf, len, pkt):
 *   Parse a received byte stream:
 *   1. Check buf[0] == PREAMBLE; return -1 if not
 *   2. Extract DEST_ADDR, SRC_ADDR, LENGTH
 *   3. Check remaining bytes >= LENGTH + 1 (CRC); return -2 if not
 *   4. Copy LENGTH bytes into pkt->data
 *   5. Verify CRC8; return -3 on mismatch
 *   6. Return 0 on success
 * ========================================================================= */
int rs485_encode_packet(const rs485_packet_t *pkt, uint8_t *buf, int buf_max)
{
    /* TODO: serialise packet into buf */
    (void)pkt; (void)buf; (void)buf_max;
    return -1;
}

int rs485_decode_packet(const uint8_t *buf, int len, rs485_packet_t *pkt)
{
    /* TODO: deserialise buf into pkt */
    (void)buf; (void)len; (void)pkt;
    return -1;
}

/* =========================================================================
 * TODO 5: Implement rs485_send_packet (with TX-enable simulation)
 *
 * In RS-485, the driver must enable TX before sending and disable it after:
 *   1. Assert DE (Driver Enable) HIGH  → enables the differential driver
 *   2. Send all bytes of the encoded packet
 *   3. De-assert DE LOW               → releases the bus for other nodes
 *
 * In software simulation:
 *   - "Sending" means copying the encoded packet into a shared bus buffer
 *   - Print a message when DE is asserted/de-asserted
 *   - Return 0 on success, -1 on error
 *
 * In hardware mode (see TODO 6), the actual UART write() replaces the copy.
 * ========================================================================= */

/* Shared simulated bus (single-byte ring buffer for demo purposes) */
#define SIM_BUS_SIZE 512
static uint8_t sim_bus[SIM_BUS_SIZE];
static int     sim_bus_len = 0;

int rs485_send_packet(const rs485_packet_t *pkt)
{
    /* TODO: encode and "send" the packet (copy to sim_bus) */
    (void)pkt;
    return -1;
}

/* =========================================================================
 * TODO 6: Implement rs485_recv_packet
 *
 * In software simulation, read from sim_bus (set by rs485_send_packet).
 * Decode the bytes with rs485_decode_packet().
 * Filter: if the destination address does not match `my_addr` and is not
 * the broadcast address, return 1 (not for us) without filling `pkt`.
 * Return 0 on successful receipt, -1 on decode error, 1 if not addressed to us.
 * ========================================================================= */
int rs485_recv_packet(uint8_t my_addr, rs485_packet_t *pkt)
{
    /* TODO: decode from sim_bus, filter by address */
    (void)my_addr; (void)pkt;
    return -1;
}

/* =========================================================================
 * TODO 7 (HARDWARE): Implement serial port functions for RS-485
 *
 * rs485_open_port(device):
 *   - open(device, O_RDWR | O_NOCTTY)
 *   - Configure with termios: raw mode, 9600 8N1 (or as needed)
 *   - On Linux, enable RS-485 mode via ioctl(fd, TIOCSRS485, &rs485conf)
 *     where rs485conf.flags = SER_RS485_ENABLED | SER_RS485_RTS_ON_SEND
 *   - Return fd or -1 on error
 *
 * rs485_hw_send(fd, buf, len):
 *   - write(fd, buf, len); return bytes written or -1
 *
 * rs485_hw_recv(fd, buf, max_len):
 *   - read(fd, buf, max_len); return bytes read or -1
 * ========================================================================= */
#ifdef HARDWARE
int rs485_open_port(const char *device)
{
    /* TODO: open serial port and enable RS-485 mode */
    (void)device;
    return -1;
}

int rs485_hw_send(int fd, const uint8_t *buf, int len)
{
    /* TODO: write buf to fd */
    (void)fd; (void)buf; (void)len;
    return -1;
}

int rs485_hw_recv(int fd, uint8_t *buf, int max_len)
{
    /* TODO: read from fd into buf */
    (void)fd; (void)buf; (void)max_len;
    return -1;
}
#endif

/* =========================================================================
 * Helper: print an RS-485 packet
 * ========================================================================= */
static void print_rs485_packet(const rs485_packet_t *pkt)
{
    printf("RS-485 Packet: DEST=0x%02X SRC=0x%02X LEN=%d  Data:",
           pkt->dest_addr, pkt->src_addr, pkt->length);
    for (int i = 0; i < pkt->length; i++)
        printf(" %02X", pkt->data[i]);
    printf("\n");
}

/* =========================================================================
 * TODO 8: Wire everything together in main()
 *
 * Software mode:
 *   1. Demonstrate RS-232 voltage encoding:
 *      - Encode bits 0 and 1, print voltages
 *      - Decode them back, verify
 *   2. Demonstrate RS-485 differential encoding:
 *      - Encode bits 0 and 1, print A/B voltages
 *      - Decode them back, verify
 *   3. Demonstrate the RS-485 packet protocol:
 *      - Create a packet (dest=0x02, src=0x01, data="Hello RS-485")
 *      - Send it with rs485_send_packet()
 *      - Receive it as node 0x02 with rs485_recv_packet()
 *      - Try receiving as node 0x03 (should return "not for us")
 *      - Send a broadcast (dest=0xFF) and receive as any node
 *
 * Hardware mode (compiled with -DHARDWARE):
 *   1. Parse argv[1] as device path
 *   2. Open with rs485_open_port()
 *   3. Send a test packet and then receive one, printing both
 * ========================================================================= */
int main(int argc, char *argv[])
{
    (void)argc; (void)argv;

    printf("=== RS-232 / RS-485 Simulator ===\n\n");

    /* --- RS-232 Voltage Demo --- */
    printf("-- RS-232 Physical Layer --\n");
    for (int bit = 0; bit <= 1; bit++) {
        rs232_voltage_t v = rs232_encode_voltage((uint8_t)bit);
        int decoded = rs232_decode_voltage(&v);
        printf("  Logic %d → %+d mV → Logic %d %s\n",
               bit, v.millivolts, decoded,
               (decoded == bit) ? "✓" : "✗ MISMATCH");
    }

    /* --- RS-485 Differential Demo --- */
    printf("\n-- RS-485 Physical Layer --\n");
    for (int bit = 0; bit <= 1; bit++) {
        rs485_pair_t p = rs485_encode_differential((uint8_t)bit);
        int decoded = rs485_decode_differential(&p);
        printf("  Logic %d → A=%+d mV, B=%+d mV (diff=%+d mV) → Logic %d %s\n",
               bit, p.a_mv, p.b_mv, p.a_mv - p.b_mv, decoded,
               (decoded == bit) ? "✓" : "✗ MISMATCH");
    }

    /* --- RS-485 Packet Demo --- */
    printf("\n-- RS-485 Packet Protocol --\n");
    /* TODO: build and exercise the send/receive packet pipeline */

    return 0;
}
