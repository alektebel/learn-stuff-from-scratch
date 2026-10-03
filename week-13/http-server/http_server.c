/*
 * HTTP Server Implementation - Template
 * 
 * This template will guide you through building an HTTP/1.1 server from scratch.
 * Follow the TODOs and implement each section step by step.
 * 
 * Compilation: gcc -o http_server http_server.c
 * Usage: ./http_server [port]
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <fcntl.h>
#include <sys/stat.h>

#define DEFAULT_PORT 8080
#define BUFFER_SIZE 4096
#define MAX_CONNECTIONS 10

/*
 * TODO 1: Implement create_server_socket function
 * 
 * Guidelines:
 * - Create a TCP socket using socket()
 * - Set socket options (SO_REUSEADDR) using setsockopt()
 * - Bind the socket to a port using bind()
 * - Start listening with listen()
 * - Return the socket file descriptor
 */
int create_server_socket(int port) {
    // TODO: Implement socket creation and binding
    return -1;
}

/*
 * TODO 2: Implement parse_http_request function
 * 
 * Guidelines:
 * - Parse the HTTP request line (method, path, version)
 * - Extract the HTTP method (GET, POST, etc.)
 * - Extract the requested path
 * - Parse HTTP headers (optional but recommended)
 * - Store results in appropriate data structures
 */
typedef struct {
    char method[16];
    char path[256];
    char version[16];
} HttpRequest;

HttpRequest* parse_http_request(const char* request) {
    // TODO: Parse HTTP request
    return NULL;
}

/*
 * TODO 3: Implement read_file function
 * 
 * Guidelines:
 * - Open the file using open()
 * - Get file size using fstat()
 * - Read file contents into a buffer
 * - Return the buffer and size
 * - Handle file not found errors
 */
char* read_file(const char* filepath, size_t* file_size) {
    // TODO: Read file from filesystem
    return NULL;
}

/*
 * TODO 4: Implement get_content_type function
 * 
 * Guidelines:
 * - Determine content type based on file extension
 * - Support common types: .html, .css, .js, .txt, .jpg, .png
 * - Return appropriate MIME type string
 * - Default to "application/octet-stream" for unknown types
 */
const char* get_content_type(const char* filepath) {
    // TODO: Determine content type from file extension
    return "text/plain";
}

/*
 * TODO 5: Implement send_response function
 * 
 * Guidelines:
 * - Build HTTP response with status line
 * - Add necessary headers (Content-Type, Content-Length, etc.)
 * - Send response using send() or write()
 * - Handle different status codes (200, 404, 500)
 */
void send_response(int client_socket, int status_code, const char* content_type, 
                   const char* body, size_t body_length) {
    // TODO: Send HTTP response to client
}

/*
 * TODO 6: Implement handle_get_request function
 * 
 * Guidelines:
 * - Map URL path to filesystem path
 * - Default to "index.html" for directory requests
 * - Read the file content
 * - Send 200 OK response with file content
 * - Send 404 Not Found if file doesn't exist
 */
void handle_get_request(int client_socket, const char* path) {
    // TODO: Handle GET request
}

/*
 * TODO 7: Implement handle_client function
 * 
 * Guidelines:
 * - Read the HTTP request from client socket
 * - Parse the request
 * - Route to appropriate handler based on method
 * - Close the client socket when done
 */
void handle_client(int client_socket) {
    // TODO: Handle client connection
}

/*
 * TODO 8 (Advanced): Implement handle_post_request function
 * 
 * Guidelines:
 * - Read request body based on Content-Length header
 * - Parse form data or JSON
 * - Process the data
 * - Send appropriate response
 */
void handle_post_request(int client_socket, const char* path, const char* body) {
    // TODO: Handle POST request (Advanced)
}

/*
 * Main server loop
 */
int main(int argc, char** argv) {
    int port = DEFAULT_PORT;
    
    if (argc > 1) {
        port = atoi(argv[1]);
    }

    printf("Starting HTTP server on port %d...\n", port);

    int server_socket = create_server_socket(port);
    if (server_socket < 0) {
        fprintf(stderr, "Failed to create server socket\n");
        return 1;
    }

    printf("Server listening on http://localhost:%d\n", port);

    while (1) {
        struct sockaddr_in client_addr;
        socklen_t client_len = sizeof(client_addr);
        
        int client_socket = accept(server_socket, 
                                   (struct sockaddr*)&client_addr, 
                                   &client_len);
        
        if (client_socket < 0) {
            perror("accept");
            continue;
        }

        printf("Client connected: %s\n", inet_ntoa(client_addr.sin_addr));
        
        handle_client(client_socket);
    }

    close(server_socket);
    return 0;
}

/*
 * IMPLEMENTATION GUIDE:
 * 
 * Step 1: Implement create_server_socket()
 *         Test that the server starts and listens on a port
 * 
 * Step 2: Implement basic request reading in handle_client()
 *         Test that you can receive HTTP requests
 * 
 * Step 3: Implement parse_http_request()
 *         Test parsing with sample HTTP request strings
 * 
 * Step 4: Implement send_response() for basic responses
 *         Test that you can send a simple "Hello World" response
 * 
 * Step 5: Implement read_file() and get_content_type()
 *         Test reading and serving static files
 * 
 * Step 6: Implement handle_get_request() completely
 *         Test serving HTML, CSS, and JavaScript files
 * 
 * Step 7 (Advanced): Add POST request handling
 *         Test with form submissions
 * 
 * Testing Tips:
 * - Use curl for testing: curl http://localhost:8080
 * - Use a web browser to test file serving
 * - Create a simple public/ directory with test files
 * - Test error cases (404, invalid requests)
 * - Use netcat (nc) to send raw HTTP requests
 */
