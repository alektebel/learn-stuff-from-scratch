# Cryptographic Library

This directory contains a from-scratch implementation of a cryptographic library in C.

## Goal
Build cryptographic primitives to understand:
- Hash functions (SHA-256, SHA-3)
- Digital signatures (ECDSA)
<<<<<<< HEAD
- Public key cryptography
- Symmetric encryption
- Key derivation and management

## Learning Path
1. Implement SHA-256 hash function
2. Build elliptic curve arithmetic
3. Implement ECDSA (Elliptic Curve Digital Signature Algorithm)
4. Add AES encryption
5. Implement key exchange protocols (ECDH)
6. Add secure random number generation

## Security Note
⚠️ This is for educational purposes only. Do not use in production systems. Use established cryptographic libraries for real applications.
=======
- Public key cryptography (ECC)
- Symmetric encryption (AES)
- Key derivation and management (ECDH, KDF)
- Secure random number generation

## Learning Path

### 1. Hash Functions (Start Here)
**Current Status:** Template and complete solution available

**Goal:** Implement SHA-256 hash function
- Understand bitwise operations and transformations
- Learn about Merkle-Damgård construction
- Practice working with fixed-size blocks

**Files:**
- `sha256.c` - Template with TODOs
- `solutions/sha256.c` - Complete implementation
- See `solutions/README.md` for details

### 2. Elliptic Curve Cryptography (ECC)
**Current Status:** Comprehensive implementation guide available

**Goal:** Understand and implement elliptic curve arithmetic
- Point addition and doubling
- Scalar multiplication (double-and-add, Montgomery ladder)
- Modular arithmetic in finite fields
- Point validation and encoding

**Resource:**
- `solutions/ecc_implementation_guide.md` - Detailed implementation guide with algorithms, security considerations, and optimization techniques

### 3. Digital Signatures (ECDSA)
**Current Status:** Comprehensive implementation guide available

**Goal:** Implement ECDSA signature generation and verification
- Key pair generation
- Deterministic nonce generation (RFC 6979)
- Signature creation and validation
- DER encoding

**Resource:**
- `solutions/ecdsa_implementation_guide.md` - Complete guide covering key generation, signing, verification, and security vulnerabilities

### 4. Symmetric Encryption (AES)
**Current Status:** Comprehensive implementation guide available

**Goal:** Implement AES-128/192/256 encryption
- SubBytes, ShiftRows, MixColumns, AddRoundKey transformations
- Key expansion algorithm
- Modes of operation (CBC, CTR, GCM)
- Galois field arithmetic GF(2^8)

**Resource:**
- `solutions/aes_implementation_guide.md` - Detailed guide with all operations, modes, and optimization strategies

### 5. Key Exchange (ECDH)
**Current Status:** Comprehensive implementation guide available

**Goal:** Implement Elliptic Curve Diffie-Hellman key agreement
- Ephemeral and static key exchange
- Shared secret computation
- Key derivation functions (HKDF, X9.63 KDF)
- Forward secrecy implementation

**Resource:**
- `solutions/ecdh_implementation_guide.md` - Complete protocol guide with security considerations and modern approaches (Curve25519)

### 6. Secure Random Number Generation
**Current Status:** Comprehensive implementation guide available

**Goal:** Implement cryptographically secure random number generator
- Entropy source collection and management
- DRBG algorithms (ChaCha20, AES-CTR, HMAC-DRBG)
- Platform-specific implementations
- Reseeding and state management

**Resource:**
- `solutions/secure_rng_guide.md` - Comprehensive guide covering entropy sources, PRNG algorithms, and security best practices

## Implementation Guides

The `solutions/` directory contains verbose implementation guides for each cryptographic component. These guides provide:

- **Mathematical foundations** and algorithm details
- **Step-by-step implementation instructions** without actual code
- **Data structure recommendations** and architecture design
- **Security considerations** including common vulnerabilities and mitigations
- **Testing strategies** with test vectors and validation approaches
- **Performance optimization** techniques
- **References** to standards, papers, and additional resources

Each guide is designed to help you implement the algorithm from scratch while understanding the underlying cryptographic principles and security requirements.

## Building and Testing

### Build SHA-256 Example
```bash
make sha256
./sha256
```

Or manually:
```bash
gcc -o sha256 sha256.c
./sha256
```

### Testing Your Implementations

When implementing the algorithms from the guides:

1. **Start with Test Vectors:**
   - Use NIST test vectors for validation
   - Implement basic functionality first
   - Verify against known correct outputs

2. **Incremental Testing:**
   - Test individual functions before integration
   - Use unit tests for each component
   - Validate edge cases

