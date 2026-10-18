CC       ?= clang
CFLAGS   ?= -fobjc-arc -Wall -Wextra -Wno-unused-parameter -O2
LDFLAGS  := -framework Foundation

LIB_SRC  := src/CSVParser.m src/Text.m src/Models.m src/DataStore.m src/Tools.m src/MCPServer.m
TEST_SRC := tests/test_main.m

SERVER   := build/brazilian-soccer-mcp
TESTS    := build/tests

.PHONY: all test clean

all: $(SERVER)

$(SERVER): $(LIB_SRC) src/main.m | build
	$(CC) $(CFLAGS) -Isrc -o $@ $(LIB_SRC) src/main.m $(LDFLAGS)

$(TESTS): $(LIB_SRC) $(TEST_SRC) | build
	$(CC) $(CFLAGS) -Isrc -o $@ $(LIB_SRC) $(TEST_SRC) $(LDFLAGS)

test: $(TESTS)
	./$(TESTS)

build:
	mkdir -p build

clean:
	rm -rf build
