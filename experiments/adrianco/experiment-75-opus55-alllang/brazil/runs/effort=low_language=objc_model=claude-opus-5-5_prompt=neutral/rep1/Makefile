CC = clang
CFLAGS = -fobjc-arc -Wall -Wextra -Wno-unused-parameter -O2 -Isrc
LDFLAGS = -framework Foundation
LIB_SRC = src/BSCSV.m src/BSTeamNames.m src/BSModels.m src/BSDatabase.m src/BSTools.m src/BSMCPServer.m

all: build/brazilian-soccer-mcp build/tests

build/brazilian-soccer-mcp: $(LIB_SRC) src/main.m src/*.h
	@mkdir -p build
	$(CC) $(CFLAGS) $(LIB_SRC) src/main.m $(LDFLAGS) -o $@

build/tests: $(LIB_SRC) tests/BSTests.m src/*.h
	@mkdir -p build
	$(CC) $(CFLAGS) $(LIB_SRC) tests/BSTests.m $(LDFLAGS) -o $@

test: build/tests
	./build/tests

clean:
	rm -rf build

.PHONY: all test clean
