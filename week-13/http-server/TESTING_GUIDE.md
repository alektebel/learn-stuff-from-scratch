# HTTP Server Testing Guide

This guide provides comprehensive testing strategies for your HTTP server implementation.

## Prerequisites

Make sure your server compiles and starts:
```bash
make
./http_server 8080
```

## Testing Tools

### 1. curl - Command-line HTTP client

**Basic usage**:
```bash
# Simple GET request
curl http://localhost:8080/

# Verbose output (shows headers)
curl -v http://localhost:8080/

# Very verbose (includes TLS handshake info)
curl -vv http://localhost:8080/

# Follow redirects
curl -L http://localhost:8080/

# Save output to file
curl -o output.html http://localhost:8080/

# Show only response headers
curl -I http://localhost:8080/

# Custom headers
curl -H "User-Agent: MyTestClient/1.0" http://localhost:8080/

# POST request (for later)
curl -X POST -d "key=value" http://localhost:8080/api
```

### 2. Web Browser

**Chrome/Firefox DevTools** (Press F12):
- **Network Tab**: See all requests, status codes, headers, timing
- **Console**: Check for JavaScript errors
- **Elements**: Inspect DOM and CSS

**Testing steps**:
1. Open http://localhost:8080/
2. Open DevTools (F12)
3. Go to Network tab
4. Refresh page (Ctrl+R)
5. Click on each request to see details

### 3. telnet - Raw TCP connection

Send raw HTTP requests:
```bash
telnet localhost 8080
```

Then type (press Enter after each line, press Enter twice after the blank line):
```
GET / HTTP/1.1
Host: localhost

```

**What you'll see**: Raw HTTP response including headers

### 4. nc (netcat) - More flexible than telnet

```bash
# Interactive
nc localhost 8080

# Send request from file
echo -e "GET / HTTP/1.1\r\nHost: localhost\r\n\r\n" | nc localhost 8080

# Check if port is open
nc -zv localhost 8080
```

### 5. Apache Bench (ab) - Load testing

```bash
# Install
# Ubuntu/Debian: sudo apt-get install apache2-utils
# macOS: brew install httpd

# Run load test
ab -n 1000 -c 10 http://localhost:8080/

# Explanation:
# -n 1000: Total requests
# -c 10: Concurrent requests
# -t 30: Timeout 30 seconds

# Save results to file
ab -n 1000 -c 10 -g results.tsv http://localhost:8080/
```

### 6. wrk - Modern load testing

```bash
# Install
# Ubuntu: sudo apt-get install wrk
# macOS: brew install wrk

# Run load test
wrk -t4 -c100 -d30s http://localhost:8080/

# With script for custom behavior
wrk -t4 -c100 -d30s -s script.lua http://localhost:8080/
```

### 7. HTTPie - User-friendly HTTP client

```bash
# Install
pip install httpie

# GET request
http localhost:8080/

# POST with JSON
http POST localhost:8080/api name=John age:=30

# Custom headers
http localhost:8080/ User-Agent:CustomClient/1.0
```

## Test Categories

### 1. Basic Functionality Tests

**Test: Server starts successfully**
```bash
./http_server 8080
# Expected: "Server listening on http://localhost:8080"
```

**Test: Can connect to server**
```bash
nc -zv localhost 8080
# Expected: Connection succeeded
```

**Test: Root path returns 200**
```bash
curl -I http://localhost:8080/
# Expected: HTTP/1.1 200 OK
```

**Test: index.html is served**
```bash
curl http://localhost:8080/ | grep -i "HTTP Server"
# Expected: Should find "HTTP Server" text
```

### 2. Static File Serving Tests

**Test: HTML file**
```bash
curl -v http://localhost:8080/index.html
# Expected: 
# - Status: 200 OK
# - Content-Type: text/html
# - Body contains HTML content
```

**Test: CSS file**
```bash
curl -v http://localhost:8080/style.css
# Expected:
# - Status: 200 OK
# - Content-Type: text/css
# - Body contains CSS rules
```

**Test: JavaScript file**
```bash
curl -v http://localhost:8080/script.js
# Expected:
# - Status: 200 OK
# - Content-Type: application/javascript
# - Body contains JavaScript code
```

**Test: Content-Length header**
```bash
curl -I http://localhost:8080/index.html
# Expected: Content-Length matches actual file size
```

**Verify**:
```bash
wc -c public/index.html
# Compare with Content-Length header
```

