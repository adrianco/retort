.PHONY: build run test clean

build:
	go build -o book-api main.go

run: build
	./book-api

test:
	go test -v

clean:
	rm -f book-api
	rm -f books.db