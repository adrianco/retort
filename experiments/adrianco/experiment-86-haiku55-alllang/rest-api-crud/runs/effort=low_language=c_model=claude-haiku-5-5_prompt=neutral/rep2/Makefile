CC ?= cc
CFLAGS ?= -std=c11 -D_DEFAULT_SOURCE -Wall -Wextra -Wpedantic -O2
SQLITE_CFLAGS := $(shell pkg-config --cflags sqlite3 2>/dev/null)
SQLITE_LIBS := $(or $(shell pkg-config --libs sqlite3 2>/dev/null),-lsqlite3)

ALL_CFLAGS = $(CFLAGS) $(SQLITE_CFLAGS) -Isrc

LIB_SRCS = src/util.c src/strbuf.c src/json.c src/db.c src/api.c src/http.c
LIB_OBJS = $(patsubst src/%.c,build/%.o,$(LIB_SRCS))

all: build/bookapi

build/bookapi: build/main.o $(LIB_OBJS)
	$(CC) $(ALL_CFLAGS) -o $@ $^ $(SQLITE_LIBS)

build/test_all: build/test_all.o $(LIB_OBJS)
	$(CC) $(ALL_CFLAGS) -o $@ $^ $(SQLITE_LIBS)

build/%.o: src/%.c | build
	$(CC) $(ALL_CFLAGS) -c -o $@ $<

build/test_all.o: tests/test_all.c | build
	$(CC) $(ALL_CFLAGS) -c -o $@ $<

build:
	mkdir -p build

test: build/test_all
	./build/test_all

clean:
	rm -rf build

.PHONY: all test clean
