CC ?= cc
CFLAGS ?= -O2 -Wall -Wextra -Wpedantic -std=c11
CPPFLAGS += $(shell pkg-config --cflags sqlite3 json-c)
LDLIBS += $(shell pkg-config --libs sqlite3 json-c)

all: books-api
books-api: server.c
	$(CC) $(CPPFLAGS) $(CFLAGS) -o $@ $< $(LDLIBS)
test: books-api
	python3 -m unittest -v test_api.py
clean:
	rm -f books-api
.PHONY: all test clean
