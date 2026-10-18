CC      ?= clang
CFLAGS  ?= -fobjc-arc -Wall -Wextra -Wno-unused-parameter -Isrc
LDFLAGS  = -framework Foundation -lsqlite3

LIB_SRC = src/Book.m src/BookStore.m src/BookAPI.m src/HTTPMessage.m src/HTTPServer.m
LIB_HDR = $(wildcard src/*.h)

all: build/bookapi

build:
	mkdir -p build

build/bookapi: src/main.m $(LIB_SRC) $(LIB_HDR) | build
	$(CC) $(CFLAGS) -o $@ src/main.m $(LIB_SRC) $(LDFLAGS)

build/tests: tests/main.m $(LIB_SRC) $(LIB_HDR) | build
	$(CC) $(CFLAGS) -o $@ tests/main.m $(LIB_SRC) $(LDFLAGS)

test: build/tests
	./build/tests

run: build/bookapi
	./build/bookapi

clean:
	rm -rf build

.PHONY: all test run clean
