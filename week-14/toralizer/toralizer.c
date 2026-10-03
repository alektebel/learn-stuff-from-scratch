/*
 * Toralizer - Route connections through Tor SOCKS proxy
 * 
 * This program routes TCP connections through the Tor network by connecting
 * to a local Tor daemon via SOCKS protocol.
 *
 * Usage: ./toralizer [-p proxy:port] [-v] <host> <port>
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <stdarg.h>
#include "socks.h"
#include "network.h"

// Default Tor SOCKS proxy settings
#define DEFAULT_TOR_HOST "127.0.0.1"
#define DEFAULT_TOR_PORT 9050

// Global verbose flag
int verbose = 0;

/*
 * Print verbose log messages
 */
void log_verbose(const char* format, ...) {
    // TODO: Implement verbose logging
    // - Check if verbose flag is set
    // - Use vfprintf to print formatted message to stderr
    // - Add newline if not present in format
}

/*
 * Print usage information
 */
void print_usage(const char* program_name) {
    fprintf(stderr, "Usage: %s [-p proxy:port] [-v] <host> <port>\n", program_name);
    fprintf(stderr, "\n");
    fprintf(stderr, "Options:\n");
    fprintf(stderr, "  -p <proxy:port>  Tor SOCKS proxy address (default: %s:%d)\n", 
            DEFAULT_TOR_HOST, DEFAULT_TOR_PORT);
    fprintf(stderr, "  -v               Verbose output\n");
    fprintf(stderr, "  -h               Show this help message\n");
    fprintf(stderr, "\n");
    fprintf(stderr, "Arguments:\n");
    fprintf(stderr, "  <host>           Destination hostname or IP address\n");
    fprintf(stderr, "  <port>           Destination port number\n");
    fprintf(stderr, "\n");
    fprintf(stderr, "Examples:\n");
    fprintf(stderr, "  %s www.example.com 80\n", program_name);
    fprintf(stderr, "  %s -v www.google.com 443\n", program_name);
    fprintf(stderr, "  %s -p 127.0.0.1:9050 3g2upl4pq6kufc4m.onion 80\n", program_name);
}

/*
 * Parse proxy address in format "host:port"
 */
int parse_proxy_address(const char* address, char* host, int* port) {
    // TODO: Parse proxy address string
    // - Copy host part to host buffer
    // - Extract and convert port number
    // - Return 0 on success, -1 on error
    // - Handle formats: "host:port" or just "port" (use default host)
    
    return -1; // Replace with actual implementation
}

/*
 * Main toralizer program
 */
int main(int argc, char* argv[]) {
    // Configuration
    char tor_host[256] = DEFAULT_TOR_HOST;
    int tor_port = DEFAULT_TOR_PORT;
    char dest_host[256] = {0};
    int dest_port = 0;
    
    // TODO: Parse command-line arguments
    // - Process options: -p, -v, -h
    // - Extract destination host and port
    // - Validate all required arguments are provided
    
    int opt;
    while ((opt = getopt(argc, argv, "p:vh")) != -1) {
        switch (opt) {
            case 'p':
                // TODO: Parse proxy address
                break;
            case 'v':
                // TODO: Enable verbose mode
                break;
            case 'h':
                print_usage(argv[0]);
                return 0;
            default:
                print_usage(argv[0]);
                return 1;
        }
    }
    
    // TODO: Get destination host and port from remaining arguments
    if (optind + 2 != argc) {
        fprintf(stderr, "Error: Missing destination host and port\n\n");
        print_usage(argv[0]);
        return 1;
    }
    
    // TODO: Copy destination host
    // strncpy(dest_host, argv[optind], sizeof(dest_host) - 1);
    
    // TODO: Parse destination port
    // dest_port = atoi(argv[optind + 1]);
    
    // TODO: Validate port number (1-65535)
    
    log_verbose("Configuration:");
    log_verbose("  Tor proxy: %s:%d", tor_host, tor_port);
    log_verbose("  Destination: %s:%d", dest_host, dest_port);
    
    // TODO: Create socket
    log_verbose("Creating socket...");
    int sock = create_socket();
    if (sock < 0) {
        fprintf(stderr, "Failed to create socket\n");
        return 1;
    }
    
    // TODO: Connect to Tor SOCKS proxy
    log_verbose("Connecting to Tor proxy %s:%d...", tor_host, tor_port);
    if (connect_to_server(sock, tor_host, tor_port) < 0) {
        fprintf(stderr, "Failed to connect to Tor proxy\n");
        close(sock);
        return 1;
    }
    log_verbose("Connected to Tor proxy");
    
    // TODO: Establish SOCKS connection to destination
    log_verbose("Establishing SOCKS connection to %s:%d...", dest_host, dest_port);
    if (socks4_connect(sock, dest_host, dest_port) < 0) {
        fprintf(stderr, "SOCKS connection failed\n");
        close(sock);
        return 1;
    }
    log_verbose("SOCKS connection established");
    
    // TODO: Relay data between stdin/stdout and the socket
    // This is a simple example - you can extend it to relay between two sockets
    log_verbose("Connection ready. Type data to send (Ctrl-D to exit):");
    
    // TODO: Use select() to handle bidirectional data transfer
    // For now, simple demonstration:
    // - Read from stdin, send to socket
    // - Read from socket, write to stdout
    
    char buffer[4096];
    fd_set read_fds;
    
    while (1) {
        FD_ZERO(&read_fds);
        FD_SET(STDIN_FILENO, &read_fds);
        FD_SET(sock, &read_fds);
        
        int max_fd = (STDIN_FILENO > sock) ? STDIN_FILENO : sock;
        
        // TODO: Wait for data on either stdin or socket
        if (select(max_fd + 1, &read_fds, NULL, NULL, NULL) < 0) {
            perror("select failed");
            break;
        }
        
        // TODO: Handle data from stdin
        if (FD_ISSET(STDIN_FILENO, &read_fds)) {
            int bytes = read(STDIN_FILENO, buffer, sizeof(buffer));
            if (bytes <= 0) {
                break;  // EOF or error
            }
            
            // Send to socket
            if (send(sock, buffer, bytes, 0) != bytes) {
                perror("send failed");
                break;
            }
        }
        
        // TODO: Handle data from socket
        if (FD_ISSET(sock, &read_fds)) {
            int bytes = recv(sock, buffer, sizeof(buffer), 0);
            if (bytes <= 0) {
                if (bytes == 0) {
                    log_verbose("Connection closed by remote host");
                } else {
                    perror("recv failed");
                }
                break;
            }
            
            // Write to stdout
            if (write(STDOUT_FILENO, buffer, bytes) != bytes) {
                perror("write failed");
                break;
            }
        }
    }
    
    // Cleanup
    log_verbose("Closing connection...");
    close(sock);
    
    return 0;
}
