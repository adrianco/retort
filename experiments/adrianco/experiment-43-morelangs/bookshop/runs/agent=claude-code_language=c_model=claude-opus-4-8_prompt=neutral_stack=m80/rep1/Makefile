CC      ?= cc
CFLAGS  ?= -std=c11 -Wall -Wextra -O2
CFLAGS  += $(shell pkg-config --cflags sqlite3 2>/dev/null)
LDLIBS  += $(shell pkg-config --libs sqlite3 2>/dev/null || echo -lsqlite3)

COMMON_SRC = json.c db.c api.c

.PHONY: all test clean run

all: bookapi

bookapi: main.c $(COMMON_SRC) json.h db.h api.h
	$(CC) $(CFLAGS) -o $@ main.c $(COMMON_SRC) $(LDLIBS)

test_runner: test.c $(COMMON_SRC) json.h db.h api.h
	$(CC) $(CFLAGS) -o $@ test.c $(COMMON_SRC) $(LDLIBS)

test: test_runner
	./test_runner

run: bookapi
	./bookapi

clean:
	rm -f bookapi test_runner books.db
