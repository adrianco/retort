// Command brazilian-soccer-mcp is an MCP (Model Context Protocol) server
// that exposes Brazilian soccer match and player data - loaded from the CSV
// datasets in data/kaggle/ - as queryable tools over a JSON-RPC 2.0 stdio
// transport.
package main

import (
	"flag"
	"fmt"
	"os"
)

func main() {
	dataDir := flag.String("data-dir", "data/kaggle", "directory containing the Kaggle CSV datasets")
	flag.Parse()

	store, err := LoadAll(*dataDir)
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to load data: %v\n", err)
		os.Exit(1)
	}
	fmt.Fprintf(os.Stderr, "loaded %d matches and %d players from %s\n", len(store.Matches), len(store.Players), *dataDir)

	registry := BuildToolRegistry()
	server := NewServer(store, registry)

	if err := server.Run(os.Stdin, os.Stdout, os.Stderr); err != nil {
		fmt.Fprintf(os.Stderr, "server error: %v\n", err)
		os.Exit(1)
	}
}
