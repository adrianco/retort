// Context: Brazilian Soccer MCP Server.
// File: cmd/server/main.go
// Purpose: Entry point. Loads the bundled Brazilian soccer datasets into an
// in-memory knowledge base and runs the MCP server over stdio (stdin/stdout),
// logging diagnostics to stderr so they never corrupt the JSON-RPC stream.
package main

import (
	"flag"
	"log"
	"os"

	"brazilian-soccer-mcp/internal/mcpserver"
	"brazilian-soccer-mcp/internal/soccer"
)

func main() {
	dataDir := flag.String("data", "data/kaggle", "directory containing the Kaggle CSV datasets")
	flag.Parse()

	log.SetOutput(os.Stderr)
	log.SetPrefix("[brazilian-soccer-mcp] ")

	log.Printf("loading datasets from %s ...", *dataDir)
	db, err := soccer.Load(*dataDir)
	if err != nil {
		log.Fatalf("failed to load data: %v", err)
	}
	log.Printf("loaded %d matches and %d players", len(db.Matches), len(db.Players))

	srv := mcpserver.NewServer(mcpserver.NewHandler(db))
	log.Printf("MCP server ready on stdio")
	if err := srv.Serve(os.Stdin, os.Stdout); err != nil {
		log.Fatalf("server error: %v", err)
	}
}
