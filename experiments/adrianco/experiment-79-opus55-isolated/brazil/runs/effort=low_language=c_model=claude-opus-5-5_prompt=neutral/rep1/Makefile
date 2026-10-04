CC ?= cc
CFLAGS ?= -O2 -g
CFLAGS += -std=c11 -Wall -Wextra -D_DEFAULT_SOURCE -D_POSIX_C_SOURCE=200809L -Isrc
LDLIBS = -lm

LIB_SRC = src/util.c src/json.c src/soccer.c src/mcp.c
HDRS = src/util.h src/json.h src/soccer.h src/mcp.h
BIN = brsoccer-mcp
TEST_BIN = tests/test_soccer

.PHONY: all test clean

all: $(BIN)

$(BIN): $(LIB_SRC) src/main.c $(HDRS)
	$(CC) $(CFLAGS) -o $@ $(LIB_SRC) src/main.c $(LDLIBS)

$(TEST_BIN): $(LIB_SRC) tests/test_soccer.c $(HDRS)
	$(CC) $(CFLAGS) -o $@ $(LIB_SRC) tests/test_soccer.c $(LDLIBS)

test: $(BIN) $(TEST_BIN)
	./$(TEST_BIN) data/kaggle
	sh tests/test_stdio.sh ./$(BIN) data/kaggle

clean:
	rm -rf $(BIN) $(TEST_BIN) *.dSYM tests/*.dSYM
