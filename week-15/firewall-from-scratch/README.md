# Firewall From Scratch

This directory contains a from-scratch implementation of a network firewall in C.

## Overview

Building a firewall is an excellent way to understand network security, packet filtering, and how systems like iptables, pfSense, and commercial firewalls work under the hood. This project will teach you about raw sockets, packet inspection, filtering rules, and network security principles.

## What You'll Learn

- **Raw Socket Programming**: Capturing and analyzing network packets
- **Network Protocols**: IP, TCP, UDP, ICMP packet structures
- **Packet Filtering**: Implementing rules-based packet filtering
- **Network Security**: Common attack patterns and prevention
- **Systems Programming**: Memory management, performance optimization
- **Linux Networking**: Netfilter, iptables integration

## Project Structure

```
firewall-from-scratch/
├── README.md                 # This file - project overview and guide
├── IMPLEMENTATION_GUIDE.md   # 📖 Step-by-step implementation instructions
├── TESTING_GUIDE.md          # 🧪 Comprehensive testing strategies
├── firewall.c                # Template with TODOs for implementation
├── Makefile                  # Build configuration
└── solutions/                # Complete working implementations
    ├── README.md            # Detailed solution walkthrough
    └── firewall.c           # Fully implemented firewall
```

## Quick Start

1. **See it working first** (recommended):
   ```bash
   cd solutions/
   make
   sudo ./firewall
   # Requires root privileges for raw socket access
   ```

2. **Build it yourself**:
   ```bash
   # Read the step-by-step guide
   cat IMPLEMENTATION_GUIDE.md
   
   # Edit the template
   vim firewall.c
   
   # Build and test
   make
   sudo ./firewall
   ```

3. **Test your implementation**:
   ```bash
   # See TESTING_GUIDE.md for comprehensive testing
   ping 8.8.8.8  # Test ICMP filtering
   curl http://example.com  # Test HTTP filtering
   ```

## Learning Path

This project is designed to be implemented incrementally. Follow these steps:

### Phase 1: Raw Socket Basics (2-3 hours)
**Goal**: Capture network packets

1. **Raw Socket Creation**
   - Create a raw socket with `socket(AF_PACKET, SOCK_RAW, htons(ETH_P_ALL))`
   - Understand the difference between raw and regular sockets
   - Requires root/CAP_NET_RAW capability

2. **Packet Reception**
   - Use `recvfrom()` to receive packets
   - Understand the Ethernet frame structure
   - Print basic packet information

3. **Network Interfaces**
   - Bind to specific network interface
   - List available network interfaces
   - Handle multiple interfaces

**Key Concepts**: Raw sockets, packet capture, network interfaces, Ethernet frames

### Phase 2: Protocol Parsing (3-4 hours)
**Goal**: Parse and understand different protocol packets

1. **Ethernet Frame Parsing**
   - Extract source and destination MAC addresses
   - Identify protocol type (IP, ARP, etc.)
   - Understand frame structure

2. **IP Header Parsing**
   - Extract IP version, header length, protocol
   - Parse source and destination IP addresses
   - Calculate and verify IP checksum
   - Handle IPv4 and IPv6

3. **Transport Layer Parsing**
   - TCP: Parse flags, ports, sequence numbers
   - UDP: Parse ports and length
   - ICMP: Parse type and code

**Key Concepts**: Protocol headers, network byte order, checksums, encapsulation

### Phase 3: Basic Packet Filtering (3-4 hours)
**Goal**: Implement simple filtering rules

1. **IP Address Filtering**
   - Block specific IP addresses
   - Allow/deny IP ranges (CIDR notation)
   - Whitelist/blacklist implementation

2. **Port Filtering**
   - Block specific TCP/UDP ports
   - Allow port ranges
   - Common services (HTTP, SSH, DNS)

3. **Protocol Filtering**
   - Allow/deny specific protocols
   - ICMP filtering (ping blocking)
   - Handle protocol-specific rules

