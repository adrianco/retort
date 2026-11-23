CC ?= cc
PKG_CONFIG ?= pkg-config
PYTHON ?= python3
PACKAGES = libevent json-c sqlite3
CPPFLAGS += $(shell $(PKG_CONFIG) --cflags $(PACKAGES))
CFLAGS ?= -O2
CFLAGS += -std=c11 -Wall -Wextra -Wpedantic
LDLIBS += $(shell $(PKG_CONFIG) --libs $(PACKAGES))

.PHONY: all test clean
all: book-api

book-api: books.c
	$(CC) $(CPPFLAGS) $(CFLAGS) $(LDFLAGS) -o $@ $< $(LDLIBS)

test-books: test_books.c books.c
	$(CC) $(CPPFLAGS) $(CFLAGS) -UNDEBUG $(LDFLAGS) -o $@ $< $(LDLIBS)

test: book-api test-books
	./test-books

.PHONY: test-http
test-http: book-api
	$(PYTHON) test_books.py

clean:
	rm -f book-api test-books
