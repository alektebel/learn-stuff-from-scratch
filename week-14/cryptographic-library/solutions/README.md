# Solutions

<<<<<<< HEAD
This directory contains complete implementations of cryptographic algorithms.

## Files

- **sha256.c** - Complete SHA-256 hash function implementation

=======
This directory contains complete implementations and comprehensive implementation guides for cryptographic algorithms.

## Files

### Complete Implementations

- **sha256.c** - Complete SHA-256 hash function implementation

### Implementation Guides

These guides provide verbose, detailed implementation instructions without actual code. They are designed to teach you how to implement cryptographic algorithms from scratch while understanding the security considerations and best practices.

- **[ecc_implementation_guide.md](ecc_implementation_guide.md)** - Elliptic Curve Cryptography (ECC) implementation guide
  - Point arithmetic (addition, doubling, scalar multiplication)
  - Modular arithmetic in finite fields
  - Curve operations and optimizations
  - Point encoding/decoding
  - Security considerations and side-channel protection

- **[ecdsa_implementation_guide.md](ecdsa_implementation_guide.md)** - ECDSA Digital Signature Algorithm guide
  - Key generation
  - Signature generation and verification
  - Deterministic nonce generation (RFC 6979)
  - DER encoding
  - Security vulnerabilities and mitigations

- **[aes_implementation_guide.md](aes_implementation_guide.md)** - AES (Advanced Encryption Standard) guide
  - Core operations (SubBytes, ShiftRows, MixColumns, AddRoundKey)
  - Key expansion
  - Encryption and decryption
  - Modes of operation (CBC, CTR, GCM)
  - Performance optimization techniques

- **[ecdh_implementation_guide.md](ecdh_implementation_guide.md)** - ECDH Key Agreement Protocol guide
  - Key generation and exchange
  - Shared secret computation
  - Key derivation functions (KDF)
  - Forward secrecy and authentication
  - Curve25519 and modern approaches

- **[secure_rng_guide.md](secure_rng_guide.md)** - Secure Random Number Generation guide
  - Entropy sources and collection
  - CSPRNG algorithms (ChaCha20, AES-CTR-DRBG, HMAC-DRBG)
  - Platform-specific implementations
  - Security best practices
  - Common pitfalls and historical failures

>>>>>>> main
## Building and Running

```bash
gcc -o sha256 sha256.c
./sha256
```

## SHA-256 Implementation

The solution includes:
- Complete SHA-256 hashing according to FIPS 180-4
- Proper message padding
- Block transformation with compression function
- All logical functions (CH, MAJ, EP0, EP1, SIG0, SIG1)
- Test vectors for verification

### Features

1. **Context Management**: Initialize, update, and finalize hash computation
2. **Streaming API**: Process data in chunks of any size
3. **Test Vectors**: Validates against official NIST test vectors

### Usage

```c
uint8_t hash[SHA256_DIGEST_SIZE];
sha256((uint8_t*)"hello", 5, hash);
// hash now contains the SHA-256 digest
```

Or with streaming:
```c
SHA256_CTX ctx;
sha256_init(&ctx);
sha256_update(&ctx, data1, len1);
sha256_update(&ctx, data2, len2);
sha256_final(&ctx, hash);
```

## Learning Points

- Cryptographic hash function design
- Bitwise operations and rotations
- Message padding and length encoding
- Big-endian/little-endian handling
- Block cipher modes
- Merkle–Damgård construction

## Security Note

⚠️ **This implementation is for educational purposes only.**

For production use:
- Use established libraries (OpenSSL, libsodium)
- This code has not been audited for security
- Timing attacks and side-channel vulnerabilities not addressed
- No hardware acceleration

## Test Vectors

The implementation passes official NIST test vectors:

```
Input: "abc"
SHA-256: ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad

Input: "abcdbcdecdefdefgefghfghighijhijkijkljklmklmnlmnomnopnopq"
SHA-256: 248d6a61d20638b8e5c026930c3e6039a33ce45964ff2167f6ecedd419db06c1
```

<<<<<<< HEAD
## Further Reading

- FIPS 180-4 Specification
- "Applied Cryptography" by Bruce Schneier
=======
## How to Use the Implementation Guides

Each implementation guide is structured to provide:

1. **Overview**: High-level understanding of the algorithm
2. **Mathematical Foundation**: Core cryptographic concepts
3. **Algorithm Details**: Step-by-step implementation instructions
4. **Data Structures**: How to organize code and data
5. **Security Considerations**: Common vulnerabilities and mitigations
6. **Testing Strategy**: How to validate your implementation
7. **Optimization Tips**: Performance improvements
8. **References**: Standards, papers, and additional resources

### Learning Path

1. **Start with Basics**: Begin with SHA-256 implementation to understand:
   - Bitwise operations
   - Fixed-size transformations
   - Hash function principles

2. **Move to Field Arithmetic**: Study the ECC guide to understand:
   - Modular arithmetic
   - Point operations on curves
   - Constant-time implementations

3. **Implement Digital Signatures**: Use ECDSA guide to learn:
   - Signature schemes
   - Nonce management
   - Security-critical details

4. **Add Encryption**: Follow AES guide for:
   - Symmetric encryption
   - Block cipher modes
   - Authenticated encryption

5. **Key Exchange**: Study ECDH guide for:
   - Key agreement protocols
   - Forward secrecy
   - Key derivation

6. **Random Number Generation**: Use RNG guide for:
   - Entropy collection
   - PRNG design
   - Platform integration

### Important Notes

⚠️ **These implementations are for educational purposes only.**

**For production systems:**
- Use established, audited libraries (OpenSSL, libsodium, mbedTLS)
- Cryptographic code requires extensive review and testing
- Side-channel attacks and timing vulnerabilities are subtle
- Security bugs can have catastrophic consequences

**Benefits of implementing yourself:**
- Deep understanding of cryptographic algorithms
- Appreciation for complexity and security challenges
- Better ability to use cryptographic libraries correctly
- Foundation for security research and analysis

## Further Reading

### Standards and Specifications
- FIPS 180-4: Secure Hash Standard (SHA-256)
- FIPS 186-4: Digital Signature Standard (ECDSA)
- FIPS 197: Advanced Encryption Standard (AES)
- NIST SP 800-56A: Key Establishment (ECDH)
- NIST SP 800-90A: Random Number Generation
- RFC 6979: Deterministic ECDSA
- RFC 5869: HKDF
- RFC 7748: Curve25519 and X448

### Books
- "Guide to Elliptic Curve Cryptography" - Hankerson, Menezes, Vanstone
- "The Design of Rijndael" - Daemen, Rijmen
- "Cryptography Engineering" - Ferguson, Schneier, Kohno
- "Handbook of Applied Cryptography" - Menezes, van Oorschot, Vanstone
- "Serious Cryptography" - Aumasson

### Online Resources
- NIST Cryptographic Algorithm Validation Program (CAVP)
- SafeCurves (https://safecurves.cr.yp.to/)
- Cryptopals Crypto Challenges (https://cryptopals.com/)
>>>>>>> main
- https://www.di-mgt.com.au/sha_testvectors.html
