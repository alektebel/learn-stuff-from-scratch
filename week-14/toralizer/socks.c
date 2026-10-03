/*
 * SOCKS Protocol Implementation
 * 
 * This file implements the SOCKS4 and SOCKS4a protocols for proxy communication.
 * 
 * SOCKS4 Protocol:
 *   Client -> Proxy: [VER=4][CMD][DSTPORT][DSTIP][USERID][NULL]
 *   Proxy -> Client: [VER=0][STATUS][DSTPORT][DSTIP]
 * 
 * SOCKS4a Extension (for hostname support):
 *   Client -> Proxy: [VER=4][CMD][DSTPORT][0.0.0.x][USERID][NULL][HOSTNAME][NULL]
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <netdb.h>
#include "socks.h"

// SOCKS4 protocol constants
#define SOCKS4_VERSION 4
#define SOCKS4_CMD_CONNECT 1
#define SOCKS4_RESPONSE_VERSION 0
#define SOCKS4_REQUEST_GRANTED 90
#define SOCKS4_REQUEST_REJECTED 91

/*
 * Check if a string is a valid IP address (IPv4)
 */
static int is_valid_ip(const char* str) {
    // TODO: Check if str is a valid IPv4 address
    // - Use inet_pton() or similar function
    // - Return 1 if valid IP, 0 if hostname
    
    struct in_addr addr;
    return inet_pton(AF_INET, str, &addr) == 1;
}

/*
 * Resolve hostname to IP address
 */
static int resolve_hostname(const char* hostname, struct in_addr* addr) {
    // TODO: Resolve hostname to IP address
    // - Use gethostbyname() or getaddrinfo()
    // - Fill addr structure with resolved IP
    // - Return 0 on success, -1 on error
    
    return -1; // Replace with actual implementation
}

/*
 * Build SOCKS4 request packet
 */
static int build_socks4_request(unsigned char* buffer, int buf_size,
                                const char* dest_host, int dest_port,
                                int use_socks4a) {
    // TODO: Build SOCKS4 request packet
    
    int offset = 0;
    
    // TODO: Byte 0: SOCKS version (4)
    // buffer[offset++] = SOCKS4_VERSION;
    
    // TODO: Byte 1: Command (1 = CONNECT)
    // buffer[offset++] = SOCKS4_CMD_CONNECT;
    
    // TODO: Bytes 2-3: Destination port (network byte order)
    // uint16_t port = htons(dest_port);
    // memcpy(buffer + offset, &port, 2);
    // offset += 2;
    
    // TODO: Bytes 4-7: Destination IP address
    if (use_socks4a) {
        // SOCKS4a: Use 0.0.0.x (x != 0) to indicate hostname follows
        // buffer[offset++] = 0;
        // buffer[offset++] = 0;
        // buffer[offset++] = 0;
        // buffer[offset++] = 1;  // Any non-zero value
    } else {
        // SOCKS4: Use actual IP address
        struct in_addr addr;
        // TODO: Resolve hostname to IP
        // TODO: Copy IP to buffer (4 bytes)
    }
    
    // TODO: Bytes 8+: User ID (can be empty) + null terminator
    // buffer[offset++] = '\0';  // Empty user ID
    
    // TODO: SOCKS4a only: Append hostname + null terminator
    if (use_socks4a) {
        // strcpy((char*)(buffer + offset), dest_host);
        // offset += strlen(dest_host) + 1;
    }
    
    return offset;  // Return total packet size
}

/*
 * Parse SOCKS4 response packet
 */
static int parse_socks4_response(unsigned char* response) {
    // TODO: Parse SOCKS4 response (8 bytes)
    
    // TODO: Byte 0: Response version (should be 0)
    if (response[0] != SOCKS4_RESPONSE_VERSION) {
        fprintf(stderr, "Invalid SOCKS4 response version: %d\n", response[0]);
        return -1;
    }
    
    // TODO: Byte 1: Status code
    // 90 = request granted
    // 91 = request rejected or failed
    // 92 = cannot connect to identd
    // 93 = different user IDs
    
    unsigned char status = response[1];
    
    switch (status) {
        case SOCKS4_REQUEST_GRANTED:
            return 0;  // Success
        case SOCKS4_REQUEST_REJECTED:
            fprintf(stderr, "SOCKS4: Request rejected or failed\n");
            return -1;
        case 92:
            fprintf(stderr, "SOCKS4: Cannot connect to identd\n");
            return -1;
        case 93:
            fprintf(stderr, "SOCKS4: Client and identd report different user IDs\n");
            return -1;
        default:
            fprintf(stderr, "SOCKS4: Unknown status code: %d\n", status);
            return -1;
    }
}

/*
 * Establish SOCKS4 connection to destination host through proxy
 */
int socks4_connect(int sock, const char* dest_host, int dest_port) {
    // TODO: Implement complete SOCKS4 connection
    
    // Step 1: Determine if we need SOCKS4a (hostname) or SOCKS4 (IP)
    int use_socks4a = !is_valid_ip(dest_host);
    
    // Step 2: Build SOCKS4 request
    unsigned char request[512];  // Large enough for hostname
    int request_size = build_socks4_request(request, sizeof(request),
                                           dest_host, dest_port, use_socks4a);
    
    if (request_size <= 0) {
        fprintf(stderr, "Failed to build SOCKS4 request\n");
        return -1;
    }
    
    // TODO: Send request to proxy
    // if (send(sock, request, request_size, 0) != request_size) {
    //     perror("Failed to send SOCKS4 request");
    //     return -1;
    // }
    
    // TODO: Receive response from proxy (8 bytes)
    unsigned char response[8];
    // int received = recv(sock, response, sizeof(response), 0);
    // if (received != 8) {
    //     perror("Failed to receive SOCKS4 response");
    //     return -1;
    // }
    
    // TODO: Parse response and check status
    // return parse_socks4_response(response);
    
    return -1; // Replace with actual implementation
}

/*
 * SOCKS5 implementation (optional - more advanced)
 * 
 * SOCKS5 has more features:
 * - Authentication methods
 * - UDP support
 * - IPv6 support
 * 
 * You can implement this after completing SOCKS4
 */

// SOCKS5 constants
#define SOCKS5_VERSION 5
#define SOCKS5_AUTH_NONE 0
#define SOCKS5_CMD_CONNECT 1

/*
 * Establish SOCKS5 connection (optional advanced feature)
 */
int socks5_connect(int sock, const char* dest_host, int dest_port) {
    // TODO: Implement SOCKS5 protocol (optional)
    
    // Phase 1: Greeting
    // Client: [VER=5][NMETHODS][METHODS]
    // Server: [VER=5][METHOD]
    
    // Phase 2: Authentication (if required)
    // Depends on method selected
    
    // Phase 3: Connection request
    // Client: [VER=5][CMD][RSV=0][ATYP][DST.ADDR][DST.PORT]
    // Server: [VER=5][REP][RSV=0][ATYP][BND.ADDR][BND.PORT]
    
    fprintf(stderr, "SOCKS5 not implemented yet\n");
    return -1;
}
