# Toralizer Implementation Guide

This guide provides step-by-step instructions for implementing a Toralizer that routes TCP connections through the Tor network using SOCKS proxies.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Phase 1: Basic Socket Programming](#phase-1-basic-socket-programming)
3. [Phase 2: SOCKS Protocol Implementation](#phase-2-socks-protocol-implementation)
4. [Phase 3: Tor Proxy Connection](#phase-3-tor-proxy-connection)
5. [Phase 4: Data Relay](#phase-4-data-relay)
6. [Phase 5: Advanced Features](#phase-5-advanced-features)
7. [Testing and Validation](#testing-and-validation)

## Prerequisites

### Knowledge Requirements
- C programming (pointers, structs, memory management)
- Basic networking concepts (TCP/IP, client-server model)
- Unix/Linux system calls
- Command-line tools (gcc, make, netcat)

### System Requirements
- Linux or macOS
- GCC or Clang compiler
- Tor daemon installed and running
- Standard C library (libc)

### Install Tor

```bash
# Ubuntu/Debian
sudo apt-get install tor
sudo systemctl start tor

# macOS
brew install tor
brew services start tor

# Verify Tor is running
netstat -an | grep 9050
```

## Phase 1: Basic Socket Programming

### Goal
Understand and implement basic TCP socket operations.

### Step 1.1: Create Socket

Implement socket creation:

```c
int create_socket() {
    // TODO: Create a TCP socket using socket()
    // Use AF_INET for IPv4 and SOCK_STREAM for TCP
    // Return the socket file descriptor or -1 on error
}
```

**Key concepts**:
- `socket(AF_INET, SOCK_STREAM, 0)` creates a TCP socket
- Returns a file descriptor (integer)
- Always check for errors (return value < 0)

### Step 1.2: Connect to Server

Implement connection establishment:

```c
int connect_to_server(int sock, const char* host, int port) {
    // TODO: Fill struct sockaddr_in with server address
    // TODO: Convert hostname to IP address (use gethostbyname or getaddrinfo)
    // TODO: Set port number (use htons for byte ordering)
    // TODO: Call connect() to establish connection
    // Return 0 on success, -1 on error
}
```

**Key concepts**:
- `struct sockaddr_in` holds address and port
- `htons()` converts port to network byte order
- `gethostbyname()` resolves hostname to IP
- `connect()` establishes TCP connection

### Step 1.3: Test Basic Connection

Create a simple test:

```c
int main() {
    int sock = create_socket();
    if (sock < 0) {
        perror("Socket creation failed");
        return 1;
    }
    
    if (connect_to_server(sock, "www.google.com", 80) < 0) {
        perror("Connection failed");
        return 1;
    }
    
    printf("Connected successfully!\n");
    close(sock);
    return 0;
}
```

**Testing**:
```bash
gcc -o test test.c
./test
# Should print: "Connected successfully!"
```

## Phase 2: SOCKS Protocol Implementation

### Goal
Implement SOCKS4 protocol for proxy communication.

### Step 2.1: Understand SOCKS4 Protocol

SOCKS4 request format:
```
Byte 0: VER (version = 4)
Byte 1: CMD (1 = CONNECT)
Byte 2-3: DSTPORT (destination port, network byte order)
Byte 4-7: DSTIP (destination IP, network byte order)
Byte 8+: USERID (null-terminated string, can be empty)
Byte N: NULL (0x00)
```

SOCKS4 response format:
```
Byte 0: VER (version = 0)
Byte 1: STATUS (90 = granted, 91 = rejected)
Byte 2-3: (ignored)
Byte 4-7: (ignored)
```

### Step 2.2: Create SOCKS4 Request

```c
int socks4_connect(int sock, const char* dest_host, int dest_port) {
    // TODO: Create SOCKS4 request buffer
    unsigned char request[9 + strlen(userid) + 1];
    
    // TODO: Fill request buffer
    // request[0] = 4;  // SOCKS version
    // request[1] = 1;  // CONNECT command
    // ... set port and IP
    
    // TODO: Send request to proxy
    // send(sock, request, sizeof(request), 0);
    
    // TODO: Receive response
    // recv(sock, response, 8, 0);
    
    // TODO: Check if connection granted (response[1] == 90)
    // Return 0 on success, -1 on failure
}
```

**Implementation steps**:

1. Create request buffer (9 bytes minimum + userid)
2. Set SOCKS version (4)
3. Set command (1 for CONNECT)
4. Set destination port (network byte order)
5. Set destination IP address
6. Add null-terminated userid (can be empty)
7. Send request via send()
8. Receive 8-byte response
9. Check status byte (90 = success)

### Step 2.3: Handle Hostname Resolution

For SOCKS4a (hostname support):

```c
// If dest_host is a hostname (not IP):
// Use SOCKS4a extension:
// - Set IP to 0.0.0.x (x != 0)
// - Append hostname after userid and null byte
```

**SOCKS4a format**:
```
[VER][CMD][DSTPORT][0.0.0.x][USERID][NULL][HOSTNAME][NULL]
```

### Step 2.4: Test SOCKS Connection

```c
int main() {
    // Connect to local Tor SOCKS proxy
    int sock = create_socket();
    connect_to_server(sock, "127.0.0.1", 9050);
    
    // Try SOCKS4 connection
    if (socks4_connect(sock, "www.example.com", 80) == 0) {
        printf("SOCKS connection established!\n");
    }
    
    close(sock);
    return 0;
}
```

## Phase 3: Tor Proxy Connection

### Goal
Route connections through Tor using the SOCKS proxy.

### Step 3.1: Connect to Tor Proxy

```c
int connect_via_tor(const char* dest_host, int dest_port) {
    // TODO: Create socket
    int sock = create_socket();
    
    // TODO: Connect to Tor SOCKS proxy (127.0.0.1:9050)
    if (connect_to_server(sock, "127.0.0.1", 9050) < 0) {
        return -1;
    }
    
    // TODO: Establish SOCKS connection to destination
    if (socks4_connect(sock, dest_host, dest_port) < 0) {
        close(sock);
        return -1;
    }
    
    // Now socket is connected to destination via Tor
    return sock;
}
```

### Step 3.2: Send HTTP Request

Test the connection:

```c
int sock = connect_via_tor("www.example.com", 80);
if (sock < 0) {
    fprintf(stderr, "Failed to connect\n");
    return 1;
}

// Send HTTP request
const char* request = 
    "GET / HTTP/1.0\r\n"
    "Host: www.example.com\r\n"
    "\r\n";

send(sock, request, strlen(request), 0);

// Receive response
char buffer[4096];
int bytes = recv(sock, buffer, sizeof(buffer) - 1, 0);
buffer[bytes] = '\0';
printf("%s\n", buffer);

close(sock);
```

### Step 3.3: Test with .onion Address

```c
// Test with DuckDuckGo onion service
int sock = connect_via_tor("3g2upl4pq6kufc4m.onion", 80);
// Send HTTP request as above
```

## Phase 4: Data Relay

### Goal
Implement bidirectional data forwarding.

### Step 4.1: Understand I/O Multiplexing

Use `select()` to monitor multiple sockets:

```c
fd_set read_fds;
FD_ZERO(&read_fds);
FD_SET(sock1, &read_fds);
FD_SET(sock2, &read_fds);

int max_fd = (sock1 > sock2) ? sock1 : sock2;

select(max_fd + 1, &read_fds, NULL, NULL, NULL);

if (FD_ISSET(sock1, &read_fds)) {
    // Data available on sock1
}
if (FD_ISSET(sock2, &read_fds)) {
    // Data available on sock2
}
```

### Step 4.2: Implement Relay Function

```c
void relay_data(int client_sock, int server_sock) {
    // TODO: Loop until connection closed
    while (1) {
        fd_set read_fds;
        FD_ZERO(&read_fds);
        FD_SET(client_sock, &read_fds);
        FD_SET(server_sock, &read_fds);
        
        int max_fd = (client_sock > server_sock) ? 
                     client_sock : server_sock;
        
        // TODO: Wait for data on either socket
        if (select(max_fd + 1, &read_fds, NULL, NULL, NULL) < 0) {
            break;
        }
        
        // TODO: Forward data from client to server
        if (FD_ISSET(client_sock, &read_fds)) {
            // Read from client, write to server
        }
        
        // TODO: Forward data from server to client
        if (FD_ISSET(server_sock, &read_fds)) {
            // Read from server, write to client
        }
    }
}
```

### Step 4.3: Handle Connection Closure

```c
int bytes = recv(sock, buffer, sizeof(buffer), 0);
if (bytes <= 0) {
    // Connection closed or error
    if (bytes == 0) {
        printf("Connection closed\n");
    } else {
        perror("recv error");
    }
    return -1;
}
```

### Step 4.4: Complete Forwarding

```c
int forward_data(int from_sock, int to_sock) {
    char buffer[4096];
    int bytes = recv(from_sock, buffer, sizeof(buffer), 0);
    
    if (bytes <= 0) {
        return -1;  // Connection closed
    }
    
    int sent = 0;
    while (sent < bytes) {
        int n = send(to_sock, buffer + sent, bytes - sent, 0);
        if (n <= 0) {
            return -1;
        }
        sent += n;
    }
    
    return bytes;
}
```

## Phase 5: Advanced Features

### Goal
Add command-line interface and robustness.

### Step 5.1: Command-line Argument Parsing

```c
int main(int argc, char* argv[]) {
    const char* tor_host = "127.0.0.1";
    int tor_port = 9050;
    const char* dest_host = NULL;
    int dest_port = 0;
    int verbose = 0;
    
    // TODO: Parse arguments
    // -p <proxy_host:port>  Set Tor proxy
    // -v                     Verbose mode
    // <host> <port>         Destination
    
    for (int i = 1; i < argc; i++) {
        if (strcmp(argv[i], "-p") == 0 && i + 1 < argc) {
            // Parse proxy address
        } else if (strcmp(argv[i], "-v") == 0) {
            verbose = 1;
        } else {
            // Positional arguments
        }
    }
    
    // Validate arguments
    if (!dest_host || dest_port == 0) {
        fprintf(stderr, "Usage: %s [-p proxy:port] [-v] <host> <port>\n", 
                argv[0]);
        return 1;
    }
}
```

### Step 5.2: Add Verbose Logging

```c
void log_verbose(int verbose, const char* format, ...) {
    if (!verbose) return;
    
    va_list args;
    va_start(args, format);
    vfprintf(stderr, format, args);
    va_end(args);
}

// Usage:
log_verbose(verbose, "Connecting to Tor proxy %s:%d\n", 
            tor_host, tor_port);
```

### Step 5.3: Error Handling

```c
#define CHECK_ERROR(condition, message) \
    do { \
        if (condition) { \
            perror(message); \
            return -1; \
        } \
    } while(0)

// Usage:
int sock = socket(AF_INET, SOCK_STREAM, 0);
CHECK_ERROR(sock < 0, "socket creation failed");
```

### Step 5.4: Signal Handling

```c
#include <signal.h>

volatile sig_atomic_t running = 1;

void signal_handler(int signum) {
    running = 0;
}

int main() {
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);
    
    while (running) {
        // Main loop
    }
    
    // Cleanup
}
```

## Testing and Validation

### Unit Tests

Test individual functions:

```bash
# Test socket creation
gcc -DTEST_SOCKET -o test_socket network.c
./test_socket

# Test SOCKS protocol
gcc -DTEST_SOCKS -o test_socks socks.c network.c
./test_socks
```

### Integration Tests

Test complete flow:

```bash
# Test with HTTP
./toralizer www.example.com 80
# In another terminal:
curl http://localhost:8080/

# Test with HTTPS (will show encrypted data)
./toralizer www.google.com 443

# Test with .onion
./toralizer 3g2upl4pq6kufc4m.onion 80
```

### Verification

Check if using Tor:

```bash
# Check your IP without Tor
curl https://check.torproject.org/api/ip

# Check through Tor
curl --socks5 127.0.0.1:9050 https://check.torproject.org/api/ip
```

### Performance Testing

```bash
# Measure latency
time curl --socks5 127.0.0.1:9050 http://www.example.com/

# Multiple connections
for i in {1..10}; do
    ./toralizer www.example.com 80 &
done
wait
```

## Debugging Tips

### Common Issues

1. **"Connection refused"**
   - Check if Tor is running: `systemctl status tor`
   - Verify port: `netstat -an | grep 9050`

2. **"SOCKS protocol error"**
   - Print request bytes in hex: `printf("%02x ", byte)`
   - Check byte ordering: use `htons()`, `htonl()`

3. **Timeout errors**
   - Tor circuit building takes time
   - Increase timeout: `setsockopt(SO_RCVTIMEO)`

4. **Data corruption**
   - Check send/recv return values
   - Ensure complete data transfer

### Debug Output

Add debug printing:

```c
void print_hex(const char* label, unsigned char* data, int len) {
    printf("%s: ", label);
    for (int i = 0; i < len; i++) {
        printf("%02x ", data[i]);
    }
    printf("\n");
}

// Usage:
print_hex("SOCKS Request", request, sizeof(request));
```

### Use strace

```bash
strace -e trace=network ./toralizer www.example.com 80
```

## Next Steps

After completing the toralizer:

1. **Add SOCKS5 support** - More features and authentication
2. **Implement HTTP proxy** - Support CONNECT method
3. **Add transparent proxying** - Use iptables for system-wide
4. **Create GUI** - User-friendly interface
5. **Performance optimization** - Async I/O, connection pooling

## Resources

### Specifications
- [SOCKS4 Protocol](https://www.openssh.com/txt/socks4.protocol)
- [SOCKS5 RFC 1928](https://www.ietf.org/rfc/rfc1928.txt)
- [Tor SOCKS Extensions](https://gitweb.torproject.org/torspec.git/tree/socks-extensions.txt)

### Books
- "TCP/IP Illustrated" by W. Richard Stevens
- "Unix Network Programming" by W. Richard Stevens
- "Linux System Programming" by Robert Love

### Online Resources
- [Beej's Guide to Network Programming](https://beej.us/guide/bgnet/)
- [Tor Project Documentation](https://www.torproject.org/docs/)
- [Linux man pages](https://man7.org/linux/man-pages/)

## Conclusion

You now have a complete guide to implementing a Toralizer. Follow the phases sequentially, test thoroughly, and refer to the solutions when needed. Understanding how network proxying works at this level will give you deep insights into network programming and anonymous communication systems.
