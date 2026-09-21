# Toralizer - SOCKS Proxy for Tor

A from-scratch implementation of a Toralizer (Tor proxy wrapper) in C that routes TCP connections through the Tor network for anonymous communication.

## Goal

Build a functional Toralizer to understand:
- **SOCKS Protocol**: SOCKS4/SOCKS5 proxy implementation
- **Socket Programming**: Low-level network communication
- **Connection Proxying**: Routing traffic through intermediate servers
- **Tor Network**: Anonymous communication protocols
- **System-level Programming**: Process spawning and IPC

## What is a Toralizer?

A Toralizer is a tool that intercepts and routes network connections through the Tor network using SOCKS proxies. This provides:
- Anonymous browsing and communication
- IP address masking
- Traffic encryption through Tor nodes
- Bypass of geographic restrictions

## Project Structure

```
toralizer/
├── README.md                   # This file
├── IMPLEMENTATION_GUIDE.md     # Detailed implementation steps
├── Makefile                    # Build system
├── toralizer.c                 # Main toralizer implementation
├── socks.c                     # SOCKS protocol implementation
├── socks.h                     # SOCKS protocol headers
├── network.c                   # Network utilities
├── network.h                   # Network headers
└── solutions/                  # Complete reference implementations
    ├── README.md
    ├── toralizer.c
    ├── socks.c
    └── network.c
```

## Features

### Core Functionality

**SOCKS Protocol Support**:
- SOCKS4 protocol implementation
- SOCKS5 protocol with authentication
- Proxy handshake and connection establishment
- IPv4 and domain name resolution

**Connection Management**:
- TCP connection interception
- Socket creation and binding
- Connection forwarding/proxying
- Bidirectional data relay

**Tor Integration**:
- Connect to local Tor daemon (default: 127.0.0.1:9050)
- Route connections through SOCKS proxy
- Handle Tor-specific responses
- Support for .onion addresses

**Command-line Interface**:
- Specify target host and port
- Configure Tor proxy settings
- Verbose output for debugging
- Error handling and reporting

## Quick Start

### Prerequisites

- GCC or Clang compiler
- Make build system
- Tor daemon running locally (default port 9050)
- Basic understanding of C and networking

### Installing Tor

**Linux (Ubuntu/Debian)**:
```bash
sudo apt-get install tor
sudo systemctl start tor
```

**macOS**:
```bash
brew install tor
brew services start tor
```

**Verify Tor is running**:
```bash
# Check if Tor is listening on port 9050
netstat -an | grep 9050
```

### Building

```bash
make            # Build the toralizer
make clean      # Clean build artifacts
```

### Usage

#### Basic Usage

Route a connection through Tor:
```bash
./toralizer www.example.com 80
```

#### Advanced Usage

Specify custom Tor proxy:
```bash
./toralizer -p 127.0.0.1:9050 www.example.com 80
```

Verbose mode:
```bash
./toralizer -v www.example.com 80
```

Connect to .onion address:
```bash
./toralizer 3g2upl4pq6kufc4m.onion 80  # DuckDuckGo onion
```

## Learning Path

### Phase 1: Socket Programming Basics (1-2 hours)
**Goal**: Understand low-level networking

1. Learn socket creation and connection
2. Implement `create_socket()` function
3. Implement `connect_to_server()` function
4. Test basic TCP connection
5. Handle errors and timeouts

**Skills learned**:
- BSD sockets API
- TCP/IP protocol basics
- Error handling in network code
- System calls (socket, connect, send, recv)

### Phase 2: SOCKS Protocol (2-3 hours)
**Goal**: Implement SOCKS proxy protocol

1. Study SOCKS4 protocol specification
2. Implement SOCKS4 handshake
3. Implement connection request
4. Parse SOCKS responses
5. Add SOCKS5 support (optional)

**Skills learned**:
- Protocol design and implementation
- Binary data formatting
- Byte ordering (network vs host)
- Protocol handshaking

### Phase 3: Proxy Connection (2-3 hours)
**Goal**: Route connections through proxy

1. Connect to Tor SOCKS proxy
2. Send SOCKS connect request
3. Verify connection establishment
4. Forward data between client and destination
5. Handle connection errors

**Skills learned**:
- Proxy architecture
- Connection forwarding
- Bidirectional communication
- Error propagation

### Phase 4: Data Relay (1-2 hours)
**Goal**: Forward traffic bidirectionally

1. Implement non-blocking I/O
2. Use select() or poll() for multiplexing
3. Forward data from source to destination
4. Forward responses back to source
5. Handle disconnections gracefully

**Skills learned**:
- I/O multiplexing
- Non-blocking sockets
- Event-driven programming
- Buffer management

### Phase 5: Advanced Features (2-3 hours)
**Goal**: Add robustness and features

1. Add command-line argument parsing
2. Implement verbose logging
3. Add authentication support
4. Support domain name resolution
5. Add .onion address support
6. Improve error messages

**Skills learned**:
- Command-line interfaces
- DNS resolution
- Authentication mechanisms
- Production-ready error handling

**Total Time**: ~8-13 hours for complete implementation

## Implementation Details

