# HTTP Server - Complete Solution

This directory contains a complete, working implementation of an HTTP/1.1 server in C.

## Overview

This solution demonstrates a minimal but functional HTTP server that:
- Accepts TCP connections on a specified port
- Parses HTTP GET requests
- Serves static files from a `public/` directory
- Returns proper HTTP responses with status codes and headers
- Handles errors gracefully with 404 and 400 responses
- Includes basic security against path traversal attacks

## Files

- **http_server.c** - Complete HTTP/1.1 server implementation (~275 lines)

## Building and Running

```bash
# Compile
gcc -o http_server http_server.c -Wall -Wextra

# Run on default port (8080)
./http_server

# Run on custom port
./http_server 3000

# The server will create a 'public' directory if it doesn't exist
```

## Testing

### Quick Test
```bash
# In one terminal
cd solutions/
./http_server 8080

# In another terminal
curl http://localhost:8080/
```

### With Test Files
```bash
# Create test content
cd solutions/
mkdir -p public
echo "<h1>Hello, World!</h1>" > public/index.html
echo "body { font-family: Arial; }" > public/style.css

# Start server
./http_server 8080

# Test in browser or with curl
curl http://localhost:8080/
curl http://localhost:8080/style.css
```

You can also copy the test files from the parent directory:
```bash
cp -r ../public/* ./public/
```

## Code Walkthrough

### 1. Server Socket Creation (`create_server_socket`)

```c
int create_server_socket(int port)
```

**What it does**:
- Creates a TCP socket using `socket(AF_INET, SOCK_STREAM, 0)`
- Sets `SO_REUSEADDR` to allow quick restart after crash
- Binds to specified port on all network interfaces (`INADDR_ANY`)
- Starts listening for connections

**Key concepts**:
- **Socket file descriptor**: Like a file, but for network I/O
- **AF_INET**: IPv4 address family
- **SOCK_STREAM**: TCP (connection-oriented, reliable)
- **SO_REUSEADDR**: Prevents "Address already in use" errors
- **INADDR_ANY**: Listen on all network interfaces (0.0.0.0)
- **htons()**: Converts port to network byte order (big-endian)

**Common mistakes**:
- Forgetting `SO_REUSEADDR` makes development painful
- Not checking return values (all syscalls can fail!)
- Using `INADDR_LOOPBACK` limits access to localhost only

### 2. HTTP Request Parsing (`parse_http_request`)

```c
HttpRequest* parse_http_request(const char* request)
```

**What it does**:
- Parses the HTTP request line (first line of request)
- Extracts: HTTP method, path, and protocol version
- Returns a struct with these fields

**HTTP Request Format**:
```
GET /index.html HTTP/1.1\r\n
Host: localhost:8080\r\n
User-Agent: curl/7.68.0\r\n
\r\n
```

The first line is the **request line**:
- **Method**: GET, POST, PUT, DELETE, etc.
- **Path**: URL path (what resource is requested)
- **Version**: HTTP/1.0, HTTP/1.1, HTTP/2

**Key concepts**:
- `sscanf()` for simple parsing (real parsers are more complex)
- HTTP uses CRLF (`\r\n`) line endings
- The request line must have exactly 3 space-separated parts

**Why not parse headers?**
- Basic GET requests don't require headers for functionality
- Headers are important for: cookies, auth, content negotiation
- Left as an exercise for enhancement

### 3. File Reading (`read_file`)

```c
char* read_file(const char* filepath, size_t* file_size)
```

**What it does**:
- Opens a file with `open()`
- Gets file size with `fstat()`
- Allocates buffer and reads entire file
- Returns buffer and size (via pointer parameter)

**Key concepts**:
- **File descriptors**: Integer handles for open files
- **fstat()**: Gets file metadata (size, permissions, type)
- **Dynamic allocation**: File size unknown at compile time
- **Error handling**: Returns NULL on any failure

