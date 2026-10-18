CC ?= cc
CFLAGS := -std=gnu11 -Wall -Wextra -Werror -O2
CPPFLAGS := -Isrc
SQLITE_CFLAGS := $(shell pkg-config --cflags sqlite3 2>/dev/null)
SQLITE_LIBS := $(shell pkg-config --libs sqlite3 2>/dev/null || echo -lsqlite3)

LIB_SRC := src/util.c src/json.c src/store.c src/router.c src/http.c
LIB_OBJ := $(LIB_SRC:.c=.o)
HEADERS := $(wildcard src/*.h)

.PHONY: all test run clean

all: books

books: $(LIB_OBJ) src/main.o
	$(CC) $(CFLAGS) -o $@ $^ $(SQLITE_LIBS)

tests/test_api: tests/test_api.c $(LIB_OBJ)
	$(CC) $(CFLAGS) $(CPPFLAGS) $(SQLITE_CFLAGS) -o $@ $^ $(SQLITE_LIBS)

test: tests/test_api
	./tests/test_api

run: books
	./books

%.o: %.c $(HEADERS)
	$(CC) $(CFLAGS) $(CPPFLAGS) $(SQLITE_CFLAGS) -c -o $@ $<

clean:
	rm -f src/*.o tests/*.o books tests/test_api
