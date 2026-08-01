CXX ?= c++
CXXFLAGS ?= -std=c++17 -Wall -Wextra -Wpedantic -O2
LDLIBS = -lsqlite3

.PHONY: all test clean
all: book_api
book_api: main.o book_service.o
	$(CXX) $(LDFLAGS) -o $@ $^ $(LDLIBS)

tests: tests.o book_service.o
	$(CXX) $(LDFLAGS) -o $@ $^ $(LDLIBS)
test: tests
	./tests

clean:
	rm -f book_api tests *.o books.db
