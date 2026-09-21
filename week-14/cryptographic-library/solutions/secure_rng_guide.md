# Secure Random Number Generation Implementation Guide

## Overview

Cryptographically secure random number generation (CSRNG) is foundational to all cryptographic systems. Weak randomness compromises security regardless of algorithm strength. This guide provides comprehensive implementation guidelines for secure random number generation.

## Why Cryptographic Randomness Matters

### Critical Uses in Cryptography

1. **Key Generation:**
   - Symmetric keys (AES, ChaCha20)
   - Private keys (RSA, ECC)
   - Weak randomness → predictable keys → system compromise

2. **Nonces and IVs:**
   - Initialization Vectors for block ciphers
   - Nonces for authenticated encryption
   - Reused or predictable values break security

3. **Salts:**
   - Password hashing
   - Key derivation
   - Prevent precomputation attacks

4. **Session Tokens:**
   - Authentication tokens
   - Session IDs
   - CSRF tokens

5. **Cryptographic Protocols:**
   - Challenge-response systems
   - Zero-knowledge proofs
   - Randomized algorithms

### Consequences of Weak Randomness

**Historical Failures:**

1. **Netscape SSL (1995):**
   - Used predictable seed (time, PID, PPID)
   - Sessions could be decrypted
   - Broken within minutes

2. **Debian OpenSSL (2008):**
   - Removed "uninitialized" memory from RNG
   - Only 32,768 possible keys
   - Millions of keys compromised

3. **Dual_EC_DRBG (2013):**
   - Backdoored NIST standard
   - NSA could predict output
   - Used in commercial products

4. **Bitcoin Android Wallets (2013):**
   - Poor randomness in Android SecureRandom
   - Same nonces used for different signatures
   - Private keys recovered, Bitcoin stolen

5. **PlayStation 3 (2010):**
   - Static ECDSA nonce in signing code
   - Private key recovered
   - Console security compromised

## Requirements for Cryptographic RNG

### Essential Properties

1. **Unpredictability:**
   - Past outputs don't predict future
   - Future outputs don't reveal past
   - Cannot be distinguished from true random

2. **Uniformity:**
   - All values equally likely
   - No statistical bias
   - Passes randomness tests

3. **Forward Secrecy:**
   - Compromise of current state doesn't reveal past outputs
   - Internal state updated securely

4. **Backward Security (Break-in Recovery):**
   - Compromise of current state doesn't predict future
   - Re-seeding from entropy restores security
   - Usually requires 2^128+ entropy bits

5. **Resistance to Manipulation:**
   - Cannot force RNG into known state
   - Protected against backdoors
   - Transparent design

## Entropy Sources

### Hardware Entropy Sources

**1. CPU-Based (RDRAND/RDSEED):**

**Intel/AMD RDRAND:**
- Hardware RNG in modern CPUs
- Based on thermal noise
- Fast and convenient
- Concern: black box, trust issues

**Intel RDSEED:**
- Direct access to entropy source
- Less processed than RDRAND
- Higher quality, slower
- Better for seeding PRNG

**Usage Guidelines:**
```
- Use as one entropy source, not sole source
- Mix with other sources
- Fallback if unavailable
- Test for failure (can fail)
- Don't trust blindly (theoretical backdoor)
```

**2. Hardware RNG Peripherals:**
- TPM (Trusted Platform Module)
- Dedicated RNG chips
- External RNG devices
- Smart cards

**3. Timing-Based Sources:**

**Interrupt Timing:**
- Timing between interrupts
- Disk, network, keyboard events
- Jitter in timing provides entropy

**High-Resolution Timers:**
- CPU cycle counters
- Nanosecond timers
- Variations provide entropy

**4. Environmental Sensors:**
- Microphone noise
- Camera sensor noise
- Temperature sensors
- Voltage fluctuations

### Software Entropy Sources

**1. System State:**
- Process IDs
- Thread IDs
- Memory addresses (ASLR)
- System uptime
- Load averages

**2. User Activity:**
- Mouse movements
- Keyboard timings
- Touch events
- Accelerometer data

**3. Network Activity:**
- Packet arrival times
- Network jitter
- Connection states

**4. File System:**
- File access times
- Disk seek times
- I/O patterns

### Entropy Quality Considerations

**High-Quality Sources:**
- Hardware RNG (RDRAND, RDSEED)
- Timing jitter between interrupts
- Thermal/quantum noise

**Medium-Quality Sources:**
- System state (PIDs, addresses)
- Network timing
- User input timing

