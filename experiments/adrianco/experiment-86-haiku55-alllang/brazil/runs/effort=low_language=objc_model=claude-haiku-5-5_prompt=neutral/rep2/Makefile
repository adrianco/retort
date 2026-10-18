# Brazilian Soccer MCP server (Objective-C, Foundation only).
#
#   make            build build/brazilian-soccer-mcp
#   make test       build and run the test suite (fixtures + the real data in data/kaggle)
#   make clean

CC        ?= clang
CFLAGS    := -fobjc-arc -Wall -Wextra -Wno-unused-parameter -O2
LDFLAGS   := -framework Foundation

BUILD     := build
LIB_SRCS  := $(filter-out src/main.m,$(wildcard src/*.m))
TEST_SRCS := $(wildcard tests/*.m)
DATA_DIR  ?= data/kaggle
FIXTURES  := tests/fixtures

SERVER    := $(BUILD)/brazilian-soccer-mcp
TESTS     := $(BUILD)/run-tests

.PHONY: all test clean

all: $(SERVER)

$(SERVER): $(LIB_SRCS) src/main.m $(wildcard src/*.h)
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -Isrc $(LIB_SRCS) src/main.m -o $@ $(LDFLAGS)

$(TESTS): $(LIB_SRCS) $(TEST_SRCS) $(wildcard src/*.h) $(wildcard tests/*.h)
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) -Isrc -Itests $(LIB_SRCS) $(TEST_SRCS) -o $@ $(LDFLAGS)

test: $(TESTS)
	./$(TESTS) $(FIXTURES) $(DATA_DIR)

clean:
	rm -rf $(BUILD)
