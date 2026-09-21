/*
 * Firewall Implementation - Template
 * 
 * This template will guide you through building a packet filtering firewall from scratch.
 * Follow the TODOs and implement each section step by step.
 * 
 * Compilation: gcc -o firewall firewall.c
 * Usage: sudo ./firewall [interface]
 * 
 * Note: Requires root privileges for raw socket access
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <netinet/in.h>
#include <netinet/ip.h>
#include <netinet/tcp.h>
#include <netinet/udp.h>
#include <netinet/ip_icmp.h>
#include <arpa/inet.h>
#include <net/ethernet.h>
#include <net/if.h>
#include <linux/if_packet.h>

#define BUFFER_SIZE 65536
#define MAX_RULES 100
#define MAX_IP_STR 16

/*
 * Rule Actions
 */
typedef enum {
    ACTION_ACCEPT,
    ACTION_DROP,
    ACTION_LOG
} RuleAction;

/*
 * Protocol Types
 */
typedef enum {
    PROTO_ANY = 0,
    PROTO_TCP = 6,
    PROTO_UDP = 17,
    PROTO_ICMP = 1
} Protocol;

/*
 * Firewall Rule Structure
 */
typedef struct {
    char src_ip[MAX_IP_STR];      // Source IP address (0.0.0.0 for any)
    char dst_ip[MAX_IP_STR];      // Destination IP address (0.0.0.0 for any)
    int src_port;                 // Source port (0 for any)
    int dst_port;                 // Destination port (0 for any)
    Protocol protocol;            // Protocol (0 for any)
    RuleAction action;            // Action to take
    int enabled;                  // Rule enabled flag
} FirewallRule;

/*
 * Firewall Statistics
 */
typedef struct {
    unsigned long packets_received;
    unsigned long packets_accepted;
    unsigned long packets_dropped;
    unsigned long bytes_received;
} FirewallStats;

// Global variables
static int running = 1;
static FirewallRule rules[MAX_RULES];
static int rule_count = 0;
static FirewallStats stats = {0};

/*
 * Signal handler for graceful shutdown
 */
void signal_handler(int sig) {
    if (sig == SIGINT) {
        printf("\n\nShutting down firewall...\n");
        running = 0;
    }
}

/*
 * TODO 1: Implement create_raw_socket function
 * 
 * Guidelines:
 * - Create a raw socket using socket() with AF_PACKET
 * - Use SOCK_RAW for raw packet access
 * - Use htons(ETH_P_ALL) to capture all protocols
 * - Optionally bind to a specific network interface
 * - Return the socket file descriptor
 * 
 * Hints:
 * - Raw sockets require root privileges
 * - AF_PACKET gives access to link layer (Ethernet)
 * - ETH_P_ALL captures all ethernet protocols
 * 
 * Example:
 *   int sock = socket(AF_PACKET, SOCK_RAW, htons(ETH_P_ALL));
 */
int create_raw_socket(const char* interface) {
    // TODO: Create raw socket
    // TODO: If interface is specified, bind to it using setsockopt with SO_BINDTODEVICE
    return -1;
}

/*
 * TODO 2: Implement parse_ethernet_frame function
 * 
 * Guidelines:
 * - Extract source and destination MAC addresses
 * - Extract the EtherType field (protocol type)
 * - EtherType 0x0800 is IPv4, 0x86DD is IPv6, 0x0806 is ARP
 * - Print MAC addresses and protocol type
 * 
 * Ethernet Frame Structure:
 * - Destination MAC (6 bytes)
 * - Source MAC (6 bytes)
 * - EtherType (2 bytes)
 * - Payload (46-1500 bytes)
 * 
 * Hints:
 * - Use struct ethhdr from <net/ethernet.h>
 * - Convert EtherType with ntohs()
 */
void parse_ethernet_frame(unsigned char* buffer, int size) {
    struct ethhdr* eth = (struct ethhdr*)buffer;
    
    // TODO: Parse and display Ethernet header information
    // TODO: Check EtherType to determine next layer protocol
    
    printf("Ethernet Frame:\n");
    // TODO: Print source and destination MAC addresses
    // TODO: Print EtherType
}

/*
 * TODO 3: Implement parse_ip_header function
 * 
 * Guidelines:
 * - Extract IP version, header length, protocol
 * - Extract source and destination IP addresses
 * - Extract TTL, packet length
 * - Verify checksum (optional but recommended)
 * 
 * IP Header Structure (20 bytes minimum):
 * - Version and IHL (1 byte)
 * - Type of Service (1 byte)
 * - Total Length (2 bytes)
 * - Identification, Flags, Fragment Offset (4 bytes)
 * - TTL (1 byte)
 * - Protocol (1 byte): 6=TCP, 17=UDP, 1=ICMP
 * - Header Checksum (2 bytes)
 * - Source IP (4 bytes)
 * - Destination IP (4 bytes)
 * 
 * Hints:
 * - Use struct iphdr from <netinet/ip.h>
 * - IP addresses need inet_ntoa() for display
 * - Protocol field tells you next layer (TCP/UDP/ICMP)
 */
