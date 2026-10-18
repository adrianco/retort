# Makefile for Brazilian Soccer MCP Server

.PHONY: build test run clean

build:
	go build -o brazilian-soccer-mcp-server cmd/main.go

test:
	go test ./...

run: build
	./brazilian-soccer-mcp-server

clean:
	rm -f brazilian-soccer-mcp-server
	rm -rf coverage.out

.PHONY: build test run clean
