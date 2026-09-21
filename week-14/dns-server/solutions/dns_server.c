/*
 * DNS Server Implementation - Complete Solution
 * 
 * A complete implementation of a basic DNS server supporting A records.
 * 
 * Compilation: gcc -o dns_server dns_server.c
 * Usage: sudo ./dns_server [port]
 * 
 * Note: Requires root privileges to bind to port 53
 * Note: This code uses strcasecmp which requires POSIX compatibility
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>  // For strcasecmp (POSIX)
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <errno.h>

#define DEFAULT_PORT 53
#define BUFFER_SIZE 512
#define MAX_DOMAIN_NAME 256

/*
 * DNS Header Structure (12 bytes)
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
    unsigned short qtype;     // Query type
    unsigned short qclass;    // Query class
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
 * Create and bind UDP socket
 */
int create_udp_socket(int port) {
    int sockfd = socket(AF_INET, SOCK_DGRAM, 0);
    if (sockfd < 0) {
        perror("socket");
        return -1;
    }

    // Allow socket reuse
    int opt = 1;
    if (setsockopt(sockfd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt)) < 0) {
        perror("setsockopt");
        close(sockfd);
        return -1;
    }

    struct sockaddr_in server_addr;
    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = INADDR_ANY;
    server_addr.sin_port = htons(port);

    if (bind(sockfd, (struct sockaddr*)&server_addr, sizeof(server_addr)) < 0) {
        perror("bind");
        close(sockfd);
        return -1;
    }

    return sockfd;
}

/*
 * Parse DNS header from buffer
 */
DNSHeader parse_dns_header(const unsigned char* buffer) {
    DNSHeader header;
    int pos = 0;

    // Use memcpy to avoid unaligned access issues
    unsigned short temp;
    
    memcpy(&temp, buffer + pos, 2);
    header.id = ntohs(temp);
    pos += 2;
    
    memcpy(&temp, buffer + pos, 2);
    header.flags = ntohs(temp);
    pos += 2;
    
    memcpy(&temp, buffer + pos, 2);
    header.qdcount = ntohs(temp);
    pos += 2;
    
    memcpy(&temp, buffer + pos, 2);
    header.ancount = ntohs(temp);
    pos += 2;
    
    memcpy(&temp, buffer + pos, 2);
    header.nscount = ntohs(temp);
    pos += 2;
    
    memcpy(&temp, buffer + pos, 2);
    header.arcount = ntohs(temp);

    return header;
}

/*
 * Parse domain name from DNS message with compression support
 */
int parse_domain_name(const unsigned char* buffer, int pos, char* output, int buffer_size) {
    int output_pos = 0;
    int jumped = 0;
    int original_pos = pos;
    int jump_count = 0;
    const int MAX_JUMPS = 5;  // Prevent infinite loops

    while (buffer[pos] != 0 && jump_count < MAX_JUMPS) {
        // Check for compression pointer (starts with 11)
        if ((buffer[pos] & 0xC0) == 0xC0) {
            if (!jumped) {
                original_pos = pos + 2;
            }
            // Extract pointer offset (14 bits)
            int offset = ((buffer[pos] & 0x3F) << 8) | buffer[pos + 1];
            pos = offset;
            jumped = 1;
            jump_count++;
            continue;
        }

        // Regular label
        int label_len = buffer[pos];
        pos++;

        if (label_len > 63 || output_pos + label_len + 1 >= MAX_DOMAIN_NAME) {
            return -1;  // Invalid label length
        }

        if (output_pos > 0) {
            output[output_pos++] = '.';
        }

        memcpy(output + output_pos, buffer + pos, label_len);
        output_pos += label_len;
        pos += label_len;
    }

    output[output_pos] = '\0';

    if (jumped) {
        return original_pos;
    } else {
        return pos + 1;  // Skip the terminating 0
    }
}

/*
 * Parse DNS question section
 */
int parse_dns_question(const unsigned char* buffer, int pos, DNSQuestion* question, int buffer_size) {
    pos = parse_domain_name(buffer, pos, question->name, buffer_size);
    if (pos < 0) {
        return -1;
    }

    // Use memcpy to avoid unaligned access
    unsigned short temp;
    
    memcpy(&temp, buffer + pos, 2);
    question->qtype = ntohs(temp);
    pos += 2;
    
    memcpy(&temp, buffer + pos, 2);
    question->qclass = ntohs(temp);
    pos += 2;

    return pos;
}

/*
 * Encode DNS header to buffer
 */
