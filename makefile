CC = gcc
CFLAGS = -Wall -Wextra -D_XOPEN_SOURCE=700 -std=c99

CLIENT_SRC = client.c
SERVER_SRC = server.c
LIB_SRC 	 = shared.c 

CLIENT_OBJ = $(CLIENT_SRC:.c=.o) $(LIB_SRC:.c=.o)
SERVER_OBJ = $(SERVER_SRC:.c=.o) $(LIB_SRC:.c=.o)

CLIENT_TARGET = client
SERVER_TARGET = server

# Build both client and server
all: $(CLIENT_TARGET) $(SERVER_TARGET)

# Build client
$(CLIENT_TARGET): $(CLIENT_OBJ)
	$(CC) $(CFLAGS) -o $(CLIENT_TARGET) $(CLIENT_OBJ) $(LIBS)

# Build server
$(SERVER_TARGET): $(SERVER_OBJ)
	$(CC) $(CFLAGS) -o $(SERVER_TARGET) $(SERVER_OBJ) $(LIBS)

# Compile source files into object files
%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

# Clean build files
clean:
	rm -f $(CLIENT_OBJ) $(SERVER_OBJ) $(CLIENT_TARGET) $(SERVER_TARGET)

.PHONY: all clean