3. **Security Testing:**
   - Check constant-time execution where required
   - Validate all inputs before processing
   - Test error handling paths

4. **Interoperability:**
   - Compare outputs with established libraries (OpenSSL, libsodium)
   - Test encoding/decoding with standard formats
   - Verify protocol compatibility

## Security Note

⚠️ **These implementations are for educational purposes only.**

### Why You Should NOT Use These in Production:

1. **Not Audited:** Code has not undergone professional security audit
2. **Side-Channel Vulnerabilities:** May leak information through timing, power, or cache
3. **No Hardware Acceleration:** Much slower than optimized libraries
4. **Implementation Bugs:** Subtle errors can have catastrophic security consequences
5. **Maintenance:** No security updates or bug fixes

### For Production Systems, Use:

- **OpenSSL** - Industry standard, widely deployed
- **libsodium** - Modern, easy-to-use, hard-to-misuse
- **mbedTLS** - Lightweight, embedded-friendly
- **BoringSSL** - Google's OpenSSL fork
- **AWS-LC** - AWS's cryptographic library

### Educational Value:

Understanding how cryptography works "under the hood" helps you:
- Use cryptographic libraries correctly
- Understand security requirements and limitations
- Make informed architectural decisions
- Appreciate the complexity of secure implementations
- Recognize common cryptographic vulnerabilities

## Learning Resources

### Standards and Specifications
- **FIPS 180-4:** Secure Hash Standard (SHA-256)
- **FIPS 186-4:** Digital Signature Standard (ECDSA)
- **FIPS 197:** Advanced Encryption Standard (AES)
- **NIST SP 800-56A:** Key Establishment Schemes Using ECDH
- **NIST SP 800-90A:** Random Number Generation Using DRBGs
- **RFC 6979:** Deterministic Usage of DSA and ECDSA
- **RFC 7748:** Elliptic Curves for Security (Curve25519)

### Books
- "Guide to Elliptic Curve Cryptography" - Hankerson, Menezes, Vanstone
- "The Design of Rijndael" - Daemen, Rijmen (AES designers)
- "Cryptography Engineering" - Ferguson, Schneier, Kohno
- "Serious Cryptography" - Jean-Philippe Aumasson
- "Handbook of Applied Cryptography" - Menezes, van Oorschot, Vanstone

### Online Resources
- NIST Cryptographic Algorithm Validation Program (CAVP)
- SafeCurves: choosing safe curves for ECC (https://safecurves.cr.yp.to/)
- Cryptopals Crypto Challenges (https://cryptopals.com/)
- SHA-256 test vectors (https://www.di-mgt.com.au/sha_testvectors.html)

## Contributing

When adding new cryptographic implementations:

1. **Implementation Guide First:**
   - Create comprehensive guide in `solutions/`
   - Include mathematical foundation
   - Document security considerations
   - Provide test vectors

2. **Template Code:**
   - Provide template with TODOs
   - Include structure definitions
   - Add guidance comments

3. **Complete Solution:**
   - Well-commented implementation
   - Test vectors included
   - Documentation of design choices

4. **Update READMEs:**
   - Add to learning path
   - Update solutions README
   - Add references and resources

## Project Status

| Component | Template | Implementation Guide | Complete Solution |
|-----------|----------|---------------------|-------------------|
| SHA-256 | ✅ | ⚠️ (in solution comments) | ✅ |
| ECC | ❌ | ✅ | ❌ |
| ECDSA | ❌ | ✅ | ❌ |
| AES | ❌ | ✅ | ❌ |
| ECDH | ❌ | ✅ | ❌ |
| Secure RNG | ❌ | ✅ | ❌ |
| SHA-3 | ❌ | ❌ | ❌ |

Legend:
- ✅ Available
- ⚠️ Partial
- ❌ Not yet implemented

## Video Courses & Resources

**Cryptography & Security**:
- [Security Courses - Various Universities](https://github.com/Developer-Y/cs-video-courses#security)
- [Applied Cryptography](https://www.coursera.org/learn/crypto)

**Mathematics Foundations**:
- [Math for Computer Scientists](https://github.com/Developer-Y/cs-video-courses#math-for-computer-scientist)
>>>>>>> main

## Sources

- **FIPS 180-4** — the SHA-2 specification. The padding rule and the message schedule are both in §5, and it is the authority when your digest disagrees with `sha256sum`.
- Ferguson, Schneier & Kohno, **Cryptography Engineering** — for why not to use any of this in production.

Full list: [`../../REFERENCES.md`](../../REFERENCES.md#week-1314--sockets-and-protocols)
