CC = clang
CFLAGS = -O2 -Wall -Wextra -Wno-unused-parameter -fobjc-arc
soccer-mcp: main.m Graph.m Graph.h
	$(CC) $(CFLAGS) main.m Graph.m -framework Foundation -lsqlite3 -o $@
test: soccer-mcp
	python3 tests.py
clean:
	rm -f soccer-mcp
.PHONY: test clean
