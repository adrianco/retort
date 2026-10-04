CC      ?= cc
CFLAGS  ?= -std=c11 -O2 -Wall -Wextra -Wpedantic -D_POSIX_C_SOURCE=200809L
LDLIBS  := -lsqlite3
BUILD   := build
LIB_SRC := src/json.c src/api.c

.PHONY: all test clean

all: $(BUILD)/books-api

$(BUILD)/books-api: src/main.c $(LIB_SRC) src/*.h | $(BUILD)
	$(CC) $(CFLAGS) -o $@ src/main.c $(LIB_SRC) $(LDLIBS)

$(BUILD)/test_api: tests/test_api.c $(LIB_SRC) src/*.h | $(BUILD)
	$(CC) $(CFLAGS) -Isrc -o $@ tests/test_api.c $(LIB_SRC) $(LDLIBS)

test: $(BUILD)/test_api
	./$(BUILD)/test_api

$(BUILD):
	mkdir -p $(BUILD)

clean:
	rm -rf $(BUILD)
