CXX ?= c++
CXXFLAGS ?= -std=c++17 -O2 -Wall -Wextra
LDLIBS = -lsqlite3
LIB = src/json.cpp src/book_store.cpp src/api.cpp

all: books_server test_api

books_server: $(LIB) src/main.cpp src/*.hpp
	$(CXX) $(CXXFLAGS) -o $@ $(LIB) src/main.cpp $(LDLIBS)

test_api: $(LIB) tests/test_api.cpp src/*.hpp
	$(CXX) $(CXXFLAGS) -o $@ $(LIB) tests/test_api.cpp $(LDLIBS)

test: test_api
	./test_api

clean:
	rm -f books_server test_api

.PHONY: all test clean
