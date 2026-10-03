# Firewall Solution - Detailed Walkthrough

This directory contains a complete, working implementation of the packet filtering firewall.

## Solution Overview

The solution implements a basic packet filtering firewall with the following features:

- **Raw Socket Packet Capture**: Captures all packets at the link layer
- **Multi-Protocol Support**: Parses Ethernet, IPv4, TCP, UDP, and ICMP
- **Rule-Based Filtering**: Implements flexible firewall rules
- **First-Match Wins**: Rules are evaluated in order
- **Statistics Tracking**: Counts packets, bytes, and drops
- **Graceful Shutdown**: Handles Ctrl+C cleanly

## Architecture

### Core Components

1. **Packet Capture**
   - Uses `AF_PACKET` raw socket
   - Captures at Ethernet layer
   - Can bind to specific interface

2. **Protocol Parsing**
   - Ethernet frame parsing (MAC addresses, EtherType)
   - IP header parsing (addresses, protocol, TTL)
   - Transport layer parsing (TCP, UDP, ICMP)

3. **Rule Engine**
   - Stores rules in array
   - Matches packet fields against rules
   - First matching rule determines action

4. **Statistics**
   - Tracks packets received/accepted/dropped
   - Tracks total bytes
   - Calculates drop rate

### Data Flow

```
Network Interface
       ↓
Raw Socket (recvfrom)
       ↓
Ethernet Frame
       ↓
IP Packet
       ↓
TCP/UDP/ICMP
       ↓
Rule Matching
       ↓
ACCEPT or DROP
       ↓
Update Statistics
```

## Key Implementation Details

### 1. Raw Socket Creation

```c
int sock = socket(AF_PACKET, SOCK_RAW, htons(ETH_P_ALL));
```

- `AF_PACKET`: Access to link layer (Ethernet)
- `SOCK_RAW`: Raw packet access
- `ETH_P_ALL`: Capture all protocol types
- Requires root/CAP_NET_RAW capability

**Interface Binding**:
- Uses `ioctl(SIOCGIFINDEX)` to get interface index
- Binds socket with `struct sockaddr_ll`
- Optional: can capture on all interfaces

### 2. Protocol Parsing

**Layer-by-Layer Parsing**:

```
buffer[0] → Ethernet Header (14 bytes)
  ├─ Destination MAC (6 bytes)
  ├─ Source MAC (6 bytes)
  └─ EtherType (2 bytes)

buffer[14] → IP Header (20+ bytes)
  ├─ Version, IHL (1 byte)
  ├─ TOS (1 byte)
  ├─ Total Length (2 bytes)
  ├─ ID, Flags, Offset (4 bytes)
  ├─ TTL (1 byte)
  ├─ Protocol (1 byte)
  ├─ Checksum (2 bytes)
  ├─ Source IP (4 bytes)
  └─ Destination IP (4 bytes)

buffer[14 + IP_HDR_LEN] → TCP/UDP/ICMP Header
```

**Pointer Arithmetic**:
- Ethernet: `(struct ethhdr*)buffer`
- IP: `(struct iphdr*)(buffer + sizeof(struct ethhdr))`
- TCP: `(struct tcphdr*)(buffer + eth_len + ip_len)`

**Byte Order Conversion**:
- All multi-byte fields in network byte order (big-endian)
- Use `ntohs()` for 16-bit, `ntohl()` for 32-bit
- IP addresses: use `inet_ntoa()` for display

### 3. Rule Matching Algorithm

**Wildcard Matching**:
- IP "0.0.0.0" matches any IP
- Port 0 matches any port
- Protocol PROTO_ANY matches any protocol

**Match Logic** (AND of all conditions):
```
IF (rule.src_ip == "0.0.0.0" OR rule.src_ip == packet.src_ip)
AND (rule.dst_ip == "0.0.0.0" OR rule.dst_ip == packet.dst_ip)
AND (rule.src_port == 0 OR rule.src_port == packet.src_port)
AND (rule.dst_port == 0 OR rule.dst_port == packet.dst_port)
AND (rule.protocol == PROTO_ANY OR rule.protocol == packet.protocol)
THEN
   Apply rule.action
```

**First-Match-Wins**:
- Rules checked in order (index 0 to rule_count-1)
- First matching rule determines action
- Remaining rules not evaluated
- If no match, default policy applies (ACCEPT)

### 4. Actions

