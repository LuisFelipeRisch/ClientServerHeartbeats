#ifndef __SHARED__
#define __SHARED__

#include <netinet/in.h>

typedef struct {
  unsigned long sequence_number; 
  unsigned long sent_at_ns;
} message_t;

int create_udp_socket();

void setup_server_socket_addr(struct sockaddr_in *server_addr, char *server_ip_addr, int server_port);

#endif