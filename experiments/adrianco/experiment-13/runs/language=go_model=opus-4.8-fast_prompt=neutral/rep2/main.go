// Command brazilian-soccer-mcp is an MCP (Model Context Protocol) server that
// answers natural-language questions about Brazilian soccer over the datasets in
// data/kaggle. It speaks JSON-RPC 2.0 over stdio and exposes tools for match,
// team, player, competition, and statistical queries (see internal/server).
//
// Context: this is the executable entry point. It resolves the data directory,
// loads the CSVs into an in-memory knowledge base, wires up the MCP tool catalog,
// and runs the stdio serve loop. Diagnostics go to stderr so they never corrupt
// the JSON-RPC stream on stdout. Usage:
//
//	brazilian-soccer-mcp [-data DIR]
//
// The -data flag (or BR_SOCCER_DATA env var) points at the directory containing
// the Kaggle CSV files; it defaults to ./data/kaggle.
package main

import (
	"flag"
	"fmt"
	"os"

	"brazilian-soccer-mcp/internal/server"
	"brazilian-soccer-mcp/internal/soccer"
)

func main() {
	defaultDir := os.Getenv("BR_SOCCER_DATA")
	if defaultDir == "" {
		defaultDir = "data/kaggle"
	}
	dataDir := flag.String("data", defaultDir, "directory containing the Kaggle CSV datasets")
	flag.Parse()

	db, err := soccer.Load(*dataDir)
	if err != nil {
		// Non-fatal: Load returns whatever it could parse alongside the error.
		fmt.Fprintf(os.Stderr, "warning: %v\n", err)
	}
	fmt.Fprintf(os.Stderr, "brazilian-soccer-mcp: loaded %d matches, %d players from %s\n",
		len(db.Matches), len(db.Players), *dataDir)

	if len(db.Matches) == 0 && len(db.Players) == 0 {
		fmt.Fprintf(os.Stderr, "error: no data loaded from %s\n", *dataDir)
		os.Exit(1)
	}

	srv := server.Build(db, os.Stdin, os.Stdout)
	if err := srv.Serve(); err != nil {
		fmt.Fprintf(os.Stderr, "serve error: %v\n", err)
		os.Exit(1)
	}
}
