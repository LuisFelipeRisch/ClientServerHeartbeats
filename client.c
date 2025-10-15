#include <unistd.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <netdb.h>
#include <string.h>
#include <sys/time.h>
#include <time.h>
#include <signal.h>
#include "shared.h"
#include "config.h"

int                 server_port;
int                 socket_desc;
int                 num_servers;           
struct sockaddr_in* server_addrs;         
char**              server_ip_addrs; 
socklen_t           server_struct_length;
unsigned long       sequence_number = 0;

void heartbeat() {
  message_t       message;
  struct timespec st;

  if (sequence_number == MAX_HEARTBEAT_COUNT + 1) {
    if (VERBOSE) fprintf(stdout, "Client has reached the maximum number of messages (%ld) allowed for sending\n", MAX_HEARTBEAT_COUNT);
    
    close(socket_desc);
    free(server_addrs); // Libera a memória alocada
    free(server_ip_addrs);
    exit(EXIT_SUCCESS);
  }

  if(clock_gettime(CLOCK_REALTIME, &st) == -1) {
    fprintf(stderr, "Failed to get current datetime\n");
    exit(EXIT_FAILURE);
  }

  message.sequence_number = sequence_number++;
  message.sent_at_ns      = st.tv_sec * (long)1E9 + st.tv_nsec;

  for (int i = 0; i < num_servers; i++) {
    if (sendto(socket_desc, 
               &message, 
               sizeof(message), 
               0, 
               (struct sockaddr*) &server_addrs[i],
               server_struct_length) < 0) {
                fprintf(stderr, "Failed to send heartbeat message to server %s!\n", server_ip_addrs[i]);
               }
    
    if (VERBOSE) {
      fprintf(stdout, 
              "Message sent to IP: %s at port: %d. Data: seq_num: %ld, sent_at_ns: %ld\n",
              server_ip_addrs[i],
              server_port, 
              message.sequence_number, 
              message.sent_at_ns);
    }
  }
}

void init_heartbeat_interval() {
  struct sigaction sa;
  struct itimerval timer;

  memset(&sa, 0, sizeof(sa));
  sa.sa_handler = heartbeat;
  sigaction(SIGALRM, &sa, NULL);

  timer.it_value.tv_sec     = 0;
  timer.it_value.tv_usec    = HEARTBEAT_INTERVAL_MS * 1000;
  timer.it_interval.tv_sec  = 0;
  timer.it_interval.tv_usec = HEARTBEAT_INTERVAL_MS * 1000;

  setitimer(ITIMER_REAL, &timer, NULL);

  if (VERBOSE) fprintf(stdout, "Heartbeat interval successfully configured!\n");
}

void show_program_execution_instructions(char *program_name) {
  fprintf(stderr, "Usage: %s <server_port> <server_ip_1> <server_ip_2> ... <server_ip_n>\n", program_name);
}

int check_arguments_length(int argc) {
  return argc >= 3;
}

int main(int argc, char *argv[]) {
  if (!check_arguments_length(argc)) {
    fprintf(stderr, "Wrong number of arguments!\n");
    show_program_execution_instructions(argv[0]);
    exit(EXIT_FAILURE);
  }

  server_port          = atoi(argv[1]);
  num_servers          = argc - 2;
  server_struct_length = sizeof(struct sockaddr_in);
  socket_desc          = create_udp_socket();

  server_addrs = malloc(num_servers * sizeof(struct sockaddr_in));
  server_ip_addrs = malloc(num_servers * sizeof(char*));

  if (server_addrs == NULL || server_ip_addrs == NULL) {
    fprintf(stderr, "Failed to allocate memory for server addresses\n");
    exit(EXIT_FAILURE);
  }

  if(VERBOSE) 
    fprintf(stdout, "Configuring client to send to %d server(s) on port %d:\n", num_servers, server_port);
  
  for (int i = 0; i < num_servers; i++) {
    server_ip_addrs[i] = argv[i + 2];

    if(VERBOSE)
      fprintf(stdout, " -> Server %d: %s\n", i + 1, server_ip_addrs[i]);

    setup_server_socket_addr(&server_addrs[i], server_ip_addrs[i], server_port);
  }

  init_heartbeat_interval();

  while (1) {
    pause();
  }
  
  return EXIT_SUCCESS;
}