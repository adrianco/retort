// Command brazilian-soccer-mcp is an MCP (Model Context Protocol) server that
// exposes a knowledge graph over the bundled Brazilian soccer datasets
// (Brasileirão, Copa do Brasil, Copa Libertadores match data plus the FIFA
// player database). It speaks JSON-RPC 2.0 over stdio, the transport used by
// MCP clients such as Claude Desktop.
//
// Usage:
//
//	brazilian-soccer-mcp [-data dir]
//
// The server loads the CSV files under -data (default ./data/kaggle, also
// overridable with the BRMCP_DATA environment variable), then serves MCP
// requests on stdin/stdout. Diagnostics are written to stderr so they never
// corrupt the JSON-RPC stream.
package main

import (
	"context"
	"flag"
	"log"
	"os"
	"os/signal"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/mcp"
	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/soccer"
)

const (
	serverName    = "brazilian-soccer-mcp"
	serverVersion = "1.0.0"
)

func main() {
	defaultDir := os.Getenv("BRMCP_DATA")
	if defaultDir == "" {
		defaultDir = "data/kaggle"
	}
	dataDir := flag.String("data", defaultDir, "directory containing the Kaggle CSV files")
	flag.Parse()

	logger := log.New(os.Stderr, "["+serverName+"] ", 0)

	db, err := soccer.Load(*dataDir)
	if err != nil {
		logger.Fatalf("failed to load data from %q: %v", *dataDir, err)
	}
	logger.Printf("loaded %d matches, %d players, %d teams across %d competitions",
		len(db.Matches), len(db.Players), db.TeamCount(), len(db.Competitions()))

	srv := mcp.NewServer(db, serverName, serverVersion)

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt)
	defer stop()

	logger.Printf("ready: %d tools, serving MCP over stdio", len(srv.Tools()))
	if err := srv.Serve(ctx, os.Stdin, os.Stdout); err != nil && ctx.Err() == nil {
		logger.Fatalf("serve error: %v", err)
	}
}
