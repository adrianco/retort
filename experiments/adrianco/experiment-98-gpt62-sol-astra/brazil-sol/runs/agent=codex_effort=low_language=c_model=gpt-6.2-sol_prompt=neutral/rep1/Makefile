CC ?= cc
PKGS = glib-2.0 json-c
CPPFLAGS += -D_POSIX_C_SOURCE=200809L $(shell pkg-config --cflags $(PKGS))
CFLAGS ?= -O2
CFLAGS += -std=c11 -Wall -Wextra -Wpedantic
LDLIBS += $(shell pkg-config --libs $(PKGS))

.PHONY: all test clean
all: soccer-mcp
soccer-mcp: mcp.o queries.o data.o
	$(CC) $(LDFLAGS) -o $@ $^ $(LDLIBS)
mcp.o queries.o data.o: soccer.h
test: soccer-mcp
	python3 test_mcp.py
clean:
	rm -f soccer-mcp mcp.o queries.o data.o
