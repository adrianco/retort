// main.go - Entry point for the Brazilian Soccer MCP server.
//
// Context: Loads the six Kaggle CSV datasets into memory and serves the MCP
// protocol over stdio (newline-delimited JSON-RPC 2.0). Configure the data
// directory with -data (default "data/kaggle", also resolved relative to the
// executable so the server works regardless of the client's working dir).
// Diagnostics go to stderr; stdout is reserved for protocol messages.
package main

import (
	"flag"
	"fmt"
	"log"
	"os"
	"path/filepath"
)

const serverVersion = "1.0.0"

func resolveDataDir(dir string) string {
	if _, err := os.Stat(dir); err == nil {
		return dir
	}
	if exe, err := os.Executable(); err == nil {
		alt := filepath.Join(filepath.Dir(exe), dir)
		if _, err := os.Stat(alt); err == nil {
			return alt
		}
	}
	return dir
}

func main() {
	dataDir := flag.String("data", filepath.Join("data", "kaggle"), "directory containing the Kaggle CSV files")
	flag.Parse()
	log.SetOutput(os.Stderr)
	log.SetPrefix("[brazilian-soccer-mcp] ")

	store, err := LoadStore(resolveDataDir(*dataDir))
	if err != nil {
		log.Fatalf("failed to load data: %v", err)
	}
	log.Printf("loaded %d matches and %d players", len(store.Matches), len(store.Players))

	server := &MCPServer{
		Name:    "brazilian-soccer-mcp",
		Version: serverVersion,
		Tools:   BuildTools(store),
	}
	if err := server.Serve(os.Stdin, os.Stdout); err != nil {
		fmt.Fprintf(os.Stderr, "server error: %v\n", err)
		os.Exit(1)
	}
}
