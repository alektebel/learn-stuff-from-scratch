# AES (Advanced Encryption Standard) Implementation Guide

## Overview

AES (Rijndael) is a symmetric block cipher that encrypts data in 128-bit blocks using keys of 128, 192, or 256 bits. It's the most widely used encryption algorithm worldwide. This guide provides comprehensive implementation guidelines without actual code.

## Prerequisites

- Understanding of finite field arithmetic (GF(2^8))
- Basic knowledge of block cipher principles
- Familiarity with bitwise operations

## AES Fundamentals

### Block and Key Sizes

| Key Size | Block Size | Number of Rounds |
|----------|------------|------------------|
| 128 bits | 128 bits   | 10               |
| 192 bits | 128 bits   | 12               |
| 256 bits | 128 bits   | 14               |

**Important Notes:**
- Block size is always 128 bits (16 bytes)
- Only key size varies
- More rounds with larger keys

### State Representation

AES operates on a 4×4 matrix of bytes called the **state**:

```
| s0,0  s0,1  s0,2  s0,3 |
| s1,0  s1,1  s1,2  s1,3 |
| s2,0  s2,1  s2,2  s2,3 |
| s3,0  s3,1  s3,2  s3,3 |
```

**Layout in Memory:**
- Can be stored as 16-byte array
- Indexing: column-major order (col 0, then col 1, etc.)
- Byte positions: [0,4,8,12, 1,5,9,13, 2,6,10,14, 3,7,11,15]

### Galois Field GF(2^8) Arithmetic

AES uses finite field arithmetic in GF(2^8) with irreducible polynomial:
```
m(x) = x^8 + x^4 + x^3 + x + 1 (or 0x11B in hex)
```

**Addition in GF(2^8):**
- Simply XOR two bytes
- a + b = a ⊕ b
- No carry, self-inverse

**Multiplication in GF(2^8):**
- More complex, requires reduction modulo m(x)
- Used extensively in MixColumns

## Core AES Operations

### 1. SubBytes (S-Box) Transformation

Applies non-linear substitution to each byte using S-Box lookup table.

**S-Box Construction:**

The S-Box is a 16×16 lookup table built through two steps:

**Step 1: Multiplicative Inverse**
- For byte b in GF(2^8), compute b^(-1)
- Special case: inverse of 0x00 is 0x00
- Uses extended Euclidean algorithm in GF(2^8)

**Step 2: Affine Transformation**
- Apply transformation: b' = Ab + c
- Matrix A and vector c are specified in AES standard
- Provides diffusion properties

**Implementation Options:**

**Option 1: Pre-computed Lookup Table**
- Store 256-byte S-Box array
- Fastest method (single memory lookup)
- Recommended for most implementations

```
S-Box[256] = {
  0x63, 0x7c, 0x77, 0x7b, 0xf2, 0x6b, 0x6f, 0xc5, ...
}
```

**Option 2: On-the-fly Calculation**
- Compute inverse in GF(2^8)
- Apply affine transformation
- Slower but saves memory (256 bytes)
- Useful for constrained environments

**Option 3: Composite Field Approach**
- Represent GF(2^8) as composite field GF((2^4)^2)
- Smaller S-Boxes, less memory
- More complex but constant-time friendly

**Algorithm:**
```
For each byte in state:
  1. Look up S-Box[byte] or compute
  2. Replace byte with S-Box value
```

**Inverse SubBytes:**
- Uses inverse S-Box for decryption
- Same structure, different table
- Pre-compute inverse S-Box lookup table

### 2. ShiftRows Transformation

Cyclically shifts the rows of the state.

**Algorithm:**
```
Row 0: No shift (stays the same)
Row 1: Shift left by 1 byte
Row 2: Shift left by 2 bytes
Row 3: Shift left by 3 bytes
```

