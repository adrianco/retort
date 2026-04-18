// Package main - Brazilian Soccer MCP Server
// main.go: Entry point for the MCP server.
// Loads all CSV datasets from data/kaggle/ and serves MCP requests over stdio.
//
// Usage: ./brazilian-soccer-mcp [data-dir]
// Default data dir: data/kaggle
package main

import (
	"log"
	"os"
)

func main() {
	log.SetOutput(os.Stderr)
	log.SetFlags(log.LstdFlags | log.Lshortfile)

	dataDir := "data/kaggle"
	if len(os.Args) > 1 {
		dataDir = os.Args[1]
	}

	db := NewDatabase()
	log.Printf("Loading data from %s ...", dataDir)
	if err := db.LoadAll(dataDir); err != nil {
		log.Fatalf("Failed to load data: %v", err)
	}
	log.Printf("Loaded %d matches and %d players", len(db.Matches), len(db.Players))

	server := NewMCPServer(db)
	log.Println("Brazilian Soccer MCP Server ready (stdio transport)")
	if err := server.Serve(os.Stdin, os.Stdout); err != nil {
		log.Fatalf("Server error: %v", err)
	}
}
