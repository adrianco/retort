# Brazilian Soccer MCP Server — build
#
# Targets:
#   make build   compile the MCP server and the BDD test runner
#   make test    build, then run the BDD suite against data/kaggle
#   make run     build, then start the MCP server on stdio
#   make clean   remove build artefacts

CC       := clang
# -MMD -MP emit a .d file per object listing the headers it included, so that
# editing a header rebuilds everything that depends on it. Without this, a
# change to a struct or an enum silently leaves stale objects in the tree.
CFLAGS   := -std=gnu11 -fobjc-arc -Wall -Wextra -Wno-unused-parameter -O2 -MMD -MP -I$(CURDIR)/src
LDFLAGS  := -framework Foundation

SRC_DIR   := src
TEST_DIR  := tests
BUILD_DIR := build

LIB_SRCS  := $(filter-out $(SRC_DIR)/main.m,$(wildcard $(SRC_DIR)/*.m))
LIB_OBJS  := $(patsubst $(SRC_DIR)/%.m,$(BUILD_DIR)/src/%.o,$(LIB_SRCS))
MAIN_OBJ  := $(BUILD_DIR)/src/main.o
TEST_SRCS := $(wildcard $(TEST_DIR)/*.m)
TEST_OBJS := $(patsubst $(TEST_DIR)/%.m,$(BUILD_DIR)/tests/%.o,$(TEST_SRCS))

SERVER := $(BUILD_DIR)/brazilian-soccer-mcp
TESTS  := $(BUILD_DIR)/run-tests

.PHONY: all build test run clean

all: build

build: $(SERVER) $(TESTS)

$(SERVER): $(LIB_OBJS) $(MAIN_OBJ)
	@mkdir -p $(dir $@)
	$(CC) $(LDFLAGS) -o $@ $^

$(TESTS): $(LIB_OBJS) $(TEST_OBJS)
	@mkdir -p $(dir $@)
	$(CC) $(LDFLAGS) -o $@ $^

$(BUILD_DIR)/src/%.o: $(SRC_DIR)/%.m
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD_DIR)/tests/%.o: $(TEST_DIR)/%.m
	@mkdir -p $(dir $@)
	$(CC) $(CFLAGS) -c $< -o $@

test: $(TESTS)
	@$(TESTS) $(CURDIR)/data/kaggle

run: $(SERVER)
	@$(SERVER) --data $(CURDIR)/data/kaggle

clean:
	rm -rf $(BUILD_DIR)

-include $(LIB_OBJS:.o=.d) $(MAIN_OBJ:.o=.d) $(TEST_OBJS:.o=.d)
