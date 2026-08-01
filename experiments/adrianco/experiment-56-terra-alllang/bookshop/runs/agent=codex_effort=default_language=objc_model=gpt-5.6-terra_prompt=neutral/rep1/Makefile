SDK := $(shell xcrun --show-sdk-path)
CFLAGS := -fobjc-arc -fmodules -fmodules-cache-path=$(CURDIR)/.module-cache -isysroot $(SDK) -framework Foundation -lsqlite3

.PHONY: all test clean
all: book-api

book-api: main.m BookStore.m BookStore.h
	clang $(CFLAGS) main.m BookStore.m -o $@

book-api-tests: tests.m BookStore.m BookStore.h
	clang $(CFLAGS) tests.m BookStore.m -o $@

test: book-api-tests
	./book-api-tests

clean:
	rm -f book-api book-api-tests books.db
	rm -rf .module-cache
