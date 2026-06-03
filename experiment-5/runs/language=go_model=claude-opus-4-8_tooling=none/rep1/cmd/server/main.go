// Command server is the entry point for the Brazilian Soccer MCP server.
//
// Context:
//   - It loads the bundled Kaggle CSV datasets into an in-memory store, builds
//     the MCP server over that store and serves the Model Context Protocol on
//     stdin/stdout so an LLM host can call the soccer query tools.
//   - The data directory defaults to ./data/kaggle but can be overridden with
//     the -data flag or the SOCCER_DATA_DIR environment variable, so the binary
//     works regardless of the working directory the host launches it from.
//   - Diagnostics (load summary, errors) go to stderr; stdout is reserved
//     exclusively for the JSON-RPC protocol stream.
package main

import (
	"flag"
	"fmt"
	"os"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/mcpserver"
	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/soccer"
)

func main() {
	defaultDir := os.Getenv("SOCCER_DATA_DIR")
	if defaultDir == "" {
		defaultDir = "data/kaggle"
	}
	dataDir := flag.String("data", defaultDir, "directory containing the Kaggle CSV files")
	flag.Parse()

	store, err := soccer.Load(*dataDir)
	if err != nil {
		fmt.Fprintf(os.Stderr, "fatal: loading data from %q: %v\n", *dataDir, err)
		os.Exit(1)
	}
	fmt.Fprintf(os.Stderr, "brazilian-soccer-mcp: loaded %d matches and %d players from %q\n",
		len(store.Matches), len(store.Players), *dataDir)
	fmt.Fprintf(os.Stderr, "competitions: %v\n", store.Competitions())

	srv := mcpserver.NewServer(store)
	if err := srv.Serve(os.Stdin, os.Stdout); err != nil {
		fmt.Fprintf(os.Stderr, "fatal: serve: %v\n", err)
		os.Exit(1)
	}
}
