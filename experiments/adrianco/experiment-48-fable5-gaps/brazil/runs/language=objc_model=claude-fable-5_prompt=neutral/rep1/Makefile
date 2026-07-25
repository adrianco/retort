# Brazilian Soccer MCP server (Objective-C / Foundation)
CC       := clang
CFLAGS   := -fobjc-arc -O2 -Wall -Wextra -Wno-unused-parameter
LDFLAGS  := -framework Foundation

LIB_SRCS := BSCSV.m BSModels.m BSDataStore.m BSTools.m BSMCPServer.m
LIB_OBJS := $(LIB_SRCS:.m=.o)

SERVER   := bss-mcp-server
TESTS    := bss-tests

.PHONY: all test clean

all: $(SERVER) $(TESTS)

%.o: %.m $(wildcard *.h)
	$(CC) $(CFLAGS) -c $< -o $@

$(SERVER): $(LIB_OBJS) main.o
	$(CC) $(LDFLAGS) $^ -o $@

$(TESTS): $(LIB_OBJS) tests_main.o
	$(CC) $(LDFLAGS) $^ -o $@

test: all
	BSS_DATA_DIR=data/kaggle ./$(TESTS)

clean:
	rm -f $(LIB_OBJS) main.o tests_main.o $(SERVER) $(TESTS)
