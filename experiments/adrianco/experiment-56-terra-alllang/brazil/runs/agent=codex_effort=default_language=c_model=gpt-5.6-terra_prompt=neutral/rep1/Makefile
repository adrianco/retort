CC ?= cc
CFLAGS ?= -std=c11 -O2 -Wall -Wextra -Wpedantic

all: brazilian_soccer_mcp

brazilian_soccer_mcp: brazilian_soccer_mcp.c
	$(CC) $(CFLAGS) -o $@ $<

test: brazilian_soccer_mcp tests.sh
	./tests.sh

clean:
	rm -f brazilian_soccer_mcp

.PHONY: all test clean
