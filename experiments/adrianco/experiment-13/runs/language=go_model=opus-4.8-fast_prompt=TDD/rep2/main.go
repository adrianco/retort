// Command brazilian-soccer-mcp is an MCP (Model Context Protocol) server that
// exposes a knowledge graph of Brazilian soccer data — matches, teams,
// players, competitions and statistics — loaded from the bundled Kaggle CSV
// datasets. It speaks JSON-RPC 2.0 over stdio so it can be connected to an LLM
// client such as Claude.
//
// Usage:
//
//	brazilian-soccer-mcp [-data DIR]
//
// The server loads every dataset under DIR (default ./data/kaggle) at startup
// and then serves tool calls on stdin/stdout.
package main

import (
	"flag"
	"fmt"
	"os"

	"brazilian-soccer-mcp/internal/mcp"
	"brazilian-soccer-mcp/internal/soccer"
)

func main() {
	dataDir := flag.String("data", "data/kaggle", "directory containing the Kaggle CSV datasets")
	flag.Parse()

	// Progress and errors go to stderr; stdout is reserved for the JSON-RPC
	// protocol stream.
	fmt.Fprintf(os.Stderr, "Loading datasets from %s ...\n", *dataDir)
	kb, err := soccer.LoadDir(*dataDir)
	if err != nil {
		fmt.Fprintf(os.Stderr, "fatal: %v\n", err)
		os.Exit(1)
	}
	fmt.Fprintf(os.Stderr, "Loaded %d matches and %d players. MCP server ready.\n",
		len(kb.Matches), len(kb.Players))

	server := mcp.New(kb)
	if err := server.Serve(os.Stdin, os.Stdout); err != nil {
		fmt.Fprintf(os.Stderr, "fatal: %v\n", err)
		os.Exit(1)
	}
}
