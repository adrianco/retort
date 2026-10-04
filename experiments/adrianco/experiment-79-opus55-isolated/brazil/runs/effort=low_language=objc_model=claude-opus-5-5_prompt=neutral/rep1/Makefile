# Brazilian Soccer MCP server (Objective-C, Foundation only).
CC      ?= clang
CFLAGS  ?= -O2 -Wall -Wextra -Wno-unused-parameter
OBJCFLAGS = -fobjc-arc -Isrc
LDFLAGS = -framework Foundation

BUILD   = build
LIB_SRC = src/BSCSV.m src/BSTeamNames.m src/BSDataStore.m src/BSQueryEngine.m src/BSTools.m src/BSMCPServer.m
HEADERS = $(wildcard src/*.h)
SERVER  = $(BUILD)/brazilian-soccer-mcp
TESTS   = $(BUILD)/bs_tests

.PHONY: all test clean

all: $(SERVER)

$(SERVER): $(LIB_SRC) src/main.m $(HEADERS)
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) $(OBJCFLAGS) $(LIB_SRC) src/main.m $(LDFLAGS) -o $@

$(TESTS): $(LIB_SRC) tests/BSTests.m $(HEADERS)
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) $(OBJCFLAGS) $(LIB_SRC) tests/BSTests.m $(LDFLAGS) -o $@

test: $(SERVER) $(TESTS)
	$(TESTS) data/kaggle $(SERVER)

clean:
	rm -rf $(BUILD)
