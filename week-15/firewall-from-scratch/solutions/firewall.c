/*
 * Firewall Implementation - Complete Solution
 * 
 * A fully functional packet filtering firewall implementation in C.
 * This solution demonstrates all concepts from the template with complete implementations.
 * 
 * Compilation: gcc -o firewall firewall.c
 * Usage: sudo ./firewall [interface]
 * 
 * Note: Requires root privileges for raw socket access
 */

#define _DEFAULT_SOURCE
#define _BSD_SOURCE

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
 * Create a raw socket for packet capture
 * 
 * This function creates a raw socket at the link layer (Ethernet level) which
 * allows us to capture all network packets before they reach the OS network stack.
 * 
 * Parameters:
 *   interface - Network interface name to bind to (e.g., "eth0"), or NULL for all
 * 
 * Returns:
 *   Socket file descriptor on success, -1 on error
 */
int create_raw_socket(const char* interface) {
    int sock;
    
    // Create raw socket with AF_PACKET to capture at link layer
    // SOCK_RAW provides raw packet access
    // ETH_P_ALL captures all Ethernet protocols (IP, ARP, etc.)
    sock = socket(AF_PACKET, SOCK_RAW, htons(ETH_P_ALL));
    if (sock < 0) {
        return -1;
    }
    
    // If a specific interface is specified, bind the socket to it
    if (interface != NULL) {
        struct ifreq ifr;
        
        // Clear the interface request structure
        memset(&ifr, 0, sizeof(ifr));
        
        // Copy interface name (safely with size limit)
        strncpy(ifr.ifr_name, interface, IFNAMSIZ - 1);
        ifr.ifr_name[IFNAMSIZ - 1] = '\0';  // Ensure null termination
        
        // Bind socket to the specified interface
        if (setsockopt(sock, SOL_SOCKET, SO_BINDTODEVICE, &ifr, sizeof(ifr)) < 0) {
            perror("Failed to bind to interface");
            close(sock);
            return -1;
        }
    }
    
    return sock;
}

/*
 * Parse and display Ethernet frame information
 * 
 * Ethernet is the link layer protocol. Each frame contains source and destination
 * MAC addresses and an EtherType field that indicates the protocol of the payload.
 * 
 * Parameters:
 *   buffer - Packet buffer starting with Ethernet header
 *   size   - Total packet size in bytes
 */
void parse_ethernet_frame(unsigned char* buffer, int size) {
    struct ethhdr* eth = (struct ethhdr*)buffer;
    (void)size;  // Size parameter available for future validation
    
    printf("Ethernet Frame:\n");
    
    // Display source MAC address (6 bytes)
    printf("  Source MAC:      %02X:%02X:%02X:%02X:%02X:%02X\n",
           eth->h_source[0], eth->h_source[1], eth->h_source[2],
           eth->h_source[3], eth->h_source[4], eth->h_source[5]);
    
    // Display destination MAC address (6 bytes)
    printf("  Dest MAC:        %02X:%02X:%02X:%02X:%02X:%02X\n",
           eth->h_dest[0], eth->h_dest[1], eth->h_dest[2],
           eth->h_dest[3], eth->h_dest[4], eth->h_dest[5]);
    
    // Display EtherType (protocol) - convert from network to host byte order
    unsigned short eth_proto = ntohs(eth->h_proto);
    printf("  Protocol:        0x%04X ", eth_proto);
    
    // Interpret common EtherType values
    switch(eth_proto) {
        case ETH_P_IP:
            printf("(IPv4)\n");
            break;
        case ETH_P_IPV6:
            printf("(IPv6)\n");
            break;
        case ETH_P_ARP:
            printf("(ARP)\n");
            break;
        default:
            printf("(Other)\n");
            break;
    }
}

/*
 * Parse and display IP header information
 * 
 * The IP header contains routing information including source/destination addresses,
 * protocol type (TCP/UDP/ICMP), and various control fields.
 * 
 * Parameters:
 *   buffer - Packet buffer starting with Ethernet header
 *   size   - Total packet size in bytes
 */
