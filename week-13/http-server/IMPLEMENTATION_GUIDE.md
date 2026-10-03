# HTTP Server - Step-by-Step Implementation Guide

This guide walks you through implementing the HTTP server incrementally, with testing at each step.

## Prerequisites

- Basic C programming knowledge
- Understanding of pointers and memory management
- Familiarity with Unix/Linux command line
- A C compiler (gcc or clang)

## Implementation Steps

### Step 0: Setup and Familiarization (15 minutes)

1. **Examine the template**
```bash
cd http-server
cat http_server.c
```

2. **Read the TODOs**: Each function has a TODO comment explaining what to implement

3. **Try to compile** (it will compile but not work yet)
```bash
make
```

4. **Review HTTP basics**
   - What is an HTTP request?
   - What is an HTTP response?
   - What are status codes?

---

### Step 1: Create Server Socket (1 hour)

**Goal**: Get the server to start and listen on a port

**What to implement**: `create_server_socket()` function

**Steps**:

1. **Create a socket**
```c
int server_socket = socket(AF_INET, SOCK_STREAM, 0);
if (server_socket < 0) {
    perror("socket");
    return -1;
}
```

2. **Set socket options** (allows quick restart)
```c
int opt = 1;
if (setsockopt(server_socket, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt)) < 0) {
    perror("setsockopt");
    close(server_socket);
    return -1;
}
```

3. **Prepare the address structure**
```c
struct sockaddr_in server_addr;
memset(&server_addr, 0, sizeof(server_addr));
server_addr.sin_family = AF_INET;           // IPv4
server_addr.sin_addr.s_addr = INADDR_ANY;   // All interfaces
server_addr.sin_port = htons(port);         // Port in network byte order
```

4. **Bind the socket to the port**
```c
if (bind(server_socket, (struct sockaddr*)&server_addr, sizeof(server_addr)) < 0) {
    perror("bind");
    close(server_socket);
    return -1;
}
```

5. **Start listening**
```c
if (listen(server_socket, MAX_CONNECTIONS) < 0) {
    perror("listen");
    close(server_socket);
    return -1;
}

return server_socket;
```

**Test it**:
```bash
# Compile and run
make
./http_server 8080

# In another terminal, check if it's listening
netstat -an | grep 8080
# or
lsof -i :8080

# Try to connect with telnet
telnet localhost 8080
```

