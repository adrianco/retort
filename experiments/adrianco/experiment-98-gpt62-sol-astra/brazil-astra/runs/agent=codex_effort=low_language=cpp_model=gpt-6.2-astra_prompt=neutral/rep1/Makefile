CXXFLAGS ?= -O2 -Wall -Wextra
CPPFLAGS += $(shell pkg-config --cflags json-c sqlite3)
LDLIBS += $(shell pkg-config --libs json-c sqlite3)

soccer-mcp: server.cpp data.cpp soccer.hpp
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) -std=c++17 server.cpp data.cpp -o $@ $(LDLIBS)

.PHONY: test clean
test: soccer-mcp
	python3 test_soccer.py
clean:
	rm -f soccer-mcp
