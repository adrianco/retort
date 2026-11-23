CC = clang
CFLAGS = -fobjc-arc -Wall -Wextra -Werror
LDLIBS = -framework Foundation -framework CoreFoundation -lsqlite3

.PHONY: all test clean

all: book-service

book-service: Server.m Books.m Books.h
	$(CC) $(CFLAGS) Server.m Books.m $(LDLIBS) -o $@

book-tests: Tests.m Books.m Books.h
	$(CC) $(CFLAGS) Tests.m Books.m $(LDLIBS) -o $@

test: book-service book-tests
	./book-tests

clean:
	rm -f book-service book-tests
