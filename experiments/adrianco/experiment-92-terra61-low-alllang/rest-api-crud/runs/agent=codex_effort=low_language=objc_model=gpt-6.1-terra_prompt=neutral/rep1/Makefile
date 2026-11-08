CC = clang
CFLAGS = -Wall -Wextra -Wno-unused-parameter -fobjc-arc

books-server: main.m
	$(CC) $(CFLAGS) -framework Foundation -lsqlite3 main.m -o $@

test: books-server
	python3 -m unittest -v test_books.py

clean:
	rm -f books-server

.PHONY: test clean
