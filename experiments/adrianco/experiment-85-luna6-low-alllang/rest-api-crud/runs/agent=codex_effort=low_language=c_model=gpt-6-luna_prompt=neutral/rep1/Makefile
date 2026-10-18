CC ?= cc
CFLAGS ?= -std=c11 -Wall -Wextra -O2
PKG_CONFIG ?= pkg-config
CFLAGS += $(shell $(PKG_CONFIG) --cflags sqlite3 libmicrohttpd)
LDLIBS += $(shell $(PKG_CONFIG) --libs sqlite3 libmicrohttpd)

all: book_service

book_service: book_service.c
	$(CC) $(CFLAGS) -o $@ $< $(LDLIBS)

test: book_service
	$(CC) $(CFLAGS) -o test_book_service test_api.c $(LDLIBS)
	./test_book_service
	rm -f test_book_service

clean:
	rm -f book_service test_book_service books.db

.PHONY: all test clean
