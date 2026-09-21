/*
 * SHA-256 Implementation - Template
 * 
 * This template guides you through implementing the SHA-256 cryptographic hash function.
 * SHA-256 is part of the SHA-2 family and produces a 256-bit (32-byte) hash.
 * 
 * Reference: FIPS 180-4 specification
 */

#include <stdio.h>
#include <stdint.h>
#include <string.h>

#define SHA256_BLOCK_SIZE 64
#define SHA256_DIGEST_SIZE 32

/*
 * TODO 1: Define the SHA-256 context structure
 * 
 * Guidelines:
 * - Store current hash state (8 x 32-bit values)
 * - Store message block buffer (64 bytes)
 * - Store total message length in bits (64-bit value)
 * - Track current position in block buffer
 */
typedef struct {
    // TODO: Define SHA-256 context structure
    uint32_t state[8];
    uint8_t buffer[SHA256_BLOCK_SIZE];
    uint64_t bitlen;
    uint32_t buflen;
} SHA256_CTX;

/*
 * SHA-256 Constants
 * These are the first 32 bits of the fractional parts of the cube roots
 * of the first 64 primes.
 */
static const uint32_t K[64] = {
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3, 0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13, 0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208, 0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
};

/*
 * TODO 2: Implement bit rotation macros
 * 
 * Guidelines:
 * - ROTR(x, n): Rotate x right by n bits
 * - Use bitwise operations: (x >> n) | (x << (32 - n))
 */
#define ROTR(x, n) (((x) >> (n)) | ((x) << (32 - (n))))

/*
 * TODO 3: Implement SHA-256 logical functions
 * 
 * Guidelines:
 * - CH(x,y,z) = (x & y) ^ (~x & z)
 * - MAJ(x,y,z) = (x & y) ^ (x & z) ^ (y & z)
 * - EP0(x) = ROTR(x,2) ^ ROTR(x,13) ^ ROTR(x,22)
 * - EP1(x) = ROTR(x,6) ^ ROTR(x,11) ^ ROTR(x,25)
 * - SIG0(x) = ROTR(x,7) ^ ROTR(x,18) ^ (x >> 3)
 * - SIG1(x) = ROTR(x,17) ^ ROTR(x,19) ^ (x >> 10)
 */
#define CH(x,y,z)  (((x) & (y)) ^ (~(x) & (z)))
#define MAJ(x,y,z) (((x) & (y)) ^ ((x) & (z)) ^ ((y) & (z)))
#define EP0(x)     (ROTR(x,2) ^ ROTR(x,13) ^ ROTR(x,22))
#define EP1(x)     (ROTR(x,6) ^ ROTR(x,11) ^ ROTR(x,25))
#define SIG0(x)    (ROTR(x,7) ^ ROTR(x,18) ^ ((x) >> 3))
#define SIG1(x)    (ROTR(x,17) ^ ROTR(x,19) ^ ((x) >> 10))

/*
 * TODO 4: Implement sha256_transform function
 * 
 * Guidelines:
 * - Process a single 512-bit (64-byte) block
 * - Create message schedule (64 words)
 * - Initialize working variables from state
 * - Perform 64 rounds of compression
 * - Update state with compressed values
 * 
 * This is the core of SHA-256 and the most complex part.
 */
void sha256_transform(SHA256_CTX *ctx, const uint8_t data[]) {
    // TODO: Implement block transformation
}

/*
 * TODO 5: Implement sha256_init function
 * 
 * Guidelines:
 * - Initialize state with SHA-256 initial hash values
 * - These are the first 32 bits of the fractional parts
 *   of the square roots of the first 8 primes
 * - Reset counters and buffers
 */
void sha256_init(SHA256_CTX *ctx) {
    // TODO: Initialize SHA-256 context
    ctx->state[0] = 0x6a09e667;
    ctx->state[1] = 0xbb67ae85;
    ctx->state[2] = 0x3c6ef372;
    ctx->state[3] = 0xa54ff53a;
    ctx->state[4] = 0x510e527f;
    ctx->state[5] = 0x9b05688c;
    ctx->state[6] = 0x1f83d9ab;
    ctx->state[7] = 0x5be0cd19;
    ctx->buflen = 0;
    ctx->bitlen = 0;
}

/*
 * TODO 6: Implement sha256_update function
 * 
 * Guidelines:
 * - Add data to the hash computation
 * - Buffer incomplete blocks
 * - Process complete blocks through transform
 * - Update bit length counter
 */
void sha256_update(SHA256_CTX *ctx, const uint8_t data[], size_t len) {
    // TODO: Update hash with new data
}

/*
 * TODO 7: Implement sha256_final function
 * 
 * Guidelines:
 * - Pad the message (append 1 bit, then zeros, then length)
 * - Process final block(s)
 * - Extract hash value from state
 * - Convert to big-endian byte order
 */
void sha256_final(SHA256_CTX *ctx, uint8_t hash[]) {
    // TODO: Finalize hash and output result
}

/*
 * Convenience function to hash data in one call
 */
void sha256(const uint8_t data[], size_t len, uint8_t hash[SHA256_DIGEST_SIZE]) {
    SHA256_CTX ctx;
    sha256_init(&ctx);
    sha256_update(&ctx, data, len);
    sha256_final(&ctx, hash);
}

/*
 * Helper function to print hash in hexadecimal
 */
void print_hash(const uint8_t hash[SHA256_DIGEST_SIZE]) {
    for (int i = 0; i < SHA256_DIGEST_SIZE; i++) {
        printf("%02x", hash[i]);
    }
    printf("\n");
}

int main() {
    // Test vectors
    const char* test1 = "abc";
    const char* test2 = "abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq";
    
    uint8_t hash[SHA256_DIGEST_SIZE];
    
    printf("SHA-256 Test Vectors:\n\n");
    
    printf("Input: \"%s\"\n", test1);
    printf("Expected: ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad\n");
    printf("Got:      ");
    sha256((uint8_t*)test1, strlen(test1), hash);
    print_hash(hash);
    printf("\n");
    
    printf("Input: \"%s\"\n", test2);
    printf("Expected: 248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1\n");
    printf("Got:      ");
    sha256((uint8_t*)test2, strlen(test2), hash);
    print_hash(hash);
    
    return 0;
}

/*
 * IMPLEMENTATION GUIDE:
 * 
 * Step 1: Study the SHA-256 specification (FIPS 180-4)
 *         Understand the algorithm structure and data flow
 * 
 * Step 2: Implement sha256_init()
 *         Set up initial hash values
 * 
 * Step 3: Implement sha256_transform()
 *         This is the core - follow the spec carefully
 *         Test with known intermediate values
 * 
 * Step 4: Implement sha256_update()
 *         Handle buffering and block processing
 * 
 * Step 5: Implement sha256_final()
 *         Handle padding according to spec
 * 
 * Step 6: Test with official test vectors
 *         Verify your implementation matches expected outputs
 * 
 * Resources:
 * - FIPS 180-4: https://csrc.nist.gov/publications/fips/fips180-4/fips-180-4.pdf
 * - Test vectors: https://www.di-mgt.com.au/sha_testvectors.html
 */
