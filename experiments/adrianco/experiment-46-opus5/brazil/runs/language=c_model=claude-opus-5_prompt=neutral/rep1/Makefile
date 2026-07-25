# =============================================================================
# Brazilian Soccer MCP Server - Build
# =============================================================================
# Targets:
#   make            build the MCP server (bin/brsoccer-mcp)
#   make test       build and run the BDD test suite (bin/brsoccer-tests)
#   make demo       answer the 20+ sample questions from the specification
#   make serve      run the MCP server on stdio (for an MCP client)
#   make clean      remove build artifacts
#
# The project is plain C11 with no third-party dependencies: the CSV reader,
# JSON parser/serialiser, hash maps and the JSON-RPC/MCP transport are all
# implemented in src/.
# =============================================================================

CC      ?= cc
CSTD    ?= -std=c11
WARN    := -Wall -Wextra -Wpedantic -Wshadow -Wstrict-prototypes -Wmissing-prototypes \
           -Wpointer-arith -Wwrite-strings -Wno-unused-parameter
OPT     ?= -O2
CFLAGS  += $(CSTD) $(WARN) $(OPT) -Isrc
LDFLAGS +=

SRC_DIR   := src
TEST_DIR  := tests
BUILD_DIR := build
BIN_DIR   := bin

LIB_SRCS  := $(SRC_DIR)/util.c $(SRC_DIR)/csv.c $(SRC_DIR)/json.c $(SRC_DIR)/teams.c \
             $(SRC_DIR)/db.c $(SRC_DIR)/query.c $(SRC_DIR)/format.c $(SRC_DIR)/tools.c \
             $(SRC_DIR)/mcp.c
LIB_OBJS  := $(patsubst $(SRC_DIR)/%.c,$(BUILD_DIR)/%.o,$(LIB_SRCS))

MAIN_OBJ  := $(BUILD_DIR)/main.o

TEST_SRCS := $(TEST_DIR)/test_main.c $(TEST_DIR)/test_util.c $(TEST_DIR)/test_csv.c \
             $(TEST_DIR)/test_json.c $(TEST_DIR)/test_teams.c $(TEST_DIR)/test_db.c \
             $(TEST_DIR)/test_query.c $(TEST_DIR)/test_mcp.c $(TEST_DIR)/test_questions.c
TEST_OBJS := $(patsubst $(TEST_DIR)/%.c,$(BUILD_DIR)/test_%.o,$(TEST_SRCS))

SERVER    := $(BIN_DIR)/brsoccer-mcp
TESTS     := $(BIN_DIR)/brsoccer-tests

.PHONY: all test demo serve clean

all: $(SERVER)

$(SERVER): $(LIB_OBJS) $(MAIN_OBJ) | $(BIN_DIR)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

$(TESTS): $(LIB_OBJS) $(TEST_OBJS) | $(BIN_DIR)
	$(CC) $(CFLAGS) -o $@ $^ $(LDFLAGS)

$(BUILD_DIR)/%.o: $(SRC_DIR)/%.c | $(BUILD_DIR)
	$(CC) $(CFLAGS) -c -o $@ $<

$(BUILD_DIR)/test_%.o: $(TEST_DIR)/%.c | $(BUILD_DIR)
	$(CC) $(CFLAGS) -I$(TEST_DIR) -c -o $@ $<

$(BUILD_DIR) $(BIN_DIR):
	mkdir -p $@

test: $(TESTS)
	./$(TESTS)

demo: $(SERVER)
	./$(SERVER) --demo

serve: $(SERVER)
	./$(SERVER)

clean:
	rm -rf $(BUILD_DIR) $(BIN_DIR)

# Header dependencies (small project: rebuild all objects when any header changes)
$(LIB_OBJS) $(MAIN_OBJ) $(TEST_OBJS): $(wildcard $(SRC_DIR)/*.h) $(wildcard $(TEST_DIR)/*.h)