void parse_ip_header(unsigned char* buffer, int size) {
    // IP header starts after Ethernet header
    struct iphdr* iph = (struct iphdr*)(buffer + sizeof(struct ethhdr));
    struct sockaddr_in source, dest;
    (void)size;  // Size parameter available for future validation
    
    // Zero out address structures
    memset(&source, 0, sizeof(source));
    memset(&dest, 0, sizeof(dest));
    
    // Set up source and destination address structures
    source.sin_addr.s_addr = iph->saddr;
    dest.sin_addr.s_addr = iph->daddr;
    
    printf("IP Header:\n");
    
    // IP version (should be 4 for IPv4)
    printf("  IP Version:      %d\n", (unsigned int)iph->version);
    
    // Header length in 32-bit words (multiply by 4 to get bytes)
    printf("  Header Length:   %d bytes\n", ((unsigned int)(iph->ihl)) * 4);
    
    // Type of Service (QoS field)
    printf("  Type Of Service: %d\n", (unsigned int)iph->tos);
    
    // Total packet length (convert from network byte order)
    printf("  Total Length:    %d bytes\n", ntohs(iph->tot_len));
    
    // Identification field (for fragmentation)
    printf("  Identification:  %d\n", ntohs(iph->id));
    
    // Time To Live (decremented at each hop)
    printf("  TTL:             %d\n", (unsigned int)iph->ttl);
    
    // Protocol field indicates next layer (TCP=6, UDP=17, ICMP=1)
    printf("  Protocol:        %d ", (unsigned int)iph->protocol);
    switch(iph->protocol) {
        case IPPROTO_TCP:
            printf("(TCP)\n");
            break;
        case IPPROTO_UDP:
            printf("(UDP)\n");
            break;
        case IPPROTO_ICMP:
            printf("(ICMP)\n");
            break;
        default:
            printf("(Other)\n");
            break;
    }
    
    // Header checksum
    printf("  Checksum:        %d\n", ntohs(iph->check));
    
    // Source and destination IP addresses
    printf("  Source IP:       %s\n", inet_ntoa(source.sin_addr));
    printf("  Dest IP:         %s\n", inet_ntoa(dest.sin_addr));
}

/*
 * Parse and display TCP header information
 * 
 * TCP is a connection-oriented transport protocol. The header contains port numbers,
 * sequence/acknowledgment numbers, flags, and window information.
 * 
 * Parameters:
 *   buffer - Packet buffer starting with Ethernet header
 *   size   - Total packet size in bytes
 *   iph    - Pointer to IP header (needed to calculate TCP header offset)
 */
void parse_tcp_header(unsigned char* buffer, int size, struct iphdr* iph) {
    // Calculate IP header length to find TCP header
    unsigned short iphdrlen = iph->ihl * 4;
    struct tcphdr* tcph = (struct tcphdr*)(buffer + iphdrlen + sizeof(struct ethhdr));
    (void)size;  // Size parameter available for future validation
    
    printf("TCP Header:\n");
    
    // Source and destination ports (convert from network byte order)
    printf("  Source Port:     %u\n", ntohs(tcph->source));
    printf("  Dest Port:       %u\n", ntohs(tcph->dest));
    
    // Sequence number (for reliable delivery)
    printf("  Sequence Num:    %u\n", ntohl(tcph->seq));
    
    // Acknowledgment number
    printf("  Ack Num:         %u\n", ntohl(tcph->ack_seq));
    
    // TCP header length in 32-bit words
    printf("  Header Length:   %d bytes\n", (unsigned int)tcph->doff * 4);
    
    // TCP flags - indicate connection state and control
    printf("  Flags:           ");
    if (tcph->urg) printf("URG ");  // Urgent pointer is valid
    if (tcph->ack) printf("ACK ");  // Acknowledgment number is valid
    if (tcph->psh) printf("PSH ");  // Push data to application immediately
    if (tcph->rst) printf("RST ");  // Reset connection
    if (tcph->syn) printf("SYN ");  // Synchronize sequence numbers (connection setup)
    if (tcph->fin) printf("FIN ");  // Finish, no more data (connection teardown)
    printf("\n");
    
    // Window size (for flow control)
    printf("  Window Size:     %d\n", ntohs(tcph->window));
    
    // Checksum
    printf("  Checksum:        %d\n", ntohs(tcph->check));
    
    // Urgent pointer (if URG flag is set)
    printf("  Urgent Pointer:  %d\n", ntohs(tcph->urg_ptr));
}

/*
 * Parse and display UDP header information
 * 
 * UDP is a connectionless transport protocol. The header is simpler than TCP,
 * containing only ports, length, and checksum.
 * 
 * Parameters:
 *   buffer - Packet buffer starting with Ethernet header
 *   size   - Total packet size in bytes
 *   iph    - Pointer to IP header (needed to calculate UDP header offset)
 */
