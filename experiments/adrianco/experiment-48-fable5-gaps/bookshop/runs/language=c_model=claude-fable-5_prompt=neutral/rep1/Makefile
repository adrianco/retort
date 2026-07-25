CC ?= cc
CFLAGS ?= -Wall -Wextra -O2
CFLAGS += -std=c11
LDLIBS = -lsqlite3

OBJS = json.o db.o http.o api.o
HDRS = json.h db.h http.h api.h
BIN = bookapi

all: $(BIN)

$(BIN): main.o $(OBJS)
	$(CC) $(CFLAGS) -o $@ main.o $(OBJS) $(LDLIBS)

test_unit: test_unit.o $(OBJS)
	$(CC) $(CFLAGS) -o $@ test_unit.o $(OBJS) $(LDLIBS)

%.o: %.c $(HDRS)
	$(CC) $(CFLAGS) -c $<

test: $(BIN) test_unit
	./test_unit
	./test_api.sh

clean:
	rm -f *.o $(BIN) test_unit test_api.db

.PHONY: all test clean