### SOCKS4 Protocol

SOCKS4 handshake format:
```
Client → Proxy: 
[VER=4][CMD][DSTPORT][DSTIP][USERID][NULL]

Proxy → Client:
[VER=0][STATUS][DSTPORT][DSTIP]
```

### SOCKS5 Protocol (Advanced)

SOCKS5 handshake:
```
1. Client greeting:
   [VER=5][NMETHODS][METHODS]

2. Server choice:
   [VER=5][METHOD]

3. Connection request:
   [VER=5][CMD][RSV=0][ATYP][DST.ADDR][DST.PORT]

4. Server response:
   [VER=5][REP][RSV=0][ATYP][BND.ADDR][BND.PORT]
```

### Architecture

```
┌──────────┐         ┌──────────┐         ┌──────────┐
│  Client  │ ──────> │Toralizer │ ──────> │   Tor    │
│ (You)    │         │  (Proxy) │         │  Daemon  │
└──────────┘         └──────────┘         └──────────┘
                           │
                           │ SOCKS Protocol
                           ▼
                     ┌──────────┐         ┌──────────┐
                     │   Tor    │ ──────> │  Target  │
                     │ Network  │         │  Server  │
                     └──────────┘         └──────────┘
```

## Testing

### Manual Testing

Test with simple HTTP request:
```bash
# Start toralizer
./toralizer www.google.com 80

# In another terminal, send HTTP request
echo -e "GET / HTTP/1.0\r\n\r\n" | nc localhost 8080
```

### Verification

Check if your IP is masked:
```bash
# Without Tor
curl https://check.torproject.org/api/ip

# With Toralizer
curl --proxy socks5://127.0.0.1:9050 https://check.torproject.org/api/ip
```

### Test with Real Services

```bash
# Test with HTTP
./toralizer www.example.com 80

# Test with HTTPS (will show encrypted traffic)
./toralizer www.google.com 443

# Test with .onion address
./toralizer 3g2upl4pq6kufc4m.onion 80
```

## Troubleshooting

### Common Issues

**"Connection refused" error**:
- Ensure Tor daemon is running: `systemctl status tor`
- Check Tor is listening: `netstat -an | grep 9050`
- Try: `tor` in terminal to start manually

**"SOCKS protocol error"**:
- Verify SOCKS version (4 or 5)
- Check byte ordering (use htons/htonl)
- Ensure proper null termination in SOCKS4

**"Timeout connecting to target"**:
- Target server may be down
- .onion address may be unreachable
- Tor circuit building may take time (wait 10-30 seconds)

**"Permission denied" on port binding**:
- Ports < 1024 require root privileges
- Use ports >= 1024 or run with sudo

## Advanced Topics

After completing the basic toralizer, explore:

### Protocol Extensions
- SOCKS5 authentication methods
- UDP relay support
- IPv6 support
- BIND and UDP ASSOCIATE commands

### Performance
- Connection pooling
- Asynchronous I/O with epoll/kqueue
- Multi-threading for concurrent connections
- Buffer optimization

### Security
- SSL/TLS inspection
- DNS leak prevention
- WebRTC leak protection
- Traffic analysis resistance

### Features
- HTTP CONNECT proxy support
- Transparent proxying with iptables
- PAC (Proxy Auto-Config) file support
- Bridge and pluggable transport support

## Documentation

### Specifications
- [SOCKS4 Protocol](https://www.openssh.com/txt/socks4.protocol)
- [SOCKS5 RFC 1928](https://www.ietf.org/rfc/rfc1928.txt)
- [Tor SOCKS Extensions](https://gitweb.torproject.org/torspec.git/tree/socks-extensions.txt)

### Resources
- [Tor Project Documentation](https://www.torproject.org/docs/documentation.html)
- [Beej's Guide to Network Programming](https://beej.us/guide/bgnet/)
- [Linux Socket Programming](https://man7.org/linux/man-pages/man7/socket.7.html)

### Video Courses
- [Computer Networks Courses](https://github.com/Developer-Y/cs-video-courses#computer-networks)
- [Security Courses](https://github.com/Developer-Y/cs-video-courses#security)
- [Systems Programming](https://github.com/Developer-Y/cs-video-courses#systems-programming)

## Security Notes

⚠️ **Important**: This is an educational project. For real anonymity needs, use:
- Official Tor Browser
- Tails OS
- Whonix

This implementation:
- May have security vulnerabilities
- May not prevent all types of traffic correlation
- Should not be relied upon for critical privacy needs
- Is intended for learning purposes only

## License

Educational purposes. Use freely for learning.

## Acknowledgments

Inspired by:
- The Tor Project
- proxychains and torsocks
- "TCP/IP Illustrated" by W. Richard Stevens
- Various SOCKS proxy implementations

## Sources

- **RFC 1928** — SOCKS5, and it is short. The handshake is §3, the request format §4.
- Dingledine, Mathewson & Syverson, **"Tor: The Second-Generation Onion Router"**, USENIX Security 2004 — what a real onion router does that a proxy does not.

Full list: [`../../REFERENCES.md`](../../REFERENCES.md#week-1314--sockets-and-protocols)