void parse_udp_header(unsigned char* buffer, int size, struct iphdr* iph) {
    // Calculate IP header length to find UDP header
    unsigned short iphdrlen = iph->ihl * 4;
    struct udphdr* udph = (struct udphdr*)(buffer + iphdrlen + sizeof(struct ethhdr));
    (void)size;  // Size parameter available for future validation
    
    printf("UDP Header:\n");
    
    // Source and destination ports (convert from network byte order)
    printf("  Source Port:     %u\n", ntohs(udph->source));
    printf("  Dest Port:       %u\n", ntohs(udph->dest));
    
    // UDP length (header + data)
    printf("  Length:          %d bytes\n", ntohs(udph->len));
    
    // Checksum (optional in IPv4)
    printf("  Checksum:        %d\n", ntohs(udph->check));
}

/*
 * Parse and display ICMP header information
 * 
 * ICMP is used for network diagnostics and error reporting. Common types include
 * Echo Request/Reply (ping), Destination Unreachable, and Time Exceeded.
 * 
 * Parameters:
 *   buffer - Packet buffer starting with Ethernet header
 *   size   - Total packet size in bytes
 *   iph    - Pointer to IP header (needed to calculate ICMP header offset)
 */
void parse_icmp_header(unsigned char* buffer, int size, struct iphdr* iph) {
    // Calculate IP header length to find ICMP header
    unsigned short iphdrlen = iph->ihl * 4;
    struct icmphdr* icmph = (struct icmphdr*)(buffer + iphdrlen + sizeof(struct ethhdr));
    (void)size;  // Size parameter available for future validation
    
    printf("ICMP Header:\n");
    
    // ICMP type and code identify the message type
    printf("  Type:            %d ", (unsigned int)(icmph->type));
    
    // Interpret common ICMP types
    switch(icmph->type) {
        case ICMP_ECHOREPLY:
            printf("(Echo Reply)\n");
            break;
        case ICMP_DEST_UNREACH:
            printf("(Destination Unreachable)\n");
            break;
        case ICMP_SOURCE_QUENCH:
            printf("(Source Quench)\n");
            break;
        case ICMP_REDIRECT:
            printf("(Redirect)\n");
            break;
        case ICMP_ECHO:
            printf("(Echo Request/Ping)\n");
            break;
        case ICMP_TIME_EXCEEDED:
            printf("(Time Exceeded)\n");
            break;
        case ICMP_PARAMETERPROB:
            printf("(Parameter Problem)\n");
            break;
        case ICMP_TIMESTAMP:
            printf("(Timestamp Request)\n");
            break;
        case ICMP_TIMESTAMPREPLY:
            printf("(Timestamp Reply)\n");
            break;
        case ICMP_INFO_REQUEST:
            printf("(Information Request)\n");
            break;
        case ICMP_INFO_REPLY:
            printf("(Information Reply)\n");
            break;
        default:
            printf("(Other)\n");
            break;
    }
    
    // ICMP code provides additional detail about the type
    printf("  Code:            %d\n", (unsigned int)(icmph->code));
    
    // Checksum
    printf("  Checksum:        %d\n", ntohs(icmph->checksum));
}

/*
 * Add a new firewall rule
 * 
 * Rules define what action to take (ACCEPT, DROP, LOG) for packets matching
 * specific criteria. Use "0.0.0.0" for any IP, 0 for any port, PROTO_ANY for
 * any protocol.
 * 
 * Parameters:
 *   src_ip   - Source IP address filter ("0.0.0.0" for any)
 *   dst_ip   - Destination IP address filter ("0.0.0.0" for any)
 *   src_port - Source port filter (0 for any)
 *   dst_port - Destination port filter (0 for any)
 *   protocol - Protocol filter (PROTO_ANY for any)
 *   action   - Action to take (ACTION_ACCEPT, ACTION_DROP, ACTION_LOG)
 * 
 * Returns:
 *   0 on success, -1 on error
 */