**ACCEPT**:
- Packet is allowed through
- Increment `packets_accepted` counter
- Continue normal processing

**DROP**:
- Packet is blocked
- Increment `packets_dropped` counter
- Log the drop (optional)

**LOG** (optional):
- Packet is logged but allowed
- Useful for monitoring suspicious traffic
- Then continues as ACCEPT

### 5. Statistics Tracking

**Counters**:
- `packets_received`: Total packets captured
- `packets_accepted`: Packets allowed
- `packets_dropped`: Packets blocked
- `bytes_received`: Total bytes processed

**Drop Rate Calculation**:
```c
float drop_rate = (packets_dropped * 100.0) / packets_received;
```

## Code Organization

### Main Function Flow

1. **Initialization**
   - Parse command-line arguments
   - Set up signal handler (SIGINT for Ctrl+C)
   - Initialize default rules
   - Create raw socket
   - Allocate packet buffer

2. **Main Loop**
   - Receive packet with `recvfrom()`
   - Process packet
   - Update statistics
   - Repeat until shutdown signal

3. **Cleanup**
   - Print final statistics
   - Free buffer
   - Close socket
   - Exit gracefully

### Error Handling

**Socket Errors**:
```c
if (sock < 0) {
    perror("Socket creation failed");
    return 1;
}
```

**Receive Errors**:
```c
if (data_size < 0) {
    if (running) {  // Don't error during shutdown
        perror("Receive failed");
    }
    break;
}
```

**Allocation Errors**:
```c
if (!buffer) {
    perror("Buffer allocation failed");
    close(sock);
    return 1;
}
```

## Example Rules

### Block All ICMP (Ping)

```c
add_rule("0.0.0.0", "0.0.0.0", 0, 0, PROTO_ICMP, ACTION_DROP);
```

**Effect**: No ping requests or replies

**Test**:
```bash
ping 8.8.8.8  # Will timeout
```

### Block SSH (Port 22)

```c
add_rule("0.0.0.0", "0.0.0.0", 0, 22, PROTO_TCP, ACTION_DROP);
```

**Effect**: Cannot SSH to any host

**Test**:
```bash
ssh user@host  # Connection will timeout
```

### Block Specific IP

```c
add_rule("192.168.1.100", "0.0.0.0", 0, 0, PROTO_ANY, ACTION_DROP);
```

**Effect**: All traffic from 192.168.1.100 blocked

### Allow Only HTTP and HTTPS

```c
// Note: Would need default DROP policy
add_rule("0.0.0.0", "0.0.0.0", 0, 80, PROTO_TCP, ACTION_ACCEPT);
add_rule("0.0.0.0", "0.0.0.0", 0, 443, PROTO_TCP, ACTION_ACCEPT);
add_rule("0.0.0.0", "0.0.0.0", 0, 0, PROTO_ANY, ACTION_DROP);
```

**Effect**: Only HTTP and HTTPS allowed, everything else dropped

## Performance Considerations

### Bottlenecks

1. **Console Output**: Heavy printf() slows processing
   - Solution: Rate-limit output or disable in production

2. **Linear Rule Search**: O(n) for n rules
   - Solution: Hash tables for O(1) lookup
   - Solution: Rule compilation/optimization

3. **Packet Copying**: Data copied from kernel to userspace
   - Solution: Use BPF to filter in kernel
   - Solution: Minimize processing in userspace

### Optimizations

**Reduce Output**:
```c
// Only print every Nth packet
if (stats.packets_received % 100 == 0) {
    // Print packet info
}
```

**Early Exit**:
```c
// Check most common rules first
// Exit rule loop on first match
```

**Efficient Data Structures**:
```c
// Use hash table for IP lookups
// Use binary search for port ranges
```

## Security Considerations

### Input Validation

**Packet Size**:
```c
if (size < sizeof(struct ethhdr) + sizeof(struct iphdr)) {
    // Too small, drop
    return;
}
```

**Header Bounds**:
```c
if (iph->ihl < 5 || iph->ihl > 15) {
    // Invalid header length
    return;
}
```

### Buffer Safety

**Use Safe Functions**:
```c
strncpy(rule->src_ip, src_ip, MAX_IP_STR - 1);
rule->src_ip[MAX_IP_STR - 1] = '\0';  // Ensure null termination
```

**Check Buffer Overflows**:
```c
if (offset + header_size > size) {
    // Would read beyond buffer
    return;
}
```

