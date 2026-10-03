/*
 * Network Utilities
 * 
 * Basic socket operations for TCP connections
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <netdb.h>
#include "network.h"

/*
 * Create a TCP socket
 */
int create_socket(void) {
    // TODO: Create a TCP socket
    // - Use socket(AF_INET, SOCK_STREAM, 0)
    // - AF_INET = IPv4
    // - SOCK_STREAM = TCP
    // - Return socket file descriptor or -1 on error
    
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) {
        perror("socket creation failed");
        return -1;
    }
    
    return sock;
}

/*
 * Connect to a server
 */
int connect_to_server(int sock, const char* host, int port) {
    // TODO: Connect to remote server
    
    struct sockaddr_in server_addr;
    memset(&server_addr, 0, sizeof(server_addr));
    
    // TODO: Set address family (IPv4)
    server_addr.sin_family = AF_INET;
    
    // TODO: Set port number (convert to network byte order)
    // server_addr.sin_port = htons(port);
    
    // TODO: Resolve hostname to IP address
    // Try inet_pton first (if it's an IP address)
    // if (inet_pton(AF_INET, host, &server_addr.sin_addr) <= 0) {
    //     // Not an IP address, try resolving hostname
    //     struct hostent* he = gethostbyname(host);
    //     if (he == NULL) {
    //         fprintf(stderr, "Cannot resolve hostname: %s\n", host);
    //         return -1;
    //     }
    //     memcpy(&server_addr.sin_addr, he->h_addr_list[0], he->h_length);
    // }
    
    // TODO: Connect to server
    // if (connect(sock, (struct sockaddr*)&server_addr, sizeof(server_addr)) < 0) {
    //     perror("connect failed");
    //     return -1;
    // }
    
    return -1;  // Replace with actual implementation
}

/*
 * Set socket timeout
 */
int set_socket_timeout(int sock, int seconds) {
    // TODO: Set receive and send timeouts
    // - Use setsockopt with SO_RCVTIMEO and SO_SNDTIMEO
    // - Useful for preventing indefinite blocking
    
    struct timeval timeout;
    timeout.tv_sec = seconds;
    timeout.tv_usec = 0;
    
    // TODO: Set receive timeout
    // if (setsockopt(sock, SOL_SOCKET, SO_RCVTIMEO, &timeout, sizeof(timeout)) < 0) {
    //     perror("setsockopt SO_RCVTIMEO failed");
    //     return -1;
    // }
    
    // TODO: Set send timeout
    // if (setsockopt(sock, SOL_SOCKET, SO_SNDTIMEO, &timeout, sizeof(timeout)) < 0) {
    //     perror("setsockopt SO_SNDTIMEO failed");
    //     return -1;
    // }
    
    return 0;
}

/*
 * Set socket to non-blocking mode
 */
int set_nonblocking(int sock) {
    // TODO: Set socket to non-blocking mode
    // - Use fcntl with O_NONBLOCK flag
    // - Useful for asynchronous I/O
    
    // int flags = fcntl(sock, F_GETFL, 0);
    // if (flags == -1) {
    //     perror("fcntl F_GETFL failed");
    //     return -1;
    // }
    // 
    // if (fcntl(sock, F_SETFL, flags | O_NONBLOCK) == -1) {
    //     perror("fcntl F_SETFL failed");
    //     return -1;
    // }
    
    return -1;  // Replace with actual implementation
}
