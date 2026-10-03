# ECDH (Elliptic Curve Diffie-Hellman) Implementation Guide

## Overview

ECDH is a key agreement protocol that allows two parties to establish a shared secret over an insecure channel. It uses elliptic curve cryptography to achieve this securely and efficiently. This guide provides comprehensive implementation guidelines without actual code.

## Prerequisites

- Working elliptic curve arithmetic implementation
- Point addition, doubling, and scalar multiplication
- Cryptographic hash function (SHA-256 or better)
- Secure random number generator

## Protocol Fundamentals

### Basic Concept

Two parties (Alice and Bob) each have:
- Private key: random scalar
- Public key: point on elliptic curve

They exchange public keys and independently compute the same shared secret.

### Mathematical Foundation

**Setup:**
- Elliptic curve E over finite field
- Base point G of prime order n
- Curve parameters publicly known

**Alice's Key Pair:**
- Private key: a (random integer, 1 < a < n)
- Public key: A = a × G

**Bob's Key Pair:**
- Private key: b (random integer, 1 < b < n)
- Public key: B = b × G

**Shared Secret Computation:**
- Alice computes: S = a × B = a × (b × G) = ab × G
- Bob computes: S = b × A = b × (a × G) = ab × G
- Both get the same point S (shared secret)

**Security:**
- Attacker knows A and B but not a or b
- Computing a or b from A or B is hard (ECDLP)
- Cannot compute S without knowing a or b

## Implementation Components

### 1. Key Generation

**Purpose:** Generate private and public key pair for ECDH.

**Algorithm:**

```
Input: Curve parameters (p, a, b, G, n, h)
Output: Private key d, Public key Q

Steps:
1. Generate random private key:
   d = random integer in range [1, n-1]
   Use cryptographically secure RNG
   Ensure sufficient entropy

2. Compute public key:
   Q = d × G
   Use scalar multiplication

3. Validate public key:
   Verify Q is on curve
   Verify Q ≠ O (point at infinity)
   Optionally verify n × Q = O

4. Return (d, Q)
```

**Implementation Considerations:**

**Random Number Generation:**
- Must use cryptographically secure RNG
- Insufficient entropy compromises security
- Consider using /dev/urandom or platform CSPRNG
- For deterministic derivation, use HKDF with secure seed

**Key Validation:**
- Always validate generated public key
- Ensures point is valid before use
- Prevents invalid curve attacks

**Key Storage:**
- Private key must be kept secret
- Store in secure storage (keychain, HSM)
- Public key can be freely shared
- Consider key compression for storage/transmission

### 2. Shared Secret Computation

**Purpose:** Compute shared secret from own private key and peer's public key.

**Algorithm:**

```
Input: 
  - Own private key d
  - Peer's public key Q_peer
  - Curve parameters

Output: Shared secret point S

Steps:
1. Validate peer's public key:
   a. Verify Q_peer ≠ O
   b. Verify Q_peer is on curve:
      y² ≡ x³ + ax + b (mod p)
   c. Verify Q_peer has correct order:
      n × Q_peer = O (optional but recommended)

2. Compute shared secret:
   S = d × Q_peer
   Use scalar multiplication

3. Extract shared secret value:
   s = x-coordinate of S
   Convert to bytes (32 bytes for 256-bit curves)

4. Return s (or derive key from it)
```

**Implementation Considerations:**

**Public Key Validation:**

**Essential Checks:**
1. **Point at Infinity:**
   - Verify Q ≠ O
   - Trivial but critical check

2. **Curve Membership:**
   - Verify y² ≡ x³ + ax + b (mod p)
   - Prevents invalid curve attacks
   - **Must always perform this check**

3. **Coordinate Range:**
   - Verify 0 ≤ x < p and 0 ≤ y < p
   - Basic sanity check

**Optional but Recommended:**
4. **Order Verification:**
   - Verify n × Q = O
   - Prevents small subgroup attacks
   - Important for curves with cofactor h > 1
   - Can be expensive for large n

**Cofactor Considerations:**

For curves with cofactor h > 1:
- Option 1: Multiply result by h: S = h × (d × Q_peer)
- Option 2: Multiply private key by h: d' = h × d, then S = d' × Q_peer
- Option 3: Verify order of Q_peer (expensive)
- Standard curves like P-256, P-384 have h = 1

