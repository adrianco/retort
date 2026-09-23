CXX ?= c++
CXXFLAGS ?= -std=c++17 -O2 -Wall -Wextra
LDLIBS = -lsqlite3

all: book_server test_api

book_server: src/main.cpp src/book_api.cpp src/book_api.hpp
	$(CXX) $(CXXFLAGS) src/main.cpp src/book_api.cpp -o $@ $(LDLIBS)

test_api: tests/test_api.cpp src/book_api.cpp src/book_api.hpp
	$(CXX) $(CXXFLAGS) tests/test_api.cpp src/book_api.cpp -o $@ $(LDLIBS)

test: test_api
	./test_api

clean:
	rm -f book_server test_api

.PHONY: all test clean
