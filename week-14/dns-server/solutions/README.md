# DNS Server Solution

This directory contains a complete implementation of a basic DNS server.

## Files

- **dns_server.c** - Complete DNS server implementation

## Building and Running

```bash
cd solutions
gcc -o dns_server dns_server.c
sudo ./dns_server
```

Default port is 53 (requires root/sudo).

You can specify a different port:
```bash
./dns_server 5353  # Non-privileged port
```

## Features

1. **UDP Socket Server**: Listens for DNS queries on port 53
2. **DNS Query Parser**: Parses DNS query messages according to RFC 1035
3. **Domain Name Parsing**: Handles DNS label encoding and compression
4. **DNS Response Builder**: Constructs proper DNS response messages
5. **A Record Resolution**: Resolves domain names to IPv4 addresses
6. **Hardcoded Lookup Table**: Simple domain to IP mapping for testing
7. **Error Handling**: Returns proper error codes (NXDOMAIN, etc.)

## Testing

### Using dig
```bash
# Terminal 1: Start the server
sudo ./dns_server

# Terminal 2: Test queries
dig @127.0.0.1 test.local
dig @127.0.0.1 example.local
dig @127.0.0.1 localhost.local
```

### Using nslookup
```bash
nslookup test.local 127.0.0.1
nslookup example.local 127.0.0.1
```

### Using host
```bash
host test.local 127.0.0.1
host example.local 127.0.0.1
```

## Hardcoded Domains

The solution includes hardcoded mappings for demonstration:
- `test.local` → 192.168.1.100
- `example.local` → 192.168.1.101
- `localhost.local` → 127.0.0.1
- `server.local` → 10.0.0.50

Other domains will return NXDOMAIN (name not found).

## Learning Points

### DNS Protocol
- DNS uses UDP on port 53
- Messages are binary with specific structure
- Network byte order (big-endian) is used throughout
- Domain names use label encoding with optional compression

### DNS Message Format
- **Header**: 12 bytes with transaction ID, flags, and section counts
- **Question**: Variable length with encoded domain name, type, and class
- **Answer**: Variable length resource records with TTL and data
- **Authority**: Nameserver records (not implemented in basic version)
- **Additional**: Extra records (not implemented in basic version)

### Name Encoding
- Each label is prefixed with its length (1 byte)
- Labels are separated (no dots in encoding)
- Name ends with zero-length label (0x00)
- Compression uses 2-byte pointers (starts with 0xC0)

### DNS Flags
- **QR**: Query (0) or Response (1)
- **OPCODE**: Operation (0 = standard query)
- **AA**: Authoritative Answer
- **TC**: Truncation (message too long)
- **RD**: Recursion Desired
- **RA**: Recursion Available
- **RCODE**: Response code (0 = no error, 3 = NXDOMAIN)

### Resource Records
- **A Record**: Type 1, IPv4 address (4 bytes)
- **TTL**: Time To Live in seconds
- **RDLENGTH**: Length of RDATA field
- **RDATA**: Record-specific data

## Code Structure

1. **Socket Creation**: `create_udp_socket()` - Sets up UDP listener
2. **Header Parsing**: `parse_dns_header()` - Extracts DNS header fields
3. **Name Parsing**: `parse_domain_name()` - Decodes DNS names with compression
4. **Question Parsing**: `parse_dns_question()` - Extracts query information
5. **Header Encoding**: `encode_dns_header()` - Builds response header
6. **Name Encoding**: `encode_domain_name()` - Converts to DNS label format
7. **Answer Encoding**: `encode_dns_answer()` - Builds resource records
8. **Response Building**: `create_dns_response()` - Assembles complete response
9. **Query Resolution**: `resolve_query()` - Looks up domain mappings
10. **Main Loop**: Receives queries, processes, and sends responses

## Limitations

This is an educational implementation with limitations:
- Only supports A records (IPv4)
- Hardcoded domain mappings (no zone files)
- No recursive resolution (doesn't forward to upstream DNS)
- No caching mechanism
- Sequential processing (one query at a time)
- Limited error handling
- No DNSSEC support
- Doesn't handle truncation properly

## Enhancements to Explore

1. **More Record Types**: AAAA (IPv6), MX (mail), NS (nameserver), CNAME (alias)
2. **Zone Files**: Read domain mappings from BIND-style zone files
3. **Recursive Resolution**: Forward unknown queries to upstream DNS (8.8.8.8, 1.1.1.1)
4. **Caching**: Store responses with TTL-based expiration
5. **Concurrency**: Use threads or async I/O for multiple simultaneous queries
6. **IPv6 Support**: Handle IPv6 addresses and AAAA records
7. **EDNS0**: Extended DNS for larger messages
8. **Security**: Rate limiting, query validation, DNSSEC
9. **Authoritative Server**: Serve as primary DNS for a domain
10. **DNS Proxy**: Forward all queries while caching responses

## References

- [RFC 1035](https://tools.ietf.org/html/rfc1035) - DNS Implementation Specification
- [RFC 1034](https://tools.ietf.org/html/rfc1034) - DNS Concepts
- [DNS Message Format](https://www2.cs.duke.edu/courses/fall16/compsci356/DNS/DNS-primer.pdf)
- [Guide to DNS](https://www.cloudflare.com/learning/dns/what-is-dns/)

## Debugging Tips

1. **Use Wireshark**: Capture DNS packets to see exact format
2. **Print Hex Dumps**: Display buffer contents in hex
3. **Compare with Real DNS**: Run tcpdump to see actual DNS responses
4. **Start Simple**: Test with one hardcoded domain first
5. **Check Byte Order**: Always use htons/ntohs/htonl/ntohl
6. **Validate Lengths**: Prevent buffer overflows
7. **Test Edge Cases**: Empty names, long names, compressed names

## Sample Output

```
Starting DNS server on port 53...
Note: This is a learning implementation. Use sudo for port 53.
DNS Server listening...

Received query from 127.0.0.1:54321 (45 bytes)
Query ID: 0x1234
Flags: 0x0100 (RD=1)
Questions: 1
Question: test.local, Type: 1, Class: 1
Sent response: 61 bytes

Received query from 127.0.0.1:54322 (47 bytes)
Query ID: 0x5678
Flags: 0x0100 (RD=1)
Questions: 1
Question: unknown.local, Type: 1, Class: 1
Sent NXDOMAIN response: 47 bytes
```