void parse_ip_header(unsigned char* buffer, int size) {
    struct iphdr* iph = (struct iphdr*)(buffer + sizeof(struct ethhdr));
    
    // TODO: Parse and display IP header information
    
    printf("IP Header:\n");
    // TODO: Print IP version
    // TODO: Print header length
    // TODO: Print source and destination IP addresses
    // TODO: Print protocol (TCP/UDP/ICMP)
    // TODO: Print TTL
}

/*
 * TODO 4: Implement parse_tcp_header function
 * 
 * Guidelines:
 * - Extract source and destination ports
 * - Extract TCP flags (SYN, ACK, FIN, RST, PSH, URG)
 * - Extract sequence and acknowledgment numbers
 * - Display window size
 * 
 * TCP Header Structure (20 bytes minimum):
 * - Source Port (2 bytes)
 * - Destination Port (2 bytes)
 * - Sequence Number (4 bytes)
 * - Acknowledgment Number (4 bytes)
 * - Data Offset, Reserved, Flags (2 bytes)
 * - Window Size (2 bytes)
 * - Checksum (2 bytes)
 * - Urgent Pointer (2 bytes)
 * 
 * TCP Flags:
 * - SYN: Synchronize (connection establishment)
 * - ACK: Acknowledgment
 * - FIN: Finish (connection termination)
 * - RST: Reset
 * - PSH: Push
 * - URG: Urgent
 * 
 * Hints:
 * - Use struct tcphdr from <netinet/tcp.h>
 * - Ports need ntohs() for host byte order
 */
void parse_tcp_header(unsigned char* buffer, int size, struct iphdr* iph) {
    unsigned short iphdrlen = iph->ihl * 4;
    struct tcphdr* tcph = (struct tcphdr*)(buffer + iphdrlen + sizeof(struct ethhdr));
    
    // TODO: Parse and display TCP header information
    
    printf("TCP Header:\n");
    // TODO: Print source and destination ports
    // TODO: Print TCP flags (SYN, ACK, FIN, etc.)
    // TODO: Print sequence number
    // TODO: Print acknowledgment number
}

/*
 * TODO 5: Implement parse_udp_header function
 * 
 * Guidelines:
 * - Extract source and destination ports
 * - Extract length and checksum
 * - UDP is simpler than TCP (no flags, sequence numbers, etc.)
 * 
 * UDP Header Structure (8 bytes):
 * - Source Port (2 bytes)
 * - Destination Port (2 bytes)
 * - Length (2 bytes)
 * - Checksum (2 bytes)
 * 
 * Hints:
 * - Use struct udphdr from <netinet/udp.h>
 * - Common UDP ports: 53 (DNS), 67/68 (DHCP), 123 (NTP)
 */
void parse_udp_header(unsigned char* buffer, int size, struct iphdr* iph) {
    unsigned short iphdrlen = iph->ihl * 4;
    struct udphdr* udph = (struct udphdr*)(buffer + iphdrlen + sizeof(struct ethhdr));
    
    // TODO: Parse and display UDP header information
    
    printf("UDP Header:\n");
    // TODO: Print source and destination ports
    // TODO: Print length
}

/*
 * TODO 6: Implement parse_icmp_header function
 * 
 * Guidelines:
 * - Extract ICMP type and code
 * - Common types: 8 (Echo Request/ping), 0 (Echo Reply)
 * - Display type-specific information
 * 
 * ICMP Header Structure (8 bytes minimum):
 * - Type (1 byte)
 * - Code (1 byte)
 * - Checksum (2 bytes)
 * - Rest of Header (4 bytes, varies by type)
 * 
 * Common ICMP Types:
 * - 0: Echo Reply (ping response)
 * - 3: Destination Unreachable
 * - 8: Echo Request (ping)
 * - 11: Time Exceeded
 * 
 * Hints:
 * - Use struct icmphdr from <netinet/ip_icmp.h>
 */
void parse_icmp_header(unsigned char* buffer, int size, struct iphdr* iph) {
    unsigned short iphdrlen = iph->ihl * 4;
    struct icmphdr* icmph = (struct icmphdr*)(buffer + iphdrlen + sizeof(struct ethhdr));
    
    // TODO: Parse and display ICMP header information
    
    printf("ICMP Header:\n");
    // TODO: Print ICMP type and code
    // TODO: Interpret type (Echo Request, Echo Reply, etc.)
}

