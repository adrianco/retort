package main

import (
	"flag"
	"fmt"
	"log"
	"os"
)

func main() {
	dataDir := flag.String("data", "data", "Path to the data directory (containing 'kaggle' subdir)")
	flag.Parse()

	store := NewDataStore()
	if err := store.LoadAll(*dataDir); err != nil {
		log.Fatalf("failed to load data: %v", err)
	}
	// Log to stderr so MCP stdout stays clean.
	fmt.Fprintf(os.Stderr, "loaded %d matches, %d players\n", len(store.Matches), len(store.Players))

	server := NewMCPServer(store)
	if err := server.Serve(os.Stdin, os.Stdout); err != nil {
		log.Fatalf("server error: %v", err)
	}
}
