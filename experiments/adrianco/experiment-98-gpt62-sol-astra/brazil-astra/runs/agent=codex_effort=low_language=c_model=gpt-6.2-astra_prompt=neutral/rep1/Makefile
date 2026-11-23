CC ?= cc
CFLAGS ?= -O2 -Wall -Wextra -Wpedantic
CPPFLAGS += -D_POSIX_C_SOURCE=200809L
soccer-mcp: server.c data.c soccer.h
	$(CC) $(CPPFLAGS) $(CFLAGS) -std=c11 server.c data.c -lsqlite3 -o $@
test: soccer-mcp
	python3 test_soccer.py
clean:
	rm -f soccer-mcp
.PHONY: clean test
