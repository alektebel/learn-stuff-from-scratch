/*
 * DNS Server Implementation - Template
 * 
 * This template will guide you through building a DNS server from scratch.
 * Follow the TODOs and implement each section step by step.
 * 
 * Compilation: gcc -o dns_server dns_server.c
 * Usage: sudo ./dns_server [port]
 * 
 * Note: Requires root privileges to bind to port 53
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>

#define DEFAULT_PORT 53
#define BUFFER_SIZE 512
#define MAX_DOMAIN_NAME 256

/*
 * DNS Header Structure (12 bytes)
 * 
 * See RFC 1035 Section 4.1.1
 */
typedef struct {
    unsigned short id;        // Transaction ID
    unsigned short flags;     // DNS flags
    unsigned short qdcount;   // Number of questions
    unsigned short ancount;   // Number of answers
    unsigned short nscount;   // Number of authority records
    unsigned short arcount;   // Number of additional records
} DNSHeader;

/*
 * DNS Question Structure
 */
typedef struct {
    char name[MAX_DOMAIN_NAME];
    unsigned short qtype;     // Query type (A, AAAA, MX, etc.)
    unsigned short qclass;    // Query class (usually IN for Internet)
} DNSQuestion;

/*
 * DNS Resource Record Structure
 */
typedef struct {
    char name[MAX_DOMAIN_NAME];
    unsigned short type;
    unsigned short class;
    unsigned int ttl;
    unsigned short rdlength;
    unsigned char rdata[256];
} DNSResourceRecord;

/*
 * TODO 1: Implement create_udp_socket function
 * 
 * Guidelines:
 * - Create a UDP socket using socket() with SOCK_DGRAM
 * - Set socket options if needed (SO_REUSEADDR)
 * - Bind the socket to the specified port using bind()
 * - Return the socket file descriptor
 * 
 * Hints:
 * - UDP uses SOCK_DGRAM instead of SOCK_STREAM (TCP)
 * - Use AF_INET for IPv4
 * - Don't forget to set the address family, port, and address
 */
int create_udp_socket(int port) {
    // TODO: Create and bind UDP socket
    return -1;
}

/*
 * TODO 2: Implement parse_dns_header function
 * 
 * Guidelines:
 * - Read 12 bytes from the buffer
 * - Extract each field from the buffer (2 bytes each)
 * - Convert from network byte order to host byte order using ntohs()
 * - Fill in the DNSHeader structure
 * 
 * DNS Header format (12 bytes total):
 * - ID (2 bytes)
 * - Flags (2 bytes)
 * - QDCOUNT (2 bytes)
 * - ANCOUNT (2 bytes)
 * - NSCOUNT (2 bytes)
 * - ARCOUNT (2 bytes)
 * 
 * Hints:
 * - Network byte order is big-endian
 * - Use ntohs() to convert 16-bit values
 */
DNSHeader parse_dns_header(const unsigned char* buffer) {
    DNSHeader header;
    // TODO: Parse DNS header from buffer
    memset(&header, 0, sizeof(DNSHeader));
    return header;
}

/*
 * TODO 3: Implement parse_domain_name function
 * 
 * Guidelines:
 * - DNS names are encoded as length-prefixed labels
 * - Each label starts with a length byte (0-63)
 * - Labels are separated by dots in the output
 * - Name ends with a zero-length label
 * - Handle label compression (pointers starting with 11xxxxxx)
 * 
 * Example encoding of "example.com":
 * [7]example[3]com[0]
 * 
 * Hints:
 * - Check if first 2 bits are 11 (0xC0) for compression pointer
 * - Compression pointer format: 11 + 14-bit offset
 * - Update the position pointer to skip past the parsed name
 * - Max label length is 63 bytes
 */
int parse_domain_name(const unsigned char* buffer, int pos, char* output, int buffer_size) {
    // TODO: Parse DNS domain name with label compression support
    return 0;
}

/*
 * TODO 4: Implement parse_dns_question function
 * 
 * Guidelines:
 * - Parse the domain name starting at position
 * - After the name, read QTYPE (2 bytes)
 * - Then read QCLASS (2 bytes)
 * - Convert values from network byte order
 * - Update position to point after the question
 * 
 * Question format:
 * - QNAME (variable length, encoded domain name)
 * - QTYPE (2 bytes)
 * - QCLASS (2 bytes)
 */
int parse_dns_question(const unsigned char* buffer, int pos, DNSQuestion* question, int buffer_size) {
    // TODO: Parse DNS question section
    return pos;
}

