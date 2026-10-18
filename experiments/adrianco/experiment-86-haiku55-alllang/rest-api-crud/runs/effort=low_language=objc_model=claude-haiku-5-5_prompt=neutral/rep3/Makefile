CC      = clang
CFLAGS  = -fobjc-arc -Isrc -Wall -Wextra -Wno-unused-parameter -g
LDFLAGS = -framework Foundation -lsqlite3

LIB_SRC  = src/Book.m src/BookStore.m src/HTTP.m src/HTTPServer.m src/BookAPI.m
APP_SRC  = src/main.m
TEST_SRC = tests/BookServiceTests.m

all: bin/bookservice

bin/bookservice: $(LIB_SRC) $(APP_SRC) | bin
	$(CC) $(CFLAGS) -o $@ $(LIB_SRC) $(APP_SRC) $(LDFLAGS)

bin/tests: $(LIB_SRC) $(TEST_SRC) | bin
	$(CC) $(CFLAGS) -o $@ $(LIB_SRC) $(TEST_SRC) $(LDFLAGS)

test: bin/tests
	./bin/tests

bin:
	mkdir -p bin

clean:
	rm -rf bin

.PHONY: all test clean