**Low-Quality Sources:**
- System time alone
- Process ID alone
- Predictable system information

**Mixing Entropy:**
- Combine multiple sources
- Use cryptographic hash to mix
- Conservative entropy estimation
- Don't overestimate entropy

## PRNG Algorithms

### CSPRNG Requirements

A cryptographically secure PRNG must:
1. Pass all statistical randomness tests
2. Be computationally indistinguishable from true random
3. Resist state compromise extension attacks
4. Support reseeding
5. Have large state space (≥128 bits security)

### Recommended Algorithms

#### 1. ChaCha20-based PRNG

**Overview:**
- Based on ChaCha20 stream cipher
- Fast, modern, well-studied
- Used in Linux kernel (ChaCha20-CRNG)
- Simple and secure

**Algorithm:**
```
State: 256-bit key + 128-bit counter

Initialization:
1. Seed with 256 bits of entropy
2. Initialize counter to 0

Generate:
1. Run ChaCha20(key, counter) → 512 bits output
2. Use first 256 bits as random output
3. Update key with next 256 bits
4. Increment counter
5. Repeat as needed

Reseed:
1. Generate 256 bits from current state
2. Mix with new entropy: key = Hash(key || entropy)
3. Reset counter
```

**Properties:**
- Forward secure (key constantly updated)
- Fast (ChaCha20 is very fast)
- Simple implementation
- No patents

**Implementation Considerations:**
- Use ChaCha20 with 20 rounds
- Ensure constant-time implementation
- Clear sensitive state on errors
- Support for add_entropy() operation

#### 2. AES-CTR DRBG

**Overview:**
- NIST SP 800-90A standard
- Based on AES in counter mode
- Widely implemented
- Hardware acceleration available

**Algorithm:**
```
State: 256-bit key + 128-bit counter (V)

Instantiate:
1. Derive key and V from seed
2. seed_material = entropy || nonce || personalization
3. key = AES_Encrypt(0, key)
4. V = counter_value

Generate:
1. For each block needed:
   V = (V + 1) mod 2^128
   output_block = AES_Encrypt(V, key)
2. Concatenate blocks
3. Update(additional_input)

Update:
1. temp = AES_Encrypt(V+1, key) || AES_Encrypt(V+2, key) || ...
2. Mix with additional_input
3. Derive new key and V
```

**Properties:**
- NIST standardized
- Hardware acceleration (AES-NI)
- Well-analyzed
- Prediction resistance (if reseeded)

**Implementation Considerations:**
- Use AES-256 for 256-bit security
- Implement reseed mechanism
- Limit requests between reseeds
- Support derivation function

#### 3. HMAC-DRBG

**Overview:**
- NIST SP 800-90A standard
- Based on HMAC construction
- Simple, no block cipher needed
- Deterministic (useful for testing)

**Algorithm:**
```
State: K (key) and V (value)

Instantiate:
1. K = 0x00 ... (hash_len bytes)
2. V = 0x01 ... (hash_len bytes)
3. Update with entropy

Generate:
1. While len(temp) < requested:
   V = HMAC(K, V)
   temp = temp || V
2. Return leftmost requested bits
3. Update(additional_input)

Update:
1. K = HMAC(K, V || 0x00 || provided_data)
2. V = HMAC(K, V)
3. If provided_data present:
   K = HMAC(K, V || 0x01 || provided_data)
   V = HMAC(K, V)
```

**Properties:**
- No block cipher needed
- Provable security
- Simple implementation
- Good for deterministic generation (RFC 6979)

**Implementation Considerations:**
- Use SHA-256 or better
- Implement reseed mechanism
- Support prediction resistance
- Clear state properly

#### 4. Fortuna

**Overview:**
- Designed by Ferguson and Schneier
- Robust against state compromise
- Multiple entropy pools
- Automatic reseeding

**Algorithm:**
```
Components:
- Generator: AES-256 in counter mode
- 32 entropy pools (P0 to P31)
- Reseed counter

Generator:
1. 256-bit key + 128-bit counter
2. Generate blocks: AES_Encrypt(counter++)
3. Update key every 1MB output

Entropy Accumulation:
1. Distribute entropy to pools round-robin
2. Pool Pi is used if 2^i divides reseed counter
3. Ensures pools accumulate entropy over time

Reseed:
1. Triggered by time or entropy threshold
2. Concatenate P0 and some other pools
3. New_key = SHA-256(key || pool_data)
4. Clear used pools
5. Increment reseed counter

Generate:
1. Check if reseed needed (time-based)
2. Generate blocks from AES-CTR
3. Update generator key periodically
```

