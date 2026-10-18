# Build the Brazilian Soccer MCP server and its test suite (Objective-C, Foundation only).
CC      ?= clang
CFLAGS  ?= -fobjc-arc -Wall -Wextra -Wno-unused-parameter -O2
FRAMEWORKS = -framework Foundation

SRC_DIR  = src
TEST_DIR = tests
BUILD    = build

LIB_SRC = $(SRC_DIR)/CSVParser.m $(SRC_DIR)/SoccerText.m $(SRC_DIR)/SoccerDataset.m \
          $(SRC_DIR)/QueryEngine.m $(SRC_DIR)/MCPServer.m
LIB_OBJ = $(LIB_SRC:$(SRC_DIR)/%.m=$(BUILD)/%.o)

all: $(BUILD)/brazilian-soccer-mcp $(BUILD)/tests

$(BUILD):
	mkdir -p $(BUILD)

$(BUILD)/%.o: $(SRC_DIR)/%.m | $(BUILD)
	$(CC) $(CFLAGS) -c $< -o $@

$(BUILD)/brazilian-soccer-mcp: $(LIB_OBJ) $(BUILD)/main.o
	$(CC) $(CFLAGS) $(FRAMEWORKS) $^ -o $@

$(BUILD)/tests: $(LIB_OBJ) $(TEST_DIR)/test_main.m
	$(CC) $(CFLAGS) $(FRAMEWORKS) -I$(SRC_DIR) $(LIB_OBJ) $(TEST_DIR)/test_main.m -o $@

test: $(BUILD)/tests
	$(BUILD)/tests

clean:
	rm -rf $(BUILD)

.PHONY: all test clean
