CC = gcc
CFLAGS = -Wall -Wextra -g
LIBS = -lcurl -lsqlite3

TARGET = book-api
SRCS = main.c http.c db.c
OBJS = $(SRCS:.c=.o)

all: $(TARGET)

$(TARGET): $(OBJS)
	$(CC) $(CFLAGS) -o $@ $^ $(LIBS)

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	rm -f $(TARGET) $(OBJS)

test: $(TARGET)
	./run_tests.sh

.PHONY: all clean test
