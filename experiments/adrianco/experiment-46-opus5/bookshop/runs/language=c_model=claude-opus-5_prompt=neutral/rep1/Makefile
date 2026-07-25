CC       ?= cc
CFLAGS   ?= -std=c11 -O2 -g
WARNINGS  = -Wall -Wextra -Wpedantic -Wshadow -Wstrict-prototypes \
            -Wmissing-prototypes -Wwrite-strings -Wno-unused-parameter
CPPFLAGS += -Isrc
LDLIBS   += -lsqlite3

UNAME_S := $(shell uname -s)
ifeq ($(UNAME_S),Darwin)
  CPPFLAGS += -D_DARWIN_C_SOURCE
else
  CPPFLAGS += -D_POSIX_C_SOURCE=200809L -D_DEFAULT_SOURCE
endif

BUILD  := build
LIB_SRCS := src/strbuf.c src/json.c src/db.c src/http.c src/book_json.c src/api.c
LIB_OBJS := $(LIB_SRCS:src/%.c=$(BUILD)/%.o)

BIN      := $(BUILD)/bookapi
TEST_BINS := $(BUILD)/test_json $(BUILD)/test_db $(BUILD)/test_api

.PHONY: all test run clean

all: $(BIN)

$(BUILD):
	@mkdir -p $(BUILD)

$(BUILD)/%.o: src/%.c | $(BUILD)
	$(CC) $(CFLAGS) $(WARNINGS) $(CPPFLAGS) -c $< -o $@

$(BUILD)/t_%.o: tests/%.c | $(BUILD)
	$(CC) $(CFLAGS) $(WARNINGS) $(CPPFLAGS) -Itests -c $< -o $@

$(BIN): $(LIB_OBJS) $(BUILD)/main.o
	$(CC) $(CFLAGS) $^ -o $@ $(LDLIBS)

$(BUILD)/test_json: $(BUILD)/t_test_json.o $(BUILD)/strbuf.o $(BUILD)/json.o
	$(CC) $(CFLAGS) $^ -o $@

$(BUILD)/test_db: $(BUILD)/t_test_db.o $(BUILD)/strbuf.o $(BUILD)/json.o \
                  $(BUILD)/db.o $(BUILD)/book_json.o
	$(CC) $(CFLAGS) $^ -o $@ $(LDLIBS)

# test_api drives the real server over TCP, so it needs the binary present.
$(BUILD)/test_api: $(BUILD)/t_test_api.o $(BUILD)/strbuf.o $(BUILD)/json.o $(BIN)
	$(CC) $(CFLAGS) $(BUILD)/t_test_api.o $(BUILD)/strbuf.o $(BUILD)/json.o -o $@

test: $(TEST_BINS)
	@set -e; for t in $(TEST_BINS); do echo "== $$t"; $$t; done
	@echo "All test suites passed."

run: $(BIN)
	$(BIN)

clean:
	rm -rf $(BUILD) books.db books.db-wal books.db-shm

# Header dependencies (small project: list them explicitly).
$(BUILD)/strbuf.o:    src/strbuf.h
$(BUILD)/json.o:      src/json.h src/strbuf.h
$(BUILD)/db.o:        src/db.h
$(BUILD)/http.o:      src/http.h src/strbuf.h
$(BUILD)/book_json.o: src/book_json.h src/db.h src/json.h src/strbuf.h
$(BUILD)/api.o:       src/api.h src/db.h src/http.h src/book_json.h src/json.h
$(BUILD)/main.o:      src/api.h src/db.h src/http.h
