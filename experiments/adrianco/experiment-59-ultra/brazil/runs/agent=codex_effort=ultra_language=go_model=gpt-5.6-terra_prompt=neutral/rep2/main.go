package main

import (
	"flag"
	"fmt"
	"log"
	"os"
)

func main() {
	dataDir := flag.String("data-dir", "data/kaggle", "directory containing the six supplied CSV datasets")
	flag.Parse()

	store, err := LoadStore(*dataDir)
	if err != nil {
		fmt.Fprintf(os.Stderr, "%s: unable to load datasets: %v\n", serverName, err)
		os.Exit(1)
	}
	log.SetOutput(os.Stderr)
	log.SetPrefix(serverName + ": ")
	log.Printf("loaded %d match rows and %d player rows from %s", len(store.Matches), len(store.Players), *dataDir)

	if err := NewMCPServer(store).Serve(os.Stdin, os.Stdout); err != nil {
		fmt.Fprintf(os.Stderr, "%s: MCP stream failed: %v\n", serverName, err)
		os.Exit(1)
	}
}