**Expected**: Server starts, you can telnet to it, but nothing happens when you type (that's OK!)

**Common issues**:
- "Address already in use" → Kill other process using port or use different port
- "Permission denied" → Ports below 1024 require root (use port ≥ 1024)

---

### Step 2: Read Incoming Requests (30 minutes)

**Goal**: Print out what clients send to the server

**What to implement**: Basic version of `handle_client()`

**Steps**:

1. **In `handle_client()`, read from socket**:
```c
void handle_client(int client_socket) {
    char buffer[BUFFER_SIZE];
    ssize_t bytes_read = recv(client_socket, buffer, sizeof(buffer) - 1, 0);
    
    if (bytes_read <= 0) {
        close(client_socket);
        return;
    }
    
    buffer[bytes_read] = '\0';  // Null terminate
    printf("Received request:\n%s\n", buffer);
    
    // We'll add response later
    close(client_socket);
}
```

**Test it**:
```bash
# Start server
./http_server 8080

# In another terminal, send a request
curl http://localhost:8080/
```

**Expected**: Server prints the HTTP request curl sent

**What you should see**:
```
Received request:
GET / HTTP/1.1
Host: localhost:8080
User-Agent: curl/7.68.0
Accept: */*

```

**Key observations**:
- Request line: `GET / HTTP/1.1`
- Headers follow
- Empty line marks end of headers
- No body (for GET requests)

---

### Step 3: Parse HTTP Requests (45 minutes)

**Goal**: Extract method, path, and version from request

**What to implement**: `parse_http_request()` function

**Steps**:

1. **Allocate and parse**:
```c
HttpRequest* parse_http_request(const char* request) {
    HttpRequest* req = malloc(sizeof(HttpRequest));
    if (req == NULL) {
        return NULL;
    }
    
    // Parse: METHOD PATH VERSION
    if (sscanf(request, "%15s %255s %15s", req->method, req->path, req->version) != 3) {
        free(req);
        return NULL;
    }
    
    return req;
}
```

2. **Use it in `handle_client()`**:
```c
void handle_client(int client_socket) {
    char buffer[BUFFER_SIZE];
    ssize_t bytes_read = recv(client_socket, buffer, sizeof(buffer) - 1, 0);
    
    if (bytes_read <= 0) {
        close(client_socket);
        return;
    }
    
    buffer[bytes_read] = '\0';
    
    HttpRequest* req = parse_http_request(buffer);
    if (req == NULL) {
        printf("Failed to parse request\n");
        close(client_socket);
        return;
    }
    
    printf("Method: %s, Path: %s, Version: %s\n", 
           req->method, req->path, req->version);
    
    free(req);
    close(client_socket);
}
```

**Test it**:
```bash
# Start server
./http_server 8080

# Test different requests
curl http://localhost:8080/
curl http://localhost:8080/test.html
curl http://localhost:8080/api/users
```

**Expected output**:
```
Method: GET, Path: /, Version: HTTP/1.1
Method: GET, Path: /test.html, Version: HTTP/1.1
Method: GET, Path: /api/users, Version: HTTP/1.1
```

---

### Step 4: Send Basic HTTP Response (1 hour)

**Goal**: Make the server actually respond to requests

**What to implement**: `send_response()` function

**Steps**:

1. **Implement the response builder**:
```c
void send_response(int client_socket, int status_code, const char* content_type, 
                   const char* body, size_t body_length) {
    char header[BUFFER_SIZE];
    const char* status_text;
    
    // Map status code to text
    switch (status_code) {
        case 200: status_text = "OK"; break;
        case 400: status_text = "Bad Request"; break;
        case 404: status_text = "Not Found"; break;
        case 405: status_text = "Method Not Allowed"; break;
        case 500: status_text = "Internal Server Error"; break;
        default: status_text = "Unknown"; break;
    }
    
    // Build header
    int header_len = snprintf(header, sizeof(header),
        "HTTP/1.1 %d %s\r\n"
        "Content-Type: %s\r\n"
        "Content-Length: %zu\r\n"
        "Connection: close\r\n"
        "\r\n",
        status_code, status_text, content_type, body_length);
    
    // Send header
    send(client_socket, header, header_len, 0);
    
    // Send body
    if (body != NULL && body_length > 0) {
        send(client_socket, body, body_length, 0);
    }
}
```

2. **Test it with a simple response**:
```c
void handle_client(int client_socket) {
    char buffer[BUFFER_SIZE];
    ssize_t bytes_read = recv(client_socket, buffer, sizeof(buffer) - 1, 0);
    
    if (bytes_read <= 0) {
        close(client_socket);
        return;
    }
    
    buffer[bytes_read] = '\0';
    
    HttpRequest* req = parse_http_request(buffer);
    if (req == NULL) {
        const char* msg = "400 Bad Request";
        send_response(client_socket, 400, "text/plain", msg, strlen(msg));
        close(client_socket);
        return;
    }
    
    printf("Request: %s %s\n", req->method, req->path);
    
    // Send a test response
    const char* msg = "<h1>Hello from HTTP Server!</h1>";
    send_response(client_socket, 200, "text/html", msg, strlen(msg));
    
    free(req);
    close(client_socket);
}
```

**Test it**:
```bash
# Start server
./http_server 8080

# Test with curl (verbose to see headers)
curl -v http://localhost:8080/

# Test in browser
# Open http://localhost:8080/ in your browser
```

**Expected**: You should see "Hello from HTTP Server!" displayed!

---

### Step 5: Read Files from Disk (1 hour)

**Goal**: Read static files that we'll serve

**What to implement**: `read_file()` function

**Steps**:

1. **Implement file reading**:
```c
char* read_file(const char* filepath, size_t* file_size) {
    int fd = open(filepath, O_RDONLY);
    if (fd < 0) {
        return NULL;
    }
    
    // Get file size
    struct stat st;
    if (fstat(fd, &st) < 0) {
        close(fd);
        return NULL;
    }
    
    *file_size = st.st_size;
    
    // Allocate buffer
    char* buffer = malloc(*file_size);
    if (buffer == NULL) {
        close(fd);
        return NULL;
    }
    
    // Read file
    ssize_t bytes_read = read(fd, buffer, *file_size);
    close(fd);
    
    if (bytes_read < 0 || (size_t)bytes_read != *file_size) {
        free(buffer);
        return NULL;
    }
    
    return buffer;
}
```

2. **Test it standalone**:
```c
// Add this temporary code to test
int main() {
    size_t size;
    char* content = read_file("http_server.c", &size);
    if (content) {
        printf("Read %zu bytes\n", size);
        free(content);
    } else {
        printf("Failed to read file\n");
    }
    return 0;
}
```

---

### Step 6: Detect Content Types (30 minutes)

**Goal**: Return correct MIME types for different files

**What to implement**: `get_content_type()` function

**Steps**:

1. **Implement content type detection**:
```c
const char* get_content_type(const char* filepath) {
    const char* ext = strrchr(filepath, '.');
    if (ext == NULL) {
        return "application/octet-stream";
    }
    
    if (strcmp(ext, ".html") == 0 || strcmp(ext, ".htm") == 0) {
        return "text/html";
    } else if (strcmp(ext, ".css") == 0) {
        return "text/css";
    } else if (strcmp(ext, ".js") == 0) {
        return "application/javascript";
    } else if (strcmp(ext, ".json") == 0) {
        return "application/json";
    } else if (strcmp(ext, ".txt") == 0) {
        return "text/plain";
    } else if (strcmp(ext, ".jpg") == 0 || strcmp(ext, ".jpeg") == 0) {
        return "image/jpeg";
    } else if (strcmp(ext, ".png") == 0) {
        return "image/png";
    } else if (strcmp(ext, ".gif") == 0) {
        return "image/gif";
    } else if (strcmp(ext, ".svg") == 0) {
        return "image/svg+xml";
    }
    
    return "application/octet-stream";
}
```

2. **Test with various filenames**:
```c
printf("%s\n", get_content_type("test.html"));  // text/html
printf("%s\n", get_content_type("style.css"));  // text/css
printf("%s\n", get_content_type("app.js"));     // application/javascript
printf("%s\n", get_content_type("unknown"));    // application/octet-stream
```

---

### Step 7: Handle GET Requests (1.5 hours)

**Goal**: Serve actual files from the filesystem

**What to implement**: `handle_get_request()` function

**Steps**:

1. **Create test files first**:
```bash
mkdir -p public
echo "<h1>Hello World</h1>" > public/index.html
echo "body { background: lightblue; }" > public/style.css
```

2. **Implement the handler**:
```c
void handle_get_request(int client_socket, const char* path) {
    char filepath[512];
    
    // Map URL path to filesystem path
    if (strcmp(path, "/") == 0) {
        snprintf(filepath, sizeof(filepath), "./public/index.html");
    } else {
        snprintf(filepath, sizeof(filepath), "./public%s", path);
    }
    
    // Security: check for path traversal
    char resolved_path[512];
    if (realpath(filepath, resolved_path) == NULL) {
        const char* msg = "404 Not Found";
        send_response(client_socket, 404, "text/plain", msg, strlen(msg));
        return;
    }
    
    // Read file
    size_t file_size;
    char* content = read_file(resolved_path, &file_size);
    
    if (content == NULL) {
        const char* msg = "404 Not Found";
        send_response(client_socket, 404, "text/plain", msg, strlen(msg));
    } else {
        const char* content_type = get_content_type(resolved_path);
        send_response(client_socket, 200, content_type, content, file_size);
        free(content);
    }
}
```

3. **Update `handle_client()` to use it**:
```c
void handle_client(int client_socket) {
    char buffer[BUFFER_SIZE];
    ssize_t bytes_read = recv(client_socket, buffer, sizeof(buffer) - 1, 0);
    
    if (bytes_read <= 0) {
        close(client_socket);
        return;
    }
    
    buffer[bytes_read] = '\0';
    
    HttpRequest* req = parse_http_request(buffer);
    if (req == NULL) {
        const char* msg = "400 Bad Request";
        send_response(client_socket, 400, "text/plain", msg, strlen(msg));
        close(client_socket);
        return;
    }
    
    printf("Request: %s %s\n", req->method, req->path);
    
    // Route based on method
    if (strcmp(req->method, "GET") == 0) {
        handle_get_request(client_socket, req->path);
    } else {
        const char* msg = "405 Method Not Allowed";
        send_response(client_socket, 405, "text/plain", msg, strlen(msg));
    }
    
    free(req);
    close(client_socket);
}
```

**Test it**:
```bash
# Copy the full test files
cp -r public/* ./public/

# Start server
./http_server 8080

# Test various URLs
curl http://localhost:8080/
curl http://localhost:8080/index.html
curl http://localhost:8080/style.css

# Test 404
curl http://localhost:8080/nonexistent.html

# Test in browser
# Open http://localhost:8080/ - you should see styled page!
```

**Expected**:
- `/` and `/index.html` show the HTML content
- `/style.css` returns CSS with `text/css` content type
- Non-existent files return 404
- Browser displays the page with styling applied

---

### Step 8: Final Testing (30 minutes)

**Comprehensive test checklist**:

1. **Basic functionality**:
```bash
# Test root path
curl http://localhost:8080/

# Test explicit index
curl http://localhost:8080/index.html

# Test CSS
curl http://localhost:8080/style.css

# Test JS
curl http://localhost:8080/script.js
```

2. **Error cases**:
```bash
# 404 for non-existent file
curl http://localhost:8080/missing.html

# Path traversal attempt (should get 404)
curl http://localhost:8080/../http_server.c
curl http://localhost:8080/../../etc/passwd
```

3. **Browser test**:
   - Open http://localhost:8080/
   - Verify HTML renders
   - Verify CSS applies
   - Verify JavaScript works (click the button)
   - Open DevTools (F12) and check Network tab
   - Verify all files load with 200 status
   - Try accessing http://localhost:8080/nonexistent (should show 404)

4. **Stress test** (optional):
```bash
# Install Apache Bench
# Ubuntu: sudo apt-get install apache2-utils
# macOS: brew install httpd

# Run load test
ab -n 1000 -c 10 http://localhost:8080/
```

---

## Debugging Tips

### Server won't start
```bash
# Check if port is in use
lsof -i :8080
netstat -an | grep 8080

# Kill process using port
kill -9 <PID>

# Try different port
./http_server 3000
```

### Request not showing up
```bash
# Add debug prints
printf("Waiting for connections...\n");
printf("Accepted client\n");
printf("Received %zd bytes\n", bytes_read);
```

### Files not found
```bash
# Print the resolved path
printf("Looking for: %s\n", filepath);
printf("Resolved to: %s\n", resolved_path);

# Check working directory
pwd

# Check file exists
ls -la public/
```

### Memory leaks
```bash
# Check with valgrind
valgrind --leak-check=full ./http_server 8080

# In another terminal, make a request
curl http://localhost:8080/

# Stop server with Ctrl+C and check valgrind output
```

---

## Congratulations!

You now have a working HTTP server! 

**What you've learned**:
- Socket programming fundamentals
- HTTP protocol structure
- File I/O in C
- String parsing and manipulation
- Error handling
- Memory management

**Next challenges**:
- Add POST request handling
- Implement concurrent connections with threads
- Add HTTPS support
- Parse and use HTTP headers
- Implement caching
- Build a simple web framework on top

Keep experimenting and learning! 🚀