int add_rule(const char* src_ip, const char* dst_ip, int src_port, 
             int dst_port, Protocol protocol, RuleAction action) {
    // Check if we've reached maximum number of rules
    if (rule_count >= MAX_RULES) {
        fprintf(stderr, "Error: Maximum number of rules (%d) reached\n", MAX_RULES);
        return -1;
    }
    
    // Get pointer to next available rule slot
    FirewallRule* rule = &rules[rule_count];
    
    // Copy source IP address (or use "0.0.0.0" for any)
    if (src_ip != NULL) {
        strncpy(rule->src_ip, src_ip, MAX_IP_STR - 1);
        rule->src_ip[MAX_IP_STR - 1] = '\0';
    } else {
        strcpy(rule->src_ip, "0.0.0.0");
    }
    
    // Copy destination IP address (or use "0.0.0.0" for any)
    if (dst_ip != NULL) {
        strncpy(rule->dst_ip, dst_ip, MAX_IP_STR - 1);
        rule->dst_ip[MAX_IP_STR - 1] = '\0';
    } else {
        strcpy(rule->dst_ip, "0.0.0.0");
    }
    
    // Set port filters
    rule->src_port = src_port;
    rule->dst_port = dst_port;
    
    // Set protocol and action
    rule->protocol = protocol;
    rule->action = action;
    
    // Enable the rule
    rule->enabled = 1;
    
    // Increment rule counter
    rule_count++;
    
    return 0;
}

/*
 * Check if a packet matches a firewall rule
 * 
 * A packet matches a rule if all non-wildcard fields match. Wildcard values
 * (0.0.0.0 for IP, 0 for port, PROTO_ANY for protocol) match any value.
 * 
 * Parameters:
 *   rule     - Firewall rule to check against
 *   src_ip   - Packet source IP address
 *   dst_ip   - Packet destination IP address
 *   src_port - Packet source port
 *   dst_port - Packet destination port
 *   protocol - Packet protocol
 * 
 * Returns:
 *   1 if packet matches rule, 0 otherwise
 */
int match_rule(FirewallRule* rule, const char* src_ip, const char* dst_ip,
               int src_port, int dst_port, Protocol protocol) {
    // Check if rule is enabled
    if (!rule->enabled) {
        return 0;
    }
    
    // Check source IP (0.0.0.0 means match any)
    if (strcmp(rule->src_ip, "0.0.0.0") != 0) {
        if (strcmp(rule->src_ip, src_ip) != 0) {
            return 0;
        }
    }
    
    // Check destination IP (0.0.0.0 means match any)
    if (strcmp(rule->dst_ip, "0.0.0.0") != 0) {
        if (strcmp(rule->dst_ip, dst_ip) != 0) {
            return 0;
        }
    }
    
    // Check source port (0 means match any)
    if (rule->src_port != 0) {
        if (rule->src_port != src_port) {
            return 0;
        }
    }
    
    // Check destination port (0 means match any)
    if (rule->dst_port != 0) {
        if (rule->dst_port != dst_port) {
            return 0;
        }
    }
    
    // Check protocol (PROTO_ANY means match any)
    if (rule->protocol != PROTO_ANY) {
        if (rule->protocol != protocol) {
            return 0;
        }
    }
    
    // All checks passed - packet matches this rule
    return 1;
}

/*
 * Apply firewall rules to a packet
 * 
 * This function extracts packet information and checks it against all rules
 * in order. The first matching rule determines the action. If no rules match,
 * the default policy (ACCEPT) is applied.
 * 
 * Parameters:
 *   buffer - Packet buffer starting with Ethernet header
 *   size   - Total packet size in bytes
 * 
 * Returns:
 *   1 for ACCEPT, 0 for DROP
 */