/*
 * TODO 7: Implement add_rule function
 * 
 * Guidelines:
 * - Add a new rule to the rules array
 * - Validate input parameters
 * - Check for maximum number of rules
 * - Set default values for unspecified fields
 * 
 * Hints:
 * - Use "0.0.0.0" to match any IP
 * - Use 0 to match any port
 * - Use PROTO_ANY to match any protocol
 */
int add_rule(const char* src_ip, const char* dst_ip, int src_port, 
             int dst_port, Protocol protocol, RuleAction action) {
    // TODO: Check if rule array is full
    // TODO: Initialize new rule structure
    // TODO: Copy IP addresses, ports, protocol, and action
    // TODO: Set enabled flag to 1
    // TODO: Increment rule_count
    // TODO: Return success
    return -1;
}

/*
 * TODO 8: Implement match_rule function
 * 
 * Guidelines:
 * - Compare packet fields against rule fields
 * - IP address: match if rule IP is "0.0.0.0" or equals packet IP
 * - Port: match if rule port is 0 or equals packet port
 * - Protocol: match if rule protocol is PROTO_ANY or equals packet protocol
 * - Return 1 if all fields match, 0 otherwise
 * 
 * Matching Logic:
 * - Empty/zero fields are wildcards (match anything)
 * - Non-empty fields must match exactly
 * - All specified fields must match for rule to apply
 * 
 * Hints:
 * - Use strcmp() for IP address comparison
 * - Handle NULL or empty strings as wildcards
 */
int match_rule(FirewallRule* rule, const char* src_ip, const char* dst_ip,
               int src_port, int dst_port, Protocol protocol) {
    // TODO: Check source IP (if not "0.0.0.0")
    // TODO: Check destination IP (if not "0.0.0.0")
    // TODO: Check source port (if not 0)
    // TODO: Check destination port (if not 0)
    // TODO: Check protocol (if not PROTO_ANY)
    // TODO: Return 1 if all checks pass, 0 otherwise
    return 0;
}

/*
 * TODO 9: Implement apply_rules function
 * 
 * Guidelines:
 * - Iterate through all enabled rules
 * - For each rule, check if packet matches using match_rule()
 * - If match found, apply the action (ACCEPT, DROP, LOG)
 * - If no match, apply default policy (typically ACCEPT)
 * - Update statistics
 * 
 * Rule Processing:
 * - First matching rule wins (like iptables)
 * - Rules are processed in order
 * - Default policy applies if no rules match
 * 
 * Hints:
 * - Extract IP addresses and ports from packet headers first
 * - Log the decision for debugging
 * - Return 1 for ACCEPT, 0 for DROP
 */
int apply_rules(unsigned char* buffer, int size) {
    // TODO: Parse packet to extract required fields
    // TODO: Get source/destination IPs and ports from packet
    // TODO: Determine protocol
    // TODO: Loop through rules and find first match
    // TODO: Apply action from matching rule
    // TODO: If no match, apply default policy
    // TODO: Update statistics
    
    // Default action: ACCEPT
    return 1;
}

/*
 * TODO 10: Implement process_packet function
 * 
 * Guidelines:
 * - Main packet processing function
 * - Parse Ethernet, IP, and transport layer headers
 * - Apply firewall rules
 * - Update statistics
 * - Log dropped packets
 * 
 * Processing Flow:
 * 1. Parse Ethernet frame
 * 2. Check if it's an IP packet
 * 3. Parse IP header
 * 4. Parse transport layer (TCP/UDP/ICMP) based on protocol
 * 5. Apply rules to decide ACCEPT or DROP
 * 6. Log the decision
 * 7. Update statistics
 * 
 * Hints:
 * - Call parse functions for debugging/logging
 * - apply_rules() returns the decision
 * - Consider rate limiting console output
 */
void process_packet(unsigned char* buffer, int size) {
    struct ethhdr* eth = (struct ethhdr*)buffer;
    struct iphdr* iph;
    
    stats.packets_received++;
    stats.bytes_received += size;
    
    // TODO: Check if it's an IP packet (EtherType 0x0800)
    if (ntohs(eth->h_proto) != ETH_P_IP) {
        // Not an IP packet, accept by default
        stats.packets_accepted++;
        return;
    }
    
    // TODO: Parse IP header
    iph = (struct iphdr*)(buffer + sizeof(struct ethhdr));
    
    // TODO: Based on protocol, parse appropriate transport header
    // TODO: Call apply_rules() to get decision
    // TODO: Update statistics based on decision
    // TODO: Log dropped packets
    
    printf("----------------------------------------\n");
    parse_ethernet_frame(buffer, size);
    parse_ip_header(buffer, size);
    
    // Parse transport layer based on protocol
    if (iph->protocol == IPPROTO_TCP) {
        parse_tcp_header(buffer, size, iph);
    } else if (iph->protocol == IPPROTO_UDP) {
        parse_udp_header(buffer, size, iph);
    } else if (iph->protocol == IPPROTO_ICMP) {
        parse_icmp_header(buffer, size, iph);
    }
    
    // Apply rules
    int action = apply_rules(buffer, size);
    if (action) {
        stats.packets_accepted++;
        printf("Action: ACCEPT\n");
    } else {
        stats.packets_dropped++;
        printf("Action: DROP\n");
    }
}

