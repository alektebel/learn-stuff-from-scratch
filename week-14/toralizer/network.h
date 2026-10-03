/*
 * Network Utilities Header
 * 
 * Function declarations for network operations
 */

#ifndef NETWORK_H
#define NETWORK_H

/*
 * Create a TCP socket
 * 
 * Returns:
 *   Socket file descriptor on success, -1 on error
 */
int create_socket(void);

/*
 * Connect to a remote server
 * 
 * Parameters:
 *   sock - Socket file descriptor
 *   host - Hostname or IP address
 *   port - Port number
 * 
 * Returns:
 *   0 on success, -1 on error
 */
int connect_to_server(int sock, const char* host, int port);

/*
 * Set socket timeout for send and receive operations
 * 
 * Parameters:
 *   sock - Socket file descriptor
 *   seconds - Timeout in seconds
 * 
 * Returns:
 *   0 on success, -1 on error
 */
int set_socket_timeout(int sock, int seconds);

/*
 * Set socket to non-blocking mode
 * 
 * Parameters:
 *   sock - Socket file descriptor
 * 
 * Returns:
 *   0 on success, -1 on error
 */
int set_nonblocking(int sock);

#endif /* NETWORK_H */
