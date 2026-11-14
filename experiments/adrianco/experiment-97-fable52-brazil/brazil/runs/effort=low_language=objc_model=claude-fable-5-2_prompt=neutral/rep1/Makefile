CC      ?= clang
CFLAGS  ?= -O2 -Wall -Wextra -Wno-unused-parameter
OBJCFLAGS = -fobjc-arc -framework Foundation
LIB_SRC = src/BSCSV.m src/BSTeamNames.m src/BSDataStore.m src/BSTools.m src/BSMCPServer.m
HEADERS = $(wildcard src/*.h)
BIN     = build/brazilian-soccer-mcp
TESTBIN = build/run-tests

.PHONY: all test clean
all: $(BIN)

$(BIN): $(LIB_SRC) src/main.m $(HEADERS)
	@mkdir -p build
	$(CC) $(CFLAGS) $(OBJCFLAGS) $(LIB_SRC) src/main.m -o $@

$(TESTBIN): $(LIB_SRC) tests/BSTests.m $(HEADERS)
	@mkdir -p build
	$(CC) $(CFLAGS) $(OBJCFLAGS) -Isrc $(LIB_SRC) tests/BSTests.m -o $@

test: $(BIN) $(TESTBIN)
	$(TESTBIN) data/kaggle $(BIN)

clean:
	rm -rf build
