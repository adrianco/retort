CC = clang
CFLAGS = -fobjc-arc -Wall -Wextra -O2
LDFLAGS = -framework Foundation -lsqlite3

LIB_SRC = BookStore.m HTTPServer.m BookAPI.m

.PHONY: all test clean run

all: bookserver booktests

bookserver: $(LIB_SRC) main.m
	$(CC) $(CFLAGS) $^ -o $@ $(LDFLAGS)

booktests: $(LIB_SRC) tests.m
	$(CC) $(CFLAGS) $^ -o $@ $(LDFLAGS)

test: booktests
	./booktests

run: bookserver
	./bookserver

clean:
	rm -f bookserver booktests books.db
