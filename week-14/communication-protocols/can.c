/*
 * CAN (Controller Area Network) Bus Implementation - Template
 *
 * CAN is a multi-master, differential serial bus designed for robust
 * communication in noisy environments (automotive, industrial).
 *
 * Key properties:
 *   - Differential signaling (CAN_H / CAN_L twisted pair + 120Ω terminators)
 *   - Multi-master with non-destructive bitwise arbitration
 *     (dominant bit = 0 always wins; lower ID wins)
 *   - Frames carry 0–8 data bytes (CAN 2.0A/B); CAN FD extends this to 64 bytes
 *   - 15-bit CRC covers ID + data; hardware detects bit errors, stuffing errors, etc.
 *   - Error confinement: TEC/REC counters; nodes go Bus-Off after too many errors
 *
 * CAN 2.0A Standard Frame (11-bit ID):
 *   SOF(1) | ID[10:0](11) | RTR(1) | IDE(1)=0 | r0(1) | DLC(4) |
 *   DATA(0–64 bits) | CRC(15) | CRC_DEL(1) | ACK(1) | ACK_DEL(1) | EOF(7) | IFS(3)
 *
 * This file has two modes:
 *   SOFTWARE mode  – simulate CAN bus entirely in software (default)
 *   HARDWARE mode  – use Linux SocketCAN (requires a CAN interface, e.g. can0)
 *                    Compile: gcc -DHARDWARE -o can can.c
 *                    Setup:   sudo ip link set can0 type can bitrate 500000
 *                             sudo ip link set can0 up
 *                    Run:     ./can can0
 *
 * Compilation (software mode): gcc -Wall -o can can.c
 * Run: ./can
 *
 * Learning path:
 *   TODO 1  – implement can_calc_crc15()
 *   TODO 2  – implement can_encode_frame()
 *   TODO 3  – implement can_decode_frame()
 *   TODO 4  – implement can_arbitrate() (multi-node simulation)
 *   TODO 5  – implement error detection (bit stuffing check)
 *   TODO 6  – (HARDWARE) open SocketCAN socket and send/receive frames
 *   TODO 7  – wire everything together in main()
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
#include <string.h>
#endif

/* =========================================================================
 * CAN frame structures
 * ========================================================================= */

#define CAN_MAX_DLC   8
#define CAN_STD_ID_MAX  0x7FFU   /* 11-bit */
#define CAN_EXT_ID_MAX  0x1FFFFFFFU  /* 29-bit */

typedef struct {
    uint32_t id;                    /* 11-bit (standard) or 29-bit (extended) */
    uint8_t  extended;              /* 0 = standard frame (IDE=0), 1 = extended */
    uint8_t  rtr;                   /* 1 = Remote Transmission Request          */
    uint8_t  dlc;                   /* Data Length Code: 0–8                    */
    uint8_t  data[CAN_MAX_DLC];    /* Payload                                  */
} can_frame_t;

/*
 * "Bit stream" representation used for CAN encoding/decoding.
 * Each element is 0 (dominant) or 1 (recessive).
 * Maximum frame size (Standard, 8 data bytes, no stuffing): ~130 bits.
 */
#define CAN_MAX_BITS  200

typedef struct {
    uint8_t bits[CAN_MAX_BITS];
    int     length;
} can_bitstream_t;

/* =========================================================================
 * TODO 1: Implement can_calc_crc15
 *
 * Compute the 15-bit CAN CRC over the provided bit array.
 *
 * CAN CRC-15 polynomial: x^15 + x^14 + x^10 + x^8 + x^7 + x^4 + x^3 + 1
 *   = 0x4599 (with implicit leading 1 → generator = 0xC599)
 *
 * Algorithm (bit-by-bit):
 *   crc = 0
 *   for each bit in the bit stream (from SOF through all data bits):
 *       crcnxt = bit XOR ((crc >> 14) & 1)   // top bit of crc XOR new bit
 *       crc = (crc << 1) & 0x7FFF             // shift left, keep 15 bits
 *       if crcnxt:
 *           crc ^= 0x4599
 *   return crc
 *
 * Guidelines:
 *   - `bits` points to the start of the bit stream (from SOF)
 *   - `length` is the number of bits to include (does NOT include CRC field itself)
 *   - Return the 15-bit CRC value
 * ========================================================================= */