**Properties:**
- Very robust design
- Recovers from state compromise
- Handles varying entropy quality
- Good for long-running systems

**Implementation Considerations:**
- Complex but well-specified
- Requires multiple hash contexts
- Careful pool management
- Time-based reseeding logic

## Implementation Architecture

### Layered Design

```
┌─────────────────────────────────────┐
│     Application Layer               │
│  (Keys, IVs, Tokens, etc.)          │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   High-Level CSPRNG API             │
│  - get_random_bytes(n)              │
│  - random_int(min, max)             │
│  - random_float()                   │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   DRBG/PRNG Engine                  │
│  (ChaCha20, AES-CTR, HMAC-DRBG)     │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   Entropy Pool/Management           │
│  - Collect from sources             │
│  - Mix and hash                     │
│  - Estimate entropy                 │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   Entropy Sources                   │
│  - Hardware RNG                     │
│  - OS entropy                       │
│  - Timing jitter                    │
│  - User input                       │
└─────────────────────────────────────┘
```

### State Management

**Global State:**
```
Structure:
  - PRNG state (key, counter, etc.)
  - Last reseed time
  - Reseed counter
  - Entropy estimate
  - Lock/mutex for thread safety
```

**Thread Safety:**
- Use mutex/lock for state access
- Or per-thread PRNG instances
- Fork detection (reinitialize after fork)

**Initialization:**
```
1. Collect initial entropy (≥256 bits)
2. Initialize PRNG with seed
3. Mix in additional sources
4. Mark as initialized
```

**Reseeding:**
```
Trigger conditions:
- Time-based (e.g., every 5 minutes)
- Request count (e.g., every 2^20 requests)
- Explicit reseed request
- After state compromise suspected

Process:
1. Collect fresh entropy
2. Mix with current state
3. Update PRNG state
4. Reset counters
```

## API Design

### Core Functions

**1. Initialize:**
```
Input: Optional personalization string
Output: Success/failure
Side effect: Initialize global PRNG state

Algorithm:
1. Collect entropy from available sources
2. Mix entropy with personalization
3. Initialize PRNG state
4. Set initialized flag
5. Return success

Error handling:
- Insufficient entropy: retry or fail
- Hardware failure: fall back to software
- Never proceed with weak seed
```

**2. Generate Random Bytes:**
```
Input: 
  - Number of bytes requested
  - Optional additional input
Output: Array of random bytes

Algorithm:
1. Check if initialized, initialize if needed
2. Acquire lock (thread safety)
3. Check if reseed needed
4. Generate bytes from PRNG
5. Mix in additional input if provided
6. Release lock
7. Return bytes

Considerations:
- Limit max bytes per request
- Reseed periodically
- Clear temporary buffers
```

**3. Reseed:**
```
Input: 
  - Additional entropy (optional)
  - Force flag (optional)
Output: Success/failure

Algorithm:
1. Collect entropy from sources
2. Mix with provided entropy
3. Update PRNG state
4. Update last reseed time
5. Increment reseed counter

When to call:
- Periodically (background thread)
- After suspected compromise
- Before critical operations
- Never hurts (if you have entropy)
```

**4. Add Entropy:**
```
Input: Entropy bytes + estimate of entropy bits
Output: Success/failure

Algorithm:
1. Validate input
2. Mix into entropy pool
3. Update entropy estimate
4. Trigger reseed if threshold reached

Use cases:
- Application-specific entropy
- Hardware RNG output
- Timing measurements
- User input events
```

### Higher-Level APIs

**Generate Random Integer in Range:**
```
Input: min, max (inclusive)
Output: Random integer in [min, max]

Algorithm (unbiased):
1. range = max - min + 1
2. bits_needed = ceil(log2(range))
3. Loop:
   a. Generate bits_needed random bits
   b. value = interpret as integer
   c. If value < range: break
4. Return min + value

Important: Avoid modulo bias
Never use: random() % range
```

**Generate Random Floating Point [0, 1):**
```
Algorithm:
1. Generate 53 random bits (for double precision)
2. value = bits / 2^53
3. Return value

Ensures uniform distribution in [0, 1)
```

**Generate UUID (Version 4):**
```
Algorithm:
1. Generate 128 random bits
2. Set version bits: bits[48-51] = 0100
3. Set variant bits: bits[64-65] = 10
4. Format as UUID string

Result: Random UUID v4
```

## Platform-Specific Implementations