**Visual Example:**
```
Before:                      After:
| s0,0  s0,1  s0,2  s0,3 |   | s0,0  s0,1  s0,2  s0,3 |
| s1,0  s1,1  s1,2  s1,3 | → | s1,1  s1,2  s1,3  s1,0 |
| s2,0  s2,1  s2,2  s2,3 |   | s2,2  s2,3  s2,0  s2,1 |
| s3,0  s3,1  s3,2  s3,3 |   | s3,3  s3,0  s3,1  s3,2 |
```

**Implementation:**
- Simple byte permutation
- Can be done in-place
- Use temporary variables or array rotation

**Inverse ShiftRows:**
- Shift right instead of left
- Same pattern, opposite direction

### 3. MixColumns Transformation

Mixes data within each column using matrix multiplication in GF(2^8).

**Algorithm:**

Each column is multiplied by fixed matrix:
```
| 02  03  01  01 |   | s0,c |   | s'0,c |
| 01  02  03  01 | × | s1,c | = | s'1,c |
| 01  01  02  03 |   | s2,c |   | s'2,c |
| 03  01  01  02 |   | s3,c |   | s'3,c |
```

**For each column c (0 to 3):**
```
s'0,c = (02 • s0,c) ⊕ (03 • s1,c) ⊕ (01 • s2,c) ⊕ (01 • s3,c)
s'1,c = (01 • s0,c) ⊕ (02 • s1,c) ⊕ (03 • s2,c) ⊕ (01 • s3,c)
s'2,c = (01 • s0,c) ⊕ (01 • s1,c) ⊕ (02 • s2,c) ⊕ (03 • s3,c)
s'3,c = (03 • s0,c) ⊕ (01 • s1,c) ⊕ (01 • s2,c) ⊕ (02 • s3,c)
```

**GF(2^8) Multiplication Implementation:**

**Multiplying by 2 (0x02):**
```
If high bit of a is 0:
  result = a << 1
Else (high bit is 1):
  result = (a << 1) ⊕ 0x1B
```

**Multiplying by 3 (0x03):**
```
result = (a × 2) ⊕ a
```

**Implementation Strategies:**

**Strategy 1: Direct Computation**
- Implement GF(2^8) multiply function
- Multiply each element as needed
- Clear and straightforward

**Strategy 2: Lookup Tables**
- Pre-compute multiplication tables
- Xtime[256] for multiply by 2
- Faster but uses memory (256 bytes per table)

**Strategy 3: Combined Lookup Tables**
- Pre-compute all needed products
- T-Tables: combine SubBytes and MixColumns
- Very fast but uses 4KB of memory
- Used in optimized implementations

**Inverse MixColumns:**
- Uses different matrix for decryption:
```
| 0E  0B  0D  09 |
| 09  0E  0B  0D |
| 0D  09  0E  0B |
| 0B  0D  09  0E |
```

### 4. AddRoundKey Transformation

XORs the state with round key.

**Algorithm:**
```
For each byte position (i, j):
  state[i][j] = state[i][j] ⊕ roundKey[i][j]
```

**Properties:**
- Simplest operation
- Self-inverse (XOR twice returns original)
- Same operation for encryption and decryption
- Provides key-dependent transformation

**Implementation:**
- Can be done in single loop
- Very fast operation
- Process as bytes or words (optimization)

## Key Expansion (Key Schedule)

Generates round keys from cipher key.

### Number of Round Keys Needed

- AES-128: 11 round keys (10 rounds + initial)
- AES-192: 13 round keys (12 rounds + initial)
- AES-256: 15 round keys (14 rounds + initial)

Each round key is 128 bits (16 bytes), same as block size.

### Key Expansion Algorithm

**Inputs:**
- Cipher key (128/192/256 bits)
- Number of rounds (Nr)
- Key length in 32-bit words (Nk = 4/6/8)

**Output:**
- Expanded key array: (Nr + 1) × 16 bytes

**Core Functions:**

**RotWord:**
- Rotate 4-byte word left by 1 byte
- [a0, a1, a2, a3] → [a1, a2, a3, a0]

