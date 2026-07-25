CC      = clang
CFLAGS  = -fobjc-arc -Wall -Wextra -O2 -I.
LDFLAGS = -framework Foundation -lsqlite3

LIB_SRC   = BookStore.m Router.m HTTPServer.m
SERVER_SRC = main.m $(LIB_SRC)
TEST_SRC   = tests/tests.m $(LIB_SRC)

SERVER_BIN = bookapi
TEST_BIN   = run_tests

.PHONY: all run test clean

all: $(SERVER_BIN)

$(SERVER_BIN): $(SERVER_SRC) BookStore.h Router.h HTTPServer.h
	$(CC) $(CFLAGS) $(SERVER_SRC) $(LDFLAGS) -o $(SERVER_BIN)

run: $(SERVER_BIN)
	./$(SERVER_BIN)

$(TEST_BIN): $(TEST_SRC) BookStore.h Router.h HTTPServer.h
	$(CC) $(CFLAGS) $(TEST_SRC) $(LDFLAGS) -o $(TEST_BIN)

test: $(TEST_BIN)
	./$(TEST_BIN)

clean:
	rm -f $(SERVER_BIN) $(TEST_BIN) books.db
