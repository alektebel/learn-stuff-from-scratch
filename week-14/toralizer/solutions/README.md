# Toralizer - Solution Files

This directory contains complete reference implementations for the Toralizer project.

## Files

- **toralizer.c** - Main toralizer program with command-line interface
- **socks.c** - Complete SOCKS4/SOCKS5 protocol implementation
- **socks.h** - SOCKS protocol header definitions
- **network.c** - Network utility functions (socket creation, connection)
- **network.h** - Network function declarations

## Building

```bash
cd solutions/
make
```

## Running

```bash
# Basic usage
./toralizer www.example.com 80

# With verbose output
./toralizer -v www.example.com 80

# Custom Tor proxy
./toralizer -p 127.0.0.1:9050 www.example.com 80

# Connect to .onion address
./toralizer 3g2upl4pq6kufc4m.onion 80
```

## Features

The complete solution includes:

1. **SOCKS4 Protocol** - Full implementation with SOCKS4a hostname support
2. **Socket Programming** - Robust TCP socket handling with error checking
3. **Data Relay** - Bidirectional data forwarding using select()
4. **Command-line Interface** - Flexible argument parsing
5. **Error Handling** - Comprehensive error messages and recovery
6. **Verbose Logging** - Debug output for troubleshooting

## Testing

Test the solution:

```bash
# Start Tor (if not running)
sudo systemctl start tor

# Test HTTP connection
./toralizer www.example.com 80

# Verify through Tor
curl --socks5 127.0.0.1:9050 https://check.torproject.org/api/ip
```

## Learning Points

Study the solution to understand:

- **Network Programming**: Creating and managing TCP sockets
- **Protocol Implementation**: Binary protocol parsing and generation
- **I/O Multiplexing**: Using select() for concurrent socket operations
- **Error Handling**: Robust error checking and user feedback
- **System Programming**: Low-level Unix/Linux system calls

## Architecture

```
toralizer.c (main)
    │
    ├─> network.c (socket operations)
    │   └─> create_socket()
    │   └─> connect_to_server()
    │
    ├─> socks.c (SOCKS protocol)
    │   └─> socks4_connect()
    │   └─> build_socks4_request()
    │   └─> parse_socks4_response()
    │
    └─> relay_data() (data forwarding)
        └─> forward_data()
```

## Code Quality

The solution demonstrates:
- Clean, readable code structure
- Proper memory management (no leaks)
- Comprehensive error handling
- POSIX-compliant system calls
- Well-commented implementation

## Extensions

The solution can be extended with:
- SOCKS5 authentication
- HTTP CONNECT proxy support
- IPv6 support
- Multi-threaded connections
- Configuration file support

## Differences from Template

The solution includes:
- Complete implementation of all TODO sections
- Additional helper functions for clarity
- Enhanced error messages
- Performance optimizations
- Production-ready code structure

## Notes

This is a reference implementation. When learning:
1. Try implementing yourself first
2. Use this to check your approach
3. Understand each function's purpose
4. Don't just copy - learn the concepts
5. Experiment with modifications

## Security Disclaimer

This implementation is for educational purposes. For production anonymity needs, use:
- Official Tor Browser
- Tails or Whonix OS
- Properly configured Tor clients

The solution may have security limitations and should not be relied upon for critical privacy requirements.