**SubWord:**
- Apply S-Box to each byte in word
- [a0, a1, a2, a3] → [S-Box[a0], S-Box[a1], S-Box[a2], S-Box[a3]]

**Rcon (Round Constant):**
- Different constant for each round
- Rcon[i] = [RC[i], 0x00, 0x00, 0x00]
- RC[i] = x^(i-1) in GF(2^8)
- RC values: [0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80, 0x1B, 0x36, ...]

**Algorithm Steps:**

```
1. Initialize first Nk words with cipher key:
   W[0..Nk-1] = key

2. For i = Nk to Nb × (Nr + 1):
   temp = W[i-1]
   
   If i mod Nk == 0:
     temp = SubWord(RotWord(temp)) ⊕ Rcon[i/Nk]
   
   Else if (Nk > 6) and (i mod Nk == 4):  // Only for AES-256
     temp = SubWord(temp)
   
   W[i] = W[i-Nk] ⊕ temp

3. Round keys are formed from words:
   RoundKey[r] = W[r×Nb .. (r+1)×Nb - 1]
```

**Implementation Considerations:**

- Can pre-compute and store all round keys
- Or compute on-the-fly to save memory
- Key schedule only needs computation once per key
- For repeated encryption with same key, cache round keys

## Complete AES Encryption Algorithm

### Encryption Process

**Input:**
- Plaintext block (128 bits)
- Cipher key (128/192/256 bits)
- Number of rounds Nr (10/12/14)

**Output:**
- Ciphertext block (128 bits)

**Algorithm:**

```
1. Key Expansion:
   Generate round keys from cipher key

2. Initial Round:
   AddRoundKey(state, roundKey[0])

3. Main Rounds (repeat Nr - 1 times):
   For round = 1 to Nr - 1:
     SubBytes(state)
     ShiftRows(state)
     MixColumns(state)
     AddRoundKey(state, roundKey[round])

4. Final Round (no MixColumns):
   SubBytes(state)
   ShiftRows(state)
   AddRoundKey(state, roundKey[Nr])

5. Output ciphertext
```

### Decryption Process

**Input:**
- Ciphertext block (128 bits)
- Cipher key (same as encryption)
- Number of rounds Nr

**Output:**
- Plaintext block (128 bits)

**Algorithm:**

```
1. Key Expansion:
   Generate round keys (same as encryption)
   Or use in reverse order

2. Initial Round:
   AddRoundKey(state, roundKey[Nr])

3. Main Rounds (reverse order):
   For round = Nr - 1 down to 1:
     InvShiftRows(state)
     InvSubBytes(state)
     AddRoundKey(state, roundKey[round])
     InvMixColumns(state)

4. Final Round (no InvMixColumns):
   InvShiftRows(state)
   InvSubBytes(state)
   AddRoundKey(state, roundKey[0])

5. Output plaintext
```

**Equivalent Inverse Cipher:**

Can rearrange operations for efficiency:
- Swap order of InvShiftRows and InvSubBytes
- Apply InvMixColumns to round keys (except first and last)
- Results in more similar structure to encryption

## Block Cipher Modes of Operation

AES encrypts only 128-bit blocks. For larger data, use modes:

### ECB (Electronic Codebook) - NOT RECOMMENDED

**Encryption:** Each block encrypted independently
```
Ci = AES_Encrypt(Pi, K)
```

**Problems:**
- Identical plaintext blocks → identical ciphertext
- Patterns visible in encrypted data
- Vulnerable to block manipulation
- **Never use ECB for actual encryption**

**Use Case:** Only for single-block encryption or key wrapping

### CBC (Cipher Block Chaining)

**Encryption:**
```
C0 = IV (Initialization Vector)
Ci = AES_Encrypt(Pi ⊕ Ci-1, K)
```

**Decryption:**
```
Pi = AES_Decrypt(Ci, K) ⊕ Ci-1
```