**Common Curves:**
- secp256k1 (Bitcoin): h = 1
- secp256r1 (P-256): h = 1
- Curve25519: h = 8 (requires handling)

### 3. Key Derivation from Shared Secret

**Purpose:** Derive cryptographic keys from shared secret point.

**Why Needed:**
- Shared secret is elliptic curve point (x, y)
- Need to convert to uniform key material
- Extract entropy properly
- Bind additional context information

**Algorithm:**

```
Input:
  - Shared secret point S (or just x-coordinate)
  - Shared information (optional)
  - Key length needed

Output: Derived key(s)

Steps:
1. Extract shared secret value:
   s = x-coordinate of S
   Convert to byte string (big-endian, fixed length)

2. Apply key derivation function:
   key = KDF(s, shared_info, key_length)
   
   Options:
   a. Simple hash: key = SHA-256(s)
   b. HKDF: Proper KDF with salt and info
   c. ANSI X9.63 KDF (standard for ECDH)
   d. Concatenation KDF

3. Return derived key
```

**Key Derivation Functions:**

**Option 1: Simple Hash (Not Recommended)**
```
key = SHA-256(s)
```
- Simple but inflexible
- Cannot derive multiple keys
- No context binding
- Use only for simple cases

**Option 2: HKDF (Recommended)**
```
Extract phase:
  PRK = HMAC-SHA256(salt, s)

Expand phase:
  OKM = HKDF-Expand(PRK, info, length)
```
- Modern, well-analyzed KDF
- Supports salt and context info
- Can derive multiple keys
- Recommended by NIST

**Option 3: ANSI X9.63 KDF (Standard)**
```
For i = 1 to ⌈length / hash_len⌉:
  K[i] = Hash(s || Counter(i) || SharedInfo)
Return leftmost length bits of K[1] || K[2] || ...
```
- Specified in SEC 1 and ANSI X9.63
- Widely used in ECC standards
- Simple and effective

**Option 4: Concatenation KDF**
```
For i = 1 to ⌈length / hash_len⌉:
  K[i] = Hash(Counter(i) || s || FixedInfo)
Return leftmost length bits of K[1] || K[2] || ...
```
- NIST SP 800-56A standard
- Similar to X9.63
- Includes counter and fixed info

**Shared Information (Info Parameter):**

Include in KDF to bind context:
- Protocol identifier
- Party identities (Alice ID || Bob ID)
- Nonces or session IDs
- Key purpose identifier
- Prevents key reuse across contexts

### 4. Complete ECDH Exchange

**Protocol Flow:**

```
Setup Phase:
1. Agree on curve parameters (p, a, b, G, n, h)
2. Both parties generate key pairs

Key Exchange Phase:
Alice                           Bob
------                          -----
Generate (a, A)                 Generate (b, B)
    |                               |
    |-------- Send A -------------->|
    |                               |
    |<------- Send B ---------------|
    |                               |
S_A = a × B                     S_B = b × A
Derive k_A = KDF(S_A)           Derive k_B = KDF(S_B)

Result: k_A == k_B (shared key)
```

**Implementation:**

**Alice's Side:**
```
1. Generate key pair:
   (a, A) = GenerateKeyPair()

2. Send public key A to Bob
   Encode A (compressed or uncompressed)
   Transmit over channel

3. Receive Bob's public key B
   Decode received bytes to point B
   Validate B

4. Compute shared secret:
   S = a × B
   Validate S ≠ O

5. Derive session key:
   k = KDF(S, shared_info)

6. Use k for encryption/MAC
```

**Bob's Side:**
```
1. Generate key pair:
   (b, B) = GenerateKeyPair()

2. Receive Alice's public key A
   Decode received bytes to point A
   Validate A

3. Send public key B to Alice
   Encode B (compressed or uncompressed)
   Transmit over channel

4. Compute shared secret:
   S = b × A
   Validate S ≠ O

5. Derive session key:
   k = KDF(S, shared_info)

6. Use k for encryption/MAC
```

## Security Considerations

### 1. Ephemeral vs Static Keys

**Static ECDH:**
- Long-term key pairs
- Keys reused across sessions
- No forward secrecy
- Compromise of private key reveals all past sessions

