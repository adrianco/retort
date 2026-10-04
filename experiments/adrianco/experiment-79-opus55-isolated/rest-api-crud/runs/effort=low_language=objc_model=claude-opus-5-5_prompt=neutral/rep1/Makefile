CC      ?= clang
CFLAGS  ?= -O2 -Wall -Wextra -Wno-unused-parameter
OBJCFLAGS = -fobjc-arc -Isrc
LDFLAGS = -framework Foundation -lsqlite3

LIB_SRCS = src/BookStore.m src/BookAPI.m src/HTTPServer.m
HEADERS  = $(wildcard src/*.h)

.PHONY: all test clean run

all: build/books-api

build/books-api: $(LIB_SRCS) src/main.m $(HEADERS)
	@mkdir -p build
	$(CC) $(CFLAGS) $(OBJCFLAGS) $(LIB_SRCS) src/main.m -o $@ $(LDFLAGS)

build/books-tests: $(LIB_SRCS) tests/BookTests.m $(HEADERS)
	@mkdir -p build
	$(CC) $(CFLAGS) $(OBJCFLAGS) $(LIB_SRCS) tests/BookTests.m -o $@ $(LDFLAGS)

test: build/books-tests
	./build/books-tests

run: build/books-api
	./build/books-api

clean:
	rm -rf build
