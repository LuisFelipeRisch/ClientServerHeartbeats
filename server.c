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
#include <math.h>
#include "shared.h"
#include "config.h"

int                server_port, socket_desc;
struct sockaddr_in server_addr, client_addr;
socklen_t          client_struct_length;
FILE               **trace_logs;
unsigned int       trace_logs_quantity;

void setup_trace_logs() {
  char         filepath[30];
  unsigned int i;

  trace_logs_quantity = (unsigned int) ceil((double) MAX_HEARTBEAT_COUNT / MAX_LINES_PER_LOG);

  trace_logs = (FILE **) malloc(trace_logs_quantity * sizeof(FILE *));
  if (!trace_logs) {
    fprintf(stderr, "Failed to alloc memory!\n");
    exit(EXIT_FAILURE);
  }

  for (i = 0; i < trace_logs_quantity; i++) {
    snprintf(filepath, sizeof(filepath), "traces/log_%i.txt", i);

    trace_logs[i] = fopen(filepath, "w");
    if (!trace_logs[i]) {
      fprintf(stderr, "Failed to open file!\n");
      exit(EXIT_FAILURE);
    }

    fprintf(trace_logs[i], "CLIENT_IP;CLIENT_PORT;CLIENT_SENT_AT_NS;SERVER_RECEIVED_AT_NS;SEQUENCE_NUMBER;HOPS\n");
  }

  if (VERBOSE) fprintf(stdout, "Created all %d files of trace logs successfully!\n", i);
}

void close_trace_logs() {
  for (unsigned int i = 0; i < trace_logs_quantity; i++) fclose(trace_logs[i]);

  free(trace_logs); 

  if (VERBOSE) fprintf(stdout, "Closed all trace files successfully!\n");
}

void listen_to_clients_messages() {
  FILE            *trace_log;
  struct msghdr   mhdr;
  struct iovec    iov[1];
  struct cmsghdr  *cmhdr;
  struct timespec received_at;
  char            data_buffer[MAX_DATA_BUFFER_LENGTH], control[MAX_DATA_BUFFER_LENGTH];
  message_t       *client_message;
  unsigned int    ttl, client_messages_count, trace_logs_index;
  unsigned long   received_at_ns;

  trace_logs_index      = 0;
  client_messages_count = 0;
  trace_log             = trace_logs[trace_logs_index];

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

    client_messages_count++;
    
    received_at_ns = received_at.tv_sec * 1E9 + received_at.tv_nsec; 
    client_message = (message_t *) data_buffer;

    if (client_message->sequence_number == MAX_HEARTBEAT_COUNT) {
      if (VERBOSE) fprintf(stdout, "Client has reached the maximum number of messages (%ld) allowed for sending. Closing server...\n", MAX_HEARTBEAT_COUNT);

      close(socket_desc); 
      close_trace_logs();

      exit(EXIT_SUCCESS);
    }

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

    if (client_messages_count % MAX_LINES_PER_LOG == 0) {
      trace_logs_index++; 
      trace_log = trace_logs[trace_logs_index];
    }

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

  setup_trace_logs();
  setup_server();
  listen_to_clients_messages();

  return 0;
}
