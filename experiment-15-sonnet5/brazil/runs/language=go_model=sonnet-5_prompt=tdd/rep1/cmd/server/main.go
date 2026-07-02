// Command server runs the Brazilian soccer MCP server over stdio, serving
// data loaded from data/kaggle.
package main

import (
	"context"
	"flag"
	"log"

	"brazilian-soccer-mcp/internal/mcpserver"
	"brazilian-soccer-mcp/internal/soccer"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func main() {
	dataDir := flag.String("data-dir", "data/kaggle", "directory containing the source CSV datasets")
	flag.Parse()

	store, err := soccer.LoadStoreFromDir(*dataDir)
	if err != nil {
		log.Fatalf("loading data from %s: %v", *dataDir, err)
	}
	log.Printf("loaded %d matches and %d players from %s", len(store.Matches), len(store.Players), *dataDir)

	server := mcpserver.New(store)
	if err := server.Run(context.Background(), &mcp.StdioTransport{}); err != nil {
		log.Fatalf("server failed: %v", err)
	}
}
