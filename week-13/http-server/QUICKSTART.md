# HTTP Server - Quick Start

Get up and running with the HTTP server project in 5 minutes!

## Option 1: Run the Working Solution (2 minutes)

Want to see what you're building first?

```bash
# Navigate to solutions
cd solutions/

# Compile
gcc -o http_server http_server.c -Wall -Wextra

# Run
./http_server 8080
```

Open http://localhost:8080 in your browser - you should see a styled webpage!

**Stop the server**: Press `Ctrl+C` (or send SIGINT signal, or close the terminal)

---

## Option 2: Build It Yourself (Follow the Guide)

Ready to implement it from scratch?

### Step 1: Read the Guides

1. **README.md** - Overview and learning path
2. **IMPLEMENTATION_GUIDE.md** - Step-by-step instructions
3. **TESTING_GUIDE.md** - How to test each feature

### Step 2: Start Implementing

```bash
# Open the template file
vim http_server.c
# or: code http_server.c (VS Code)
# or: nano http_server.c

# Follow the TODO comments in order
```

### Step 3: Test as You Go

```bash
# Compile
make

# Run
./http_server 8080

# Test in another terminal
curl http://localhost:8080/
```

### Recommended Order

1. ✅ `create_server_socket()` - Get server listening
2. ✅ `handle_client()` - Read requests
3. ✅ `parse_http_request()` - Parse request line
4. ✅ `send_response()` - Send basic response
5. ✅ `read_file()` - Read files from disk
6. ✅ `get_content_type()` - Detect MIME types
7. ✅ `handle_get_request()` - Serve static files

**Time estimate**: 8-12 hours total (can split across multiple sessions)

---

## Option 3: Copy and Modify (Learning by Experimentation)

Start with the solution and experiment:

```bash
# Copy solution to workspace
cp solutions/http_server.c my_server.c

# Modify and extend it
vim my_server.c
```

**Experiment ideas**:
- Change the default port
- Add more MIME types
- Modify the 404 message
- Add request logging
- Try breaking things to see what happens!

---

## File Structure

```
http-server/
├── README.md                 ⭐ Start here - overview
├── IMPLEMENTATION_GUIDE.md   📖 Step-by-step instructions
├── TESTING_GUIDE.md          🧪 How to test
├── EXTENSIONS.md             🚀 Advanced features to add
├── http_server.c             📝 Template (your workspace)
├── Makefile                  🔨 Build configuration
├── public/                   📁 Static files to serve
│   ├── index.html
│   ├── style.css
│   ├── script.js
│   └── 404.html
└── solutions/                ✅ Complete implementation
    ├── README.md             - Detailed code walkthrough
    └── http_server.c         - Working solution
```

---

## Essential Commands

### Build
```bash
make              # Compile
make clean        # Remove binary
```

### Run
```bash
./http_server 8080        # Run on port 8080
./http_server 3000        # Run on port 3000
```

### Test
```bash
# In browser
http://localhost:8080/

# With curl
curl http://localhost:8080/
curl -v http://localhost:8080/      # Verbose (see headers)
curl -I http://localhost:8080/      # Headers only

# Test 404
curl http://localhost:8080/missing.html
```

---

## Common First-Time Issues

### "Address already in use"
Something else is using port 8080.

**Solution**: Use a different port
```bash
./http_server 3000
```

Or kill the other process:
```bash
lsof -i :8080          # Find PID
kill -9 <PID>          # Kill it
```

### "Permission denied" on port
Ports below 1024 require root privileges.

**Solution**: Use port ≥ 1024
```bash
./http_server 8080     # ✅ OK
./http_server 80       # ❌ Needs sudo
```

### Can't find files
Server looks for `./public/` directory from where you run it.

**Solution**: Run from the `http-server/` directory
```bash
cd http-server/
./http_server 8080
```

### "Connection refused" from browser
Server not running or wrong port.

**Solution**: 
1. Check server is running (look for "Server listening..." message)
2. Check the port number in URL matches
3. Try `curl http://127.0.0.1:8080/` instead

---

## Quick Checklist

Before you start, make sure you have:

- [ ] C compiler installed (`gcc --version`)
- [ ] Basic C knowledge (pointers, structs, memory management)
- [ ] Text editor or IDE
- [ ] Terminal/command line access
- [ ] curl installed (for testing)
- [ ] A few hours of focused time

---

## Getting Help

**Stuck on implementation?**
1. Check IMPLEMENTATION_GUIDE.md for detailed steps
2. Look at the solution in `solutions/http_server.c`
3. Read the code comments - they explain each section

**Something not working?**
1. Check TESTING_GUIDE.md for debugging tips
2. Add `printf()` statements to see what's happening
3. Use `curl -v` to see full request/response

**Want to understand the code better?**
1. Read `solutions/README.md` - detailed walkthrough
2. Try modifying small parts and see what changes
3. Read HTTP protocol basics online

---

## Learning Approach

### 🎯 Goal-Oriented
Know what you want to learn? Jump straight to that section:
- Network programming → Focus on socket functions
- HTTP protocol → Focus on parsing and response generation
- File I/O → Focus on read_file and serving static content

### 📚 Systematic
Prefer structured learning? Follow IMPLEMENTATION_GUIDE.md from start to finish.

### 🔬 Experimental
Learn by doing? Copy the solution and start modifying it to see what happens.

**All approaches are valid!** Choose what works for your learning style.

---

## Next Steps After Completion

1. ✅ **Verify it works**
   - Test with browser
   - Test with curl
   - Try the test script in TESTING_GUIDE.md

2. 🚀 **Add features**
   - See EXTENSIONS.md for 25+ ideas
   - Start with easy ones (logging, POST handling)
   - Progress to advanced (HTTPS, HTTP/2)

3. 📊 **Benchmark it**
   - Use Apache Bench: `ab -n 1000 -c 10 http://localhost:8080/`
   - Compare with nginx
   - Profile with `perf` or `gprof`

4. 🔄 **Optimize it**
   - Add multithreading
   - Implement caching
   - Use epoll for event loop
   - See how fast you can make it!

5. 🎓 **Understand production servers**
   - Read nginx source code
   - Study Apache architecture
   - Learn about load balancing, CDNs

---

## Resources for Learning

### Recommended Reading
- *Unix Network Programming* by W. Richard Stevens
- *Beej's Guide to Network Programming* (free online)
- HTTP/1.1 RFC 7230-7235

### Video Tutorials
- Search YouTube: "build http server from scratch"
- Look for C socket programming tutorials

### Online Tools
- https://httpstatuses.com/ - HTTP status code reference
- https://www.iana.org/assignments/media-types/ - MIME types
- https://httpbin.org/ - HTTP testing service

---

## Time Expectations

**Reading documentation**: 30-60 minutes  
**Basic implementation** (GET requests, static files): 6-8 hours  
**Testing and debugging**: 2-4 hours  
**Advanced features** (POST, threading, etc.): 10-20 hours  

**Total**: Expect 10-30 hours for a solid understanding and working implementation.

**Remember**: This is a learning project. Take your time, experiment, and understand each piece before moving on.

---

## Have Fun! 🎉

Building an HTTP server from scratch is challenging but incredibly rewarding. You'll gain deep understanding of:
- How the web works at a fundamental level
- Network programming and sockets
- The HTTP protocol
- Systems programming in C
- Real-world software architecture

**Most importantly**: You'll be able to say "I built that!" when you use the web. 

Ready? Let's go! 🚀

```bash
cd http-server/
cat README.md        # Read the overview
cat IMPLEMENTATION_GUIDE.md   # Follow step by step
# Start coding!
```
