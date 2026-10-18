SDK := $(shell xcrun --show-sdk-path)
OBJC := clang
CFLAGS := -fobjc-arc -framework Foundation -isysroot $(SDK)

all: books-api

books-api: main.m BookService.m BookService.h
	$(OBJC) $(CFLAGS) main.m BookService.m -lsqlite3 -o books-api

tests: Tests.m BookService.m BookService.h
	$(OBJC) $(CFLAGS) Tests.m BookService.m -lsqlite3 -o books-tests
	./books-tests

clean:
	rm -f books-api books-tests books.sqlite
