# Makefile — builds the Brazilian Soccer MCP server and its test runner (plain C11, no deps).
# Usage: make            build build/brazil-soccer-mcp
#        make test       build and run the test suite against data/kaggle
#        make clean

CC ?= cc
CFLAGS ?= -std=c11 -Wall -Wextra -Wpedantic -O2 -D_POSIX_C_SOURCE=200809L -Isrc

LIB_SRC := src/util.c src/csv.c src/json.c src/names.c src/dataset.c src/query.c src/tools.c src/mcp.c
LIB_OBJ := $(LIB_SRC:src/%.c=build/%.o)
BIN := build/brazil-soccer-mcp
TEST := build/test_runner
DATA ?= data/kaggle

all: $(BIN)

$(BIN): build/main.o $(LIB_OBJ)
	$(CC) $(CFLAGS) -o $@ $^

$(TEST): tests/test_main.c $(LIB_OBJ)
	$(CC) $(CFLAGS) -o $@ tests/test_main.c $(LIB_OBJ)

build/%.o: src/%.c $(wildcard src/*.h)
	@mkdir -p build
	$(CC) $(CFLAGS) -c -o $@ $<

test: $(TEST)
	./$(TEST) $(DATA)

clean:
	rm -rf build

.PHONY: all test clean
