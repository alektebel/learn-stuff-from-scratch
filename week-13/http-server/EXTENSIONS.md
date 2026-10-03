# HTTP Server - Extension Ideas

This document provides ideas for extending the basic HTTP server with additional features and functionality.

## Easy Extensions (1-3 hours each)

### 1. Request Logging

Add logging of all requests to a file.

**What to log**:
- Timestamp
- Client IP address
- HTTP method
- Request path
- Status code
- Response size
- User-Agent

**Example log format**:
```
2024-02-07 15:30:45 | 127.0.0.1 | GET /index.html | 200 | 1234 bytes | curl/7.68.0
```

**Implementation hints**:
- Open log file in append mode: `open("access.log", O_WRONLY | O_CREAT | O_APPEND, 0644)`
- Get timestamp: `time()` and `strftime()`
- Flush after each write for reliability
- Consider log rotation (daily files, size limits)

---

### 2. Custom 404 Page

Serve a custom 404.html page instead of plain text error.

**Steps**:
1. Create an attractive `public/404.html` (already exists!)
2. In `handle_get_request()`, when file not found:
   - Try to read `public/404.html`
   - If exists, serve it with 404 status
   - Otherwise, fall back to plain text

**Challenge**: Make sure the Content-Type is `text/html`

---

### 3. Directory Listing

When accessing a directory without index.html, show list of files.

**Example output**:
```html
<html>
<head><title>Index of /images/</title></head>
<body>
<h1>Index of /images/</h1>
<ul>
<li><a href="logo.png">logo.png</a> (1.2 MB)</li>
<li><a href="photo.jpg">photo.jpg</a> (843 KB)</li>
</ul>
</body>
</html>
```

**Implementation hints**:
- Check if path is a directory: `S_ISDIR(st.st_mode)`
- Use `opendir()` and `readdir()` to list files
- Generate HTML dynamically
- Add file sizes with `stat()`

---

### 4. Query Parameter Parsing

Parse URL query strings and make them available.

**Example**: `/search?q=hello&page=2`

**Data structure**:
```c
typedef struct {
    char key[64];
    char value[256];
} QueryParam;

typedef struct {
    QueryParam params[32];
    int count;
} QueryString;
```

**Implementation hints**:
- Split on `?` to separate path from query string
- Split query string on `&`
- Split each part on `=`
- URL-decode values (handle `%20`, `%2B`, etc.)

---

### 5. Basic Authentication

Require username/password to access certain paths.

**HTTP Basic Auth**:
1. Client sends request
2. Server responds: `401 Unauthorized` with `WWW-Authenticate: Basic realm="Restricted"`
3. Browser shows login dialog
4. Client resends with `Authorization: Basic base64(username:password)`
5. Server decodes and checks credentials

**Implementation hints**:
- Parse `Authorization` header
- Base64 decode (implement or use library)
- Compare with hardcoded credentials
- Consider `/admin/` requires auth, `/` is public

---

### 6. ETag Support

Implement ETags for caching.

**How ETags work**:
1. Server generates hash of file content
2. Sends `ETag: "abc123"` header
3. Client caches file with ETag
4. Next request includes `If-None-Match: "abc123"`
5. If file unchanged, server sends `304 Not Modified` (no body)

**Implementation hints**:
- Use MD5 or simple hash of file content + modification time
- Parse `If-None-Match` header
- Send 304 with ETag header but no body

---

### 7. HEAD Method Support

Support HTTP HEAD method (like GET but without body).

**Use case**: Check if file exists without downloading it

**Implementation**:
```c
if (strcmp(req->method, "HEAD") == 0) {
    handle_head_request(client_socket, req->path);
}
```

**Similar to GET but**:
- Send status line and headers
- Don't send the body
- Content-Length should still be accurate

---

### 8. Configuration File

Load settings from `server.conf`.

**Example config**:
```
port=8080
public_dir=./public
log_file=./access.log
max_connections=100
default_file=index.html
enable_directory_listing=true
```

**Implementation hints**:
- Parse line by line: `key=value`
- Use `strtok()` or `strchr()` to split
- Store in a config struct
- Load before creating server socket

---

## Medium Extensions (3-6 hours each)

### 9. POST Request Handling

Accept and process POST requests.

**Form data example**:
```
POST /submit HTTP/1.1
Content-Type: application/x-www-form-urlencoded
Content-Length: 23

name=John&email=j@e.com
```

**Steps**:
1. Check `Content-Length` header
2. Read that many bytes after headers
3. Parse form data (similar to query params)
4. Process or store the data
5. Send response (redirect or JSON)

