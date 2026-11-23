CC = clang
CFLAGS = -O2 -Wall -Wextra -Werror -fobjc-arc
LDLIBS = -framework Foundation

.PHONY: all test clean
all: soccer-mcp

soccer-mcp: main.m Soccer.m Soccer.h
	$(CC) $(CFLAGS) main.m Soccer.m $(LDLIBS) -o $@

test: soccer-mcp
	python3 tests.py ./soccer-mcp

clean:
	rm -f soccer-mcp
