CC = clang
CFLAGS = -Wall -Wextra -Wno-unused-parameter -fobjc-arc
LDLIBS = -framework Foundation -lsqlite3

books: main.m
	$(CC) $(CFLAGS) $< -o $@ $(LDLIBS)

test: books
	python3 -m unittest -v test_books.py

clean:
	rm -f books

.PHONY: test clean