int encode_dns_header(unsigned char* buffer, DNSHeader* header) {
    int pos = 0;
    unsigned short temp;
    unsigned int temp_int;

    temp = htons(header->id);
    memcpy(buffer + pos, &temp, 2);
    pos += 2;
    
    temp = htons(header->flags);
    memcpy(buffer + pos, &temp, 2);
    pos += 2;
    
    temp = htons(header->qdcount);
    memcpy(buffer + pos, &temp, 2);
    pos += 2;
    
    temp = htons(header->ancount);
    memcpy(buffer + pos, &temp, 2);
    pos += 2;
    
    temp = htons(header->nscount);
    memcpy(buffer + pos, &temp, 2);
    pos += 2;
    
    temp = htons(header->arcount);
    memcpy(buffer + pos, &temp, 2);
    pos += 2;

    (void)temp_int;  // Unused, but kept for future use
    return pos;
}

/*
 * Encode domain name to DNS label format
 */
int encode_domain_name(unsigned char* buffer, const char* domain) {
    int pos = 0;
    int label_start = 0;
    int i = 0;
    int domain_len = strlen(domain);

    while (i <= domain_len) {
        if (domain[i] == '.' || domain[i] == '\0') {
            int label_len = i - label_start;
            if (label_len > 0) {
                if (label_len > 63) {
                    return -1;  // Label too long
                }
                buffer[pos++] = label_len;
                memcpy(buffer + pos, domain + label_start, label_len);
                pos += label_len;
            }
            label_start = i + 1;
        }
        i++;
    }

    buffer[pos++] = 0;  // Terminating zero-length label
    return pos;
}

/*
 * Encode DNS answer (resource record) to buffer
 */
int encode_dns_answer(unsigned char* buffer, DNSResourceRecord* answer) {
    int pos = 0;
    unsigned short temp;
    unsigned int temp_int;

    // Encode name
    int name_len = encode_domain_name(buffer + pos, answer->name);
    if (name_len < 0) {
        return -1;
    }
    pos += name_len;

    // Type
    temp = htons(answer->type);
    memcpy(buffer + pos, &temp, 2);
    pos += 2;

    // Class
    temp = htons(answer->class);
    memcpy(buffer + pos, &temp, 2);
    pos += 2;

    // TTL
    temp_int = htonl(answer->ttl);
    memcpy(buffer + pos, &temp_int, 4);
    pos += 4;

    // RDLENGTH
    temp = htons(answer->rdlength);
    memcpy(buffer + pos, &temp, 2);
    pos += 2;

    // RDATA
    memcpy(buffer + pos, answer->rdata, answer->rdlength);
    pos += answer->rdlength;

    return pos;
}

/*
 * Simple domain lookup table
 */
DNSResourceRecord* resolve_query(const DNSQuestion* question) {
    // Only support A records (IPv4)
    if (question->qtype != 1 || question->qclass != 1) {
        return NULL;
    }

    // Hardcoded lookup table for demonstration
    struct {
        const char* domain;
        const char* ip;
    } lookup_table[] = {
        {"test.local", "192.168.1.100"},
        {"example.local", "192.168.1.101"},
        {"localhost.local", "127.0.0.1"},
        {"server.local", "10.0.0.50"},
        {NULL, NULL}
    };

    for (int i = 0; lookup_table[i].domain != NULL; i++) {
        if (strcasecmp(question->name, lookup_table[i].domain) == 0) {
            DNSResourceRecord* answer = malloc(sizeof(DNSResourceRecord));
            if (answer == NULL) {
                return NULL;
            }

            strncpy(answer->name, question->name, MAX_DOMAIN_NAME - 1);
            answer->name[MAX_DOMAIN_NAME - 1] = '\0';
            answer->type = 1;      // A record
            answer->class = 1;     // IN (Internet)
            answer->ttl = 300;     // 5 minutes

            // Convert IP address to binary
            struct in_addr addr;
            if (inet_pton(AF_INET, lookup_table[i].ip, &addr) == 1) {
                answer->rdlength = 4;
                memcpy(answer->rdata, &addr.s_addr, 4);
                return answer;
            } else {
                free(answer);
                return NULL;
            }
        }
    }

    return NULL;  // Domain not found
}

/*
 * Create DNS response from query
 */
