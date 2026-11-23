books: Books.m
	clang -Wall -Wextra -fobjc-arc -framework Foundation -lsqlite3 Books.m -o books

.PHONY: test clean
test: books
	python3 -m unittest -v test_books

clean:
	rm -f books
