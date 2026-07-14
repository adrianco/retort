// brazilian-soccer-mcp is an MCP server providing a knowledge graph interface
// for Brazilian soccer data loaded from Kaggle CSV datasets.
package main

import (
	"context"
	"fmt"
	"log"
	"os"
	"path/filepath"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"

	"brazilian-soccer-mcp/data"
	"brazilian-soccer-mcp/tools"
)

func main() {
	// Determine data directory
	dataDir := os.Getenv("DATA_DIR")
	if dataDir == "" {
		// Default: relative to executable
		exe, err := os.Executable()
		if err != nil {
			log.Fatalf("cannot determine executable path: %v", err)
		}
		dataDir = filepath.Join(filepath.Dir(exe), "data", "kaggle")
	}

	log.Printf("Loading datasets from %s ...", dataDir)
	store, err := data.LoadStore(dataDir)
	if err != nil {
		log.Fatalf("failed to load data: %v", err)
	}
	log.Printf("Loaded: %d brasileirao, %d cup, %d libertadores, %d br-football, %d historical, %d players",
		len(store.BrasileiraoMatches),
		len(store.CupMatches),
		len(store.LibertadoresMatches),
		len(store.BRFootballMatches),
		len(store.HistoricalMatches),
		len(store.Players),
	)

	s := server.NewMCPServer(
		"Brazilian Soccer MCP",
		"1.0.0",
		server.WithToolCapabilities(true),
	)

	// Register all tools
	tools.RegisterMatchTools(s, store)
	tools.RegisterTeamTools(s, store)
	tools.RegisterPlayerTools(s, store)
	tools.RegisterCompetitionTools(s, store)

	// Add a helpful resource listing available data
	s.AddResource(mcp.NewResource(
		"soccer://datasets",
		"Available Datasets",
		mcp.WithResourceDescription("Lists all datasets loaded and their record counts"),
		mcp.WithMIMEType("text/plain"),
	), func(_ context.Context, _ mcp.ReadResourceRequest) ([]mcp.ResourceContents, error) {
		text := fmt.Sprintf(
			"Brazilian Soccer MCP Datasets\n\n"+
				"Brasileirão Serie A:     %d matches\n"+
				"Copa do Brasil:          %d matches\n"+
				"Copa Libertadores:       %d matches\n"+
				"BR Football (extended):  %d matches\n"+
				"Historical Brasileirão:  %d matches\n"+
				"FIFA Players:            %d players\n",
			len(store.BrasileiraoMatches),
			len(store.CupMatches),
			len(store.LibertadoresMatches),
			len(store.BRFootballMatches),
			len(store.HistoricalMatches),
			len(store.Players),
		)
		return []mcp.ResourceContents{
			mcp.TextResourceContents{
				URI:      "soccer://datasets",
				MIMEType: "text/plain",
				Text:     text,
			},
		}, nil
	})

	// Run using stdio transport (standard for MCP servers)
	if err := server.ServeStdio(s); err != nil {
		log.Fatalf("server error: %v", err)
	}
}
