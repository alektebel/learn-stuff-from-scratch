/*
 * RS-232 / RS-485 Implementation - Solution
 *
 * Complete working implementation: RS-232 voltage model, RS-485
 * differential encoding, and a framed multi-drop packet protocol.
 *
 * Compilation: gcc -Wall -o rs485 rs232_485.c
 * Run: ./rs485
 *
 * Hardware variant: gcc -DHARDWARE -Wall -o rs485 rs232_485.c
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
 * RS-232 Physical Layer
 * ========================================================================= */
typedef struct {
    int millivolts;
} rs232_voltage_t;

rs232_voltage_t rs232_encode_voltage(uint8_t logic_bit)
{
    /* RS-232: 0 = +12V (SPACE), 1 = -12V (MARK) */
    rs232_voltage_t v;
    v.millivolts = (logic_bit == 0) ? 12000 : -12000;
    return v;
}

int rs232_decode_voltage(const rs232_voltage_t *v)
{
    if (v->millivolts >  3000) return 0;   /* SPACE = logic 0 */
    if (v->millivolts < -3000) return 1;   /* MARK  = logic 1 */
    return -1;                              /* undefined       */
}

/* =========================================================================
 * RS-485 Physical Layer
 * ========================================================================= */
typedef struct {
    int a_mv;
    int b_mv;
} rs485_pair_t;

rs485_pair_t rs485_encode_differential(uint8_t logic_bit)
{
    rs485_pair_t p;
    if (logic_bit) {
        p.a_mv = 2500; p.b_mv = 500;   /* A > B → logic 1 */
    } else {
        p.a_mv = 500;  p.b_mv = 2500;  /* A < B → logic 0 */
    }
    return p;
}

int rs485_decode_differential(const rs485_pair_t *pair)
{
    int diff = pair->a_mv - pair->b_mv;
    if (diff >  200) return 1;
    if (diff < -200) return 0;
    return -1;  /* undefined */
}

/* =========================================================================
 * RS-485 Packet Protocol
 * PREAMBLE(1) | DEST(1) | SRC(1) | LEN(1) | DATA(LEN) | CRC8(1)
 * ========================================================================= */
#define RS485_PREAMBLE     0xAA
#define RS485_BROADCAST    0xFF
#define RS485_MAX_PAYLOAD  255
#define RS485_HEADER_SIZE  4
#define RS485_PACKET_MAX   (RS485_HEADER_SIZE + RS485_MAX_PAYLOAD + 1)

typedef struct {
    uint8_t dest_addr;
    uint8_t src_addr;
    uint8_t length;
    uint8_t data[RS485_MAX_PAYLOAD];
} rs485_packet_t;

uint8_t rs485_calc_crc8(const rs485_packet_t *pkt)
{
    uint8_t crc = pkt->dest_addr ^ pkt->src_addr ^ pkt->length;
    for (int i = 0; i < pkt->length; i++)
        crc ^= pkt->data[i];
    return crc;
}

int rs485_encode_packet(const rs485_packet_t *pkt, uint8_t *buf, int buf_max)
{
    int needed = RS485_HEADER_SIZE + pkt->length + 1;
    if (buf_max < needed) return -1;

    int pos = 0;
    buf[pos++] = RS485_PREAMBLE;
    buf[pos++] = pkt->dest_addr;
    buf[pos++] = pkt->src_addr;
    buf[pos++] = pkt->length;
    memcpy(buf + pos, pkt->data, pkt->length);
    pos += pkt->length;
    buf[pos++] = rs485_calc_crc8(pkt);
    return pos;
}

int rs485_decode_packet(const uint8_t *buf, int len, rs485_packet_t *pkt)
{
    if (len < RS485_HEADER_SIZE + 1) return -1;
    if (buf[0] != RS485_PREAMBLE)    return -1;

    pkt->dest_addr = buf[1];
    pkt->src_addr  = buf[2];
    pkt->length    = buf[3];

    if (len < RS485_HEADER_SIZE + pkt->length + 1) return -2;

    memcpy(pkt->data, buf + RS485_HEADER_SIZE, pkt->length);

    uint8_t expected = rs485_calc_crc8(pkt);
    uint8_t received = buf[RS485_HEADER_SIZE + pkt->length];
    if (expected != received) return -3;

    return 0;
}

/* =========================================================================
 * Shared simulated bus
 * ========================================================================= */
#define SIM_BUS_SIZE 512
static uint8_t sim_bus[SIM_BUS_SIZE];
static int     sim_bus_len = 0;

