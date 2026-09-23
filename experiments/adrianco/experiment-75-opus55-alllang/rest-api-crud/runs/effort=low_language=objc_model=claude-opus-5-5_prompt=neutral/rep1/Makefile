CC = clang
CFLAGS = -fobjc-arc -Wall -Isrc
LIBS = -framework Foundation -lsqlite3

all: bookapi

bookapi: src/main.m src/BookAPI.m src/BookAPI.h
	$(CC) $(CFLAGS) -o $@ src/main.m src/BookAPI.m $(LIBS)

book_tests: tests/test_main.m src/BookAPI.m src/BookAPI.h
	$(CC) $(CFLAGS) -o $@ tests/test_main.m src/BookAPI.m $(LIBS)

test: book_tests
	./book_tests

clean:
	rm -f bookapi book_tests

.PHONY: all test clean