### Linux

**/dev/urandom:**
```
Usage:
  fd = open("/dev/urandom", O_RDONLY)
  read(fd, buffer, num_bytes)
  close(fd)

Properties:
- Non-blocking
- Suitable for all uses
- Kernel manages entropy
- Reseeds automatically

When to use: Default choice on Linux
```

**getrandom() syscall:**
```
Usage:
  getrandom(buffer, num_bytes, 0)

Properties:
- Direct syscall (no file descriptor)
- Faster than /dev/urandom
- Blocks until initialized (at boot)
- Available since Linux 3.17

When to use: Modern Linux systems
Fallback: /dev/urandom
```

**/dev/random:**
```
Properties:
- Blocks when entropy estimate low
- Not necessary for cryptographic use
- Myths about being "more random"

When to use: Never for applications
Use urandom instead
```

### Windows

**BCryptGenRandom:**
```
Usage:
  BCryptGenRandom(NULL, buffer, num_bytes, 
                  BCRYPT_USE_SYSTEM_PREFERRED_RNG)

Properties:
- Modern Windows API (Vista+)
- FIPS compliant
- Thread-safe
- Recommended method

When to use: Default on Windows
```

**RtlGenRandom (CryptGenRandom):**
```
Usage:
  RtlGenRandom(buffer, num_bytes)

Properties:
- Older API, still supported
- Available on XP+
- Simpler than CryptoAPI

When to use: Legacy Windows support
```

### macOS/iOS

**arc4random_buf:**
```
Usage:
  arc4random_buf(buffer, num_bytes)

Properties:
- Modern, secure PRNG
- Automatically seeded
- Thread-safe
- No failure modes

When to use: Default on macOS/iOS
```

**getentropy:**
```
Usage:
  getentropy(buffer, num_bytes)

Properties:
- Similar to getrandom()
- Max 256 bytes per call
- Blocks until initialized

When to use: Recent macOS versions
Fallback: arc4random_buf
```

### Cross-Platform Approach

**Recommended Strategy:**

```
Platform detection:
1. Check platform (Linux, Windows, macOS, etc.)
2. Use platform-specific API as primary
3. Have fallback for older versions
4. Verify availability at runtime

Example:
  #ifdef __linux__
    Use getrandom() → fallback to /dev/urandom
  #elif _WIN32
    Use BCryptGenRandom() → fallback to RtlGenRandom
  #elif __APPLE__
    Use arc4random_buf() → fallback to getentropy()
  #else
    #error "Unsupported platform"
  #endif

Always: Test for failure, never continue with zeros
```

## Security Best Practices

### Dos and Don'ts

**DO:**
- Use operating system CSPRNG when available
- Collect entropy from multiple sources
- Reseed periodically
- Use NIST or well-analyzed algorithms
- Test for initialization failure
- Clear sensitive state on errors
- Use constant-time operations where needed
- Handle fork() correctly (reinitialize)

**DON'T:**
- Use rand() or random() for crypto
- Use timestamp alone as seed
- Reuse nonces in cryptographic protocols
- Ignore RNG failures
- Mix weak and strong randomness incorrectly
- Trust closed-source RNGs blindly
- Proceed with insufficient entropy

### Common Mistakes

**1. Using Non-Cryptographic RNG:**
```
// WRONG:
srand(time(NULL));
key[i] = rand() % 256;

// RIGHT:
getentropy(key, key_len);
```

**2. Weak Seeding:**
```
// WRONG:
seed = time(NULL) + getpid();

// RIGHT:
getrandom(&seed, sizeof(seed), 0);
```

**3. Modulo Bias:**
```
// WRONG:
value = rand() % range;

// RIGHT:
value = uniform_random(0, range - 1);
```

**4. Reusing Nonces:**
```
// WRONG:
nonce = constant_value;

// RIGHT:
getrandom(nonce, nonce_len, 0);
```

**5. Ignoring Failures:**
```
// WRONG:
int ret = getrandom(buf, len, 0);
// continue regardless

// RIGHT:
if (getrandom(buf, len, 0) != len) {
    // Handle error, don't continue
    return ERROR;
}
```

### Testing Random Numbers

**Statistical Tests:**
- NIST Statistical Test Suite
- Dieharder battery of tests
- TestU01 suite
- ENT (entropy estimation)

**What to Test:**
- Uniformity
- Independence
- Runs and patterns
- Frequency
- Serial correlation

**Important:**
- Passing tests doesn't prove security
- Failing tests proves insecurity
- Tests detect obvious flaws only
- Security requires theoretical analysis

