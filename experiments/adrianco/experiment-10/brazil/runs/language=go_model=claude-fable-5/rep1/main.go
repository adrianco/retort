// Brazilian Soccer MCP Server: exposes Kaggle datasets of Brazilian soccer
// matches and FIFA player data as MCP tools over stdio, so an LLM can answer
// natural-language questions about players, teams, matches and competitions.
//
// Usage: brazilian-soccer-mcp [-data data/kaggle]
package main

import (
	"flag"
	"log"
	"os"
)

func main() {
	dataDir := flag.String("data", "data/kaggle", "directory containing the Kaggle CSV files")
	flag.Parse()

	log.SetOutput(os.Stderr) // stdout is reserved for the MCP protocol
	log.SetPrefix(serverName + ": ")

	store, err := LoadStore(*dataDir)
	if err != nil {
		log.Fatalf("loading data from %s: %v", *dataDir, err)
	}
	log.Printf("loaded %d matches and %d players from %s", len(store.Matches), len(store.Players), *dataDir)

	srv := NewServer(store)
	if err := srv.Serve(os.Stdin, os.Stdout); err != nil {
		log.Fatalf("serve: %v", err)
	}
}
