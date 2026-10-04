CC ?= cc
CFLAGS ?= -std=c11 -O2 -Wall -Wextra -D_DEFAULT_SOURCE -D_DARWIN_C_SOURCE
LDLIBS = -lsqlite3 -lm

all: books-api

books-api: src/main.c src/api.c src/api.h
	$(CC) $(CFLAGS) -o $@ src/main.c src/api.c $(LDLIBS)

test_api: tests/test_api.c src/api.c src/api.h
	$(CC) $(CFLAGS) -o $@ tests/test_api.c src/api.c $(LDLIBS)

test: test_api books-api
	./test_api
	sh tests/smoke.sh

clean:
	rm -f books-api test_api

.PHONY: all test clean
