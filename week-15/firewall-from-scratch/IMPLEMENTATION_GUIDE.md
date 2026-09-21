# Firewall Implementation Guide

This guide provides step-by-step instructions for implementing the packet filtering firewall. Follow each TODO in order, testing as you go.

## Table of Contents

1. [Setup and Prerequisites](#setup-and-prerequisites)
2. [TODO 1: Create Raw Socket](#todo-1-create-raw-socket)
3. [TODO 2: Parse Ethernet Frame](#todo-2-parse-ethernet-frame)
4. [TODO 3: Parse IP Header](#todo-3-parse-ip-header)
5. [TODO 4: Parse TCP Header](#todo-4-parse-tcp-header)
6. [TODO 5: Parse UDP Header](#todo-5-parse-udp-header)
7. [TODO 6: Parse ICMP Header](#todo-6-parse-icmp-header)
8. [TODO 7: Add Firewall Rule](#todo-7-add-firewall-rule)
9. [TODO 8: Match Rule](#todo-8-match-rule)
10. [TODO 9: Apply Rules](#todo-9-apply-rules)
11. [TODO 10: Process Packet](#todo-10-process-packet)
12. [TODO 11: Print Statistics](#todo-11-print-statistics)
13. [TODO 12: Initialize Default Rules](#todo-12-initialize-default-rules)

---

## Setup and Prerequisites

### Required Packages

```bash
# Ubuntu/Debian
sudo apt-get install build-essential tcpdump wireshark

# Fedora/RHEL
sudo dnf install gcc tcpdump wireshark

# Arch Linux
sudo pacman -S gcc tcpdump wireshark-qt
```

### Understanding Raw Sockets

Raw sockets allow you to:
- Capture packets at the link layer (Ethernet)
- See all packets on the network interface
- Access packet headers directly
- Require root/administrator privileges

### Important Concepts

**Network Byte Order**: Network protocols use big-endian byte order. Always use:
- `ntohs()` - Network to Host Short (16-bit)
- `ntohl()` - Network to Host Long (32-bit)
- `htons()` - Host to Network Short
- `htonl()` - Host to Network Long

**Packet Structure**:
```
┌──────────────┐
│   Ethernet   │  14 bytes
├──────────────┤
│   IP Header  │  20+ bytes
├──────────────┤
│  TCP/UDP/    │  Variable
│  ICMP Header │
├──────────────┤
│   Payload    │  Variable
└──────────────┘
```

---

## TODO 1: Create Raw Socket

**Location**: `create_raw_socket()` function

### What You Need to Do

Create a raw socket that can capture all network packets on an interface.

### Implementation

```c
int create_raw_socket(const char* interface) {
    int sock;
    struct sockaddr_ll sll;
    
    // Create raw socket with AF_PACKET to capture link layer
    sock = socket(AF_PACKET, SOCK_RAW, htons(ETH_P_ALL));
    if (sock < 0) {
        perror("Socket creation failed");
        return -1;
    }
    
    // If specific interface requested, bind to it
    if (interface != NULL) {
        struct ifreq ifr;
        
        memset(&ifr, 0, sizeof(ifr));
        strncpy(ifr.ifr_name, interface, IFNAMSIZ - 1);
        
        // Get interface index
        if (ioctl(sock, SIOCGIFINDEX, &ifr) < 0) {
            perror("Interface not found");
            close(sock);
            return -1;
        }
        
        // Bind socket to interface
        memset(&sll, 0, sizeof(sll));
        sll.sll_family = AF_PACKET;
        sll.sll_ifindex = ifr.ifr_index;
        sll.sll_protocol = htons(ETH_P_ALL);
        
        if (bind(sock, (struct sockaddr*)&sll, sizeof(sll)) < 0) {
            perror("Bind failed");
            close(sock);
            return -1;
        }
    }
    
    return sock;
}
```

### Testing

```bash
make
sudo ./firewall

# You should see: "Raw socket created successfully"
# Press Ctrl+C to stop
```

### Key Points

- `AF_PACKET` gives access to link layer (Ethernet frames)
- `SOCK_RAW` means we get raw packets, not processed by kernel
- `ETH_P_ALL` captures all protocol types
- Root privileges required for raw socket access
- Binding to specific interface is optional but recommended

---

## TODO 2: Parse Ethernet Frame

**Location**: `parse_ethernet_frame()` function

### What You Need to Do

Extract and display information from the Ethernet frame header.

### Implementation

```c
void parse_ethernet_frame(unsigned char* buffer, int size) {
    struct ethhdr* eth = (struct ethhdr*)buffer;
    
    printf("Ethernet Frame:\n");
    printf("  Source MAC:      %02x:%02x:%02x:%02x:%02x:%02x\n",
           eth->h_source[0], eth->h_source[1], eth->h_source[2],
           eth->h_source[3], eth->h_source[4], eth->h_source[5]);
    printf("  Dest MAC:        %02x:%02x:%02x:%02x:%02x:%02x\n",
           eth->h_dest[0], eth->h_dest[1], eth->h_dest[2],
           eth->h_dest[3], eth->h_dest[4], eth->h_dest[5]);
    
    unsigned short eth_type = ntohs(eth->h_proto);
    printf("  Protocol:        0x%04x ", eth_type);
    
    switch(eth_type) {
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
```

### Testing

```bash
sudo ./firewall

# In another terminal:
ping 8.8.8.8

# You should see Ethernet frame information including MAC addresses
```

### Key Points

- Ethernet header is always first (14 bytes)
- MAC addresses are 6 bytes each
- EtherType tells us the next layer protocol
- 0x0800 = IPv4, 0x86DD = IPv6, 0x0806 = ARP

---

## TODO 3: Parse IP Header

**Location**: `parse_ip_header()` function

### What You Need to Do

Extract and display IP header information.

### Implementation

```c
void parse_ip_header(unsigned char* buffer, int size) {
    struct iphdr* iph = (struct iphdr*)(buffer + sizeof(struct ethhdr));
    struct sockaddr_in source, dest;
    
    memset(&source, 0, sizeof(source));
    source.sin_addr.s_addr = iph->saddr;
    
    memset(&dest, 0, sizeof(dest));
    dest.sin_addr.s_addr = iph->daddr;
    
    printf("IP Header:\n");
    printf("  Version:         %d\n", (unsigned int)iph->version);
    printf("  Header Length:   %d bytes\n", (unsigned int)(iph->ihl * 4));
    printf("  Type of Service: %d\n", (unsigned int)iph->tos);
    printf("  Total Length:    %d bytes\n", ntohs(iph->tot_len));
    printf("  TTL:             %d\n", (unsigned int)iph->ttl);
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
    
    printf("  Source IP:       %s\n", inet_ntoa(source.sin_addr));
    printf("  Dest IP:         %s\n", inet_ntoa(dest.sin_addr));
}
```

### Testing

```bash
sudo ./firewall

# In another terminal:
curl http://example.com

# You should see IP addresses and protocol information
```

### Key Points

- IP header follows Ethernet header (skip 14 bytes)
- Header length (ihl) is in 4-byte words, multiply by 4 for bytes
- Protocol field tells us next layer (6=TCP, 17=UDP, 1=ICMP)
- IP addresses stored in network byte order
- Use `inet_ntoa()` to convert IP to string

---

## TODO 4: Parse TCP Header

**Location**: `parse_tcp_header()` function

### Implementation

```c
void parse_tcp_header(unsigned char* buffer, int size, struct iphdr* iph) {
    unsigned short iphdrlen = iph->ihl * 4;
    struct tcphdr* tcph = (struct tcphdr*)(buffer + iphdrlen + sizeof(struct ethhdr));
    
    printf("TCP Header:\n");
    printf("  Source Port:     %u\n", ntohs(tcph->source));
    printf("  Dest Port:       %u\n", ntohs(tcph->dest));
    printf("  Sequence:        %u\n", ntohl(tcph->seq));
    printf("  Ack Sequence:    %u\n", ntohl(tcph->ack_seq));
    printf("  Flags:           ");
    
    if (tcph->syn) printf("SYN ");
    if (tcph->ack) printf("ACK ");
    if (tcph->psh) printf("PSH ");
    if (tcph->fin) printf("FIN ");
    if (tcph->rst) printf("RST ");
    if (tcph->urg) printf("URG ");
    printf("\n");
    
    printf("  Window Size:     %u\n", ntohs(tcph->window));
}
```

### Testing

```bash
sudo ./firewall

# In another terminal:
curl http://example.com

# You should see TCP ports and flags (SYN, ACK, etc.)
```

---

## TODO 5: Parse UDP Header

**Location**: `parse_udp_header()` function

### Implementation

```c
void parse_udp_header(unsigned char* buffer, int size, struct iphdr* iph) {
    unsigned short iphdrlen = iph->ihl * 4;
    struct udphdr* udph = (struct udphdr*)(buffer + iphdrlen + sizeof(struct ethhdr));
    
    printf("UDP Header:\n");
    printf("  Source Port:     %u\n", ntohs(udph->source));
    printf("  Dest Port:       %u\n", ntohs(udph->dest));
    printf("  Length:          %u\n", ntohs(udph->len));
    printf("  Checksum:        %u\n", ntohs(udph->check));
}
```

### Testing

```bash
sudo ./firewall

# In another terminal:
dig @8.8.8.8 google.com

# You should see UDP header with ports (likely 53 for DNS)
```

---

## TODO 6: Parse ICMP Header

**Location**: `parse_icmp_header()` function

### Implementation

```c
void parse_icmp_header(unsigned char* buffer, int size, struct iphdr* iph) {
    unsigned short iphdrlen = iph->ihl * 4;
    struct icmphdr* icmph = (struct icmphdr*)(buffer + iphdrlen + sizeof(struct ethhdr));
    
    printf("ICMP Header:\n");
    printf("  Type:            %d ", (unsigned int)icmph->type);
    
    switch(icmph->type) {
        case ICMP_ECHO:
            printf("(Echo Request/Ping)\n");
            break;
        case ICMP_ECHOREPLY:
            printf("(Echo Reply/Pong)\n");
            break;
        case ICMP_DEST_UNREACH:
            printf("(Destination Unreachable)\n");
            break;
        case ICMP_TIME_EXCEEDED:
            printf("(Time Exceeded)\n");
            break;
        default:
            printf("(Other)\n");
            break;
    }
    
    printf("  Code:            %d\n", (unsigned int)icmph->code);
}
```

### Testing

```bash
sudo ./firewall

# In another terminal:
ping 8.8.8.8

# You should see ICMP type 8 (Echo Request) and type 0 (Echo Reply)
```

---

## TODO 7: Add Firewall Rule

**Location**: `add_rule()` function

### Implementation

```c
int add_rule(const char* src_ip, const char* dst_ip, int src_port, 
             int dst_port, Protocol protocol, RuleAction action) {
    if (rule_count >= MAX_RULES) {
        fprintf(stderr, "Maximum number of rules reached\n");
        return -1;
    }
    
    FirewallRule* rule = &rules[rule_count];
    
    // Copy source IP (use "0.0.0.0" for any)
    if (src_ip != NULL) {
        strncpy(rule->src_ip, src_ip, MAX_IP_STR - 1);
    } else {
        strcpy(rule->src_ip, "0.0.0.0");
    }
    
    // Copy destination IP (use "0.0.0.0" for any)
    if (dst_ip != NULL) {
        strncpy(rule->dst_ip, dst_ip, MAX_IP_STR - 1);
    } else {
        strcpy(rule->dst_ip, "0.0.0.0");
    }
    
    rule->src_port = src_port;
    rule->dst_port = dst_port;
    rule->protocol = protocol;
    rule->action = action;
    rule->enabled = 1;
    
    rule_count++;
    
    printf("  Rule %d: src=%s:%d dst=%s:%d proto=%d action=%s\n",
           rule_count, rule->src_ip, rule->src_port,
           rule->dst_ip, rule->dst_port, rule->protocol,
           (action == ACTION_ACCEPT ? "ACCEPT" : 
            action == ACTION_DROP ? "DROP" : "LOG"));
    
    return 0;
}
```

---

## TODO 8: Match Rule

**Location**: `match_rule()` function

### Implementation

```c
int match_rule(FirewallRule* rule, const char* src_ip, const char* dst_ip,
               int src_port, int dst_port, Protocol protocol) {
    // Check source IP (0.0.0.0 means any)
    if (strcmp(rule->src_ip, "0.0.0.0") != 0) {
        if (strcmp(rule->src_ip, src_ip) != 0) {
            return 0;
        }
    }
    
    // Check destination IP (0.0.0.0 means any)
    if (strcmp(rule->dst_ip, "0.0.0.0") != 0) {
        if (strcmp(rule->dst_ip, dst_ip) != 0) {
            return 0;
        }
    }
    
    // Check source port (0 means any)
    if (rule->src_port != 0) {
        if (rule->src_port != src_port) {
            return 0;
        }
    }
    
    // Check destination port (0 means any)
    if (rule->dst_port != 0) {
        if (rule->dst_port != dst_port) {
            return 0;
        }
    }
    
    // Check protocol (PROTO_ANY means any)
    if (rule->protocol != PROTO_ANY) {
        if (rule->protocol != protocol) {
            return 0;
        }
    }
    
    // All checks passed
    return 1;
}
```

---

## TODO 9: Apply Rules

**Location**: `apply_rules()` function

### Implementation

```c
int apply_rules(unsigned char* buffer, int size) {
    struct ethhdr* eth = (struct ethhdr*)buffer;
    struct iphdr* iph;
    struct tcphdr* tcph;
    struct udphdr* udph;
    
    // Only process IP packets
    if (ntohs(eth->h_proto) != ETH_P_IP) {
        return 1;  // Accept non-IP packets
    }
    
    iph = (struct iphdr*)(buffer + sizeof(struct ethhdr));
    
    // Extract IP addresses
    struct sockaddr_in source, dest;
    memset(&source, 0, sizeof(source));
    source.sin_addr.s_addr = iph->saddr;
    memset(&dest, 0, sizeof(dest));
    dest.sin_addr.s_addr = iph->daddr;
    
    char src_ip[MAX_IP_STR];
    char dst_ip[MAX_IP_STR];
    strcpy(src_ip, inet_ntoa(source.sin_addr));
    strcpy(dst_ip, inet_ntoa(dest.sin_addr));
    
    // Extract ports based on protocol
    int src_port = 0, dst_port = 0;
    Protocol protocol = (Protocol)iph->protocol;
    
    unsigned short iphdrlen = iph->ihl * 4;
    
    if (iph->protocol == IPPROTO_TCP) {
        tcph = (struct tcphdr*)(buffer + iphdrlen + sizeof(struct ethhdr));
        src_port = ntohs(tcph->source);
        dst_port = ntohs(tcph->dest);
    } else if (iph->protocol == IPPROTO_UDP) {
        udph = (struct udphdr*)(buffer + iphdrlen + sizeof(struct ethhdr));
        src_port = ntohs(udph->source);
        dst_port = ntohs(udph->dest);
    }
    
    // Check each rule
    for (int i = 0; i < rule_count; i++) {
        if (!rules[i].enabled) continue;
        
        if (match_rule(&rules[i], src_ip, dst_ip, src_port, dst_port, protocol)) {
            // Rule matched
            if (rules[i].action == ACTION_DROP) {
                return 0;  // Drop packet
            } else if (rules[i].action == ACTION_ACCEPT) {
                return 1;  // Accept packet
            } else if (rules[i].action == ACTION_LOG) {
                printf("LOG: Packet matched rule %d\n", i + 1);
                return 1;  // Log and accept
            }
        }
    }
    
    // No rule matched, default policy: ACCEPT
    return 1;
}
```

---

## TODO 10: Process Packet

This function is mostly implemented. Just ensure `apply_rules()` is called and statistics are updated correctly. The template already has most of this.

---

## TODO 11: Print Statistics

The template already implements this. No changes needed unless you want to enhance formatting.

---

## TODO 12: Initialize Default Rules

**Location**: `init_default_rules()` function

### Implementation

```c
void init_default_rules() {
    printf("Initializing default firewall rules...\n");
    
    // Example 1: Block all ICMP (ping)
    // Uncomment to activate:
    // add_rule("0.0.0.0", "0.0.0.0", 0, 0, PROTO_ICMP, ACTION_DROP);
    
    // Example 2: Block SSH (port 22)
    // add_rule("0.0.0.0", "0.0.0.0", 0, 22, PROTO_TCP, ACTION_DROP);
    
    // Example 3: Block specific IP
    // add_rule("192.168.1.100", "0.0.0.0", 0, 0, PROTO_ANY, ACTION_DROP);
    
    // Example 4: Log all HTTP traffic (port 80)
    // add_rule("0.0.0.0", "0.0.0.0", 0, 80, PROTO_TCP, ACTION_LOG);
    
    printf("Loaded %d firewall rules\n", rule_count);
}
```

---

## Final Testing

### Test 1: Compile and Run

```bash
make
sudo ./firewall
```

### Test 2: Block ICMP

Uncomment the ICMP blocking rule in `init_default_rules()`:
```c
add_rule("0.0.0.0", "0.0.0.0", 0, 0, PROTO_ICMP, ACTION_DROP);
```

Rebuild and test:
```bash
make
sudo ./firewall

# In another terminal:
ping 8.8.8.8  # Should see packets dropped
```

### Test 3: Monitor Statistics

Let it run for a minute, then press Ctrl+C to see statistics.

---

## Troubleshooting

**"Permission denied" error**:
- Run with `sudo`
- Check: `sudo setcap cap_net_raw+ep ./firewall`

**No packets captured**:
- Check interface name: `ip link show`
- Try without interface argument
- Verify network activity

**Compilation errors**:
- Install development tools: `sudo apt-get install build-essential`
- Check for typos in header includes

**High CPU usage**:
- This is normal for raw packet processing
- Consider adding output rate limiting

---

## Next Steps

1. Add support for CIDR notation (e.g., 192.168.1.0/24)
2. Implement connection tracking for stateful filtering
3. Add configuration file support
4. Implement packet modification (NAT)
5. Add BPF filters for better performance
6. Create a management interface (CLI or web)

Congratulations! You've built a basic packet filtering firewall from scratch.
