CC ?= cc
PACKAGES = libevent json-c sqlite3
CFLAGS ?= -O2 -g
all: books
books: books.c
test_handler: test_handler.c books.c
books test_handler:
	$(CC) $(CPPFLAGS) $(CFLAGS) -std=c11 -Wall -Wextra -Wpedantic $(shell pkg-config --cflags $(PACKAGES)) $< $(LDFLAGS) $(shell pkg-config --libs $(PACKAGES)) -o $@
test: books test_handler
	python3 -m unittest -v test_books
clean:
	rm -f books test_handler
.PHONY: test clean