**Ephemeral ECDH (ECDHE):**
- Fresh key pair for each session
- Keys discarded after use
- Provides forward secrecy
- Compromise doesn't affect past sessions
- **Recommended for most applications**

**Semi-Static:**
- One party static, one ephemeral
- Used in some protocols (IKE)
- Limited forward secrecy

### 2. Public Key Validation

**Critical Importance:**

Skipping validation enables attacks:
- Invalid curve attacks
- Small subgroup attacks
- Twist attacks

**Invalid Curve Attack:**

Attacker sends point on different curve:
- Same field, different parameters
- Weaker curve with smaller order
- Can reveal bits of private key
- Repeating attack reveals full key

**Prevention:**
- Always validate point is on specified curve
- Check y² ≡ x³ + ax + b (mod p)
- Do not skip this check

**Small Subgroup Attack:**

For curves with cofactor h > 1:
- Attacker sends point of small order
- Shared secret has limited possibilities
- Can brute-force shared secret

**Prevention:**
- Verify n × Q = O (expensive)
- Or multiply result by cofactor h
- Or choose curve with h = 1 (P-256, secp256k1)

### 3. Timing Attacks

**Vulnerabilities:**

Variable-time scalar multiplication:
- Leaks information about private key bits
- Multiple observations can reveal full key
- Applies to both key generation and shared secret computation

**Mitigations:**

**Use Constant-Time Scalar Multiplication:**
- Montgomery ladder
- Same operations regardless of key bits
- No secret-dependent branches

**Blinding Techniques:**
- Randomize point representation
- Randomize scalar: d' = d + rn
- Add randomness to intermediate values

**Timing-Resistant Implementation Checklist:**
- [ ] Use Montgomery ladder or equivalent
- [ ] Avoid secret-dependent branches
- [ ] Avoid secret-dependent memory access
- [ ] Use constant-time field operations
- [ ] Test with timing analysis tools

### 4. Key Confirmation

**Problem:**

Basic ECDH has no authentication:
- No proof of peer identity
- Vulnerable to man-in-the-middle (MITM)
- Attacker can intercept and replace public keys

**Solutions:**

**Option 1: Authenticated ECDH**
- Sign public keys with long-term signing key
- Verify signatures before accepting public key
- Requires PKI or trust establishment

**Option 2: Password-Authenticated Key Exchange (PAKE)**
- Use password to authenticate exchange
- Protocols: SPAKE2, OPAQUE
- Resistant to offline dictionary attacks

**Option 3: Key Confirmation Step**
- After ECDH, exchange MAC of transcript:
  - MAC_A = MAC(k, transcript || "Alice")
  - MAC_B = MAC(k, transcript || "Bob")
- Verify MACs match
- Confirms both computed same key
- Doesn't prevent MITM but detects failures

**Option 4: Use Established Protocol**
- TLS 1.3 handshake (includes ECDHE)
- Noise Protocol Framework
- Signal Protocol
- Don't invent your own

### 5. Forward Secrecy

**Achieving Forward Secrecy:**

1. **Use Ephemeral Keys:**
   - Generate fresh key pair per session
   - Discard private key after use

2. **Secure Key Deletion:**
   - Overwrite private key memory
   - Use secure deletion functions
   - Ensure compiler doesn't optimize away

3. **Avoid Key Logging:**
   - Don't write keys to disk
   - Avoid storing in core dumps
   - Clear from swap/page files

4. **Regular Key Rotation:**
   - Even within long sessions
   - Re-run ECDHE periodically
   - Limits exposure window

### 6. Common Pitfalls

**Pitfall 1: Skipping Validation**
- **Never skip public key validation**
- Always check point is on curve
- Critical for security

**Pitfall 2: Reusing Ephemeral Keys**
- Defeats purpose of ephemeral keys
- Loses forward secrecy
- Generate fresh keys per session

**Pitfall 3: Using Raw Shared Secret**
- Don't use x-coordinate directly as key
- Always use KDF
- Ensures uniform key material

**Pitfall 4: No Authentication**
- ECDH alone doesn't authenticate
- Combine with signatures or use authenticated protocol
- Prevent MITM attacks

**Pitfall 5: Weak Random Numbers**
- Predictable private keys
- Catastrophic security failure
- Use cryptographically secure RNG

## Advanced Topics

### 1. Curve25519

