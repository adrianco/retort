CC      ?= cc
CFLAGS  ?= -std=c11 -Wall -Wextra -O2
LDLIBS  := -lsqlite3

COMMON_SRC := strbuf.c json.c db.c api.c
COMMON_OBJ := $(COMMON_SRC:.c=.o)

.PHONY: all test integration clean

all: bookapi

bookapi: main.o $(COMMON_OBJ)
	$(CC) $(CFLAGS) -o $@ $^ $(LDLIBS)

test_api: test_api.o $(COMMON_OBJ)
	$(CC) $(CFLAGS) -o $@ $^ $(LDLIBS)

# Build and run the unit/integration test binary.
test: test_api
	./test_api

# Run the HTTP-level integration test (needs a built server + curl).
integration: bookapi
	./test_integration.sh

%.o: %.c
	$(CC) $(CFLAGS) -c -o $@ $<

clean:
	rm -f bookapi test_api *.o books.db

# Header dependencies
main.o:     api.h db.h strbuf.h
api.o:      api.h db.h json.h strbuf.h
db.o:       db.h
json.o:     json.h
strbuf.o:   strbuf.h
test_api.o: api.h db.h json.h strbuf.h
