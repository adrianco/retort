CC     ?= cc
CFLAGS += -std=c11 -Wall -Wextra -Wpedantic -Werror -O2 -D_POSIX_C_SOURCE=200809L
LDLIBS += -lsqlite3 -lpthread

SRC  = src/buf.c src/json.c src/book.c src/api.c src/http.c
HDR  = $(wildcard src/*.h)
BIN  = bin/books-api
TEST = bin/test_api

all: $(BIN)

$(BIN): src/main.c $(SRC) $(HDR)
	@mkdir -p bin
	$(CC) $(CFLAGS) -Isrc -o $@ src/main.c $(SRC) $(LDLIBS)

$(TEST): tests/test_api.c $(SRC) $(HDR)
	@mkdir -p bin
	$(CC) $(CFLAGS) -Isrc -o $@ tests/test_api.c $(SRC) $(LDLIBS)

test: $(TEST)
	./$(TEST)

clean:
	rm -rf bin

.PHONY: all test clean