**Key Concepts**: ACLs (Access Control Lists), default policies, rule ordering

### Phase 4: Stateful Filtering (4-5 hours)
**Goal**: Track connection states

1. **Connection Tracking**
   - Maintain a connection table
   - Track TCP connection states (SYN, ESTABLISHED, FIN)
   - Handle UDP pseudo-connections
   - Timeout management

2. **State-Based Rules**
   - Allow established connections
   - Block new connections from certain sources
   - Handle related connections (FTP data channel)

3. **Session Management**
   - Connection table cleanup
   - Hash tables for fast lookup
   - Memory management

**Key Concepts**: Stateful vs stateless, connection tracking, NAT-like state

### Phase 5: Advanced Filtering (3-4 hours)
**Goal**: Implement advanced firewall features

1. **Deep Packet Inspection**
   - Inspect packet payload
   - Pattern matching for malicious content
   - Protocol validation

2. **Rate Limiting**
   - Limit packets per second from source
   - Prevent DoS attacks
   - Token bucket algorithm

3. **Logging and Alerts**
   - Log dropped packets
   - Alert on suspicious patterns
   - Statistics and reporting

**Key Concepts**: DPI, rate limiting, intrusion detection, logging

### Phase 6: Rule Management (2-3 hours)
**Goal**: Create a flexible rule configuration system

1. **Rule Parser**
   - Read rules from configuration file
   - Parse rule syntax (iptables-like)
   - Validate rules

2. **Rule Storage**
   - Efficient rule data structures
   - Rule priority and ordering
   - Chain-based organization

3. **Dynamic Updates**
   - Add/remove rules at runtime
   - Rule hot-reloading
   - Rule verification

**Key Concepts**: Configuration parsing, rule engines, DSL design

### Phase 7 (Advanced): NAT and Packet Modification (4-6 hours)
**Goal**: Implement Network Address Translation

Options:
- **SNAT**: Source NAT for outbound traffic
- **DNAT**: Destination NAT for port forwarding
- **Masquerading**: Dynamic NAT for routers
- **Packet rewriting**: Modify packet headers

**Key Concepts**: NAT, packet modification, checksum recalculation

## Firewall Architecture

### Basic Components

```
┌─────────────────────────────────────────┐
│         Network Interface               │
│         (eth0, wlan0, etc.)            │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│      Packet Capture (Raw Socket)        │
│   - Receive all packets on interface   │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│         Protocol Parsing                │
│   - Ethernet, IP, TCP/UDP, ICMP        │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│       Rule Matching Engine              │
│   - Check against firewall rules       │
│   - Evaluate conditions                │
└──────────────┬──────────────────────────┘
               │
        ┌──────┴──────┐
        ▼             ▼
┌─────────────┐  ┌────────────┐
│   ACCEPT    │  │    DROP    │
│  (Forward)  │  │  (Block)   │
└─────────────┘  └────────────┘
```

### Rule Matching Flow

```
Packet arrives
    │
    ▼
┌─────────────────┐
│ Match Rule 1?   │──Yes──► Apply Action
└────┬────────────┘
     │ No
     ▼
┌─────────────────┐
│ Match Rule 2?   │──Yes──► Apply Action
└────┬────────────┘
     │ No
     ▼
    ...
     │
     ▼
┌─────────────────┐
│ Default Policy  │──────► ACCEPT or DROP
└─────────────────┘
```

## Testing Your Firewall

### Basic Testing

```bash
# Test IP blocking
sudo ./firewall --block-ip 192.168.1.100
ping 192.168.1.100  # Should be blocked

# Test port blocking
sudo ./firewall --block-port 80
curl http://example.com  # Should be blocked

# Test protocol blocking
sudo ./firewall --block-icmp
ping 8.8.8.8  # Should be blocked
```

### Using tcpdump

```bash
# Capture packets on interface
sudo tcpdump -i eth0 -n

# Capture specific protocol
sudo tcpdump -i eth0 icmp

# Capture to file
sudo tcpdump -i eth0 -w capture.pcap
```

