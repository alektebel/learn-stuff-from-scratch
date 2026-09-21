/*
 * CAN Bus Implementation - Solution
 *
 * Complete CAN 2.0A encoder/decoder with CRC-15, bit stuffing, and
 * arbitration simulation.
 *
 * Compilation: gcc -Wall -o can can.c
 * Run: ./can
 *
 * Hardware variant: gcc -DHARDWARE -Wall -o can can.c
 */

#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>

#ifdef HARDWARE
#include <unistd.h>
#include <net/if.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <linux/can.h>
#include <linux/can/raw.h>
#include <errno.h>
#endif

#define CAN_MAX_DLC      8
#define CAN_STD_ID_MAX   0x7FFU
#define CAN_MAX_BITS     200

typedef struct {
    uint32_t id;
    uint8_t  extended;
    uint8_t  rtr;
    uint8_t  dlc;
    uint8_t  data[CAN_MAX_DLC];
} can_frame_t;

typedef struct {
    uint8_t bits[CAN_MAX_BITS];
    int     length;
} can_bitstream_t;

/* =========================================================================
 * can_calc_crc15
 * CAN polynomial: 0x4599
 * ========================================================================= */
uint16_t can_calc_crc15(const uint8_t *bits, int length)
{
    uint16_t crc = 0;
    for (int i = 0; i < length; i++) {
        uint16_t crcnxt = (uint16_t)(bits[i] ^ ((crc >> 14) & 1));
        crc = (uint16_t)((crc << 1) & 0x7FFF);
        if (crcnxt)
            crc ^= 0x4599;
    }
    return crc;
}

/* =========================================================================
 * Helper: append a single bit
 * ========================================================================= */
static inline void push_bit(can_bitstream_t *s, uint8_t bit)
{
    if (s->length < CAN_MAX_BITS)
        s->bits[s->length++] = bit;
}

/* =========================================================================
 * can_encode_frame – CAN 2.0A standard frame (11-bit ID)
 * ========================================================================= */
void can_encode_frame(const can_frame_t *frame, can_bitstream_t *stream)
{
    stream->length = 0;

    /* SOF */
    push_bit(stream, 0);

    /* ID [10:0] MSB first */
    for (int i = 10; i >= 0; i--)
        push_bit(stream, (frame->id >> i) & 1);

    /* RTR */
    push_bit(stream, frame->rtr & 1);

    /* IDE = 0 (standard), r0 = 0 */
    push_bit(stream, 0);
    push_bit(stream, 0);

    /* DLC [3:0] MSB first */
    for (int i = 3; i >= 0; i--)
        push_bit(stream, (frame->dlc >> i) & 1);

    /* DATA */
    for (int b = 0; b < frame->dlc; b++)
        for (int i = 7; i >= 0; i--)
            push_bit(stream, (frame->data[b] >> i) & 1);

    /* CRC (over SOF through last data bit) */
    uint16_t crc = can_calc_crc15(stream->bits, stream->length);
    for (int i = 14; i >= 0; i--)
        push_bit(stream, (crc >> i) & 1);

    /* CRC delimiter, ACK slot, ACK delimiter */
    push_bit(stream, 1);
    push_bit(stream, 1);  /* sender transmits recessive; receiver overwrites with 0 */
    push_bit(stream, 1);

    /* EOF: 7 recessive bits */
    for (int i = 0; i < 7; i++)
        push_bit(stream, 1);

    /* IFS: 3 recessive bits */
    for (int i = 0; i < 3; i++)
        push_bit(stream, 1);
}

/* =========================================================================
 * can_decode_frame
 * ========================================================================= */
int can_decode_frame(const can_bitstream_t *stream, can_frame_t *frame)
{
    int pos = 0;

    /* SOF */
    if (stream->bits[pos++] != 0) return -1;

    /* ID [10:0] */
    frame->id = 0;
    for (int i = 10; i >= 0; i--)
        frame->id |= (uint32_t)(stream->bits[pos++] << i);

    /* RTR */
    frame->rtr = stream->bits[pos++];

    /* IDE, r0 */
    frame->extended = 0;
    pos += 2;  /* skip IDE and r0 */

    /* DLC */
    frame->dlc = 0;
    for (int i = 3; i >= 0; i--)
        frame->dlc |= (uint8_t)(stream->bits[pos++] << i);

    if (frame->dlc > CAN_MAX_DLC) return -1;

    /* DATA */
    for (int b = 0; b < frame->dlc; b++) {
        frame->data[b] = 0;
        for (int i = 7; i >= 0; i--)
            frame->data[b] |= (uint8_t)(stream->bits[pos++] << i);
    }

    /* CRC: recompute and compare */
    uint16_t expected = can_calc_crc15(stream->bits, pos);
    uint16_t received = 0;
    for (int i = 14; i >= 0; i--)
        received |= (uint16_t)(stream->bits[pos++] << i);

    if (expected != received) return -2;

    return 0;
}

