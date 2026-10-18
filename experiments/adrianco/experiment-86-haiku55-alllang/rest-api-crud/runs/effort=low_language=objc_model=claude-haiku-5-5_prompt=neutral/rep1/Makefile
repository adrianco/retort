CC      = clang
CFLAGS  = -fobjc-arc -Wall -Wextra -Wno-unused-parameter -g
LDLIBS  = -framework Foundation -lsqlite3
BUILD   = build

APP_SRC  = src/main.m src/BookStore.m src/BookAPI.m src/HTTPServer.m
LIB_SRC  = src/BookStore.m src/BookAPI.m src/HTTPServer.m
TEST_SRC = tests/test_main.m $(LIB_SRC)

all: $(BUILD)/books-api

$(BUILD)/books-api: $(APP_SRC) src/*.h | $(BUILD)
	$(CC) $(CFLAGS) -o $@ $(APP_SRC) $(LDLIBS)

$(BUILD)/tests: $(TEST_SRC) src/*.h | $(BUILD)
	$(CC) $(CFLAGS) -Isrc -o $@ $(TEST_SRC) $(LDLIBS)

test: $(BUILD)/tests
	./$(BUILD)/tests

run: $(BUILD)/books-api
	./$(BUILD)/books-api

$(BUILD):
	mkdir -p $@

clean:
	rm -rf $(BUILD)

.PHONY: all test run clean
