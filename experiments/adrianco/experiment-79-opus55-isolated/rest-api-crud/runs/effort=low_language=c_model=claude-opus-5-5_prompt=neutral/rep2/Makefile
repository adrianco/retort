CC ?= cc
CFLAGS ?= -std=c11 -O2 -Wall -Wextra -Wpedantic
CPPFLAGS += -D_POSIX_C_SOURCE=200809L -D_DARWIN_C_SOURCE -D_DEFAULT_SOURCE
LDLIBS += -lsqlite3

.PHONY: all test clean

all: bookapi

bookapi: server.c app.c app.h
	$(CC) $(CPPFLAGS) $(CFLAGS) -o $@ server.c app.c $(LDLIBS)

test_app: test_app.c app.c app.h
	$(CC) $(CPPFLAGS) $(CFLAGS) -o $@ test_app.c app.c $(LDLIBS)

test: test_app bookapi
	./test_app
	./test_http.sh

clean:
	rm -f bookapi test_app
