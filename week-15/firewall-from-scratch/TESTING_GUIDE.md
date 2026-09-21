# Firewall Testing Guide

This guide provides comprehensive testing strategies for your packet filtering firewall implementation.

## Table of Contents

1. [Testing Environment Setup](#testing-environment-setup)
2. [Basic Functionality Tests](#basic-functionality-tests)
3. [Protocol-Specific Tests](#protocol-specific-tests)
4. [Rule Matching Tests](#rule-matching-tests)
5. [Performance Tests](#performance-tests)
6. [Security Tests](#security-tests)
7. [Debugging and Troubleshooting](#debugging-and-troubleshooting)

---

## Testing Environment Setup

### Virtual Machine (Recommended)

Test in an isolated environment to avoid blocking your main network:

```bash
# Using VirtualBox or VMware
# Create a Linux VM with bridged networking
# Test firewall inside the VM
```

### Network Namespace (Linux)

Create isolated network environment:

```bash
# Create network namespace
sudo ip netns add test-fw

# Run firewall in namespace
sudo ip netns exec test-fw ./firewall
```

### Safety Precautions

⚠️ **Important**:
- Always have physical/console access when testing
- Test in VM or isolated network first
- Keep a second terminal open to kill the process
- Start with permissive rules (ACCEPT) and gradually make restrictive

---

## Basic Functionality Tests

### Test 1: Socket Creation

**Goal**: Verify raw socket is created successfully

```bash
make
sudo ./firewall
```

**Expected Output**:
```
========================================
  Simple Packet Filtering Firewall
========================================

Capturing on all interfaces
Raw socket created successfully
Firewall is running... (Press Ctrl+C to stop)
```

**What to Check**:
- No error messages
- Process starts without crashing
- Ctrl+C stops the firewall gracefully

---

### Test 2: Packet Capture

**Goal**: Verify firewall captures packets

**Setup**:
```bash
# Terminal 1
sudo ./firewall
```

**Test**:
```bash
# Terminal 2
ping -c 3 8.8.8.8
```

**Expected Output**:
You should see packet information for each ping:
- Ethernet frame (MAC addresses)
- IP header (source/dest IPs)
- ICMP header (type 8 for request, type 0 for reply)

**What to Check**:
- Packets are captured (you see output)
- MAC addresses are displayed correctly
- IP addresses match your machine and 8.8.8.8
- Protocol is identified as ICMP

---

### Test 3: Different Protocols

**Goal**: Verify firewall handles TCP, UDP, and ICMP

**TCP Test**:
```bash
# Terminal 1: Start firewall
sudo ./firewall

# Terminal 2: Generate TCP traffic
curl http://example.com
```

**Expected**: See TCP packets with:
- Source/destination ports
- TCP flags (SYN, ACK, etc.)
- Protocol identified as TCP (6)

**UDP Test**:
```bash
# Terminal 2: Generate UDP traffic (DNS query)
dig @8.8.8.8 google.com
```

**Expected**: See UDP packets with:
- Port 53 (DNS)
- Protocol identified as UDP (17)

**ICMP Test**:
```bash
# Terminal 2: Generate ICMP traffic
ping -c 3 8.8.8.8
```

**Expected**: See ICMP packets with:
- Type 8 (Echo Request)
- Type 0 (Echo Reply)
- Protocol identified as ICMP (1)

---

## Protocol-Specific Tests

### TCP Connection Tracking

**Goal**: Observe full TCP handshake

**Test**:
```bash
# Terminal 1
sudo ./firewall

# Terminal 2
telnet example.com 80
```

**Expected Sequence**:
1. TCP packet with SYN flag (connection request)
2. TCP packet with SYN ACK flags (server response)
3. TCP packet with ACK flag (connection established)
4. Data packets with PSH ACK flags
5. TCP packet with FIN flag (connection close)

**What to Verify**:
- All three-way handshake packets captured
- Sequence numbers increment
- Flags are correctly displayed

---

### UDP Stateless Communication

**Goal**: Verify UDP doesn't have connection state

**Test**:
```bash
# Terminal 1
sudo ./firewall

# Terminal 2: Multiple DNS queries
dig @8.8.8.8 google.com
dig @8.8.8.8 facebook.com
dig @8.8.8.8 github.com
```

**What to Verify**:
- Each query is independent
- No connection state maintained
- Source port changes between queries

---

### ICMP Types

**Goal**: Test different ICMP message types

**Echo Request/Reply**:
```bash
ping -c 3 8.8.8.8
```

**Destination Unreachable**:
```bash
# Ping non-existent host
ping -c 1 192.168.255.255
```

**What to Verify**:
- ICMP type correctly identified
- Different ICMP types handled properly

---

## Rule Matching Tests

### Test 4: Block ICMP (Ping)

**Setup**: Edit `firewall.c` and uncomment in `init_default_rules()`:
```c
add_rule("0.0.0.0", "0.0.0.0", 0, 0, PROTO_ICMP, ACTION_DROP);
```

**Rebuild**:
```bash
make
```

**Test**:
```bash
# Terminal 1
sudo ./firewall

# Terminal 2
ping -c 5 8.8.8.8
```

**Expected Output**:
- Firewall shows ICMP packets with "Action: DROP"
- Ping command gets no response (request timeout)
- Statistics show dropped packets

**Verification**:
```bash
# Ping should fail
ping -c 5 8.8.8.8
# Expected: Request timeout or 100% packet loss
```

---

### Test 5: Block Specific Port

**Setup**: Add rule to block SSH (port 22):
```c
add_rule("0.0.0.0", "0.0.0.0", 0, 22, PROTO_TCP, ACTION_DROP);
```

**Test**:
```bash
# Terminal 1
sudo ./firewall

# Terminal 2: Try to SSH to another machine
ssh user@192.168.1.100
# Or test locally
telnet localhost 22
```

**Expected**:
- SSH connection should be blocked
- Firewall shows dropped TCP packets on port 22
- Connection timeout or refused

**Verify HTTP Still Works**:
```bash
curl http://example.com
# Should work (port 80 not blocked)
```

---

### Test 6: Block Specific IP Address

**Setup**: Add rule to block traffic from specific IP:
```c
// Block all traffic from 8.8.8.8
add_rule("8.8.8.8", "0.0.0.0", 0, 0, PROTO_ANY, ACTION_DROP);
```

**Test**:
```bash
# Terminal 1
sudo ./firewall

# Terminal 2
ping -c 5 8.8.8.8
```

**Expected**:
- Ping requests sent but replies from 8.8.8.8 are dropped
- Firewall shows dropped packets from source IP 8.8.8.8
- No ping responses received

---

### Test 7: Allow Specific Traffic (Whitelist)

**Setup**: Set a default deny policy by blocking all, then allow specific:
```c
// Allow only HTTP (port 80)
add_rule("0.0.0.0", "0.0.0.0", 0, 80, PROTO_TCP, ACTION_ACCEPT);
// Drop everything else would require modifying default policy
```

**Note**: Current implementation has default ACCEPT policy. For true whitelist, you'd need to modify the default in `apply_rules()`.

---

### Test 8: Rule Priority

**Goal**: Verify first matching rule wins

**Setup**: Add conflicting rules:
```c
// Rule 1: Drop ICMP
add_rule("0.0.0.0", "0.0.0.0", 0, 0, PROTO_ICMP, ACTION_DROP);

// Rule 2: Accept from specific IP (should not override rule 1 for ICMP)
add_rule("8.8.8.8", "0.0.0.0", 0, 0, PROTO_ANY, ACTION_ACCEPT);
```

**Test**:
```bash
ping 8.8.8.8
```

**Expected**: ICMP still dropped because Rule 1 matches first.

---

## Performance Tests

### Test 9: High Packet Rate

**Goal**: Test firewall under load

**Using ping flood** (requires root):
```bash
# Terminal 1
sudo ./firewall

# Terminal 2
sudo ping -f 8.8.8.8
# Press Ctrl+C after a few seconds
```

**What to Monitor**:
- CPU usage: `top` or `htop`
- Memory usage
- Packet drop rate
- Response time

**Expected**:
- High CPU usage (this is normal)
- No crashes or hangs
- Statistics show large packet counts

---

### Test 10: Memory Leaks

**Goal**: Verify no memory leaks

**Using Valgrind**:
```bash
make clean
make

# Run with valgrind
sudo valgrind --leak-check=full --show-leak-kinds=all ./firewall

# In another terminal, generate traffic
ping -c 100 8.8.8.8

# Stop firewall (Ctrl+C) and check valgrind output
```

**Expected**:
- No "definitely lost" memory blocks
- All allocated memory freed on exit

---

### Test 11: Long-Running Stability

**Goal**: Verify firewall runs stably over time

**Test**:
```bash
# Start firewall
sudo ./firewall > firewall.log 2>&1 &

# Generate continuous traffic
while true; do
    ping -c 10 8.8.8.8
    curl http://example.com > /dev/null 2>&1
    sleep 5
done

# Let run for several hours
# Monitor: top, memory usage, log size
```

**What to Check**:
- No memory growth over time
- No performance degradation
- No crashes or errors in logs

---

## Security Tests

### Test 12: Path Traversal (Not Applicable)

This firewall doesn't handle file paths, but be aware of:
- Buffer overflow vulnerabilities
- Integer overflow in packet sizes
- Malformed packet handling

---

### Test 13: Malformed Packets

**Goal**: Test firewall with invalid packets

**Using hping3**:
```bash
# Install hping3
sudo apt-get install hping3

# Terminal 1
sudo ./firewall

# Terminal 2: Send malformed packets
# TCP with invalid flags
sudo hping3 -S -F --destport 80 192.168.1.1

# Tiny packets
sudo hping3 -d 0 192.168.1.1

# Fragmented packets
sudo hping3 -f 192.168.1.1
```

**Expected**:
- Firewall doesn't crash
- Handles errors gracefully
- May drop malformed packets

---

### Test 14: DoS Attack Simulation

**Goal**: Test resilience against denial of service

**SYN Flood**:
```bash
# Terminal 1
sudo ./firewall

# Terminal 2
sudo hping3 -S --flood -p 80 192.168.1.1
```

**Expected**:
- High CPU usage
- Firewall continues running
- Statistics show high packet rate
- System remains responsive (to some degree)

---

## Debugging and Troubleshooting

### Enable Verbose Logging

**Modify Code**: Add `-DDEBUG` flag or add debug printf statements:

```c
#ifdef DEBUG
    printf("DEBUG: Processing packet %lu\n", stats.packets_received);
#endif
```

**Compile with Debug**:
```bash
make debug
```

---

### Using tcpdump for Comparison

**Capture same traffic as firewall**:
```bash
# Terminal 1: Run your firewall
sudo ./firewall

# Terminal 2: Run tcpdump
sudo tcpdump -i eth0 -n -v

# Terminal 3: Generate traffic
ping 8.8.8.8
```

**Compare**:
- Verify your firewall sees same packets as tcpdump
- Check header values match
- Verify packet counts match

---

### Using Wireshark

**Visual Analysis**:
```bash
# Capture to file
sudo tcpdump -i eth0 -w capture.pcap

# Open in Wireshark
wireshark capture.pcap
```

**What to Check**:
- Packet structure matches your parsing
- Verify protocol identification
- Check for errors in packet data

---

### Common Issues

**Issue**: No packets captured
**Solution**: 
- Check interface name: `ip link show`
- Try running without interface parameter
- Verify network activity: `ping 8.8.8.8` in another terminal

**Issue**: Permission denied
**Solution**:
- Run with `sudo`
- Or set capability: `sudo setcap cap_net_raw+ep ./firewall`

**Issue**: High CPU usage
**Solution**:
- This is expected with raw packet processing
- Add rate limiting to console output
- Consider using BPF filters

**Issue**: Incomplete packet data
**Solution**:
- Increase BUFFER_SIZE
- Check for truncated packets
- Verify packet size calculations

---

## Test Checklist

Use this checklist to verify your implementation:

- [ ] Firewall compiles without errors
- [ ] Raw socket created successfully
- [ ] Ethernet frames parsed correctly
- [ ] IP headers parsed correctly
- [ ] TCP headers parsed correctly
- [ ] UDP headers parsed correctly
- [ ] ICMP headers parsed correctly
- [ ] Rules can be added
- [ ] ICMP blocking works
- [ ] Port blocking works
- [ ] IP address blocking works
- [ ] Statistics displayed correctly
- [ ] No memory leaks (valgrind)
- [ ] Handles high packet rates
- [ ] Graceful shutdown (Ctrl+C)
- [ ] No crashes with malformed packets

---

## Advanced Testing

### Test with iptables

**Compare behavior**:
```bash
# Test iptables rule
sudo iptables -A INPUT -p icmp -j DROP
ping 8.8.8.8  # Should be blocked

# Clear rule
sudo iptables -F

# Test your firewall
sudo ./firewall  # With ICMP blocking rule
ping 8.8.8.8  # Should be blocked
```

### Network Scanning

**Test with nmap**:
```bash
# Terminal 1
sudo ./firewall

# Terminal 2
nmap -sS localhost  # SYN scan
nmap -sU localhost  # UDP scan
```

**Monitor**:
- See all scan packets
- Verify port detection
- Check rule matching

---

## Performance Benchmarks

### Baseline Measurements

**Without firewall**:
```bash
# Measure ping latency
ping -c 100 8.8.8.8

# Measure throughput
iperf3 -c 192.168.1.100
```

**With firewall**:
```bash
# Terminal 1
sudo ./firewall

# Terminal 2
ping -c 100 8.8.8.8
iperf3 -c 192.168.1.100
```

**Compare**:
- Latency increase
- Throughput reduction
- CPU overhead

---

## Conclusion

Thorough testing ensures your firewall:
- Correctly parses packets
- Applies rules accurately
- Handles edge cases
- Performs acceptably
- Remains stable under load

Remember: This is an educational project. Production firewalls undergo much more rigorous testing including fuzzing, security audits, and compliance verification.