int apply_rules(unsigned char* buffer, int size) {
    struct ethhdr* eth = (struct ethhdr*)buffer;
    struct iphdr* iph;
    struct sockaddr_in source, dest;
    char src_ip[MAX_IP_STR];
    char dst_ip[MAX_IP_STR];
    int src_port = 0;
    int dst_port = 0;
    Protocol protocol;
    (void)size;  // Size parameter available for future validation
    
    // Only process IP packets
    if (ntohs(eth->h_proto) != ETH_P_IP) {
        return 1;  // Accept non-IP packets by default
    }
    
    // Get IP header
    iph = (struct iphdr*)(buffer + sizeof(struct ethhdr));
    unsigned short iphdrlen = iph->ihl * 4;
    
    // Extract source and destination IP addresses
    memset(&source, 0, sizeof(source));
    memset(&dest, 0, sizeof(dest));
    source.sin_addr.s_addr = iph->saddr;
    dest.sin_addr.s_addr = iph->daddr;
    
    // Use inet_ntop or store first result before second call to avoid buffer reuse
    char* temp_src = inet_ntoa(source.sin_addr);
    strncpy(src_ip, temp_src, MAX_IP_STR - 1);
    src_ip[MAX_IP_STR - 1] = '\0';
    
    char* temp_dst = inet_ntoa(dest.sin_addr);
    strncpy(dst_ip, temp_dst, MAX_IP_STR - 1);
    dst_ip[MAX_IP_STR - 1] = '\0';
    
    // Extract protocol
    protocol = (Protocol)iph->protocol;
    
    // Extract port information based on protocol
    if (iph->protocol == IPPROTO_TCP) {
        struct tcphdr* tcph = (struct tcphdr*)(buffer + iphdrlen + sizeof(struct ethhdr));
        src_port = ntohs(tcph->source);
        dst_port = ntohs(tcph->dest);
    } else if (iph->protocol == IPPROTO_UDP) {
        struct udphdr* udph = (struct udphdr*)(buffer + iphdrlen + sizeof(struct ethhdr));
        src_port = ntohs(udph->source);
        dst_port = ntohs(udph->dest);
    }
    // ICMP doesn't have ports
    
    // Check packet against all rules
    for (int i = 0; i < rule_count; i++) {
        if (match_rule(&rules[i], src_ip, dst_ip, src_port, dst_port, protocol)) {
            // Found a matching rule
            printf("  Matched Rule %d: ", i + 1);
            
            switch(rules[i].action) {
                case ACTION_DROP:
                    printf("DROP\n");
                    return 0;  // Drop packet
                    
                case ACTION_ACCEPT:
                    printf("ACCEPT\n");
                    return 1;  // Accept packet
                    
                case ACTION_LOG:
                    printf("LOG (and ACCEPT)\n");
                    // Log and continue checking rules
                    break;
            }
        }
    }
    
    // No matching rule found - apply default policy (ACCEPT)
    printf("  No rule matched - Default: ACCEPT\n");
    return 1;
}

/*
 * Process a captured packet
 * 
 * This is the main packet processing function. It parses the packet headers,
 * applies firewall rules, and updates statistics.
 * 
 * Parameters:
 *   buffer - Packet buffer starting with Ethernet header
 *   size   - Total packet size in bytes
 */
void process_packet(unsigned char* buffer, int size) {
    struct ethhdr* eth = (struct ethhdr*)buffer;
    struct iphdr* iph;
    
    // Update basic statistics
    stats.packets_received++;
    stats.bytes_received += size;
    
    // Only process IP packets for filtering
    if (ntohs(eth->h_proto) != ETH_P_IP) {
        // Accept non-IP packets by default (e.g., ARP)
        stats.packets_accepted++;
        return;
    }
    
    // Get IP header
    iph = (struct iphdr*)(buffer + sizeof(struct ethhdr));
    
    // Print packet separator
    printf("----------------------------------------\n");
    
    // Parse and display headers
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
    
    // Apply firewall rules and get decision
    int action = apply_rules(buffer, size);
    
    // Update statistics based on action
    if (action) {
        stats.packets_accepted++;
        printf("Action: ACCEPT\n");
    } else {
        stats.packets_dropped++;
        printf("Action: DROP\n");
    }
}

/*
 * Print firewall statistics
 * 
 * Displays a summary of firewall activity including packets processed,
 * accepted, dropped, and bandwidth statistics.
 */
void print_statistics() {
    printf("\n========================================\n");
    printf("Firewall Statistics\n");
    printf("========================================\n");
    
    // Display packet counts
    printf("Packets Received: %lu\n", stats.packets_received);
    printf("Packets Accepted: %lu\n", stats.packets_accepted);
    printf("Packets Dropped:  %lu\n", stats.packets_dropped);
    
    // Display bandwidth statistics
    printf("Bytes Received:   %lu (%.2f KB, %.2f MB)\n", 
           stats.bytes_received, 
           stats.bytes_received / 1024.0,
           stats.bytes_received / (1024.0 * 1024.0));
    
    // Calculate and display drop rate
    if (stats.packets_received > 0) {
        float drop_rate = (stats.packets_dropped * 100.0) / stats.packets_received;
        float accept_rate = (stats.packets_accepted * 100.0) / stats.packets_received;
        printf("Drop Rate:        %.2f%%\n", drop_rate);
        printf("Accept Rate:      %.2f%%\n", accept_rate);
    }
    
    printf("========================================\n");
}

