# Makefile for Book API REST Service

CC = clang
CFLAGS = -Wall -Wextra -g -I/usr/include -I/usr/local/include $(shell pkg-config --cflags json-c 2>/dev/null || echo "")
JSON_C_LIBS := $(shell pkg-config --libs json-c 2>/dev/null || echo "-ljson-c")
LDFLAGS = -lpthread -lsqlite3 $(JSON_C_LIBS)

# Source files
SRCS = main.m server.m database.m routes.m utils.m
OBJS = $(SRCS:.m=.o)

# Target executable
TARGET = book-api

# Default target
all: $(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(CFLAGS) -o $(TARGET) $(OBJS) $(LDFLAGS)

main.o: main.m server.h database.h routes.h utils.h
	$(CC) $(CFLAGS) -c main.m -o main.o

server.o: server.m server.h utils.h
	$(CC) $(CFLAGS) -c server.m -o server.o

database.o: database.m database.h utils.h
	$(CC) $(CFLAGS) -c database.m -o database.o

routes.o: routes.m routes.h database.h utils.h
	$(CC) $(CFLAGS) -c routes.m -o routes.o

utils.o: utils.m utils.h
	$(CC) $(CFLAGS) -c utils.m -o utils.o

clean:
	rm -f $(TARGET) $(OBJS) *.o

test: $(TARGET)
	./run_tests.sh

run: $(TARGET)
	./$(TARGET)

.PHONY: all clean test run