### 3. Error Handling Tests

**Test: 404 for non-existent file**
```bash
curl -v http://localhost:8080/nonexistent.html
# Expected:
# - Status: 404 Not Found
# - Content-Type: text/plain
# - Body: "404 Not Found"
```

**Test: 404 for directory without index**
```bash
mkdir public/empty
curl -v http://localhost:8080/empty/
# Expected: 404 Not Found
```

**Test: Malformed request**
```bash
echo "INVALID REQUEST" | nc localhost 8080
# Expected: 400 Bad Request or connection closes
```

**Test: Unsupported HTTP method**
```bash
curl -X POST http://localhost:8080/
# Expected: 405 Method Not Allowed (if POST not implemented)
```

### 4. Security Tests

**Test: Path traversal prevention**
```bash
curl http://localhost:8080/../http_server.c
# Expected: 404 Not Found (should not serve files outside public/)

curl http://localhost:8080/../../etc/passwd
# Expected: 404 Not Found

curl http://localhost:8080/../../../etc/hosts
# Expected: 404 Not Found
```

**Test: Null byte injection**
```bash
curl "http://localhost:8080/index.html%00.txt"
# Expected: 404 or handled safely
```

**Test: URL encoding**
```bash
curl "http://localhost:8080/%2e%2e%2f%2e%2e%2fetc%2fpasswd"
# Expected: 404 Not Found
```

### 5. Content Type Tests

Create test files:
```bash
mkdir -p public/test
echo "Plain text" > public/test/file.txt
echo '{"key":"value"}' > public/test/data.json
cp some-image.png public/test/image.png
```

**Test various content types**:
```bash
# Text
curl -I http://localhost:8080/test/file.txt | grep Content-Type
# Expected: text/plain

# JSON
curl -I http://localhost:8080/test/data.json | grep Content-Type
# Expected: application/json

# Image
curl -I http://localhost:8080/test/image.png | grep Content-Type
# Expected: image/png
```

### 6. Browser Tests

**Test: Page loads in browser**
1. Open http://localhost:8080/
2. Expected: HTML page displays correctly
3. CSS styling applies
4. JavaScript button works

**Test: DevTools inspection**
1. Open http://localhost:8080/
2. Press F12
3. Go to Network tab
4. Refresh (Ctrl+R)
5. Check each request:
   - index.html: 200 OK, text/html
   - style.css: 200 OK, text/css
   - script.js: 200 OK, application/javascript

**Test: Console errors**
1. Open http://localhost:8080/
2. Press F12, go to Console
3. Expected: No errors

### 7. Concurrent Connection Tests

**Test: Multiple sequential requests**
```bash
for i in {1..10}; do
    curl -s http://localhost:8080/ > /dev/null
    echo "Request $i completed"
done
```

**Test: Concurrent requests**
```bash
# Using xargs for parallel execution
seq 1 10 | xargs -P 10 -I {} curl -s http://localhost:8080/ -o /dev/null
```

**Test: Load testing**
```bash
# Light load
ab -n 100 -c 5 http://localhost:8080/

# Medium load
ab -n 1000 -c 10 http://localhost:8080/

# Heavy load (for stress testing)
ab -n 10000 -c 100 http://localhost:8080/
```

**Metrics to check**:
- Requests per second
- Time per request
- Failed requests (should be 0)
- Transfer rate

### 8. Memory Leak Tests

**Test with valgrind**:
```bash
# Start server with valgrind
valgrind --leak-check=full --show-leak-kinds=all ./http_server 8080

# In another terminal, make requests
for i in {1..10}; do
    curl http://localhost:8080/ > /dev/null
done

# Stop server (Ctrl+C)
# Check valgrind output for leaks
```

**Expected output**:
```
LEAK SUMMARY:
   definitely lost: 0 bytes in 0 blocks
   indirectly lost: 0 bytes in 0 blocks
     possibly lost: 0 bytes in 0 blocks
```

### 9. Large File Tests

**Create large test file**:
```bash
dd if=/dev/urandom of=public/large.bin bs=1M count=10
# Creates 10MB random file
```

**Test: Download large file**
```bash
time curl http://localhost:8080/large.bin -o /dev/null
# Check it completes successfully and reasonably fast
```

**Test: Verify integrity**
```bash
# Download file
curl http://localhost:8080/large.bin -o downloaded.bin

# Compare with original
diff public/large.bin downloaded.bin
# Expected: No differences
```

