CC      ?= clang
CFLAGS  += -fobjc-arc -Wall -Wextra -O2 -Isrc
LDFLAGS += -framework Foundation -lsqlite3

LIB_SRCS := src/BookStore.m src/BookAPI.m src/HTTPServer.m
HEADERS  := $(wildcard src/*.h)
BUILD    := build

.PHONY: all test run clean

all: $(BUILD)/books-api

$(BUILD)/books-api: $(LIB_SRCS) src/main.m $(HEADERS)
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) $(LIB_SRCS) src/main.m -o $@ $(LDFLAGS)

$(BUILD)/books-tests: $(LIB_SRCS) tests/test_main.m $(HEADERS)
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) $(LIB_SRCS) tests/test_main.m -o $@ $(LDFLAGS)

test: $(BUILD)/books-tests
	./$(BUILD)/books-tests

run: all
	./$(BUILD)/books-api

clean:
	rm -rf $(BUILD)
