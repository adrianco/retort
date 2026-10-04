CC      ?= clang
CFLAGS  ?= -O2 -g
CFLAGS  += -fobjc-arc -Wall -Wextra -Isrc
LDFLAGS += -framework Foundation -lsqlite3

LIB_SRCS = src/BookStore.m src/BooksAPI.m src/HTTPServer.m
HEADERS  = $(wildcard src/*.h)

.PHONY: all test run clean

all: build/books-api

build/books-api: $(LIB_SRCS) src/main.m $(HEADERS)
	@mkdir -p build
	$(CC) $(CFLAGS) $(LIB_SRCS) src/main.m -o $@ $(LDFLAGS)

build/books-tests: $(LIB_SRCS) tests/test_main.m $(HEADERS)
	@mkdir -p build
	$(CC) $(CFLAGS) $(LIB_SRCS) tests/test_main.m -o $@ $(LDFLAGS)

test: build/books-tests
	./build/books-tests

run: build/books-api
	./build/books-api

clean:
	rm -rf build