int create_dns_response(unsigned char* response, const unsigned char* query, int query_len) {
    int pos = 0;

    // Parse query header
    DNSHeader query_header = parse_dns_header(query);

    // Create response header
    DNSHeader response_header;
    response_header.id = query_header.id;
    response_header.flags = 0x8180;  // Response, Recursion Desired/Available
    response_header.qdcount = query_header.qdcount;
    response_header.ancount = 0;
    response_header.nscount = 0;
    response_header.arcount = 0;

    // Skip header in query to get to questions
    int query_pos = 12;

    // Parse questions and copy to response
    DNSQuestion questions[10];
    int num_questions = query_header.qdcount < 10 ? query_header.qdcount : 10;

    for (int i = 0; i < num_questions; i++) {
        query_pos = parse_dns_question(query, query_pos, &questions[i], query_len);
        if (query_pos < 0) {
            return -1;
        }
    }

    // Try to resolve each question
    DNSResourceRecord* answers[10];
    int answer_count = 0;

    for (int i = 0; i < num_questions; i++) {
        DNSResourceRecord* answer = resolve_query(&questions[i]);
        if (answer != NULL) {
            answers[answer_count++] = answer;
        }
    }

    // Set answer count and RCODE
    response_header.ancount = answer_count;
    if (answer_count == 0) {
        response_header.flags = 0x8183;  // NXDOMAIN (name not found)
    }

    // Encode response header
    pos = encode_dns_header(response, &response_header);

    // Copy question section from query
    int question_section_len = query_pos - 12;
    memcpy(response + pos, query + 12, question_section_len);
    pos += question_section_len;

    // Encode answers
    for (int i = 0; i < answer_count; i++) {
        int answer_len = encode_dns_answer(response + pos, answers[i]);
        if (answer_len < 0) {
            for (int j = 0; j < answer_count; j++) {
                free(answers[j]);
            }
            return -1;
        }
        pos += answer_len;
        free(answers[i]);
    }

    return pos;
}

/*
 * Main server loop
 */
int main(int argc, char* argv[]) {
    int port = DEFAULT_PORT;

    if (argc > 1) {
        char* endptr;
        errno = 0;
        long parsed_port = strtol(argv[1], &endptr, 10);
        
        if (errno != 0 || *endptr != '\0' || parsed_port < 1 || parsed_port > 65535) {
            fprintf(stderr, "Invalid port number. Please use a port between 1 and 65535.\n");
            return 1;
        }
        port = (int)parsed_port;
    }

    printf("Starting DNS server on port %d...\n", port);
    printf("Note: This is a learning implementation. Use sudo for port 53.\n");

    int sockfd = create_udp_socket(port);
    if (sockfd < 0) {
        fprintf(stderr, "Failed to create socket\n");
        return 1;
    }

    printf("DNS Server listening...\n\n");

    unsigned char buffer[BUFFER_SIZE];
    unsigned char response[BUFFER_SIZE];
    struct sockaddr_in client_addr;
    socklen_t client_addr_len = sizeof(client_addr);

    while (1) {
        // Receive DNS query
        int recv_len = recvfrom(sockfd, buffer, BUFFER_SIZE, 0,
                                (struct sockaddr*)&client_addr, &client_addr_len);

        if (recv_len < 0) {
            perror("recvfrom");
            continue;
        }

        printf("Received query from %s:%d (%d bytes)\n",
               inet_ntoa(client_addr.sin_addr),
               ntohs(client_addr.sin_port),
               recv_len);

        // Parse and display query info
        DNSHeader header = parse_dns_header(buffer);
        printf("Query ID: 0x%04x\n", header.id);
        printf("Flags: 0x%04x (RD=%d)\n", header.flags, (header.flags & 0x0100) ? 1 : 0);
        printf("Questions: %d\n", header.qdcount);

        // Parse first question for display
        if (header.qdcount > 0) {
            DNSQuestion question;
            int pos = parse_dns_question(buffer, 12, &question, recv_len);
            if (pos >= 0) {
                printf("Question: %s, Type: %d, Class: %d\n",
                       question.name, question.qtype, question.qclass);
            }
        }

        // Create response
        int response_len = create_dns_response(response, buffer, recv_len);

        if (response_len < 0) {
            fprintf(stderr, "Failed to create response\n");
            continue;
        }

        // Check if we found an answer
        DNSHeader response_header = parse_dns_header(response);
        if (response_header.ancount > 0) {
            printf("Sent response: %d bytes\n\n", response_len);
        } else {
            printf("Sent NXDOMAIN response: %d bytes\n\n", response_len);
        }

        // Send response
        int sent = sendto(sockfd, response, response_len, 0,
                         (struct sockaddr*)&client_addr, client_addr_len);

        if (sent < 0) {
            perror("sendto");
        }
    }

    close(sockfd);
    return 0;
}
