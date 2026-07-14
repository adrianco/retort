// main.go is the entry point for the Brazilian Soccer MCP server. It loads the
// CSV datasets into memory and serves MCP requests over stdio.
//
// Usage:
//
//	brazilian-soccer-mcp [-data DIR]
//
// The server speaks newline-delimited JSON-RPC 2.0 on stdin/stdout; all
// diagnostics go to stderr so they never corrupt the protocol stream.
package main

import (
	"flag"
	"log"
	"os"
)

func main() {
	dataDir := flag.String("data", "data/kaggle", "directory containing the Kaggle CSV datasets")
	flag.Parse()

	log.SetOutput(os.Stderr)
	log.SetPrefix("[brazilian-soccer-mcp] ")
	log.SetFlags(0)

	store, err := LoadAll(*dataDir)
	if err != nil {
		log.Fatalf("failed to load data: %v", err)
	}
	log.Printf("loaded %d matches and %d players from %s",
		len(store.Matches), len(store.Players), *dataDir)

	server := NewServer(BuildTools(store), os.Stdout)
	log.Printf("MCP server ready (%d tools); waiting for requests on stdin", len(server.tools))

	if err := server.Serve(os.Stdin); err != nil {
		log.Fatalf("server error: %v", err)
	}
}
