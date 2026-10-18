CC ?= cc
CFLAGS ?= -std=c11 -Wall -Wextra -Wpedantic -O2
CFLAGS += -D_POSIX_C_SOURCE=200809L

SRC := src/csv.c src/util.c src/json.c src/db.c src/query.c src/mcp.c
HDR := $(wildcard src/*.h)
BIN := bin/brazilian-soccer-mcp
TEST := bin/test_unit

.PHONY: all test clean

all: $(BIN)

$(BIN): src/main.c $(SRC) $(HDR)
	@mkdir -p bin
	$(CC) $(CFLAGS) -o $@ src/main.c $(SRC)

$(TEST): tests/test_unit.c $(SRC) $(HDR)
	@mkdir -p bin
	$(CC) $(CFLAGS) -DFIXTURE_DIR='"tests/fixtures"' -o $@ tests/test_unit.c $(SRC)

test: $(BIN) $(TEST)
	./$(TEST)
	sh tests/test_mcp.sh $(BIN)

clean:
	rm -rf bin
