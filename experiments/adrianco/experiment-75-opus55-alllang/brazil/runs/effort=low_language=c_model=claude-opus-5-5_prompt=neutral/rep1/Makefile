CC ?= cc
CFLAGS ?= -O2 -Wall -Wextra -std=c11 -D_GNU_SOURCE -D_DEFAULT_SOURCE
SRC = src/data.c src/query.c src/mcp.c

all: soccer-mcp test_soccer

soccer-mcp: $(SRC) src/main.c src/soccer.h
	$(CC) $(CFLAGS) -o $@ $(SRC) src/main.c

test_soccer: $(SRC) tests/test_soccer.c src/soccer.h
	$(CC) $(CFLAGS) -Isrc -o $@ $(SRC) tests/test_soccer.c

test: test_soccer soccer-mcp
	./test_soccer data/kaggle

clean:
	rm -f soccer-mcp test_soccer

.PHONY: all test clean