## Implementation Checklist

### Design Phase
- [ ] Choose PRNG algorithm (ChaCha20 recommended)
- [ ] Design state structure
- [ ] Plan entropy sources
- [ ] Define API
- [ ] Thread safety strategy

### Implementation Phase
- [ ] Implement PRNG core
- [ ] Implement entropy collection
- [ ] Implement mixing/hashing
- [ ] Implement reseeding logic
- [ ] Add thread safety (mutex)
- [ ] Handle initialization
- [ ] Error handling

### Security Hardening
- [ ] Fork detection and handling
- [ ] Constant-time where needed
- [ ] Clear sensitive data
- [ ] Validate all inputs
- [ ] Secure defaults
- [ ] Rate limiting (DoS prevention)

### Testing
- [ ] Unit tests for PRNG
- [ ] Test entropy collection
- [ ] Test reseeding
- [ ] Statistical tests
- [ ] Thread safety tests
- [ ] Fork() behavior
- [ ] Platform compatibility

### Documentation
- [ ] API documentation
- [ ] Security considerations
- [ ] Example usage
- [ ] Known limitations
- [ ] Platform requirements

## Example Implementation Outline

### Core Structure

```
// State structure
typedef struct {
    uint8_t key[32];        // ChaCha20 key
    uint8_t nonce[12];      // ChaCha20 nonce
    uint64_t counter;       // Block counter
    uint64_t reseed_counter;// Reseed counter
    time_t last_reseed;     // Last reseed time
    pthread_mutex_t lock;   // Thread safety
    bool initialized;       // Init flag
} CSRNG_CTX;

// Global instance
static CSRNG_CTX g_rng = {0};

// Initialize
int csrng_init(void);

// Generate random bytes
int csrng_random_bytes(uint8_t *out, size_t len);

// Reseed
int csrng_reseed(void);

// Add entropy
int csrng_add_entropy(const uint8_t *data, size_t len);

// Helper functions
int collect_entropy(uint8_t *out, size_t len);
void mix_entropy(uint8_t *state, const uint8_t *entropy, size_t len);
int platform_random_bytes(uint8_t *out, size_t len);
```

## References

### Standards
- NIST SP 800-90A: Recommendation for Random Number Generation Using Deterministic Random Bit Generators
- NIST SP 800-90B: Recommendation for the Entropy Sources Used for Random Bit Generation
- NIST SP 800-90C: Recommendation for Random Bit Generator (RBG) Constructions
- BSI AIS 20/31: Functionality classes and evaluation methodology for deterministic random number generators

### Papers
- "Fortuna: A Cryptographically Secure Pseudo-Random Number Generator" - Ferguson, Schneier
- "Mining Your Ps and Qs: Detection of Widespread Weak Keys in Network Devices" - Heninger et al.
- "Random Number Generation: An Illustrated Primer" - Downey
- "Analysis of the Linux Random Number Generator" - Gutterman et al.

### Books
- "Cryptography Engineering" - Ferguson, Schneier, Kohno (Chapter 9)
- "Random Number Generation and Monte Carlo Methods" - Gentle
- "Handbook of Applied Cryptography" - Menezes et al. (Chapter 5)

### Online Resources
- Linux kernel CRNG documentation
- NIST Random Number Generation test suite
- "Good practices for Random Number Generation" (OpenSSL)
- RFC 4086: Randomness Requirements for Security

## Conclusion

Secure random number generation is critical to all cryptographic systems. Key takeaways:

1. **Use System CSPRNG:**
   - Platform APIs are usually best choice
   - Well-tested and maintained
   - Handle complexity for you

2. **Never Use Weak RNGs:**
   - rand(), random() are NOT secure
   - Time-based seeding is weak
   - Predictability is catastrophic

3. **Collect Good Entropy:**
   - Multiple sources better than one
   - Mix properly with hash function
   - Conservative entropy estimates

4. **Implement Reseeding:**
   - Periodic reseeding essential
   - Recovers from state compromise
   - Mix in fresh entropy regularly

5. **Test Thoroughly:**
   - Statistical tests
   - Platform compatibility
   - Fork/thread safety
   - Failure handling

6. **⚠️ Production Warning:**
   - Use OS-provided CSPRNGs when possible
   - This guide is educational
   - RNG failures have catastrophic consequences
   - Study historical failures to avoid repeating them

Random number generation seems simple but is deceptively complex. Take it seriously—your system's security depends on it.