**Overview:**
- Modern high-speed curve
- Designed for ECDH specifically
- Used in TLS 1.3, Signal, WireGuard

**Key Features:**
- Montgomery curve: By² = x³ + Ax² + x
- Fast and secure
- Built-in protection against various attacks
- Cofactor h = 8 (requires handling)

**Differences from Weierstrass Curves:**

**Scalar Multiplication:**
- Only x-coordinate used (no y)
- Faster computation
- Simpler implementation

**Key Format:**
- Private key: 32 random bytes
- Clamp private key bits:
  - Clear bits 0, 1, 2
  - Clear bit 255
  - Set bit 254
- Public key: 32 bytes (x-coordinate only)

**Implementation:**

```
1. Generate private key:
   d = 32 random bytes
   Clamp d:
     d[0] &= 248  // Clear low 3 bits
     d[31] &= 127 // Clear high bit
     d[31] |= 64  // Set bit 254

2. Compute public key:
   Q = X25519(d, 9)  // 9 is base point x-coordinate

3. Compute shared secret:
   S = X25519(d_A, Q_B)
```

**Security Notes:**
- Clamping makes all keys valid
- No point validation needed (designed in)
- Cofactor handled by clamping
- Still need to check for low-order points: reject if S = 0

### 2. X448

**Overview:**
- 448-bit security level
- Similar design to Curve25519
- Specified in RFC 7748

**Key Features:**
- Montgomery curve over larger field
- Cofactor h = 4
- 224-bit security (post-quantum: ~192-bit)

**Usage:**
- Similar to Curve25519
- Longer keys: 56 bytes
- Slower but higher security margin

### 3. Hybrid Post-Quantum ECDH

**Motivation:**
- Quantum computers threaten ECDH
- Transition to post-quantum cryptography
- Hybrid approach for safety

**Approach:**

Combine classical ECDH with PQ KEM:
```
1. Perform ECDH: S_classical = ECDH(...)

2. Perform PQ KEM: S_pq = KEM_Encaps(...)
   Examples: Kyber, NTRU, Classic McEliece

3. Combine secrets:
   S_combined = KDF(S_classical || S_pq)

4. Use S_combined as session key
```

**Benefits:**
- Secure if either primitive is secure
- Smooth transition path
- Deployed in TLS experiments

## Testing Strategy

### Unit Tests

**Key Generation:**
- Test private key in valid range [1, n-1]
- Verify public key is on curve
- Test deterministic generation (if supported)
- Test key encoding/decoding

**Shared Secret Computation:**
- Test with known test vectors
- Verify Alice and Bob get same secret
- Test with various curves
- Test identity: S = d × (1 × G) = d × G

**Public Key Validation:**
- Test rejection of invalid points
- Test point not on curve
- Test point at infinity
- Test points of small order (for curves with h > 1)

**Key Derivation:**
- Test KDF with known vectors
- Test multiple key derivation
- Test with different info parameters

### Integration Tests

**Full Exchange:**
- Simulate full ECDH exchange
- Test with different curve types
- Test with random key pairs
- Verify computed keys match

**Interoperability:**
- Test against OpenSSL implementation
- Test against libsodium (Curve25519)
- Use same private/public keys
- Verify shared secrets match

**Protocol Tests:**
- Test with TLS-like handshake
- Test rekeying scenarios
- Test with authenticated ECDH

### Security Tests

**Timing Analysis:**
- Measure scalar multiplication time
- Verify constant-time execution
- Test with various private keys

**Invalid Input Tests:**
- Test with invalid public keys
- Test with points not on curve
- Test with point at infinity
- Verify proper rejection

**Attack Simulations:**
- Simulate invalid curve attack
- Simulate small subgroup attack
- Test with weak curves
- Verify validation prevents attacks

## Performance Optimization

### 1. Curve Selection

Choose curve based on requirements:
- **P-256:** Widely supported, good performance
- **secp256k1:** Used in Bitcoin, similar to P-256
- **Curve25519:** Fastest, simplest, modern choice
- **P-384:** Higher security margin
- **X448:** Post-quantum resistance

### 2. Scalar Multiplication Optimization

Use efficient algorithms:
- Montgomery ladder (constant-time)
- Fixed-base optimization (for generator)
- Precomputation tables
- Projective coordinates (avoid divisions)