### Privilege Dropping

**After Socket Creation**:
```c
// Create socket (requires root)
int sock = create_raw_socket(interface);

// Drop privileges
setuid(getuid());
setgid(getgid());
```

## Limitations

This implementation is educational and has limitations:

1. **No State Tracking**: Doesn't track TCP connections
2. **No Fragmentation Handling**: Can't reassemble fragmented packets
3. **IPv4 Only**: No IPv6 support
4. **No NAT**: Can't modify or rewrite packets
5. **Userspace**: Slower than kernel-based filtering (iptables/nftables)
6. **No BPF**: Captures all packets, not pre-filtered
7. **Linear Rules**: Doesn't scale to thousands of rules
8. **No Logging**: No persistent log files
9. **No Configuration**: Rules hardcoded, no config file
10. **Default ACCEPT**: Not secure for production

## Extending the Firewall

### Feature Ideas

1. **Connection Tracking**
   - Maintain TCP state table
   - Allow ESTABLISHED/RELATED
   - Track UDP pseudo-connections

2. **CIDR Support**
   - Parse 192.168.1.0/24 notation
   - Match IP ranges efficiently

3. **Configuration File**
   - Parse rules from file (like iptables-restore)
   - Hot-reload rules without restart

4. **Logging System**
   - Write dropped packets to file
   - Syslog integration
   - Rate-limited logging

5. **Rate Limiting**
   - Packets per second per source
   - Token bucket algorithm
   - Prevent DoS attacks

6. **Deep Packet Inspection**
   - Inspect payload for patterns
   - Protocol validation (HTTP, DNS)
   - Application-layer filtering

7. **NAT/Masquerading**
   - Source NAT (SNAT)
   - Destination NAT (DNAT)
   - Port forwarding

8. **IPv6 Support**
   - Dual-stack filtering
   - IPv6 header parsing
   - ICMPv6 handling

9. **BPF Filters**
   - Kernel-space pre-filtering
   - Reduce packets to userspace
   - Berkeley Packet Filter

10. **Management Interface**
    - Web UI for rule management
    - CLI tool (like iptables)
    - REST API

## Comparison with iptables

| Feature | This Firewall | iptables |
|---------|--------------|----------|
| Location | Userspace | Kernel (Netfilter) |
| Speed | Slower | Very Fast |
| Rules | Array, O(n) | Hash tables, O(1) |
| State | None | Full conntrack |
| NAT | No | Yes |
| IPv6 | No | Yes (ip6tables) |
| Config | Hardcoded | iptables-save/restore |
| Logging | Printf | syslog/ulog |

## Building and Testing

### Build

```bash
cd solutions/
make
```

### Run

```bash
# Run with all interfaces
sudo ./firewall

# Run on specific interface
sudo ./firewall eth0
```

### Test

See [TESTING_GUIDE.md](../TESTING_GUIDE.md) for comprehensive tests.

**Quick Test**:
```bash
# Terminal 1
sudo ./firewall

# Terminal 2
ping 8.8.8.8
curl http://example.com
```

## Troubleshooting

**No packets seen**:
- Check interface name
- Generate traffic: `ping 8.8.8.8`
- Try without interface parameter

**Permission denied**:
- Run with sudo
- Or: `sudo setcap cap_net_raw+ep ./firewall`

**Compilation errors**:
- Install build tools: `sudo apt-get install build-essential`
- Check Linux headers: `sudo apt-get install linux-headers-$(uname -r)`

## Learning Resources

- [RFC 791 - Internet Protocol](https://tools.ietf.org/html/rfc791)
- [RFC 793 - TCP](https://tools.ietf.org/html/rfc793)
- [Beej's Guide to Network Programming](https://beej.us/guide/bgnet/)
- [Linux Packet Filtering HOWTO](https://www.netfilter.org/documentation/)

## Conclusion

This solution provides a working packet filtering firewall that demonstrates:
- Low-level network programming
- Packet parsing and protocol understanding
- Rule-based filtering logic
- Systems programming in C

While not suitable for production, it's an excellent learning tool for understanding how firewalls work at a fundamental level.

For production use, always use established solutions like:
- iptables/nftables (Linux)
- pf (OpenBSD/FreeBSD)
- Windows Firewall
- Commercial firewalls (Cisco ASA, Palo Alto, etc.)