**Properties:**
- Each block depends on all previous blocks
- Requires random IV (must be unpredictable)
- IV doesn't need to be secret (send with ciphertext)
- Decryption can be parallelized
- Encryption is sequential

**Padding:** Required for non-multiple-of-16-byte data
- PKCS#7: Pad with bytes, each byte = padding length
- Example: "hello" (5 bytes) → "hello\x0B\x0B\x0B\x0B\x0B\x0B\x0B\x0B\x0B\x0B\x0B"

### CTR (Counter Mode)

**Encryption/Decryption (same operation):**
```
For block i:
  Counter = Nonce || i
  Keystream = AES_Encrypt(Counter, K)
  Ci = Pi ⊕ Keystream
```

**Properties:**
- Turns block cipher into stream cipher
- Both encryption and decryption parallelizable
- Random access to any block
- No padding required
- Requires unique nonce for each message
- Never reuse nonce with same key

**Counter Construction:**
- Nonce (96 bits) || Counter (32 bits)
- Counter starts at 1 or 0
- Increment for each block

### GCM (Galois/Counter Mode) - RECOMMENDED

**Encryption:**
```
1. Encrypt using CTR mode
2. Compute authentication tag using GHASH
   Tag = GHASH(H, A, C) ⊕ AES_Encrypt(J0, K)
   Where H = AES_Encrypt(0, K)
```

**Properties:**
- Authenticated encryption (AE)
- Provides both confidentiality and authenticity
- Detects tampering
- Efficient and parallelizable
- Industry standard (TLS 1.3, SSH)

**Components:**
- Key K (128/192/256 bits)
- IV (typically 96 bits, 12 bytes)
- Additional Authenticated Data (AAD) - optional
- Produces ciphertext + authentication tag

**Implementation:**
- Use optimized GHASH (table-based or CLMUL)
- Verify tag before decrypting (constant-time comparison)
- Reject message if tag doesn't match

### CCM (Counter with CBC-MAC)

**Properties:**
- Alternative authenticated encryption
- Combines CTR mode with CBC-MAC
- Less efficient than GCM (two passes)
- Used in some protocols (WPA2)

## Implementation Strategies

### Strategy 1: Straightforward Implementation

**Approach:**
- Implement each operation separately
- Clear, easy to understand
- Good for learning and debugging

**Functions:**
- SubBytes(state)
- ShiftRows(state)
- MixColumns(state)
- AddRoundKey(state, roundKey)
- KeyExpansion(key)

**Performance:**
- Moderate speed
- Low memory usage
- Portable across platforms

### Strategy 2: T-Table Optimization

**Approach:**
- Pre-compute combined lookup tables
- Merge SubBytes, ShiftRows, and MixColumns
- Four T-tables (T0, T1, T2, T3), each 256 × 4 bytes

**T-Table Structure:**
```
T0[x] = [S-Box[x] × 02, S-Box[x], S-Box[x], S-Box[x] × 03]
T1[x] = [S-Box[x] × 03, S-Box[x] × 02, S-Box[x], S-Box[x]]
T2[x] = [S-Box[x], S-Box[x] × 03, S-Box[x] × 02, S-Box[x]]
T3[x] = [S-Box[x], S-Box[x], S-Box[x] × 03, S-Box[x] × 02]
```

**Encryption Round:**
```
For each column j:
  temp[j] = T0[s[0,j]] ⊕ T1[s[1,j]] ⊕ T2[s[2,j]] ⊕ T3[s[3,j]] ⊕ RoundKey[j]
```

**Advantages:**
- Much faster (3-5x speedup)
- Reduces operations per round
- Standard in many libraries

**Disadvantages:**
- Uses 4KB memory for tables
- Vulnerable to cache-timing attacks
- Not constant-time

### Strategy 3: Bitsliced Implementation

**Approach:**
- Process multiple blocks simultaneously
- Transpose bit representation
- Operate on bits across blocks

**Advantages:**
- Constant-time execution
- Resistant to cache-timing
- SIMD-friendly

