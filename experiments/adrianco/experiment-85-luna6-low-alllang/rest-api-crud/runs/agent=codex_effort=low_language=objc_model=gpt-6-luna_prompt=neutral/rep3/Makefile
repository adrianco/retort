CC=clang
CFLAGS=-fobjc-arc -Wall -Wextra -Wno-unused-parameter -framework Foundation
LIBS=-lsqlite3

all: book-service

book-service: main.m BookServer.m BookServer.h
	$(CC) $(CFLAGS) main.m BookServer.m -o $@ $(LIBS)

tests: Tests.m BookServer.m BookServer.h
	$(CC) $(CFLAGS) Tests.m BookServer.m -o book-tests $(LIBS)

test: tests
	./book-tests

clean:
	rm -f book-service book-tests

.PHONY: all tests test clean
