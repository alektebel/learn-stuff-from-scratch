# DNS Server From Scratch

This directory contains a from-scratch implementation of a DNS (Domain Name System) server in C.

## Goal
Build a DNS server to understand:
- DNS protocol specification (RFC 1035)
- UDP networking and packet handling
- Binary data parsing and encoding
- DNS query/response format
- Name resolution process
- DNS records and resource types
- Network byte order (big-endian)

## Learning Path
1. **UDP Server** - Set up socket to receive DNS queries
2. **DNS Packet Parser** - Parse DNS query messages
3. **DNS Message Format** - Understand header, questions, answers sections
4. **Name Compression** - Handle DNS label compression
5. **DNS Response Builder** - Construct DNS response packets
6. **Resource Records** - Support A, AAAA, NS, CNAME, MX records
7. **Recursive Resolution** - Forward queries to upstream DNS servers
8. **Caching** - Implement TTL-based caching
9. **Zone Files** - Read and serve records from zone files
10. **DNSSEC** - Add security extensions (advanced)

## DNS Protocol Basics

### DNS Message Structure
```
+---------------------+
|   Header (12 bytes) |
+---------------------+
|   Question Section  |
+---------------------+
|   Answer Section    |
+---------------------+
|   Authority Section |
+---------------------+
|   Additional Section|
+---------------------+
```

### DNS Header Format (12 bytes)
- Transaction ID (2 bytes)
- Flags (2 bytes): QR, Opcode, AA, TC, RD, RA, Z, RCODE
- Question Count (2 bytes)
- Answer Count (2 bytes)
- Authority Count (2 bytes)
- Additional Count (2 bytes)

### Common DNS Record Types
- **A**: IPv4 address (type 1)
- **NS**: Name server (type 2)
- **CNAME**: Canonical name (type 5)
- **MX**: Mail exchange (type 15)
- **AAAA**: IPv6 address (type 28)

## Features to Implement

### Basic Features
- UDP socket server on port 53
- Parse DNS query messages
- Extract domain names with label parsing
- Build DNS response messages
- Support A record lookups
- Handle multiple questions per query

### Intermediate Features
- Name compression/decompression
- Support multiple record types (A, AAAA, NS, CNAME, MX)
- Implement proper DNS header flags
- Handle query classes (IN for Internet)
- Error responses (NXDOMAIN, SERVFAIL)

### Advanced Features
- Recursive resolution with upstream DNS servers
- TTL-based caching mechanism
- Zone file parsing and serving
- Concurrent query handling
- DNS forwarding and proxying
- Rate limiting and security

## Building and Testing

```bash
# Build the DNS server
make

# Run the DNS server (requires root/sudo for port 53)
sudo ./dns_server

# Test with dig (in another terminal)
dig @127.0.0.1 example.com

# Test with nslookup
nslookup example.com 127.0.0.1
```

## Resources

- RFC 1035: Domain Names - Implementation and Specification
- RFC 1034: Domain Names - Concepts and Facilities
- DNS message format: https://www.ietf.org/rfc/rfc1035.txt
- Network byte order: Use htons(), ntohs(), htonl(), ntohl()

## Security Considerations

- Validate message lengths to prevent buffer overflows
- Limit response size to prevent amplification attacks
- Implement query rate limiting
- Sanitize domain names to prevent cache poisoning
- Use DNSSEC for authenticated responses (advanced)

## Common Pitfalls

1. **Byte Order**: DNS uses network byte order (big-endian)
2. **Name Compression**: DNS names can use pointers for compression
3. **Label Length**: Each label is max 63 bytes, full name max 255 bytes
4. **UDP Size**: Standard DNS messages should fit in 512 bytes
5. **Null Terminator**: DNS names end with a zero-length label

## Next Steps

After building a basic DNS server, consider:
- Adding IPv6 support
- Implementing authoritative DNS server with zone files
- Building a DNS resolver library
- Adding DNSSEC validation
- Creating a DNS proxy/forwarder
- Implementing DoH (DNS over HTTPS) or DoT (DNS over TLS)

## Video Courses & Resources

**Computer Networks**:
- [Computer Networks Courses](https://github.com/Developer-Y/cs-video-courses#computer-networks)
- [Systems Programming Courses](https://github.com/Developer-Y/cs-video-courses#systems-programming)

**Additional Resources**:
- [DNS RFC 1035](https://tools.ietf.org/html/rfc1035)
- [DNSSEC Overview](https://www.cloudflare.com/dns/dnssec/how-dnssec-works/)

## Sources

- **RFC 1035** — the wire format, §4 for the message structure and the pointer compression scheme that trips everyone up.
- **RFC 1034** — the concepts, if 1035 reads like a byte layout with no explanation.
- **RFC 7766** — DNS over TCP, for the truncation-and-retry path.

Full list: [`../../REFERENCES.md`](../../REFERENCES.md#week-1314--sockets-and-protocols)
