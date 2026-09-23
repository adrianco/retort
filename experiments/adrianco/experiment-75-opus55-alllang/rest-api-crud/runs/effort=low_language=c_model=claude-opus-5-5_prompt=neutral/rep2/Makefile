CC ?= cc
CFLAGS ?= -std=c11 -D_DEFAULT_SOURCE -D_DARWIN_C_SOURCE -Wall -Wextra -O2
LDLIBS = -lsqlite3

all: books_server

books_server: src/server.c src/books.c src/books.h
	$(CC) $(CFLAGS) -o $@ src/server.c src/books.c $(LDLIBS)

test_books: tests/test_books.c src/books.c src/books.h
	$(CC) $(CFLAGS) -o $@ tests/test_books.c src/books.c $(LDLIBS)

test: test_books books_server
	./test_books
	./tests/http_test.sh

clean:
	rm -f books_server test_books books.db

.PHONY: all test clean
