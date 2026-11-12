CC      ?= clang
CFLAGS  += -fobjc-arc -Wall -Wextra -O2 -Isrc
LDFLAGS += -framework Foundation -lsqlite3

LIB_SRC = src/BookStore.m src/BooksAPI.m src/HTTPServer.m
BUILD   = build

.PHONY: all test run clean
all: $(BUILD)/bookapi

$(BUILD)/bookapi: $(LIB_SRC) src/main.m src/*.h
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) $(LIB_SRC) src/main.m -o $@ $(LDFLAGS)

$(BUILD)/tests: $(LIB_SRC) tests/test_main.m src/*.h
	@mkdir -p $(BUILD)
	$(CC) $(CFLAGS) $(LIB_SRC) tests/test_main.m -o $@ $(LDFLAGS)

test: $(BUILD)/tests
	./$(BUILD)/tests

run: $(BUILD)/bookapi
	./$(BUILD)/bookapi

clean:
	rm -rf $(BUILD)
