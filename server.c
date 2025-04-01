#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <string.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/time.h>
#include <time.h>
#include <signal.h>
#include <netdb.h>
#include "shared.h"
#include "config.h"

int                server_port, socket_desc;
struct sockaddr_in server_addr, client_addr;
socklen_t          client_struct_length;

void listen_to_clients_messages() {
  FILE            *trace_log;
  struct msghdr   mhdr;
  struct iovec    iov[1];
  struct cmsghdr  *cmhdr;
  struct timespec received_at;
  char            data_buffer[MAX_DATA_BUFFER_LENGTH], control[MAX_DATA_BUFFER_LENGTH];
  message_t       *client_message;
  unsigned int    ttl;
  unsigned long   received_at_ns;

  trace_log = fopen("traces/log.txt", "w");
  if (!trace_log) {
    fprintf(stderr, "Failed to open trace log!\n"); 
    exit(EXIT_FAILURE);
  }

  fprintf(trace_log, "CLIENT_IP;CLIENT_PORT;CLIENT_SENT_AT_NS;SERVER_RECEIVED_AT_NS;SEQUENCE_NUMBER;HOPS\n");

  mhdr.msg_name       = &client_addr;
  mhdr.msg_namelen    = sizeof(client_addr);
  mhdr.msg_iov        = iov;
  mhdr.msg_iovlen     = 1;
  mhdr.msg_control    = &control;
  mhdr.msg_controllen = sizeof(control);
  iov[0].iov_base     = data_buffer;
  iov[0].iov_len      = sizeof(data_buffer);

  memset(data_buffer, '\0', sizeof(data_buffer));

  while (1) {
    if (recvmsg(socket_desc, &mhdr, 0) < 0) { 
      fprintf(stderr, "Failed on receiving message from clients!\n"); 
      exit(EXIT_FAILURE);
    }

    cmhdr = CMSG_FIRSTHDR(&mhdr);
    while (cmhdr) {
      if (cmhdr->cmsg_level == IPPROTO_IP && cmhdr->cmsg_type == IP_TTL)
        ttl = *((unsigned int *) CMSG_DATA(cmhdr));
      cmhdr = CMSG_NXTHDR(&mhdr, cmhdr);
    }

    if (clock_gettime(CLOCK_REALTIME, &received_at) < 0) {
      fprintf(stderr, "Failed to get current time!\n");
      exit(EXIT_FAILURE);
    }

    received_at_ns = received_at.tv_sec * 1E9 + received_at.tv_nsec; 
    client_message = (message_t *) data_buffer;

    fprintf(trace_log, 
            "%s;%i;%ld;%ld;%ld;%d\n", 
            inet_ntoa(client_addr.sin_addr),
            ntohs(client_addr.sin_port),
            client_message->sent_at_ns,
            received_at_ns, 
            client_message->sequence_number, 
            DEFAULT_TTL - ttl);

    if (VERBOSE)
      fprintf(stdout, 
              "Received message from IP: %s and port: %i at %ld. Client message data: sequence_number: %ld, sent_at_ns: %ld, ttl: %d, hops: %d\n",
              inet_ntoa(client_addr.sin_addr),
              ntohs(client_addr.sin_port),    
              received_at_ns,
              client_message->sequence_number, 
              client_message->sent_at_ns, 
              ttl, 
              DEFAULT_TTL - ttl);

    memset(data_buffer, '\0', sizeof(data_buffer));
  }
}

void show_program_execution_instructions(char *program_name) {
  fprintf(stderr, "%s <server_port>\n", program_name);
}

void setup_server() {
  socket_desc = create_udp_socket();

  if (VERBOSE) fprintf(stdout, "Socket descriptor successfully created!\n");

  memset(&server_addr, 0, sizeof(server_addr));

  server_addr.sin_addr.s_addr = htonl(INADDR_ANY);
  server_addr.sin_port        = htons(server_port);
  server_addr.sin_family      = AF_INET;

  if(bind(socket_desc, (struct sockaddr*) &server_addr, sizeof(struct sockaddr_in)) < 0) {
    fprintf(stderr, "Failed to bind server socket!\n");
    exit(EXIT_FAILURE);
  }

  if (VERBOSE) fprintf(stdout, 
                       "Server socket bound successfully!. Listening on port: %d\n", 
                       ntohs(server_addr.sin_port));

  int yes = 1;
  if (setsockopt(socket_desc, IPPROTO_IP, IP_RECVTTL, &yes, sizeof(yes)) < 0) {
    fprintf(stderr, "Failed to activate TTL reader from IP header!\n");
    exit(EXIT_FAILURE);
  }

  if (VERBOSE) fprintf(stdout, "Successfully activated TTL read from IP header\n");
}

int check_arguments_length(int argc) {
  return argc == 2;
}

int main(int argc, char *argv[]) {
  if (!check_arguments_length(argc)) {
    fprintf(stderr, "Wrong number of arguments!\n");
    show_program_execution_instructions(argv[0]);
    exit(EXIT_FAILURE);
  }

  client_struct_length = sizeof(client_addr);
  server_port          = atoi(argv[1]);

  setup_server();
  listen_to_clients_messages();

  return 0;
}
