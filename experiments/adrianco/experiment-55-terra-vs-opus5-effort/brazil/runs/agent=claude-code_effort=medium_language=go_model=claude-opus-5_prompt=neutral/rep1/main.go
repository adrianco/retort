// Command brazilian-soccer-mcp serves the Brazilian soccer knowledge graph
// over the Model Context Protocol on stdio.
//
// The whole dataset (about 17k matches and 18k player records) is loaded into
// memory at start-up, which takes roughly 100ms and makes every query a
// pointer walk rather than a file scan — comfortably inside the specification's
// 2s simple / 5s aggregate response budget.
//
// Usage:
//
//	brazilian-soccer-mcp [-data DIR]
//	brazilian-soccer-mcp -check          # load the data, print a report, exit
//
// The data directory defaults to ./data/kaggle and can also be set with
// SOCCER_DATA_DIR.
package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os"

	"github.com/modelcontextprotocol/go-sdk/mcp"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/mcpserver"
	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/soccer"
)

func main() {
	defaultDir := os.Getenv("SOCCER_DATA_DIR")
	if defaultDir == "" {
		defaultDir = "data/kaggle"
	}
	dataDir := flag.String("data", defaultDir, "directory holding the Kaggle CSV files")
	check := flag.Bool("check", false, "load the data, print a summary and exit")
	flag.Parse()

	// MCP speaks JSON-RPC on stdout, so diagnostics must go to stderr.
	log.SetFlags(0)
	log.SetOutput(os.Stderr)

	g, err := soccer.Load(*dataDir)
	if err != nil {
		log.Fatalf("loading data from %s: %v", *dataDir, err)
	}
	st := g.Stats()

	if *check {
		out, _ := json.MarshalIndent(map[string]any{
			"load":         st,
			"competitions": g.Competitions(),
		}, "", "  ")
		fmt.Println(string(out))
		return
	}

	log.Printf("brazilian-soccer-mcp %s: %d matches, %d clubs, %d players loaded in %s",
		mcpserver.Version, st.Matches, st.Teams, st.Players, st.LoadDuration)

	server := mcpserver.New(g)
	if err := server.Run(context.Background(), &mcp.StdioTransport{}); err != nil {
		log.Fatalf("server: %v", err)
	}
}