**Disadvantages:**
- Complex implementation
- Requires multiple blocks for efficiency
- Not suitable for single-block encryption

### Strategy 4: Hardware Acceleration

**AES-NI Instructions:**

Modern processors have AES instructions:
- AESENC: Encryption round
- AESENCLAST: Final round
- AESDEC: Decryption round
- AESDECLAST: Final decryption round
- AESKEYGENASSIST: Key expansion

**Advantages:**
- Extremely fast (10+ Gbps)
- Constant-time by design
- Reduces code complexity

**Usage:**
- Check CPU support at runtime
- Provide fallback implementation
- Use intrinsics or inline assembly

## Security Considerations

### Key Management

**Best Practices:**
- Generate keys with cryptographically secure RNG
- Never hard-code keys in source code
- Use key derivation functions (PBKDF2, Argon2)
- Implement secure key storage (OS keychain, HSM)
- Zero key memory after use
- Rotate keys periodically

### IV/Nonce Requirements

**CBC Mode:**
- IV must be unpredictable
- Generate with CSPRNG
- IV doesn't need to be secret
- Send IV with ciphertext
- Never reuse IV with same key

**CTR/GCM Mode:**
- Nonce must be unique (never reuse)
- Can be sequential counter (if managed correctly)
- Nonce reuse is catastrophic in CTR/GCM
- Use 96-bit nonces for GCM

### Padding Oracle Attacks

**Vulnerability:**
- In CBC mode with padding
- Error messages reveal padding validity
- Attacker can decrypt without key

**Mitigation:**
- Use authenticated encryption (GCM, CCM)
- Don't reveal padding errors
- Return generic error for all decryption failures
- Implement constant-time padding check

### Timing Attacks

**Vulnerabilities:**
- Variable-time table lookups
- Cache timing side-channels
- Branch prediction based on secret data

**Mitigations:**
- Use constant-time implementations
- Bitsliced or AES-NI implementations
- Avoid secret-dependent memory access
- Avoid secret-dependent branches

### Side-Channel Attacks

**Power Analysis:**
- Hardware-based attacks
- Monitor power consumption
- Can recover keys

**Mitigation:**
- Hardware countermeasures
- Randomize intermediate values
- Use masking techniques

**Cache Timing:**
- Software-based attack
- Exploits CPU cache behavior
- Works remotely via shared cache

**Mitigation:**
- Avoid table lookups
- Use AES-NI if available
- Bitsliced implementation

## Testing Strategy

### Test Vectors

**NIST Test Vectors:**
- FIPS 197 Appendix B (example vectors)
- NIST CAVP test vectors
- Known answer tests (KAT)

**Test Categories:**
1. **Single Block:**
   - Encrypt known plaintext with known key
   - Verify ciphertext matches expected
   - Decrypt and verify roundtrip

2. **Key Sizes:**
   - Test AES-128, AES-192, AES-256
   - Verify different number of rounds

3. **All Zeros/Ones:**
   - Edge cases
   - All-zero key, all-zero plaintext
   - All-ones scenarios

4. **Randomized:**
   - Random keys and plaintexts
   - Verify encrypt/decrypt roundtrip
   - Test many iterations

### Mode Testing

**CBC Mode:**
- Test with various IV values
- Verify chaining works correctly
- Test padding and unpadding
- Test decryption with corrupted ciphertext

**CTR Mode:**
- Test counter increment
- Test different nonce values
- Verify random access decryption

**GCM Mode:**
- Test authentication tag generation
- Verify tag validation
- Test with AAD
- Test tamper detection

### Security Testing

**Timing Analysis:**
- Measure operation time
- Verify constant-time where required
- Test with various inputs

**Memory Safety:**
- Check for buffer overflows
- Verify proper bounds checking
- Test with valgrind or sanitizers

**Key Zeroization:**
- Verify keys are cleared after use
- Check compiler doesn't optimize away memset

## Performance Optimization Tips