**JSON example**:
```
POST /api/users HTTP/1.1
Content-Type: application/json
Content-Length: 35

{"name":"John","email":"j@e.com"}
```

**Consider**: Use a JSON library like cJSON or jsmn for parsing

---

### 10. Cookie Support

Set and read cookies.

**Setting cookies** (server to client):
```
Set-Cookie: session_id=abc123; Path=/; HttpOnly
```

**Reading cookies** (client to server):
```
Cookie: session_id=abc123; user_pref=dark_mode
```

**Implementation hints**:
- Parse `Cookie` header
- Split on `;` and `=`
- Store in request struct
- Generate and send `Set-Cookie` headers

**Use case**: Session tracking, user preferences

---

### 11. Compression (gzip)

Compress text responses to save bandwidth.

**How it works**:
1. Client sends: `Accept-Encoding: gzip, deflate`
2. Server compresses body with gzip
3. Server sends: `Content-Encoding: gzip`
4. Client decompresses

**Implementation**:
- Use zlib library: `compress2()`
- Only compress text files (HTML, CSS, JS, JSON)
- Don't compress if already small (<1KB)
- Check `Accept-Encoding` header

**Bandwidth savings**: 60-80% for text files

---

### 12. Range Requests

Support partial content (resumable downloads).

**Example request**:
```
GET /large-file.zip HTTP/1.1
Range: bytes=0-1023
```

**Response**:
```
HTTP/1.1 206 Partial Content
Content-Range: bytes 0-1023/5242880
Content-Length: 1024

[1024 bytes of data]
```

**Implementation hints**:
- Parse `Range` header
- Use `lseek()` to position in file
- Send `206` status with `Content-Range`
- Support multiple ranges (advanced)

**Use cases**: Large file downloads, video streaming

---

### 13. WebSocket Support

Enable real-time bidirectional communication.

**WebSocket handshake**:
1. Client sends Upgrade request with special headers
2. Server responds with 101 Switching Protocols
3. Connection switches to WebSocket protocol
4. Both sides can send/receive messages anytime

**Implementation hints**:
- Parse `Upgrade: websocket` header
- Parse `Sec-WebSocket-Key` and compute accept hash
- Send 101 response
- Implement WebSocket frame parsing
- Keep connection open (no Connection: close)

**Use cases**: Chat apps, live updates, gaming

---

### 14. Multithreading

Handle multiple clients concurrently with threads.

**Using pthreads**:
```c
void* handle_client_thread(void* arg) {
    int client_socket = *(int*)arg;
    free(arg);
    handle_client(client_socket);
    return NULL;
}

// In accept loop:
pthread_t thread;
int* client_sock = malloc(sizeof(int));
*client_sock = client_socket;
pthread_create(&thread, NULL, handle_client_thread, client_sock);
pthread_detach(thread);
```

**Considerations**:
- Thread-safe logging (use mutex)
- Limit concurrent threads
- Memory management (avoid leaks)
- Test with load testing tools

**Performance improvement**: Can handle 100+ concurrent clients

---

### 15. Static File Caching

Cache frequently accessed files in memory.

**Simple LRU cache**:
```c
typedef struct {
    char path[256];
    char* content;
    size_t size;
    time_t last_used;
} CacheEntry;

CacheEntry cache[128];
int cache_size = 0;
```

**Implementation**:
1. Before reading file, check cache
2. If found and not stale, return cached version
3. If not found, read file and add to cache
4. Implement LRU eviction when cache full

**Performance improvement**: 10-100x faster for cached files

---

## Advanced Extensions (1-3 days each)

### 16. HTTPS with OpenSSL

Add TLS/SSL encryption.

**Steps**:
1. Install OpenSSL development libraries
2. Initialize SSL context
3. Load certificate and private key
4. Use SSL_accept() instead of accept()
5. Use SSL_read/SSL_write instead of recv/send

**Generating self-signed cert**:
```bash
openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
```

**Resources**: OpenSSL documentation, examples online

---

### 17. HTTP/2 Support

Implement modern HTTP/2 protocol.

**HTTP/2 features**:
- Binary protocol (not text)
- Multiplexing (multiple requests on one connection)
- Server push
- Header compression (HPACK)
- Stream prioritization

**Complexity**: High - consider using nghttp2 library

**Benefits**: Significantly faster page loads

---

### 18. Reverse Proxy

Forward requests to backend servers.

**Use case**: Frontend server proxies to backend APIs

**Example**:
```
Client -> Your Server :80 -> Backend :3000
                          -> Backend :3001
```

**Implementation**:
1. Accept client request
2. Create new connection to backend
3. Forward request to backend
4. Read backend response
5. Forward response to client