/* =========================================================================
 * can_arbitrate – returns index of winning frame (lowest ID)
 * ========================================================================= */
int can_arbitrate(const can_frame_t **frames, int count)
{
    if (count <= 0) return -1;

    int winner = 0;
    for (int i = 1; i < count; i++) {
        uint32_t w_id = frames[winner]->id;
        uint32_t c_id = frames[i]->id;
        if (c_id < w_id) {
            winner = i;
        } else if (c_id == w_id) {
            /* Data frame (RTR=0) beats Remote frame (RTR=1) */
            if (frames[i]->rtr == 0 && frames[winner]->rtr == 1)
                winner = i;
        }
    }
    return winner;
}

/* =========================================================================
 * can_apply_bit_stuffing
 * ========================================================================= */
int can_apply_bit_stuffing(const uint8_t *in, int in_len, int stuff_end,
                            uint8_t *out, int out_max)
{
    int out_pos   = 0;
    int run       = 1;
    uint8_t last  = in[0];

    for (int i = 0; i < in_len; i++) {
        if (out_pos >= out_max) return -1;
        out[out_pos++] = in[i];

        if (i < stuff_end) {
            if (i > 0 && in[i] == last) {
                run++;
                if (run == 5) {
                    /* Insert complementary stuff bit */
                    if (out_pos >= out_max) return -1;
                    out[out_pos++] = in[i] ^ 1;
                    run  = 1;
                    last = in[i] ^ 1;
                }
            } else {
                run  = 1;
                last = in[i];
            }
        }
    }
    return out_pos;
}

/* =========================================================================
 * Hardware: SocketCAN
 * ========================================================================= */
