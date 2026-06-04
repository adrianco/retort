// Brazilian Soccer MCP Server
//
// File: main.go
// Responsibility: Process entry point. Resolves the data directory, loads all
// datasets into the in-memory Store, registers the soccer tools on a stdio MCP
// server and runs the JSON-RPC loop until stdin closes. Diagnostic/progress
// output goes to stderr so it never corrupts the JSON-RPC stream on stdout.
//
// Usage:
//
//	brazilian-soccer-mcp [--data <dir>]
//
// The server speaks MCP over stdio and is intended to be launched by an MCP
// client (e.g. an LLM host). The optional --data flag overrides the default
// "data/kaggle" dataset location; the BR_SOCCER_DATA environment variable is
// also honored.
package main

import (
	"flag"
	"fmt"
	"os"
)

const (
	serverName    = "brazilian-soccer-mcp"
	serverVersion = "1.0.0"
)

func main() {
	dataDir := flag.String("data", defaultDataDir(), "directory containing the Kaggle CSV datasets")
	flag.Parse()

	store, err := LoadAll(*dataDir)
	if err != nil {
		fmt.Fprintf(os.Stderr, "fatal: failed to load data: %v\n", err)
		os.Exit(1)
	}
	fmt.Fprintf(os.Stderr, "%s %s ready: %d matches, %d players\n",
		serverName, serverVersion, len(store.Matches), len(store.Players))

	srv := NewServer(serverName, serverVersion)
	RegisterTools(srv, store)

	if err := srv.Serve(os.Stdin, os.Stdout); err != nil {
		fmt.Fprintf(os.Stderr, "fatal: server error: %v\n", err)
		os.Exit(1)
	}
}

// defaultDataDir returns the dataset directory, honoring the BR_SOCCER_DATA
// environment variable and falling back to "data/kaggle".
func defaultDataDir() string {
	if d := os.Getenv("BR_SOCCER_DATA"); d != "" {
		return d
	}
	return "data/kaggle"
}