**Features to add**:
- Load balancing (round-robin, least connections)
- Health checks
- Connection pooling

---

### 19. CGI Script Execution

Run external programs to generate dynamic content.

**CGI (Common Gateway Interface)**:
1. Server receives request for `/cgi-bin/script.py`
2. Server forks and executes script
3. Script reads environment variables (QUERY_STRING, etc.)
4. Script writes response to stdout
5. Server sends script output to client

**Environment variables to set**:
- REQUEST_METHOD
- QUERY_STRING
- CONTENT_LENGTH
- HTTP_USER_AGENT

**Challenges**: Security (input validation), process management

---

### 20. Server-Sent Events (SSE)

Push updates from server to client.

**Example**:
```
GET /events HTTP/1.1

HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache

data: {"message": "Hello"}\n\n
data: {"message": "World"}\n\n
```

**Implementation**:
- Keep connection open
- Send events as they occur
- Format: `data: ...\n\n`
- Client JavaScript uses EventSource API

**Use cases**: Live notifications, stock tickers, chat

---

### 21. Rate Limiting

Prevent abuse by limiting request rate.

**Token bucket algorithm**:
- Each client has N tokens
- Each request consumes 1 token
- Tokens refill at rate R per second
- Reject requests when tokens = 0

**Implementation**:
```c
typedef struct {
    char ip[16];
    int tokens;
    time_t last_refill;
} RateLimit;
```

**Response**: `429 Too Many Requests` when limit exceeded

---

### 22. Event Loop with epoll

High-performance event-driven architecture.

**epoll (Linux)**:
- Register file descriptors (sockets) for events
- `epoll_wait()` blocks until events occur
- Handle events (new connection, data ready, etc.)
- Single-threaded but handles thousands of connections

**Advantages over threads**:
- Less memory (no stack per connection)
- No context switching overhead
- Better cache locality

**Complexity**: High - requires state machines

**Similar**: kqueue (BSD/macOS), IOCP (Windows)

---

### 23. Virtual Hosting

Serve different sites based on Host header.

**Example**:
```
GET / HTTP/1.1
Host: site1.example.com
-> Serve from /var/www/site1/

GET / HTTP/1.1
Host: site2.example.com
-> Serve from /var/www/site2/
```

**Implementation**:
1. Parse `Host` header
2. Map hostname to directory
3. Serve files from that directory

**Config example**:
```
[site1.example.com]
root=/var/www/site1
index=index.html

[site2.example.com]
root=/var/www/site2
index=home.html
```

---

### 24. Load Balancer

Distribute requests across multiple backend servers.

**Algorithms**:
- **Round-robin**: Rotate through servers
- **Least connections**: Send to server with fewest active connections
- **IP hash**: Same client always goes to same server (sticky sessions)
- **Weighted**: Some servers get more traffic

**Health checking**:
- Periodically ping backends
- Remove unhealthy servers from pool
- Add back when healthy

**Implementation challenge**: Connection management, error handling

---

### 25. Full Web Application

Build a complete web app on top of your server.

**Example: Todo List App**

**Backend** (C):
- GET /api/todos - List all todos (JSON)
- POST /api/todos - Create new todo
- PUT /api/todos/:id - Update todo
- DELETE /api/todos/:id - Delete todo
- Data stored in SQLite database

**Frontend** (HTML/JS):
- Single-page app with JavaScript
- Fetch API to call backend
- Dynamic DOM updates

**Technologies to integrate**:
- SQLite for database
- jsmn or cJSON for JSON parsing
- Template engine for HTML generation

---

## Learning Path Recommendations

**Beginner** → Easy extensions (1-8)  
**Intermediate** → Medium extensions (9-15)  
**Advanced** → Advanced extensions (16-25)

Start with extensions that interest you most. Don't feel obligated to do them all - pick what aligns with your learning goals!

## Resources

### Libraries
- **cJSON**: JSON parsing
- **SQLite**: Embedded database  
- **OpenSSL**: TLS/SSL
- **zlib**: Compression
- **pthread**: Threading
- **nghttp2**: HTTP/2

### Learning Materials
- *Unix Network Programming* by Stevens
- *The Linux Programming Interface* by Kerrisk
- HTTP RFCs: 7230-7235
- nginx source code (production example)

### Tools
- **valgrind**: Memory leak detection
- **gdb**: Debugging
- **strace**: System call tracing
- **perf**: Performance profiling
- **wireshark**: Network packet analysis

## Contributing Your Extensions

If you implement cool extensions:
1. Document your implementation
2. Add tests
3. Share with others learning
4. Compare approaches with production servers

Happy coding! 🚀
