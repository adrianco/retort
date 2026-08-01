CC ?= cc
CFLAGS ?= -std=c11 -Wall -Wextra -Werror -O2
LDLIBS ?= -lsqlite3

book_api: book_api.c
	$(CC) $(CFLAGS) -o $@ $< $(LDLIBS)

test: book_api
	$(CC) $(CFLAGS) -o test_book_api test_book_api.c $(LDLIBS)
	./test_book_api

integration-test: book_api
	./test_api.sh

clean:
	rm -f book_api test_book_api books.db test-books.db
