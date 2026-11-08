CC = clang
CFLAGS = -fobjc-arc -Wall -Wextra -Wno-unused-parameter

books: main.m
	$(CC) $(CFLAGS) main.m -framework Foundation -lsqlite3 -o books

test-harness: tests/harness.m main.m
	$(CC) $(CFLAGS) tests/harness.m -framework Foundation -lsqlite3 -o test-harness

test: books test-harness
	python3 -m unittest discover -s tests -v

clean:
	rm -f books test-harness

.PHONY: test clean
