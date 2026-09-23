CC = clang
CFLAGS = -fobjc-arc -Wall -Isrc
LDFLAGS = -framework Foundation -lsqlite3
LIB = src/BookStore.m src/BookAPI.m

all: bookserver

bookserver: $(LIB) src/main.m
	$(CC) $(CFLAGS) $^ $(LDFLAGS) -o $@

run_tests: $(LIB) tests/tests.m
	$(CC) $(CFLAGS) $^ $(LDFLAGS) -o $@

test: run_tests
	./run_tests

clean:
	rm -f bookserver run_tests books.db

.PHONY: all test clean
