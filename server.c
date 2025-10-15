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

// --- Nova Estrutura para Gerenciar Cada Cliente ---
typedef struct {
    int is_active;                          // Flag: 1 se o slot está em uso, 0 se está livre
    struct sockaddr_in addr;                // Endereço do cliente (IP e porta)
    char ip_str[INET_ADDRSTRLEN];           // IP do cliente em formato string
    FILE **trace_logs;                      // Array de ponteiros para os arquivos de log DESTE cliente
    unsigned int trace_logs_quantity;       // Quantidade de arquivos de log
    unsigned int current_trace_log_index;   // Índice do arquivo de log atual
    unsigned int messages_count;            // Contagem de mensagens recebidas DESTE cliente
} client_info_t;


// --- Variáveis Globais Modificadas ---
int                server_port;
int                socket_desc;
struct sockaddr_in server_addr;
int                g_num_clients;           // Número total de clientes esperados (via argv)
int                g_registered_clients;    // Número de clientes já associados a um IP
client_info_t      *g_clients;              // Array global para gerenciar os clientes

// --- Funções Modificadas e Novas ---

void close_all_client_logs() {
    for (int i = 0; i < g_num_clients; i++) {
        for (unsigned int j = 0; j < g_clients[i].trace_logs_quantity; j++) {
            if (g_clients[i].trace_logs[j]) {
                fclose(g_clients[i].trace_logs[j]);
            }
        }
        free(g_clients[i].trace_logs);
    }
    free(g_clients);
    if (VERBOSE) fprintf(stdout, "Closed all trace files and freed memory successfully!\n");
}

// Cria as pastas e os arquivos de log para cada slot de cliente
void setup_clients(int num_clients) {
    g_num_clients = num_clients;
    g_registered_clients = 0;
    g_clients = malloc(num_clients * sizeof(client_info_t));
    if (!g_clients) {
        fprintf(stderr, "Failed to allocate memory for clients\n");
        exit(EXIT_FAILURE);
    }

    // Cria o diretório principal de traces se não existir
    mkdir("traces", 0755);

    for (int i = 0; i < num_clients; i++) {
        g_clients[i].is_active = 0; // Marca o slot como livre
        g_clients[i].messages_count = 0;
        g_clients[i].current_trace_log_index = 0;
        g_clients[i].trace_logs_quantity = (unsigned int) ceil((double) MAX_HEARTBEAT_COUNT / MAX_LINES_PER_LOG);
        g_clients[i].trace_logs = malloc(g_clients[i].trace_logs_quantity * sizeof(FILE *));
        if (!g_clients[i].trace_logs) {
            fprintf(stderr, "Failed to allocate memory for client %d trace logs\n", i);
            exit(EXIT_FAILURE);
        }

        char client_dir[30];
        snprintf(client_dir, sizeof(client_dir), "traces/client_%d", i);
        mkdir(client_dir, 0755); // Cria a pasta para o cliente_i

        // Cria todos os arquivos de log para este slot de cliente
        for (unsigned int j = 0; j < g_clients[i].trace_logs_quantity; j++) {
            char filepath[50];
            snprintf(filepath, sizeof(filepath), "%s/log_%u.txt", client_dir, j);
            g_clients[i].trace_logs[j] = fopen(filepath, "w");
            if (!g_clients[i].trace_logs[j]) {
                fprintf(stderr, "Failed to open file: %s\n", filepath);
                exit(EXIT_FAILURE);
            }
            // Escreve o cabeçalho no arquivo
            fprintf(g_clients[i].trace_logs[j], "CLIENT_IP;CLIENT_PORT;CLIENT_SENT_AT_NS;SERVER_RECEIVED_AT_NS;SEQUENCE_NUMBER;HOPS\n");
        }
    }

    if (VERBOSE) fprintf(stdout, "Created trace directories and log files for %d clients successfully!\n", num_clients);
}


// Procura um cliente pelo endereço. Retorna o ponteiro para o cliente ou NULL se não encontrar.
client_info_t* find_or_register_client(struct sockaddr_in *addr) {
    // 1. Procura por um cliente já registrado com este IP
    for (int i = 0; i < g_registered_clients; i++) {
        if (g_clients[i].addr.sin_addr.s_addr == addr->sin_addr.s_addr) {
            return &g_clients[i];
        }
    }

    // 2. Se não encontrou, tenta registrar como um novo cliente se houver vaga
    if (g_registered_clients < g_num_clients) {
        int client_index = g_registered_clients;
        g_clients[client_index].is_active = 1;
        memcpy(&g_clients[client_index].addr, addr, sizeof(struct sockaddr_in));
        strcpy(g_clients[client_index].ip_str, inet_ntoa(addr->sin_addr));
        
        g_registered_clients++;

        if (VERBOSE) {
            fprintf(stdout, "[INFO] New client registered: IP %s assigned to slot client_%d\n",
                    g_clients[client_index].ip_str, client_index);
        }
        return &g_clients[client_index];
    }

    // 3. Se não encontrou e não há vagas, retorna NULL
    if (VERBOSE) {
        fprintf(stdout, "[WARN] Maximum number of clients (%d) reached. Ignoring message from %s\n",
                g_num_clients, inet_ntoa(addr->sin_addr));
    }
    return NULL;
}


