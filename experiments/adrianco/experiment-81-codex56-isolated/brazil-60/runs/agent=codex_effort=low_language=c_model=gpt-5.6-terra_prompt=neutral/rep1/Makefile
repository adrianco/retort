CC ?= cc
CFLAGS ?= -std=c11 -O2 -Wall -Wextra -Wpedantic

all: soccer_mcp

soccer_mcp: soccer_mcp.c
	$(CC) $(CFLAGS) -o $@ $<

test: soccer_mcp
	./tests.sh

clean:
	rm -f soccer_mcp

.PHONY: all test clean