### 3. Batch Operations

Process multiple ECDH operations together:
- Batch validation of public keys
- Parallel scalar multiplications
- Amortize overhead

### 4. Hardware Acceleration

Use platform features:
- ARM crypto extensions
- Intel/AMD optimizations
- Hardware random number generators
- Dedicated crypto accelerators

## Implementation Phases

### Phase 1: Basic ECDH
1. Implement key generation
2. Implement shared secret computation
3. Test with known vectors
4. Verify roundtrip works

### Phase 2: Key Derivation
1. Choose KDF (HKDF recommended)
2. Implement KDF
3. Test KDF separately
4. Integrate with ECDH

### Phase 3: Validation
1. Implement public key validation
2. Test validation logic
3. Add to shared secret computation
4. Test with invalid inputs

### Phase 4: Security Hardening
1. Audit for timing leaks
2. Implement constant-time operations
3. Add key zeroization
4. Security testing

### Phase 5: Protocol Integration
1. Design complete protocol
2. Add authentication
3. Implement key confirmation
4. Document usage

## Real-World Usage Examples

### TLS 1.3 Key Exchange

```
1. ClientHello:
   Client generates ephemeral key pair (c, C)
   Sends C in key_share extension

2. ServerHello:
   Server generates ephemeral key pair (s, S)
   Sends S in key_share extension
   Computes shared secret: K = s × C

3. Client Computes:
   K = c × S
   Derives keys: KDF(K, handshake_context)

4. Both derive:
   - Handshake traffic keys
   - Application traffic keys
   Using HKDF with handshake transcript
```

### Signal Protocol (Double Ratchet)

```
Uses ECDH for key agreement:
1. Initial X3DH (Extended Triple Diffie-Hellman)
   Multiple ECDH operations for strong authentication

2. Double Ratchet:
   - DH ratchet: New ECDH every response
   - Symmetric ratchet: KDF chains
   - Provides forward secrecy and break-in recovery
```

### WireGuard VPN

```
Noise Protocol Framework with Curve25519:
1. Static-static ECDH (authentication)
2. Ephemeral-static ECDH (forward secrecy)
3. Ephemeral-ephemeral ECDH (additional secrecy)
4. Multiple ECDH outputs combined with KDF
```

## References

### Standards
- NIST SP 800-56A: Recommendation for Pair-Wise Key-Establishment
- RFC 7748: Elliptic Curves for Security (Curve25519 and X448)
- RFC 8446: TLS 1.3 (uses ECDHE)
- SEC 1: Elliptic Curve Cryptography (includes ECDH)
- ANSI X9.63: Key Agreement and Key Transport Using Elliptic Curve Cryptography

### Books
- "Guide to Elliptic Curve Cryptography" - Hankerson, Menezes, Vanstone
- "Cryptography Engineering" - Ferguson, Schneier, Kohno
- "Real-World Cryptography" - David Wong

### Papers
- "Curve25519: New Diffie-Hellman Speed Records" - Daniel J. Bernstein
- "A Security Analysis of the Signal Protocol" - Cohn-Gordon et al.
- "The Noise Protocol Framework" - Trevor Perrin

### Online Resources
- RFC 7748 Test Vectors
- SafeCurves (https://safecurves.cr.yp.to/)
- Noise Protocol Framework
- Signal Protocol Specifications

## Conclusion

ECDH is a fundamental building block for secure communications. Key takeaways:

1. **Always Validate Public Keys:**
   - Check point is on curve
   - Critical security requirement
   - Never skip this step

2. **Use Ephemeral Keys:**
   - Provides forward secrecy
   - Fresh keys per session
   - Secure key deletion

3. **Apply KDF:**
   - Don't use raw shared secret
   - Use proper KDF (HKDF)
   - Include context information

4. **Add Authentication:**
   - ECDH alone is unauthenticated
   - Combine with signatures
   - Or use complete protocol (TLS, Noise)

5. **Choose Modern Curves:**
   - Curve25519 for new designs
   - P-256 for compatibility
   - Avoid deprecated curves

6. **⚠️ Production Warning:**
   - Use established libraries
   - This guide is educational
   - Crypto mistakes are costly

ECDH enables secure key agreement but must be implemented carefully with proper validation, authentication, and integration into complete protocols.
