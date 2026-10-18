CC ?= cc
CFLAGS ?= -std=c11 -O2 -Wall -Wextra -Wpedantic
LDLIBS += $(shell pkg-config --libs libmicrohttpd sqlite3)
CPPFLAGS += $(shell pkg-config --cflags libmicrohttpd sqlite3)

.PHONY: all clean test
all: book_server
book_server: server.c
	$(CC) $(CPPFLAGS) $(CFLAGS) -o $@ $< $(LDLIBS)
test: book_server test_server
	./test_server
test_server: test_server.c server.c
	$(CC) $(CPPFLAGS) $(CFLAGS) -o $@ test_server.c $(LDLIBS)
clean:
	rm -f book_server test_server books.db