uint16_t can_calc_crc15(const uint8_t *bits, int length)
{
    /* TODO: compute and return the 15-bit CRC */
    (void)bits; (void)length;
    return 0;
}

/* =========================================================================
 * TODO 2: Implement can_encode_frame
 *
 * Encode a can_frame_t into a CAN 2.0A standard bit stream.
 *
 * Standard frame bit layout (no bit stuffing yet):
 *   [1]  SOF              = 0 (dominant)
 *   [11] ID[10:0]          MSB first
 *   [1]  RTR
 *   [1]  IDE              = 0 (standard frame)
 *   [1]  r0               = 0 (reserved)
 *   [4]  DLC              MSB first
 *   [0–64] DATA           8 bits per byte, MSB first
 *   [15] CRC              computed over SOF..DATA
 *   [1]  CRC delimiter    = 1 (recessive)
 *   [1]  ACK slot         = 1 (recessive; sender sends 1, receiver pulls 0)
 *   [1]  ACK delimiter    = 1
 *   [7]  EOF              = 1111111
 *   [3]  IFS (interframe space) = 111
 *
 * Guidelines:
 *   - Fill stream->bits[] in order
 *   - After building SOF through DATA, call can_calc_crc15() on those bits
 *   - Append the CRC (MSB first), then the delimiters and EOF
 *   - Set stream->length
 *   - Do NOT apply bit stuffing for the basic implementation
 *     (implement it as an extension in the advanced section)
 * ========================================================================= */
void can_encode_frame(const can_frame_t *frame, can_bitstream_t *stream)
{
    /* TODO: encode frame into bit stream */
    (void)frame; (void)stream;
    stream->length = 0;
}

/* =========================================================================
 * TODO 3: Implement can_decode_frame
 *
 * Decode a CAN bit stream back into a can_frame_t.
 *
 * Guidelines:
 *   - Parse bits in the same order as can_encode_frame()
 *   - Check SOF == 0 (dominant); return -1 if not
 *   - Extract ID, RTR, IDE, r0, DLC
 *   - Extract DLC data bytes
 *   - Extract the 15-bit CRC from the stream
 *   - Recompute CRC over SOF..DATA and compare; return -2 on mismatch
 *   - Fill the can_frame_t structure
 *   - Return 0 on success
 *
 * Hint: use a `pos` index variable to track current bit position
 * ========================================================================= */
int can_decode_frame(const can_bitstream_t *stream, can_frame_t *frame)
{
    /* TODO: decode bit stream into frame, return 0 on success */
    (void)stream; (void)frame;
    return -1;
}

/* =========================================================================
 * TODO 4: Implement can_arbitrate
 *
 * Simulate non-destructive bitwise arbitration between multiple CAN nodes.
 *
 * In real CAN:
 *   - All nodes start transmitting simultaneously
 *   - The bus is a wired-AND: if any node transmits 0 (dominant), the bus is 0
 *   - Each node monitors the bus while sending:
 *       if it sent 1 but sees 0, it LOST arbitration and stops transmitting
 *   - The frame with the lowest ID (most dominant bits early on) wins
 *
 * Guidelines:
 *   - Accept an array of can_frame_t pointers and a count
 *   - Simulate the arbitration field bit by bit (ID bits, MSB first)
 *   - Return the index of the winning frame (smallest ID wins)
 *   - For RTR vs data frame tie: data frame (RTR=0) wins
 *
 * Hint: you don't need to build full bit streams; just compare ID values
 * ========================================================================= */
int can_arbitrate(const can_frame_t **frames, int count)
{
    /* TODO: return index of winning frame */
    (void)frames; (void)count;
    return 0;
}

/* =========================================================================
 * TODO 5: Implement can_apply_bit_stuffing (extension)
 *
 * CAN uses "bit stuffing": after 5 consecutive bits of the same polarity,
 * a complementary "stuff bit" is inserted. This ensures enough transitions
 * for clock synchronisation.
 *
 * Applies to: SOF through CRC (inclusive); NOT to CRC delimiter, ACK, EOF.
 *
 * Guidelines:
 *   - Scan the input bit array up to `stuff_end` bits
 *   - Keep a counter of consecutive identical bits
 *   - Whenever count reaches 5, insert the opposite bit into the output
 *     and reset the counter
 *   - Copy non-stuffed bits as-is
 *   - Return the new length of the stuffed bit stream
 * ========================================================================= */
