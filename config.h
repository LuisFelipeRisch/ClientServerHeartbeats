#ifndef CONFIG_H
#define CONFIG_H

#include <math.h>

#define VERBOSE                1
#define HEARTBEAT_INTERVAL_MS  100                                                                                                /* In miliseconds */
#define CLIENT_LIFETIME        1                                                                                                  /* In days */
#define MAX_HEARTBEAT_COUNT    ((unsigned long int)ceil((double)(CLIENT_LIFETIME * 24 * 60 * 60 * 1000) / HEARTBEAT_INTERVAL_MS))
#define MAX_DATA_BUFFER_LENGTH 2000
#define MAX_LINES_PER_LOG      50000
#define DEFAULT_TTL            64

#endif