int rs485_send_packet(const rs485_packet_t *pkt)
{
    uint8_t buf[RS485_PACKET_MAX];
    int len = rs485_encode_packet(pkt, buf, sizeof(buf));
    if (len < 0) return -1;

    printf("  [TX] DE=HIGH (bus driven)\n");
    memcpy(sim_bus, buf, (size_t)len);
    sim_bus_len = len;
    printf("  [TX] %d bytes: ", len);
    for (int i = 0; i < len; i++) printf("%02X ", buf[i]);
    printf("\n");
    printf("  [TX] DE=LOW  (bus released)\n");
    return 0;
}

int rs485_recv_packet(uint8_t my_addr, rs485_packet_t *pkt)
{
    if (sim_bus_len == 0) return -1;

    rs485_packet_t tmp;
    int rc = rs485_decode_packet(sim_bus, sim_bus_len, &tmp);
    if (rc != 0) return rc;

    /* Address filter */
    if (tmp.dest_addr != my_addr && tmp.dest_addr != RS485_BROADCAST)
        return 1;  /* not for us */

    *pkt = tmp;
    return 0;
}

/* =========================================================================
 * Hardware: RS-485 via Linux serial port
 * ========================================================================= */
#ifdef HARDWARE
int rs485_open_port(const char *device)
{
    int fd = open(device, O_RDWR | O_NOCTTY | O_SYNC);
    if (fd < 0) { perror("open"); return -1; }

    struct termios tty;
    if (tcgetattr(fd, &tty) != 0) { perror("tcgetattr"); close(fd); return -1; }
    cfmakeraw(&tty);
    cfsetispeed(&tty, B9600);
    cfsetospeed(&tty, B9600);
    tty.c_cflag = CS8 | CLOCAL | CREAD;
    tty.c_cc[VMIN] = 1; tty.c_cc[VTIME] = 5;
    if (tcsetattr(fd, TCSANOW, &tty) != 0) {
        perror("tcsetattr"); close(fd); return -1;
    }

    /* Enable RS-485 mode via Linux serial ioctl */
    struct serial_rs485 rs485conf;
    memset(&rs485conf, 0, sizeof(rs485conf));
    rs485conf.flags = SER_RS485_ENABLED | SER_RS485_RTS_ON_SEND;
    if (ioctl(fd, TIOCSRS485, &rs485conf) < 0)
        perror("TIOCSRS485 (RS-485 mode may not be available on this adapter)");

    return fd;
}

int rs485_hw_send(int fd, const uint8_t *buf, int len)
{
    return (int)write(fd, buf, (size_t)len);
}

int rs485_hw_recv(int fd, uint8_t *buf, int max_len)
{
    return (int)read(fd, buf, (size_t)max_len);
}
#endif  /* HARDWARE */

/* =========================================================================
 * Helper: print packet
 * ========================================================================= */
static void print_rs485_packet(const rs485_packet_t *pkt)
{
    printf("  RS-485 Packet: DEST=0x%02X SRC=0x%02X LEN=%d  Data:",
           pkt->dest_addr, pkt->src_addr, pkt->length);
    for (int i = 0; i < pkt->length; i++)
        printf(" %02X", pkt->data[i]);
    /* also print as string if printable */
    int printable = 1;
    for (int i = 0; i < pkt->length; i++)
        if (pkt->data[i] < 0x20 || pkt->data[i] > 0x7E) { printable = 0; break; }
    if (printable && pkt->length > 0) {
        printf("  \"");
        for (int i = 0; i < pkt->length; i++) printf("%c", pkt->data[i]);
        printf("\"");
    }
    printf("\n");
}

/* =========================================================================
 * main
 * ========================================================================= */