**Why not use stdio.h (fopen, fread)?**
- Lower-level syscalls give more control
- Matches the style of socket operations
- Understanding `open()` and `read()` is more fundamental
- Both approaches are valid

**Security consideration**:
- Always check file size before allocating
- Large files can cause memory exhaustion
- Production servers use streaming or memory mapping

### 4. Content Type Detection (`get_content_type`)

```c
const char* get_content_type(const char* filepath)
```

**What it does**:
- Determines MIME type from file extension
- Returns appropriate `Content-Type` header value

**Supported types**:
- `.html`, `.htm` → `text/html`
- `.css` → `text/css`
- `.js` → `application/javascript`
- `.json` → `application/json`
- `.txt` → `text/plain`
- `.jpg`, `.jpeg` → `image/jpeg`
- `.png` → `image/png`
- `.gif` → `image/gif`
- `.svg` → `image/svg+xml`
- Unknown → `application/octet-stream` (generic binary)

**Key concepts**:
- **MIME types**: Tell clients how to interpret content
- `text/*` types can be displayed as-is
- `application/*` types may trigger downloads
- Wrong MIME type = browser won't render correctly

**Enhancement ideas**:
- Use libmagic to detect type from content (not just filename)
- Support more types (PDF, video, audio)
- Read from a configuration file

### 5. HTTP Response (`send_response`)

```c
void send_response(int client_socket, int status_code, 
                   const char* content_type, const char* body, 
                   size_t body_length)
```

**What it does**:
- Builds and sends complete HTTP response
- Includes status line, headers, and body

**HTTP Response Format**:
```
HTTP/1.1 200 OK\r\n
Content-Type: text/html\r\n
Content-Length: 27\r\n
Connection: close\r\n
\r\n
<h1>Hello, World!</h1>
```

**Components**:
1. **Status line**: `HTTP/1.1 200 OK`
   - Protocol version
   - Numeric status code (200, 404, 500, etc.)
   - Text description

2. **Headers**: Key-value pairs
   - `Content-Type`: MIME type of body
   - `Content-Length`: Body size in bytes (required for HTTP/1.1)
   - `Connection: close`: Don't reuse connection

3. **Blank line**: `\r\n\r\n` (separates headers from body)

4. **Body**: The actual content

**Status codes**:
- **200 OK**: Success
- **400 Bad Request**: Malformed request
- **404 Not Found**: File doesn't exist
- **405 Method Not Allowed**: Unsupported method (POST, etc.)
- **500 Internal Server Error**: Server problem

**Key concepts**:
- `snprintf()` for safe string formatting
- Two separate `send()` calls: headers first, then body
- Content-Length is required (tells client how much to read)
- Connection: close simplifies implementation (no keep-alive)

### 6. GET Request Handler (`handle_get_request`)

```c
void handle_get_request(int client_socket, const char* path)
```

**What it does**:
- Maps URL path to filesystem path
- Serves `index.html` for `/` requests
- Reads and serves the file
- Returns 404 if file not found

**Path mapping**:
```
URL path          → Filesystem path
/                 → ./public/index.html
/index.html       → ./public/index.html
/style.css        → ./public/style.css
/images/logo.png  → ./public/images/logo.png
```

**Security: Path Traversal Prevention**

The code uses `realpath()` to prevent path traversal attacks:

```c
// Attacker tries: http://localhost:8080/../../../etc/passwd
// filepath becomes: ./public/../../../etc/passwd
// realpath() resolves to: /etc/passwd (outside public dir)
// We detect this and return 404
```

