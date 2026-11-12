CC      ?= cc
CFLAGS  ?= -std=c11 -O2 -Wall -Wextra -Wpedantic
CFLAGS  += -D_POSIX_C_SOURCE=200809L -D_DARWIN_C_SOURCE -D_DEFAULT_SOURCE
LDLIBS  = -lsqlite3

LIB_SRC = src/sb.c src/book_json.c src/api.c
HEADERS = $(wildcard src/*.h)

all: bookapi

bookapi: $(LIB_SRC) src/server.c src/main.c $(HEADERS)
	$(CC) $(CFLAGS) -o $@ $(LIB_SRC) src/server.c src/main.c $(LDLIBS)

test_api: $(LIB_SRC) tests/test_api.c $(HEADERS)
	$(CC) $(CFLAGS) -g -o $@ $(LIB_SRC) tests/test_api.c $(LDLIBS)

test: test_api bookapi
	./test_api
	./tests/integration.sh ./bookapi

clean:
	rm -rf bookapi test_api *.dSYM

.PHONY: all test clean
