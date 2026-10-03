/*
 * SOCKS Protocol Header
 * 
 * Definitions and function declarations for SOCKS protocol implementation
 */

#ifndef SOCKS_H
#define SOCKS_H

/*
 * Establish SOCKS4 connection to destination through proxy
 * 
 * Parameters:
 *   sock - Connected socket to SOCKS proxy
 *   dest_host - Destination hostname or IP address
 *   dest_port - Destination port number
 * 
 * Returns:
 *   0 on success, -1 on error
 */
int socks4_connect(int sock, const char* dest_host, int dest_port);

/*
 * Establish SOCKS5 connection (optional advanced feature)
 * 
 * Parameters:
 *   sock - Connected socket to SOCKS proxy
 *   dest_host - Destination hostname or IP address
 *   dest_port - Destination port number
 * 
 * Returns:
 *   0 on success, -1 on error
 */
int socks5_connect(int sock, const char* dest_host, int dest_port);

#endif /* SOCKS_H */