/*
 * TODO 5: Implement encode_dns_header function
 * 
 * Guidelines:
 * - Write 12 bytes to the buffer
 * - Convert each field from host byte order to network byte order using htons()
 * - Set appropriate flags (QR=1 for response, AA, RD, RA as needed)
 * - Copy transaction ID from query
 * 
 * DNS Flags (16 bits):
 * - QR (1 bit): 0=query, 1=response
 * - OPCODE (4 bits): 0=standard query
 * - AA (1 bit): Authoritative answer
 * - TC (1 bit): Truncated
 * - RD (1 bit): Recursion desired
 * - RA (1 bit): Recursion available
 * - Z (3 bits): Reserved (must be 0)
 * - RCODE (4 bits): Response code (0=no error, 3=NXDOMAIN)
 * 
 * Hints:
 * - Use htons() to convert to network byte order
 * - QR bit is the most significant bit
 */
int encode_dns_header(unsigned char* buffer, DNSHeader* header) {
    // TODO: Encode DNS header to buffer
    return 12;
}

/*
 * TODO 6: Implement encode_domain_name function
 * 
 * Guidelines:
 * - Convert dot-separated domain name to DNS label format
 * - Each label is prefixed with its length
 * - End with a zero-length label
 * - No compression needed for basic implementation
 * 
 * Example: "example.com" -> [7]example[3]com[0]
 * 
 * Hints:
 * - Split the domain by '.'
 * - Write length byte before each label
 * - Maximum label length is 63
 * - End with 0x00
 */
int encode_domain_name(unsigned char* buffer, const char* domain) {
    // TODO: Encode domain name to DNS label format
    return 0;
}

/*
 * TODO 7: Implement encode_dns_answer function
 * 
 * Guidelines:
 * - Encode the domain name
 * - Write TYPE (2 bytes)
 * - Write CLASS (2 bytes)
 * - Write TTL (4 bytes) using htonl()
 * - Write RDLENGTH (2 bytes)
 * - Write RDATA (IP address or other data)
 * 
 * Answer format:
 * - NAME (variable length)
 * - TYPE (2 bytes)
 * - CLASS (2 bytes)
 * - TTL (4 bytes)
 * - RDLENGTH (2 bytes)
 * - RDATA (variable length based on RDLENGTH)
 * 
 * For A records (IPv4):
 * - TYPE = 1
 * - CLASS = 1 (IN)
 * - RDLENGTH = 4
 * - RDATA = 4-byte IP address
 */
int encode_dns_answer(unsigned char* buffer, DNSResourceRecord* answer) {
    // TODO: Encode DNS resource record
    return 0;
}

/*
 * TODO 8: Implement create_dns_response function
 * 
 * Guidelines:
 * - Copy query header and set response flags
 * - Copy question section from query
 * - Add answer section with resource records
 * - Set answer count in header
 * - Return total response size
 * 
 * Response structure:
 * 1. Copy header from query
 * 2. Modify flags (QR=1, set RCODE)
 * 3. Copy question section
 * 4. Add answer records
 * 5. Update counts in header
 * 
 * Hints:
 * - Use functions you've already implemented
 * - For a simple server, you can hardcode some IP addresses
 * - RCODE 0 = success, 3 = NXDOMAIN (name not found)
 */
int create_dns_response(unsigned char* response, const unsigned char* query, int query_len) {
    // TODO: Build complete DNS response
    return 0;
}

/*
 * TODO 9: Implement resolve_query function
 * 
 * Guidelines:
 * - Parse the DNS question to get the domain name
 * - Look up the domain (use a simple lookup table or hardcoded values)
 * - Create appropriate resource records
 * - Return NULL if domain not found
 * 
 * For a basic implementation:
 * - Support A records (IPv4 addresses)
 * - Hardcode some example mappings (e.g., "test.local" -> "127.0.0.1")
 * - Set TTL to a reasonable value (e.g., 300 seconds)
 * 
 * Hints:
 * - This is where you'd normally query upstream DNS or read zone files
 * - For learning, start with a simple hardcoded lookup table
 */
DNSResourceRecord* resolve_query(const DNSQuestion* question) {
    // TODO: Resolve domain name to resource record
    return NULL;
}

/*
 * TODO 10: Implement main server loop
 * 
 * Guidelines:
 * - Create UDP socket
 * - Loop forever receiving DNS queries
 * - Parse incoming queries
 * - Create responses
 * - Send responses back to clients
 * 
 * Server loop:
 * 1. recvfrom() to receive query and client address
 * 2. Parse query and extract questions
 * 3. Build response with answers
 * 4. sendto() to send response to client
 * 
 * Hints:
 * - Use recvfrom() for UDP (not accept() like TCP)
 * - Store client address for sendto()
 * - Handle errors gracefully
 * - Add logging for debugging
 */
int main(int argc, char* argv[]) {
    int port = DEFAULT_PORT;
    
    if (argc > 1) {
        port = atoi(argv[1]);
    }
    
    printf("Starting DNS server on port %d...\n", port);
    printf("Note: This is a learning implementation. Use sudo for port 53.\n");
    
    // TODO: Implement main server loop
    // 1. Create UDP socket
    // 2. Loop forever:
    //    - Receive DNS query
    //    - Parse query
    //    - Build response
    //    - Send response
    
    return 0;
}
