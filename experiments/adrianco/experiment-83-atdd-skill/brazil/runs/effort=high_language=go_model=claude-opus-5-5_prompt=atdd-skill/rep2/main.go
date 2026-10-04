// Command brsoccer is an MCP server answering questions about Brazilian
// football from the provided Kaggle datasets: matches from the Brasileirão,
// Copa do Brasil and Copa Libertadores, and FIFA player ratings.
//
// Usage: brsoccer [-data data/kaggle]
//
// It speaks the Model Context Protocol over stdin/stdout.
package main

import (
	"flag"
	"fmt"
	"os"
	"time"

	"brsoccer/internal/mcp"
	"brsoccer/internal/soccer"
	"brsoccer/internal/tools"
)

func main() {
	dataDir := flag.String("data", envOr("SOCCER_DATA_DIR", "data/kaggle"), "directory holding the Kaggle CSV files")
	flag.Parse()

	start := time.Now()
	store := soccer.Load(*dataDir)
	for _, d := range store.Datasets {
		if !d.Loaded {
			fmt.Fprintf(os.Stderr, "brsoccer: %s not loaded: %s\n", d.File, d.Error)
		}
	}
	fmt.Fprintf(os.Stderr, "brsoccer: %d matches and %d players loaded from %s in %v\n",
		len(store.Matches), len(store.Players), *dataDir, time.Since(start).Round(time.Millisecond))

	server := mcp.NewServer("brazilian-soccer", "1.0.0",
		"Answers questions about Brazilian football: Brasileirão (2003-2023), Copa do Brasil, Copa Libertadores matches, "+
			"team records, standings, head-to-head, statistics, and FIFA 19 player ratings. Team names may be given in any common form.")
	tools.Register(server, store)
	if err := server.Serve(os.Stdin, os.Stdout); err != nil {
		fmt.Fprintln(os.Stderr, "brsoccer:", err)
		os.Exit(1)
	}
}

func envOr(key, def string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return def
}