#ifdef HARDWARE
int can_open_socket(const char *ifname)
{
    int s = socket(PF_CAN, SOCK_RAW, CAN_RAW);
    if (s < 0) { perror("socket"); return -1; }

    struct ifreq ifr;
    memset(&ifr, 0, sizeof(ifr));
    strncpy(ifr.ifr_name, ifname, IFNAMSIZ - 1);
    if (ioctl(s, SIOCGIFINDEX, &ifr) < 0) {
        perror("SIOCGIFINDEX"); close(s); return -1;
    }

    struct sockaddr_can addr = {
        .can_family  = AF_CAN,
        .can_ifindex = ifr.ifr_ifindex,
    };
    if (bind(s, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("bind"); close(s); return -1;
    }
    return s;
}

int can_send(int fd, const can_frame_t *frame)
{
    struct can_frame cf;
    memset(&cf, 0, sizeof(cf));
    cf.can_id  = frame->extended ? (frame->id | CAN_EFF_FLAG) : frame->id;
    if (frame->rtr) cf.can_id |= CAN_RTR_FLAG;
    cf.can_dlc = frame->dlc;
    memcpy(cf.data, frame->data, frame->dlc);
    return (write(fd, &cf, sizeof(cf)) == sizeof(cf)) ? 0 : -1;
}

int can_recv(int fd, can_frame_t *frame)
{
    struct can_frame cf;
    if (read(fd, &cf, sizeof(cf)) != sizeof(cf)) return -1;
    frame->extended = (cf.can_id & CAN_EFF_FLAG) ? 1 : 0;
    frame->rtr      = (cf.can_id & CAN_RTR_FLAG) ? 1 : 0;
    frame->id       = cf.can_id & (frame->extended ? CAN_EFF_MASK : CAN_SFF_MASK);
    frame->dlc      = cf.can_dlc;
    memcpy(frame->data, cf.data, cf.can_dlc);
    return 0;
}
#endif  /* HARDWARE */

/* =========================================================================
 * Helper: print a CAN frame
 * ========================================================================= */
static void print_can_frame(const can_frame_t *f)
{
    printf("  CAN Frame: ID=0x%03X (%s) DLC=%d RTR=%d  Data:",
           f->id, f->extended ? "EXT" : "STD", f->dlc, f->rtr);
    for (int i = 0; i < f->dlc; i++)
        printf(" %02X", f->data[i]);
    printf("\n");
}

static void print_bitstream(const can_bitstream_t *s, int max_bits)
{
    printf("  Bits [%d]: ", s->length);
    for (int i = 0; i < s->length && i < max_bits; i++)
        printf("%d", s->bits[i]);
    if (s->length > max_bits) printf("...");
    printf("\n");
}

/* =========================================================================
 * main
 * ========================================================================= */
int main(int argc, char *argv[])
{
    (void)argc; (void)argv;

    printf("=== CAN Bus Simulator ===\n\n");

    /* Test frames with different IDs */
    can_frame_t frames[] = {
        { .id = 0x123, .extended = 0, .rtr = 0, .dlc = 4,
          .data = { 0xDE, 0xAD, 0xBE, 0xEF } },
        { .id = 0x100, .extended = 0, .rtr = 0, .dlc = 2,
          .data = { 0xCA, 0xFE } },
        { .id = 0x001, .extended = 0, .rtr = 0, .dlc = 1,
          .data = { 0xFF } },
        { .id = 0x7FF, .extended = 0, .rtr = 1, .dlc = 0,
          .data = { 0 } },    /* RTR frame */
    };
    int nframes = (int)(sizeof(frames) / sizeof(frames[0]));

    /* Encode, decode, verify */
    printf("--- Encode / Decode Round-Trip ---\n");
    int all_ok = 1;
    for (int i = 0; i < nframes; i++) {
        can_bitstream_t stream;
        can_encode_frame(&frames[i], &stream);

        print_can_frame(&frames[i]);
        print_bitstream(&stream, 40);

        can_frame_t decoded;
        memset(&decoded, 0, sizeof(decoded));
        int rc = can_decode_frame(&stream, &decoded);
        if (rc != 0) {
            printf("  DECODE ERROR: %d\n", rc);
            all_ok = 0;
        } else if (decoded.id  != frames[i].id  ||
                   decoded.dlc != frames[i].dlc ||
                   memcmp(decoded.data, frames[i].data, frames[i].dlc) != 0) {
            printf("  ROUND-TRIP MISMATCH\n");
            all_ok = 0;
        } else {
            printf("  Round-trip ✓\n");
        }
        printf("\n");
    }
    printf("Encode/Decode: %s\n\n", all_ok ? "ALL PASSED" : "ERRORS FOUND");

    /* CRC demonstration */
    printf("--- CRC-15 Verification ---\n");
    {
        can_frame_t f = { .id = 0x555, .extended = 0, .rtr = 0, .dlc = 3,
                          .data = { 0x01, 0x02, 0x03 } };
        can_bitstream_t s;
        can_encode_frame(&f, &s);

        /* CRC covers bits 0..(SOF+ID+control+data-1) = 1+11+3+4+24 = 43 bits */
        int crc_end = 1 + 11 + 1 + 1 + 1 + 4 + f.dlc * 8;  /* SOF+ID+RTR+IDE+r0+DLC+DATA */
        uint16_t crc = can_calc_crc15(s.bits, crc_end);
        printf("  Frame ID=0x555 data={01 02 03}: CRC-15 = 0x%04X\n", crc);
    }
    printf("\n");

    /* Arbitration */
    printf("--- Bus Arbitration Simulation ---\n");
    printf("Contending frames:\n");
    for (int i = 0; i < nframes; i++) {
        printf("  [%d] ID=0x%03X RTR=%d\n", i, frames[i].id, frames[i].rtr);
    }
    const can_frame_t *ptrs[4];
    for (int i = 0; i < nframes; i++) ptrs[i] = &frames[i];
    int winner = can_arbitrate(ptrs, nframes);
    printf("Winner: frame [%d] with ID=0x%03X "
           "(lowest ID wins in CAN arbitration)\n\n", winner, frames[winner].id);

    /* Bit stuffing demo */
    printf("--- Bit Stuffing ---\n");
    {
        /* Construct a pathological bit stream: five 0s followed by five 1s */
        uint8_t raw[]     = { 0,0,0,0,0, 1,1,1,1,1, 0,1,0,1 };
        int     raw_len   = (int)(sizeof(raw));
        uint8_t stuffed[30];
        int stuffed_len = can_apply_bit_stuffing(raw, raw_len, raw_len, stuffed, 30);
        printf("  Before stuffing (%d bits): ", raw_len);
        for (int i = 0; i < raw_len; i++) printf("%d", raw[i]);
        printf("\n");
        printf("  After  stuffing (%d bits): ", stuffed_len);
        for (int i = 0; i < stuffed_len; i++) printf("%d", stuffed[i]);
        printf("\n");
    }
    printf("\n");

#ifdef HARDWARE
    if (argc > 1) {
        int fd = can_open_socket(argv[1]);
        if (fd < 0) return 1;
        can_frame_t test_frame = { .id=0x123, .extended=0, .rtr=0,
                                    .dlc=4, .data={0xDE,0xAD,0xBE,0xEF} };
        printf("Hardware: sending frame on %s...\n", argv[1]);
        if (can_send(fd, &test_frame) < 0) perror("can_send");
        else printf("Sent ✓\n");
        close(fd);
    }
#endif

    return 0;
}
