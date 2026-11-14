CC ?= cc
CFLAGS ?= -std=c11 -O2 -Wall -Wextra -D_POSIX_C_SOURCE=200809L -D_DARWIN_C_SOURCE
LIB_SRC = src/util.c src/data.c src/query.c src/mcp.c
HDR = src/soccer.h
DATA ?= data/kaggle

all: brsoccer-mcp

brsoccer-mcp: $(LIB_SRC) src/main.c $(HDR)
	$(CC) $(CFLAGS) -o $@ $(LIB_SRC) src/main.c

tests/test_bdd: $(LIB_SRC) tests/test_bdd.c $(HDR)
	$(CC) $(CFLAGS) -Isrc -o $@ $(LIB_SRC) tests/test_bdd.c

test: brsoccer-mcp tests/test_bdd
	./tests/test_bdd $(DATA)
	sh tests/test_stdio.sh $(DATA)

clean:
	rm -f brsoccer-mcp tests/test_bdd

.PHONY: all test clean