1. **Use AES-NI if available:**
   - Check CPU capabilities
   - Massive speedup
   - Constant-time by default

2. **Batch Processing:**
   - Process multiple blocks together
   - Amortize overhead
   - Enable better compiler optimization

3. **Optimize Key Schedule:**
   - Pre-compute round keys
   - Cache for repeated use
   - Consider on-the-fly for one-time use

4. **Choose Right Mode:**
   - GCM for general purpose
   - CTR for parallelizable encryption
   - Avoid ECB entirely

5. **Platform-Specific:**
   - Use SIMD instructions
   - Optimize for cache hierarchy
   - Consider endianness

## Common Implementation Mistakes

1. **Using ECB Mode:**
   - Never appropriate for multi-block data
   - Use CBC, CTR, or GCM instead

2. **Reusing IV/Nonce:**
   - Catastrophic in CTR/GCM
   - Weakens CBC security
   - Always use fresh IV

3. **No Authentication:**
   - Ciphertext can be modified
   - Use GCM or separate MAC
   - Verify before decrypt

4. **Predictable IVs:**
   - In CBC mode, allows attacks
   - Must be unpredictable
   - Use CSPRNG

5. **Incorrect Padding:**
   - Off-by-one errors
   - Incorrect validation
   - Test thoroughly

6. **Timing Leaks:**
   - Variable-time operations
   - Enable cache attacks
   - Use constant-time code

## Implementation Phases

### Phase 1: Core Cipher
1. Implement S-Box (forward and inverse)
2. Implement basic state operations
3. Implement SubBytes, ShiftRows, MixColumns
4. Implement AddRoundKey
5. Test each operation individually

### Phase 2: Key Schedule
1. Implement RotWord, SubWord
2. Implement Rcon generation
3. Implement key expansion
4. Test with known vectors

### Phase 3: Complete Cipher
1. Integrate all operations
2. Implement encryption
3. Implement decryption
4. Test with NIST vectors

### Phase 4: Modes of Operation
1. Implement ECB (for testing only)
2. Implement CBC
3. Implement CTR
4. Implement GCM

### Phase 5: Optimization
1. Profile performance
2. Implement T-tables if appropriate
3. Add AES-NI support
4. Optimize hot paths

### Phase 6: Security Hardening
1. Audit for timing leaks
2. Add constant-time operations
3. Implement key zeroization
4. Add error handling

## References

### Standards
- FIPS 197: Advanced Encryption Standard (AES)
- NIST SP 800-38A: Modes of Operation
- NIST SP 800-38D: GCM and GMAC
- RFC 3610: CCM Mode
- RFC 5116: AEAD Interface

### Books
- "The Design of Rijndael" - Daemen and Rijmen (AES creators)
- "Cryptography Engineering" - Ferguson, Schneier, Kohno
- "Understanding Cryptography" - Paar and Pelzl

### Papers
- Original Rijndael Proposal
- "Cache-timing attacks on AES" - Daniel Bernstein
- "Advanced Encryption Standard: Variants and Implementation Options"

### Online Resources
- NIST AES test vectors
- Stick Figure Guide to AES
- Wikipedia AES article (surprisingly good)

## Conclusion

AES is a well-designed, secure symmetric cipher when implemented correctly. Key points:

1. **Use Standard Modes:**
   - Prefer GCM for authenticated encryption
   - Never use ECB for actual data
   - Understand IV/nonce requirements

2. **Implement Securely:**
   - Use constant-time operations
   - Validate all inputs
   - Clear sensitive data
   - Test thoroughly

3. **Consider Hardware:**
   - AES-NI provides huge speedup
   - Inherently constant-time
   - Worth the complexity

4. **⚠️ Production Warning:**
   - Use established libraries (OpenSSL, libsodium)
   - This guide is educational only
   - Crypto bugs can be catastrophic

AES is the foundation of modern symmetric encryption. Understanding its internals is valuable, but always use vetted implementations in production.