/*
 * Initialize default firewall rules
 * 
 * This function sets up example firewall rules for testing and demonstration.
 * In a production firewall, these would be loaded from a configuration file.
 * 
 * Example rules included (commented out by default):
 * - Block all ICMP traffic (ping blocking)
 * - Block SSH access (port 22)
 * - Block Telnet access (port 23)
 * - Allow HTTP traffic (port 80)
 * - Allow HTTPS traffic (port 443)
 */
void init_default_rules() {
    printf("Initializing default firewall rules...\n");
    
    // Example 1: Block all ICMP traffic (uncomment to activate)
    // This will block all ping requests and replies
    // add_rule("0.0.0.0", "0.0.0.0", 0, 0, PROTO_ICMP, ACTION_DROP);
    // printf("  Rule 1: DROP all ICMP traffic\n");
    
    // Example 2: Block SSH connections on port 22 (uncomment to activate)
    // This blocks incoming SSH connections for security
    // add_rule("0.0.0.0", "0.0.0.0", 0, 22, PROTO_TCP, ACTION_DROP);
    // printf("  Rule 2: DROP TCP port 22 (SSH)\n");
    
    // Example 3: Block Telnet connections on port 23 (uncomment to activate)
    // Telnet is insecure and should typically be blocked
    // add_rule("0.0.0.0", "0.0.0.0", 0, 23, PROTO_TCP, ACTION_DROP);
    // printf("  Rule 3: DROP TCP port 23 (Telnet)\n");
    
    // Example 4: Allow HTTP traffic on port 80 (uncomment to activate)
    // This explicitly allows web traffic
    // add_rule("0.0.0.0", "0.0.0.0", 0, 80, PROTO_TCP, ACTION_ACCEPT);
    // printf("  Rule 4: ACCEPT TCP port 80 (HTTP)\n");
    
    // Example 5: Allow HTTPS traffic on port 443 (uncomment to activate)
    // This explicitly allows secure web traffic
    // add_rule("0.0.0.0", "0.0.0.0", 0, 443, PROTO_TCP, ACTION_ACCEPT);
    // printf("  Rule 5: ACCEPT TCP port 443 (HTTPS)\n");
    
    // Example 6: Block traffic from specific IP (uncomment and modify to activate)
    // Replace "192.168.1.100" with actual IP to block
    // add_rule("192.168.1.100", "0.0.0.0", 0, 0, PROTO_ANY, ACTION_DROP);
    // printf("  Rule 6: DROP all traffic from 192.168.1.100\n");
    
    // Example 7: Block traffic to specific IP (uncomment and modify to activate)
    // Replace "10.0.0.50" with actual IP to block
    // add_rule("0.0.0.0", "10.0.0.50", 0, 0, PROTO_ANY, ACTION_DROP);
    // printf("  Rule 7: DROP all traffic to 10.0.0.50\n");
    
    // Example 8: Log all DNS queries (port 53) (uncomment to activate)
    // This will log DNS traffic but still allow it through
    // add_rule("0.0.0.0", "0.0.0.0", 0, 53, PROTO_UDP, ACTION_LOG);
    // printf("  Rule 8: LOG UDP port 53 (DNS)\n");
    
    printf("Loaded %d firewall rules\n", rule_count);
    
    if (rule_count == 0) {
        printf("  (All rules are commented out - using default ACCEPT policy)\n");
        printf("  Edit init_default_rules() to activate example rules\n");
    }
}

/*
 * Main function
 * 
 * Entry point for the firewall program. Handles initialization, packet capture,
 * and cleanup.
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
    
    // Set up signal handler for graceful shutdown (Ctrl+C)
    signal(SIGINT, signal_handler);
    
    // Initialize firewall rules
    init_default_rules();
    
    // Create raw socket for packet capture
    sock = create_raw_socket(interface);
    if (sock < 0) {
        perror("Socket creation failed");
        printf("\nNote: This program requires root privileges\n");
        printf("Try running: sudo %s\n", argv[0]);
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
        // Receive packet from socket
        data_size = recvfrom(sock, buffer, BUFFER_SIZE, 0, &saddr, (socklen_t*)&saddr_len);
        if (data_size < 0) {
            if (running) {  // Only show error if not shutting down
                perror("Packet receive failed");
            }
            break;
        }
        
        // Process the received packet
        process_packet(buffer, data_size);
    }
    
    // Cleanup
    print_statistics();
    free(buffer);
    close(sock);
    
    printf("\nFirewall stopped.\n");
    return 0;
}