**How it works**:
1. Construct filepath: `./public` + requested path
2. Call `realpath()` to resolve `.`, `..`, symlinks
3. Check if resolved path is inside public directory
4. If not, return 404 (don't expose filesystem structure)

**Why this matters**:
- Path traversal is a common vulnerability
- Never trust user input in file operations
- Production servers do extensive validation

### 7. Client Handler (`handle_client`)

```c
void handle_client(int client_socket)
```

**What it does**:
- Reads HTTP request from socket
- Parses the request
- Routes to appropriate handler (GET, POST, etc.)
- Sends error responses for bad requests
- Closes connection when done

**Flow**:
1. `recv()` - Read request data from socket
2. Parse request line with `parse_http_request()`
3. Check HTTP method
   - GET → `handle_get_request()`
   - Others → 405 Method Not Allowed
4. Free resources and close socket

**Key concepts**:
- Each connection is handled sequentially (not concurrent)
- Connection is closed after each request (no keep-alive)
- All errors result in proper HTTP error responses

### 8. Main Server Loop (`main`)

```c
int main(int argc, char** argv)
```

**What it does**:
- Parses command-line arguments (port number)
- Creates server socket
- Enters infinite loop to accept connections
- Creates `public/` directory if needed

**The Accept Loop**:
```c
while (1) {
    client_socket = accept(server_socket, ...);
    handle_client(client_socket);
}
```

**How it works**:
1. `accept()` blocks until a client connects
2. Returns new socket for this client
3. `handle_client()` processes one request
4. Loop repeats for next client

**Key concepts**:
- **Blocking I/O**: `accept()` waits for connections
- **Sequential processing**: One client at a time
- **Long-running process**: Server never exits normally
- `Ctrl+C` sends SIGINT to stop server

## Architecture Decisions

### Sequential vs Concurrent

This implementation handles connections **sequentially** (one at a time):

**Pros**:
- Simple, easy to understand
- No race conditions or synchronization needed
- Sufficient for learning and low-traffic scenarios

**Cons**:
- One slow client blocks all others
- Can't utilize multiple CPU cores
- Not suitable for production

**Alternatives**:
1. **Fork**: Create child process per connection
2. **Threads**: Create thread per connection (pthread)
3. **Event loop**: `select()`, `poll()`, `epoll()` for multiplexing
4. **Async I/O**: Non-blocking sockets with state machines

### HTTP/1.0 vs HTTP/1.1

This server supports **HTTP/1.1** requests but:
- No persistent connections (Connection: close)
- No chunked transfer encoding
- No range requests
- Minimal header parsing

**Why HTTP/1.1?**
- Modern browsers send HTTP/1.1 requests
- Compatible with HTTP/1.0 clients too
- Easy to extend with more features

### Memory Management

The server uses **dynamic allocation** for:
- File contents (size unknown at compile time)
- Request structs (returned from parse function)

**Best practices**:
- Every `malloc()` needs a corresponding `free()`
- Check all allocation return values
- Use valgrind to detect leaks: `valgrind --leak-check=full ./http_server`

## Common Issues and Solutions

### "Address already in use" Error

**Problem**: Can't start server after stopping it

**Cause**: TCP sockets enter TIME_WAIT state for 60 seconds after close

**Solution**: Already implemented with `SO_REUSEADDR`
```c
setsockopt(server_socket, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));
```

### Browser Shows Garbled Content

**Problem**: Text appears as gibberish or downloads instead of displaying

**Cause**: Wrong Content-Type header

**Solution**: Check `get_content_type()` returns correct MIME type for the file

### CSS/JS Not Loading

**Problem**: HTML loads but CSS/JS don't apply

**Cause**: Wrong paths, missing files, or CORS issues

**Debugging**:
1. Check browser console (F12) for 404 errors
2. Verify paths in HTML match filesystem
3. Check server logs for requested paths
4. Use browser Network tab to see requests

### Server Hangs After One Connection

**Problem**: Server stops responding after first request

**Cause**: Forgot to close client socket

**Solution**: Always close in `handle_client()` (already done in solution)

### File Not Found Despite Correct Path

**Problem**: File exists but server returns 404

**Possible causes**:
1. Server running in wrong directory
2. File permissions (server can't read)
3. Case sensitivity (linux: `Index.html` ≠ `index.html`)

**Debugging**:
```bash
# Check current directory
pwd

# Check file permissions
ls -la public/

# Run server with explicit path
cd /path/to/http-server/solutions
./http_server
```

## Testing Checklist

- [ ] Server starts without errors
- [ ] Can access http://localhost:8080/ in browser
- [ ] index.html is served for `/` and `/index.html`
- [ ] CSS file loads and styles apply
- [ ] JavaScript file loads and executes
- [ ] 404 returned for non-existent files
- [ ] Content-Type headers are correct
- [ ] Path traversal blocked (try `curl http://localhost:8080/../http_server.c`)
- [ ] Server recovers from bad requests
- [ ] Can restart server quickly (SO_REUSEADDR works)

## Performance Testing

```bash
# Install Apache Bench
sudo apt-get install apache2-utils  # Ubuntu/Debian
brew install httpd                   # macOS

# Run load test
ab -n 10000 -c 100 http://localhost:8080/

# Explanation:
# -n 10000: Send 10,000 requests total
# -c 100: Use 100 concurrent connections
```

**Expected results** (sequential server):
- Slow (handles one at a time)
- No failures if implemented correctly
- Good for learning, bad for production

**Compare with nginx**:
```bash
# Start nginx
nginx

# Test nginx
ab -n 10000 -c 100 http://localhost:80/

# Typically 10-100x faster than sequential server
```

## Enhancement Ideas

### Easy (1-2 hours each)
1. **Logging**: Log all requests to a file with timestamp
2. **MIME types**: Add support for more file types
3. **Default files**: Try index.htm, index.html, default.html in order
4. **Stats endpoint**: `/stats` shows request count, uptime
5. **Custom 404 page**: Serve `public/404.html` for not found

### Medium (3-5 hours each)
1. **POST handling**: Accept and log POST request bodies
2. **Query parameters**: Parse and use URL query strings
3. **Request headers**: Parse and use headers (Host, User-Agent, etc.)
4. **Configuration file**: Load settings from config.txt
5. **Signal handling**: Graceful shutdown on SIGTERM/SIGINT
6. **Directory listing**: Show files in directory if no index.html

### Hard (1-2 days each)
1. **Threading**: Use pthread to handle connections concurrently
2. **epoll**: Use epoll for high-performance event loop
3. **Keep-alive**: Support persistent connections
4. **HTTPS**: Add TLS/SSL with OpenSSL
5. **HTTP/2**: Implement HTTP/2 protocol
6. **Compression**: Gzip compression for text files
7. **Range requests**: Support resumable downloads
8. **Proxy mode**: Forward requests to backend servers

## Further Reading

### Books
- "Unix Network Programming" by W. Richard Stevens (Volume 1)
- "TCP/IP Illustrated" by W. Richard Stevens
- "HTTP: The Definitive Guide" by David Gourley

### Online Resources
- [Beej's Guide to Network Programming](https://beej.us/guide/bgnet/)
- [RFC 7230: HTTP/1.1 Message Syntax](https://tools.ietf.org/html/rfc7230)
- [High Performance Browser Networking](https://hpbn.co/)

### Similar Projects
- [Build Your Own Web Server (Python)](https://ruslanspivak.com/lsbaws-part1/)
- [Let's code a web server from scratch](https://medium.com/from-the-scratch/http-server-what-do-you-need-to-know-to-build-a-simple-http-server-from-scratch-d1ef8945e4fa)
- Study nginx, Apache httpd, lighttpd source code

## Next Steps

After understanding this solution:

1. **Implement it yourself** without looking at solution
2. **Add features** from enhancement ideas above
3. **Compare performance** with production servers
4. **Learn async I/O** (this is how fast servers work)
5. **Build a framework** - add routing, middleware, templates

The goal isn't to build a production server - it's to understand how they work! 🚀