/*
 * TODO 11: Implement print_statistics function
 * 
 * Guidelines:
 * - Display firewall statistics in a readable format
 * - Show packets received, accepted, dropped
 * - Show bytes received
 * - Calculate and show drop rate percentage
 * 
 * Hints:
 * - Format numbers with thousand separators for readability
 * - Show bandwidth in human-readable units (KB, MB)
 */
void print_statistics() {
    printf("\n========================================\n");
    printf("Firewall Statistics\n");
    printf("========================================\n");
    // TODO: Print packets received
    // TODO: Print packets accepted
    // TODO: Print packets dropped
    // TODO: Print bytes received (in KB/MB)
    // TODO: Print drop rate percentage
    printf("Packets Received: %lu\n", stats.packets_received);
    printf("Packets Accepted: %lu\n", stats.packets_accepted);
    printf("Packets Dropped:  %lu\n", stats.packets_dropped);
    printf("Bytes Received:   %lu (%.2f MB)\n", 
           stats.bytes_received, stats.bytes_received / (1024.0 * 1024.0));
    if (stats.packets_received > 0) {
        float drop_rate = (stats.packets_dropped * 100.0) / stats.packets_received;
        printf("Drop Rate:        %.2f%%\n", drop_rate);
    }
    printf("========================================\n");
}

/*
 * TODO 12: Implement init_default_rules function
 * 
 * Guidelines:
 * - Add some default firewall rules for testing
 * - Example rules:
 *   - Block ICMP (ping) from any source
 *   - Block specific IP address
 *   - Block specific port (e.g., 22 for SSH)
 * - These are just examples for testing
 * 
 * Common Rules:
 * - Block all ICMP: src=any, dst=any, proto=ICMP, action=DROP
 * - Block port 22: src=any, dst=any, dst_port=22, action=DROP
 * - Allow HTTP: src=any, dst=any, dst_port=80, proto=TCP, action=ACCEPT
 * 
 * Hints:
 * - Use add_rule() function
 * - Start with simple rules for testing
 * - Comment out rules you don't want active
 */
void init_default_rules() {
    printf("Initializing default firewall rules...\n");
    
    // TODO: Add default rules here
    // Example: Block ICMP (uncomment to activate)
    // add_rule("0.0.0.0", "0.0.0.0", 0, 0, PROTO_ICMP, ACTION_DROP);
    
    // Example: Block SSH port 22 (uncomment to activate)
    // add_rule("0.0.0.0", "0.0.0.0", 0, 22, PROTO_TCP, ACTION_DROP);
    
    printf("Loaded %d firewall rules\n", rule_count);
}

/*
 * Main function
 */
int main(int argc, char* argv[]) {
    int sock;
    unsigned char* buffer;
    struct sockaddr saddr;
    int saddr_len = sizeof(saddr);
    int data_size;
    const char* interface = NULL;
    
    printf("========================================\n");
    printf("  Simple Packet Filtering Firewall\n");
    printf("========================================\n\n");
    
    // Parse command line arguments
    if (argc > 1) {
        interface = argv[1];
        printf("Binding to interface: %s\n", interface);
    } else {
        printf("Capturing on all interfaces\n");
        printf("Usage: %s [interface]\n", argv[0]);
        printf("Example: %s eth0\n\n", argv[0]);
    }
    
    // Set up signal handler for graceful shutdown
    signal(SIGINT, signal_handler);
    
    // Initialize default rules
    init_default_rules();
    
    // TODO: Create raw socket
    sock = create_raw_socket(interface);
    if (sock < 0) {
        perror("Socket creation failed");
        return 1;
    }
    
    printf("Raw socket created successfully\n");
    printf("Firewall is running... (Press Ctrl+C to stop)\n\n");
    
    // Allocate buffer for packet data
    buffer = (unsigned char*)malloc(BUFFER_SIZE);
    if (!buffer) {
        perror("Buffer allocation failed");
        close(sock);
        return 1;
    }
    
    // Main packet capture loop
    while (running) {
        // TODO: Receive packet using recvfrom()
        data_size = recvfrom(sock, buffer, BUFFER_SIZE, 0, &saddr, (socklen_t*)&saddr_len);
        if (data_size < 0) {
            if (running) {  // Only show error if not shutting down
                perror("Packet receive failed");
            }
            break;
        }
        
        // Process the packet
        process_packet(buffer, data_size);
    }
    
    // Cleanup
    print_statistics();
    free(buffer);
    close(sock);
    
    printf("\nFirewall stopped.\n");
    return 0;
}
