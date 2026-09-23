CC = clang
CFLAGS = -fobjc-arc -Wall -O2
LIBS = -framework Foundation -lsqlite3
SRC = BookStore.m BookAPI.m

all: bookserver

bookserver: $(SRC) main.m *.h
	$(CC) $(CFLAGS) $(SRC) main.m $(LIBS) -o $@

booktests: $(SRC) tests.m *.h
	$(CC) $(CFLAGS) $(SRC) tests.m $(LIBS) -o $@

test: booktests
	./booktests

clean:
	rm -f bookserver booktests

.PHONY: all test clean