int main(int argc, char *argv[])
{
    (void)argc; (void)argv;

    printf("=== RS-232 / RS-485 Simulator ===\n\n");

    /* --- RS-232 Voltage Demo --- */
    printf("-- RS-232 Physical Layer (inverted logic!) --\n");
    for (int bit = 0; bit <= 1; bit++) {
        rs232_voltage_t v = rs232_encode_voltage((uint8_t)bit);
        int decoded = rs232_decode_voltage(&v);
        printf("  Logic %d → %+d mV → Logic %d  %s\n",
               bit, v.millivolts, decoded,
               (decoded == bit) ? "✓" : "✗ MISMATCH");
    }
    {
        /* Show the transition region */
        rs232_voltage_t v = { .millivolts = 1500 };
        int d = rs232_decode_voltage(&v);
        printf("  +1500 mV (transition zone) → %s\n",
               d < 0 ? "undefined ✓" : "ERROR");
    }

    /* --- RS-485 Differential Demo --- */
    printf("\n-- RS-485 Physical Layer (differential, NOT inverted) --\n");
    for (int bit = 0; bit <= 1; bit++) {
        rs485_pair_t p = rs485_encode_differential((uint8_t)bit);
        int decoded = rs485_decode_differential(&p);
        printf("  Logic %d → A=%+d mV, B=%+d mV (diff=%+d mV) → Logic %d  %s\n",
               bit, p.a_mv, p.b_mv, p.a_mv - p.b_mv, decoded,
               (decoded == bit) ? "✓" : "✗ MISMATCH");
    }
    {
        rs485_pair_t p = { .a_mv = 1500, .b_mv = 1500 };  /* no differential */
        int d = rs485_decode_differential(&p);
        printf("  Bus idle (A=B=1500 mV, diff=0) → %s\n",
               d < 0 ? "undefined ✓" : "ERROR");
    }

    /* --- RS-485 Packet Protocol Demo --- */
    printf("\n-- RS-485 Multi-Drop Packet Protocol --\n");

    /* Node addresses */
    uint8_t node1 = 0x01, node2 = 0x02, node3 = 0x03;

    /* Node 1 sends a message to Node 2 */
    rs485_packet_t tx_pkt;
    tx_pkt.dest_addr = node2;
    tx_pkt.src_addr  = node1;
    const char *msg  = "Hello RS-485!";
    tx_pkt.length    = (uint8_t)strlen(msg);
    memcpy(tx_pkt.data, msg, tx_pkt.length);

    printf("\n[Node 0x%02X → Node 0x%02X]\n", node1, node2);
    rs485_send_packet(&tx_pkt);

    /* Node 2 receives (should succeed) */
    rs485_packet_t rx_pkt;
    memset(&rx_pkt, 0, sizeof(rx_pkt));
    int rc = rs485_recv_packet(node2, &rx_pkt);
    printf("\n[Node 0x%02X tries to receive]\n", node2);
    if (rc == 0) {
        printf("  Received ✓\n");
        print_rs485_packet(&rx_pkt);
    } else {
        printf("  ERROR: rc=%d\n", rc);
    }

    /* Node 3 tries to receive (should be filtered out) */
    printf("\n[Node 0x%02X tries to receive (not the destination)]\n", node3);
    rc = rs485_recv_packet(node3, &rx_pkt);
    printf("  %s\n", rc == 1 ? "Filtered (not for us) ✓" : "ERROR: should not receive");

    /* Broadcast demo */
    printf("\n-- Broadcast from Node 0x%02X to all nodes --\n", node1);
    rs485_packet_t bcast_pkt;
    bcast_pkt.dest_addr = RS485_BROADCAST;
    bcast_pkt.src_addr  = node1;
    const char *bcast_msg = "BROADCAST";
    bcast_pkt.length = (uint8_t)strlen(bcast_msg);
    memcpy(bcast_pkt.data, bcast_msg, bcast_pkt.length);
    rs485_send_packet(&bcast_pkt);

    for (uint8_t n = node1; n <= node3; n++) {
        memset(&rx_pkt, 0, sizeof(rx_pkt));
        rc = rs485_recv_packet(n, &rx_pkt);
        printf("  Node 0x%02X: %s\n", n,
               rc == 0 ? "received broadcast ✓" : "did not receive (error)");
    }

    /* CRC error detection demo */
    printf("\n-- CRC Error Detection --\n");
    {
        uint8_t buf[RS485_PACKET_MAX];
        int len = rs485_encode_packet(&tx_pkt, buf, sizeof(buf));
        buf[len - 1] ^= 0xFF;  /* corrupt CRC */
        rs485_packet_t bad_pkt;
        memset(&bad_pkt, 0, sizeof(bad_pkt));
        memcpy(sim_bus, buf, (size_t)len);
        sim_bus_len = len;
        rc = rs485_recv_packet(node2, &bad_pkt);
        printf("  Corrupted CRC packet received by node 0x%02X: rc=%d %s\n",
               node2, rc, rc == -3 ? "(CRC error detected ✓)" : "(unexpected result)");
    }

#ifdef HARDWARE
    if (argc > 1) {
        int fd = rs485_open_port(argv[1]);
        if (fd < 0) return 1;
        uint8_t buf[RS485_PACKET_MAX];
        int len = rs485_encode_packet(&tx_pkt, buf, sizeof(buf));
        rs485_hw_send(fd, buf, len);
        printf("\nHardware: sent %d bytes on %s\n", len, argv[1]);
        close(fd);
    }
#endif

    return 0;
}