### Using iptables for Comparison

```bash
# Block an IP
sudo iptables -A INPUT -s 192.168.1.100 -j DROP

# Block a port
sudo iptables -A INPUT -p tcp --dport 80 -j DROP

# List rules
sudo iptables -L -v -n

# Clear all rules
sudo iptables -F
```

### Load Testing

```bash
# hping3 for packet crafting
sudo hping3 -S -p 80 192.168.1.1

# nmap for port scanning
nmap -sS 192.168.1.1

# iperf for bandwidth testing
iperf -c 192.168.1.1
```

## Common Pitfalls

1. **Permissions**
   - Raw sockets require root privileges
   - Use `sudo` or set CAP_NET_RAW capability
   - Security implications of running as root

2. **Byte Order**
   - Network byte order is big-endian
   - Use `ntohs()`, `ntohl()`, `htons()`, `htonl()`
   - Don't mix host and network byte order

3. **Packet Copying**
   - Don't block the entire network
   - Test in isolated environment first
   - Have a way to disable firewall quickly

4. **Performance**
   - Raw socket processing is expensive
   - Use efficient data structures (hash tables)
   - Consider packet filtering in kernel space

5. **Memory Management**
   - Large connection tables can use lots of memory
   - Implement proper cleanup and timeouts
   - Watch for memory leaks with valgrind

6. **Checksum Calculation**
   - Must recalculate checksums after packet modification
   - IP checksum is different from TCP/UDP checksum
   - Incorrect checksums cause packet drops

## Building and Running

```bash
# Build
make

# Run (requires root)
sudo make run

# Run with specific interface
sudo ./firewall -i eth0

# Run with configuration file
sudo ./firewall -c firewall.conf

# Clean build artifacts
make clean

# Run with debugging
sudo ./firewall -v  # Verbose mode
```

## Features to Implement

Core features (in order of difficulty):
- ✅ Raw socket creation
- ✅ Packet capture on network interface
- ✅ Ethernet frame parsing
- ✅ IP header parsing (IPv4)
- ✅ TCP/UDP header parsing
- ✅ ICMP parsing
- ✅ IP address filtering (allow/deny)
- ✅ Port filtering (TCP/UDP)
- ✅ Protocol filtering
- ⬜ Connection tracking (stateful)
- ⬜ Configuration file parsing
- ⬜ Logging system
- ⬜ Rate limiting

Advanced features:
- ⬜ IPv6 support
- ⬜ Deep packet inspection
- ⬜ NAT/SNAT/DNAT
- ⬜ Port forwarding
- ⬜ Application-layer filtering (HTTP, DNS)
- ⬜ IDS/IPS capabilities
- ⬜ GeoIP blocking
- ⬜ Integration with netfilter/nftables

## Resources