### 10. Keep-Alive Tests (Advanced)

**Test: Connection reuse**
```bash
# HTTP/1.1 should close connection (Connection: close header)
curl -v http://localhost:8080/ 2>&1 | grep "Connection"
# Expected: Connection: close
```

If you implement keep-alive:
```bash
# Multiple requests on same connection
curl -v --http1.1 --keepalive-time 60 \
    http://localhost:8080/index.html \
    http://localhost:8080/style.css
```

## Automated Test Script

Create `test_server.sh`:
```bash
#!/bin/bash

SERVER_URL="http://localhost:8080"
FAILED=0

test_case() {
    local name="$1"
    local command="$2"
    local expected="$3"
    
    echo -n "Testing: $name... "
    result=$(eval "$command" 2>&1)
    
    if echo "$result" | grep -q "$expected"; then
        echo "✓ PASS"
    else
        echo "✗ FAIL"
        echo "  Expected: $expected"
        echo "  Got: $result"
        FAILED=$((FAILED + 1))
    fi
}

echo "=== HTTP Server Test Suite ==="
echo

# Test 1: Server is running
test_case "Server is accessible" \
    "curl -s -o /dev/null -w '%{http_code}' $SERVER_URL/" \
    "200"

# Test 2: HTML is served
test_case "index.html returns HTML" \
    "curl -s $SERVER_URL/ | head -1" \
    "<!DOCTYPE html>"

# Test 3: CSS is served
test_case "style.css returns CSS" \
    "curl -s -I $SERVER_URL/style.css" \
    "text/css"

# Test 4: 404 for missing file
test_case "404 for missing file" \
    "curl -s -o /dev/null -w '%{http_code}' $SERVER_URL/missing.html" \
    "404"

# Test 5: Path traversal blocked
test_case "Path traversal blocked" \
    "curl -s -o /dev/null -w '%{http_code}' $SERVER_URL/../http_server.c" \
    "404"

# Test 6: Content-Length header present
test_case "Content-Length header" \
    "curl -s -I $SERVER_URL/" \
    "Content-Length"

echo
if [ $FAILED -eq 0 ]; then
    echo "=== All tests passed! ✓ ==="
else
    echo "=== $FAILED test(s) failed ✗ ==="
    exit 1
fi
```

Run it:
```bash
chmod +x test_server.sh
./test_server.sh
```

## Performance Benchmarks

### Baseline measurements

Run these to establish baseline performance:

```bash
# Measure requests per second
ab -n 1000 -c 10 http://localhost:8080/ | grep "Requests per second"

# Measure latency
ab -n 1000 -c 10 http://localhost:8080/ | grep "Time per request"

# Connection times
ab -n 100 -c 10 http://localhost:8080/ | grep "Connect:"
```

### Compare with nginx

```bash
# Start nginx
nginx

# Test nginx
ab -n 1000 -c 10 http://localhost:80/

# Compare results with your server
```

**Expected**: nginx will be 10-100x faster (it's production-grade and highly optimized)

## Troubleshooting Test Failures

### "Connection refused"
- Is server running? Check with `ps aux | grep http_server`
- Correct port? Check with `netstat -an | grep 8080`
- Firewall blocking? Try `curl http://127.0.0.1:8080/`

### "Empty reply from server"
- Server might be crashing on request
- Check server output for errors
- Run with valgrind to catch memory errors

### Content not displaying correctly
- Check Content-Type header with `curl -I`
- Verify file exists in public/ directory
- Check file permissions: `ls -la public/`

### Performance is terrible
- Sequential server handles one request at a time (expected)
- Don't run under valgrind for performance tests (it's slow)
- Check file I/O (use strace to see syscalls)

## Next Steps

After passing all tests:

1. **Add more features** and create tests for them
2. **Benchmark against production servers** (nginx, Apache)
3. **Profile with perf** to find bottlenecks
4. **Implement concurrency** and see performance improve
5. **Write unit tests** for individual functions

## Resources

- [HTTP Testing Best Practices](https://www.softwaretestinghelp.com/http-testing/)
- [curl Documentation](https://curl.se/docs/)
- [Apache Bench Guide](https://httpd.apache.org/docs/2.4/programs/ab.html)
- [HTTP Status Codes](https://httpstatuses.com/)

Happy testing! 🧪
