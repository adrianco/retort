# =============================================================================
# Brazilian Soccer MCP Server -- build file
#
# Targets:
#   make            build the server binary (brsoccer-mcp) and the test runner
#   make test       build everything and run the BDD test suite + protocol test
#   make run        start the MCP server on stdio (for manual poking)
#   make demo       answer the 25 benchmark sample questions from the CLI
#   make clean      remove build artefacts
# =============================================================================

CC      ?= cc
CSTD    ?= -std=c11
CFLAGS  ?= -O2 -g
CFLAGS  += $(CSTD) -Wall -Wextra -Wshadow -Wno-unused-parameter -Isrc
LDFLAGS ?=
LDLIBS  ?= -lm

BUILD   := build
SRCDIR  := src
TESTDIR := tests

LIB_SRCS := $(SRCDIR)/util.c $(SRCDIR)/strutil.c $(SRCDIR)/csv.c $(SRCDIR)/date.c \
            $(SRCDIR)/teams.c $(SRCDIR)/data.c $(SRCDIR)/query.c $(SRCDIR)/json.c $(SRCDIR)/tools.c \
            $(SRCDIR)/mcp.c
LIB_OBJS := $(LIB_SRCS:$(SRCDIR)/%.c=$(BUILD)/%.o)

MAIN_OBJ := $(BUILD)/main.o

TEST_SRCS := $(TESTDIR)/run_tests.c $(TESTDIR)/test_strutil.c $(TESTDIR)/test_csv.c \
             $(TESTDIR)/test_date.c $(TESTDIR)/test_json.c $(TESTDIR)/test_teams.c \
             $(TESTDIR)/test_data.c $(TESTDIR)/test_query.c $(TESTDIR)/test_mcp.c
TEST_OBJS := $(TEST_SRCS:$(TESTDIR)/%.c=$(BUILD)/t_%.o)

SERVER := brsoccer-mcp
TESTS  := run_tests

.PHONY: all test run demo clean

all: $(SERVER) $(TESTS)

$(SERVER): $(LIB_OBJS) $(MAIN_OBJ)
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $^ $(LDLIBS)

$(TESTS): $(LIB_OBJS) $(TEST_OBJS)
	$(CC) $(CFLAGS) $(LDFLAGS) -o $@ $^ $(LDLIBS)

$(BUILD)/%.o: $(SRCDIR)/%.c | $(BUILD)
	$(CC) $(CFLAGS) -c -o $@ $<

$(BUILD)/t_%.o: $(TESTDIR)/%.c | $(BUILD)
	$(CC) $(CFLAGS) -I$(TESTDIR) -c -o $@ $<

$(BUILD):
	mkdir -p $(BUILD)

test: all
	./$(TESTS)
	@sh $(TESTDIR)/mcp_stdio_test.sh

run: $(SERVER)
	./$(SERVER)

demo: $(SERVER)
	./$(SERVER) --demo

clean:
	rm -rf $(BUILD) $(SERVER) $(TESTS)

-include $(LIB_OBJS:.o=.d) $(MAIN_OBJ:.o=.d) $(TEST_OBJS:.o=.d)
CFLAGS += -MMD -MP