### Network Protocols
- [RFC 791: Internet Protocol (IP)](https://tools.ietf.org/html/rfc791)
- [RFC 793: Transmission Control Protocol (TCP)](https://tools.ietf.org/html/rfc793)
- [RFC 768: User Datagram Protocol (UDP)](https://tools.ietf.org/html/rfc768)
- [Ethernet Frame Format](https://en.wikipedia.org/wiki/Ethernet_frame)

### Firewall Concepts
- [Netfilter/iptables Documentation](https://netfilter.org/documentation/)
- [Linux Packet Filtering](https://www.netfilter.org/documentation/HOWTO/packet-filtering-HOWTO.html)
- [pfSense Documentation](https://docs.netfilter.org/)

### Socket Programming
- Beej's Guide to Network Programming
- Unix Network Programming by Stevens
- Linux Socket Filtering (LSF/BPF)

### Similar Projects
- iptables/netfilter
- pfSense
- OpenBSD pf (Packet Filter)
- Cisco ASA
- nftables

## Security Considerations

⚠️ **Important Security Notes**:

1. **Running as Root**
   - Raw sockets require elevated privileges
   - Minimize code running with root privileges
   - Consider dropping privileges after socket creation

2. **Input Validation**
   - Validate all packet data before processing
   - Prevent buffer overflows
   - Sanitize configuration file input

3. **Default Deny**
   - Consider default-deny policy for security
   - Explicitly allow known-good traffic
   - Log denied packets for analysis

4. **Testing Environment**
   - Test in isolated network/VM first
   - Don't lock yourself out
   - Have physical/console access for recovery

5. **Attack Surface**
   - Firewall itself can be target
   - Protect against malformed packets
   - Rate limit to prevent resource exhaustion

## Troubleshooting

**Permission denied**
- Run with `sudo` or as root
- Check capabilities: `getcap ./firewall`
- Set capability: `sudo setcap cap_net_raw+ep ./firewall`

**No packets captured**
- Check network interface is up
- Verify interface name (eth0, wlan0, etc.)
- Check promiscuous mode: `ifconfig eth0 promisc`

**Locked out of system**
- Have console/physical access
- Set timeout for rules to auto-disable
- Test with non-critical services first

**High CPU usage**
- Packet processing is CPU intensive
- Optimize rule matching
- Use BPF filters to reduce packet capture

**Memory leaks**
- Use valgrind: `sudo valgrind ./firewall`
- Properly free connection table entries
- Implement timeout-based cleanup

## Documentation Guide

This project includes comprehensive documentation:

- **[README.md](README.md)** - This file, project overview
- **[IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md)** - Step-by-step coding instructions
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - How to test each feature thoroughly
- **[solutions/README.md](solutions/README.md)** - Detailed code walkthrough

**Recommended reading order**:
1. This README (overview and concepts)
2. IMPLEMENTATION_GUIDE.md (while coding)
3. TESTING_GUIDE.md (for verification)
4. solutions/README.md (to understand complete solution)

## Next Steps

After completing this project:

1. **Integrate with Netfilter** - Use Netfilter hooks instead of raw sockets
2. **Build a GUI** - Create web interface for rule management
3. **Add IDS Features** - Implement intrusion detection capabilities
4. **Study iptables** - Compare with production firewall source code
5. **Implement BPF** - Use Berkeley Packet Filter for performance
6. **Add IPv6** - Full dual-stack support
7. **Create NAT Gateway** - Build a home router

## Video Courses & Resources

**Systems Programming & Networks**:
- [15-213 Introduction to Computer Systems - CMU](https://scs.hosted.panopto.com/Panopto/Pages/Sessions/List.aspx#folderID=%22b96d90ae-9871-4fae-91e2-b1627b43e25e%22&maxResults=150)
- [Computer Networks Courses](https://github.com/Developer-Y/cs-video-courses#computer-networks)
- [Security Courses](https://github.com/Developer-Y/cs-video-courses#security)

**Additional Resources**:
- [TCP/IP Illustrated by Stevens](https://www.amazon.com/TCP-Illustrated-Vol-Addison-Wesley-Professional/dp/0201633469)
- [Wireshark Documentation](https://www.wireshark.org/docs/)
- [Linux Kernel Networking Documentation](https://www.kernel.org/doc/html/latest/networking/)

## License

Educational project for learning purposes.

---

**⚠️ Important Note**: This is an educational project. For production use, rely on established firewall solutions like iptables, nftables, pfSense, or commercial firewalls. This implementation prioritizes learning and understanding over security and performance.

## Sources

- **RFC 791** (IP) and **RFC 793** (TCP) — the headers being parsed, byte by byte.
- The **netfilter/iptables** documentation — for what a production packet filter's rule evaluation looks like, and how it differs from a linear scan.
- Compare with `vpc.py` in week 1: a security group is stateful and a NACL is not, and this directory is where you see why that costs what it costs.

Full list: [`../../REFERENCES.md`](../../REFERENCES.md#week-15--compilers)
