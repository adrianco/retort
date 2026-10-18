// Command brazilian-soccer-mcp serves Brazilian soccer data to an LLM over the
// Model Context Protocol (stdio transport).
//
//	go run . -data data/kaggle
package main

import (
	"flag"
	"log"
	"os"
)

func main() {
	dataDir := flag.String("data", "data/kaggle", "directory containing the Kaggle CSV files")
	flag.Parse()

	store, err := LoadStore(*dataDir)
	if err != nil {
		log.Fatalf("loading data from %s: %v", *dataDir, err)
	}
	log.Printf("loaded %d matches, %d teams, %d players", len(store.Matches), len(store.Teams), len(store.Players))

	srv := NewServer("brazilian-soccer-mcp", "1.0.0", newTools(store))
	if err := srv.Serve(os.Stdin, os.Stdout); err != nil {
		log.Fatalf("serving: %v", err)
	}
}
