#include "shared.h"
#include "config.h"
#include "stdio.h"
#include <stdlib.h>
#include <unistd.h>
#include "sys/socket.h"
#include "arpa/inet.h"
#include <netinet/in.h>

int create_udp_socket() {
  int socket_desc; 

  socket_desc = socket(AF_INET, SOCK_DGRAM, IPPROTO_UDP); 
  if (socket_desc < 0) {
    fprintf(stderr, "Error while creating UDP socket!\n"); 
    exit(EXIT_FAILURE);
  }

  if (VERBOSE) fprintf(stdout, "Socket successfully created!\n");

  return socket_desc;
}

void setup_server_socket_addr(struct sockaddr_in *server_addr, char *server_ip_addr, int server_port) {
  server_addr->sin_family      = AF_INET; 
  server_addr->sin_port        = htons(server_port); 
  server_addr->sin_addr.s_addr = inet_addr(server_ip_addr);

  if (VERBOSE) fprintf(stdout, "Server socket addr successfully configured!\n");
}

