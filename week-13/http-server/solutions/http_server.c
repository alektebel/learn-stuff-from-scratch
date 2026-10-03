/*
 * HTTP Server Implementation - Complete Solution
 * 
 * A complete implementation of a basic HTTP/1.1 server.
 * Supports GET requests and serves static files.
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
#define PUBLIC_DIR "./public"

typedef struct {
    char method[16];
    char path[256];
    char version[16];
} HttpRequest;

int create_server_socket(int port) {
    int server_socket = socket(AF_INET, SOCK_STREAM, 0);
    if (server_socket < 0) {
        perror("socket");
        return -1;
    }

    // Allow socket reuse
    int opt = 1;
    if (setsockopt(server_socket, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt)) < 0) {
        perror("setsockopt");
        close(server_socket);
        return -1;
    }

    struct sockaddr_in server_addr;
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = INADDR_ANY;
    server_addr.sin_port = htons(port);

    if (bind(server_socket, (struct sockaddr*)&server_addr, sizeof(server_addr)) < 0) {
        perror("bind");
        close(server_socket);
        return -1;
    }

    if (listen(server_socket, MAX_CONNECTIONS) < 0) {
        perror("listen");
        close(server_socket);
        return -1;
    }

    return server_socket;
}

HttpRequest* parse_http_request(const char* request) {
    HttpRequest* req = malloc(sizeof(HttpRequest));
    if (req == NULL) {
        return NULL;
    }

    // Parse request line: METHOD PATH VERSION
    if (sscanf(request, "%15s %255s %15s", req->method, req->path, req->version) != 3) {
        free(req);
        return NULL;
    }

    return req;
}

char* read_file(const char* filepath, size_t* file_size) {
    int fd = open(filepath, O_RDONLY);
    if (fd < 0) {
        return NULL;
    }

    struct stat st;
    if (fstat(fd, &st) < 0) {
        close(fd);
        return NULL;
    }

    *file_size = st.st_size;
    char* buffer = malloc(*file_size);
    if (buffer == NULL) {
        close(fd);
        return NULL;
    }

    ssize_t bytes_read = read(fd, buffer, *file_size);
    close(fd);

    if (bytes_read < 0 || (size_t)bytes_read != *file_size) {
        free(buffer);
        return NULL;
    }

    return buffer;
}

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

void send_response(int client_socket, int status_code, const char* content_type, 
                   const char* body, size_t body_length) {
    char header[BUFFER_SIZE];
    const char* status_text;

    switch (status_code) {
        case 200: status_text = "OK"; break;
        case 400: status_text = "Bad Request"; break;
        case 404: status_text = "Not Found"; break;
        case 405: status_text = "Method Not Allowed"; break;
        case 500: status_text = "Internal Server Error"; break;
        default: status_text = "Unknown"; break;
    }

    int header_len = snprintf(header, sizeof(header),
        "HTTP/1.1 %d %s\r\n"
        "Content-Type: %s\r\n"
        "Content-Length: %zu\r\n"
        "Connection: close\r\n"
        "\r\n",
        status_code, status_text, content_type, body_length);

    send(client_socket, header, header_len, 0);
    if (body != NULL && body_length > 0) {
        send(client_socket, body, body_length, 0);
    }
}

void handle_get_request(int client_socket, const char* path) {
    char filepath[512];
    
    // Build file path
    if (strcmp(path, "/") == 0) {
        snprintf(filepath, sizeof(filepath), "%s/index.html", PUBLIC_DIR);
    } else {
        snprintf(filepath, sizeof(filepath), "%s%s", PUBLIC_DIR, path);
    }

    // Check if path tries to escape public directory
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

void handle_client(int client_socket) {
    char buffer[BUFFER_SIZE];
    ssize_t bytes_read = recv(client_socket, buffer, sizeof(buffer) - 1, 0);
    
    if (bytes_read <= 0) {
        close(client_socket);
        return;
    }

    buffer[bytes_read] = '\0';
    
    // Parse request
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

int main(int argc, char** argv) {
    int port = DEFAULT_PORT;
    
    if (argc > 1) {
        port = atoi(argv[1]);
    }

    printf("Starting HTTP server on port %d...\n", port);

    // Create public directory if it doesn't exist
    mkdir(PUBLIC_DIR, 0755);

    int server_socket = create_server_socket(port);
    if (server_socket < 0) {
        fprintf(stderr, "Failed to create server socket\n");
        return 1;
    }

    printf("Server listening on http://localhost:%d\n", port);
    printf("Serving files from %s/\n", PUBLIC_DIR);

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

        handle_client(client_socket);
    }

    close(server_socket);
    return 0;
}
