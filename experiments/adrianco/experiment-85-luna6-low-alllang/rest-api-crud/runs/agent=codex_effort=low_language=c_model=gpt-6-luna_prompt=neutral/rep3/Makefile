CC ?= cc
CFLAGS ?= -O2 -Wall -Wextra -Wpedantic
LDLIBS += -lsqlite3

.PHONY: all clean test
all: book_service

book_service: server.c
	$(CC) $(CFLAGS) -o $@ $< $(LDLIBS)

test: book_service
	python3 -m unittest -v test_api.py

clean:
	rm -f book_service books.db books.db-shm books.db-wal