int can_apply_bit_stuffing(const uint8_t *in, int in_len, int stuff_end,
                            uint8_t *out, int out_max)
{
    /* TODO: apply bit stuffing, return new length */
    (void)in; (void)in_len; (void)stuff_end; (void)out; (void)out_max;
    return 0;
}

/* =========================================================================
 * TODO 6 (HARDWARE): Implement SocketCAN functions
 *
 * can_open_socket(ifname):
 *   - socket(PF_CAN, SOCK_RAW, CAN_RAW)
 *   - strcpy(ifr.ifr_name, ifname); ioctl(s, SIOCGIFINDEX, &ifr)
 *   - bind(s, (struct sockaddr *)&addr, sizeof(addr))
 *   - Return socket fd, or -1 on error
 *
 * can_send(fd, frame):
 *   - Fill struct can_frame { .can_id, .can_dlc, .data[] }
 *   - write(fd, &cf, sizeof(cf))
 *   - Return 0 on success, -1 on error
 *
 * can_recv(fd, frame):
 *   - read(fd, &cf, sizeof(cf))
 *   - Populate can_frame_t from struct can_frame
 *   - Return 0 on success, -1 on error
 * ========================================================================= */
#ifdef HARDWARE
int can_open_socket(const char *ifname)
{
    /* TODO: open SocketCAN raw socket, bind to ifname */
    (void)ifname;
    return -1;
}

int can_send(int fd, const can_frame_t *frame)
{
    /* TODO: send a CAN frame via SocketCAN */
    (void)fd; (void)frame;
    return -1;
}

int can_recv(int fd, can_frame_t *frame)
{
    /* TODO: receive a CAN frame via SocketCAN */
    (void)fd; (void)frame;
    return -1;
}
#endif

/* =========================================================================
 * Helper: print a CAN frame
 * ========================================================================= */
static void print_can_frame(const can_frame_t *f)
{
    printf("CAN Frame: ID=0x%03X (%s) DLC=%d RTR=%d  Data:",
           f->id,
           f->extended ? "EXT" : "STD",
           f->dlc, f->rtr);
    for (int i = 0; i < f->dlc; i++)
        printf(" %02X", f->data[i]);
    printf("\n");
}

static void print_bitstream(const can_bitstream_t *s)
{
    printf("Bit stream (%d bits): ", s->length);
    for (int i = 0; i < s->length && i < 64; i++)
        printf("%d", s->bits[i]);
    if (s->length > 64) printf("...");
    printf("\n");
}

/* =========================================================================
 * TODO 7: Wire everything together in main()
 *
 * Software mode:
 *   1. Create a few can_frame_t with different IDs and payloads
 *   2. Encode each frame with can_encode_frame() and print the bit stream
 *   3. Decode each stream with can_decode_frame() and verify round-trip
 *   4. Simulate arbitration with can_arbitrate() and print the winner
 *   5. (Extension) apply can_apply_bit_stuffing() and show stuffed stream
 *
 * Hardware mode (compiled with -DHARDWARE):
 *   1. Parse argv[1] as CAN interface (e.g. "can0")
 *   2. Open socket with can_open_socket()
 *   3. Send a test frame and then receive one, printing both
 * ========================================================================= */
int main(int argc, char *argv[])
{
    (void)argc; (void)argv;

    printf("=== CAN Bus Simulator ===\n\n");

    /* Example frames */
    can_frame_t f1 = { .id = 0x123, .extended = 0, .rtr = 0, .dlc = 4,
                        .data = { 0xDE, 0xAD, 0xBE, 0xEF } };
    can_frame_t f2 = { .id = 0x100, .extended = 0, .rtr = 0, .dlc = 2,
                        .data = { 0xCA, 0xFE } };
    can_frame_t f3 = { .id = 0x7FF, .extended = 0, .rtr = 0, .dlc = 1,
                        .data = { 0xFF } };

    /* TODO: encode, decode, and arbitrate the example frames */
    print_can_frame(&f1);
    print_can_frame(&f2);
    print_can_frame(&f3);

    return 0;
}
