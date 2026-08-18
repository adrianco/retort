CC ?= cc
CFLAGS ?= -std=c17 -Wall -Wextra -Wpedantic -O2

.PHONY: all test clean
all: brazilian-soccer-mcp
brazilian-soccer-mcp: main.o soccer.o
	$(CC) $(CFLAGS) -o $@ $^
tests/test_soccer: tests/test_soccer.c soccer.o soccer.h
	$(CC) $(CFLAGS) -o $@ tests/test_soccer.c soccer.o
test: brazilian-soccer-mcp tests/test_soccer
	./tests/test_soccer
	sh tests/test_mcp.sh
clean:
	rm -f *.o brazilian-soccer-mcp tests/test_soccer
