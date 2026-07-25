CC      ?= cc
CFLAGS  ?= -O2 -std=c11 -Wall -Wextra
LDFLAGS ?=

CORE_SRCS = csv.c json.c data.c tools.c
HDRS      = bsmcp.h

all: bsmcp test_bsmcp

bsmcp: $(CORE_SRCS) mcp_main.c $(HDRS)
	$(CC) $(CFLAGS) -o $@ $(CORE_SRCS) mcp_main.c $(LDFLAGS)

test_bsmcp: $(CORE_SRCS) test_main.c $(HDRS)
	$(CC) $(CFLAGS) -o $@ $(CORE_SRCS) test_main.c $(LDFLAGS)

test: all
	./test_bsmcp data/kaggle
	sh test_mcp.sh

clean:
	rm -f bsmcp test_bsmcp

.PHONY: all test clean