void listen_to_clients_messages() {
    struct msghdr   mhdr;
    struct iovec    iov[1];
    struct cmsghdr  *cmhdr;
    struct timespec received_at;
    char            data_buffer[MAX_DATA_BUFFER_LENGTH], control[MAX_DATA_BUFFER_LENGTH];
    message_t       *client_message;
    unsigned int    ttl;
    unsigned long   received_at_ns;
    struct sockaddr_in incoming_addr; // Para guardar o endereço do remetente
    socklen_t       incoming_addr_len = sizeof(incoming_addr);
    
    // Configuração do recvmsg
    mhdr.msg_name       = &incoming_addr;
    mhdr.msg_namelen    = incoming_addr_len;
    mhdr.msg_iov        = iov;
    mhdr.msg_iovlen     = 1;
    mhdr.msg_control    = &control;
    mhdr.msg_controllen = sizeof(control);
    iov[0].iov_base     = data_buffer;
    iov[0].iov_len      = sizeof(data_buffer);

    while (1) {
        memset(data_buffer, '\0', sizeof(data_buffer));
        if (recvmsg(socket_desc, &mhdr, 0) < 0) { 
            fprintf(stderr, "Failed on receiving message from clients!\n"); 
            exit(EXIT_FAILURE);
        }

        client_info_t* current_client = find_or_register_client(&incoming_addr);
        if (current_client == NULL) {
            continue; // Ignora o pacote se o cliente não pode ser registrado (slots cheios)
        }

        // Extrai o TTL
        ttl = 0;
        for (cmhdr = CMSG_FIRSTHDR(&mhdr); cmhdr != NULL; cmhdr = CMSG_NXTHDR(&mhdr, cmhdr)) {
            if (cmhdr->cmsg_level == IPPROTO_IP && cmhdr->cmsg_type == IP_TTL) {
                ttl = *((int *) CMSG_DATA(cmhdr));
                break;
            }
        }

        if (clock_gettime(CLOCK_REALTIME, &received_at) < 0) {
            fprintf(stderr, "Failed to get current time!\n");
            exit(EXIT_FAILURE);
        }

        received_at_ns = received_at.tv_sec * (long)1E9 + received_at.tv_nsec; 
        client_message = (message_t *) data_buffer;

        // Verifica se é a última mensagem de um cliente para fechar o servidor
        if (client_message->sequence_number == MAX_HEARTBEAT_COUNT) {
            if (VERBOSE) fprintf(stdout, "Client %s has reached the max number of messages. Closing server...\n", current_client->ip_str);
            close(socket_desc); 
            close_all_client_logs();
            exit(EXIT_SUCCESS);
        }
        
        current_client->messages_count++;

        // Escreve no arquivo de log do cliente correto
        FILE *trace_log = current_client->trace_logs[current_client->current_trace_log_index];
        fprintf(trace_log, 
                "%s;%i;%ld;%ld;%ld;%d\n", 
                current_client->ip_str,
                ntohs(current_client->addr.sin_port),
                client_message->sent_at_ns,
                received_at_ns, 
                client_message->sequence_number, 
                DEFAULT_TTL - ttl);

        if (VERBOSE)
            fprintf(stdout, 
                    "Msg from %s:%i | Seq: %ld | Hops: %d\n",
                    current_client->ip_str,
                    ntohs(current_client->addr.sin_port),
                    client_message->sequence_number, 
                    DEFAULT_TTL - ttl);

        // Muda para o próximo arquivo de log se o atual estiver cheio
        if (current_client->messages_count % MAX_LINES_PER_LOG == 0 &&
            current_client->current_trace_log_index < current_client->trace_logs_quantity - 1) {
            current_client->current_trace_log_index++;
        }
    }
}


void setup_server() {
    socket_desc = create_udp_socket();
    if (VERBOSE) fprintf(stdout, "Socket descriptor successfully created!\n");
    memset(&server_addr, 0, sizeof(server_addr));

    server_addr.sin_addr.s_addr = htonl(INADDR_ANY);
    server_addr.sin_port        = htons(server_port);
    server_addr.sin_family      = AF_INET;

    if(bind(socket_desc, (struct sockaddr*) &server_addr, sizeof(server_addr)) < 0) {
        fprintf(stderr, "Failed to bind server socket!\n");
        exit(EXIT_FAILURE);
    }
    if (VERBOSE) fprintf(stdout, "Server socket bound successfully! Listening on port: %d\n", ntohs(server_addr.sin_port));

    int yes = 1;
    if (setsockopt(socket_desc, IPPROTO_IP, IP_RECVTTL, &yes, sizeof(yes)) < 0) {
        fprintf(stderr, "Failed to activate TTL reader from IP header!\n");
        exit(EXIT_FAILURE);
    }
    if (VERBOSE) fprintf(stdout, "Successfully activated TTL read from IP header\n");
}

void show_program_execution_instructions(char *program_name) {
  fprintf(stderr, "Usage: %s <server_port> <number_of_clients>\n", program_name);
}

int check_arguments_length(int argc) {
  return argc == 3;
}

int main(int argc, char *argv[]) {
  if (!check_arguments_length(argc)) {
    fprintf(stderr, "Wrong number of arguments!\n");
    show_program_execution_instructions(argv[0]);
    exit(EXIT_FAILURE);
  }

    server_port   = atoi(argv[1]);
    int num_clients = atoi(argv[2]);

    if (num_clients <= 0) {
      fprintf(stderr, "Number of clients must be a positive integer.\n");
      exit(EXIT_FAILURE);
    }

    setup_clients(num_clients);
    setup_server();
    listen_to_clients_messages();

    return 0;
}