// Command brazilian-soccer-mcp is an MCP (Model Context Protocol) server that
// exposes a knowledge-graph-style query interface over Brazilian soccer
// datasets (matches, teams, competitions and FIFA players).
//
// Context:
//   - Project: Brazilian Soccer MCP Server (see TASK.md).
//   - Role of this file: process entry point. It loads the CSV datasets from
//     data/kaggle (override with -data or BRAZIL_SOCCER_DATA), constructs the
//     query engine and MCP server, and serves JSON-RPC over stdio.
//   - Transport: MCP stdio — requests on stdin, responses on stdout, logs on
//     stderr. Run with an MCP client (e.g. Claude Desktop) or pipe JSON-RPC
//     lines for manual testing.
package main

import (
	"flag"
	"log"
	"os"

	"brazilian-soccer-mcp/internal/data"
	"brazilian-soccer-mcp/internal/mcp"
	"brazilian-soccer-mcp/internal/query"
)

func main() {
	dataDir := flag.String("data", defaultDataDir(), "directory containing the Kaggle CSV datasets")
	flag.Parse()

	logger := log.New(os.Stderr, "[brazilian-soccer-mcp] ", log.LstdFlags)

	logger.Printf("loading datasets from %q", *dataDir)
	db, err := data.Load(*dataDir)
	if err != nil {
		logger.Fatalf("failed to load datasets: %v", err)
	}
	logger.Printf("loaded %d matches and %d players", len(db.Matches), len(db.Players))

	engine := query.New(db)
	srv := mcp.NewServer(os.Stdin, os.Stdout, logger.Printf)
	mcp.NewSoccerServer(engine, srv)

	logger.Printf("brazilian-soccer-mcp ready (stdio transport)")
	if err := srv.Serve(); err != nil {
		logger.Fatalf("server error: %v", err)
	}
}

// defaultDataDir resolves the dataset directory, honoring the
// BRAZIL_SOCCER_DATA environment variable, then falling back to data/kaggle.
func defaultDataDir() string {
	if v := os.Getenv("BRAZIL_SOCCER_DATA"); v != "" {
		return v
	}
	return "data/kaggle"
}
