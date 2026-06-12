// Context: Entry point for the Brazilian Soccer MCP server binary. It loads the
// bundled Kaggle datasets from the data directory (overridable via the
// BRAZIL_SOCCER_DATA_DIR environment variable or a -data flag) into an in-memory
// Store, then runs the MCP JSON-RPC server over stdin/stdout so an LLM client
// can query Brazilian soccer matches, teams, players, competitions and
// statistics through the advertised tools.
package main

import (
	"context"
	"flag"
	"fmt"
	"os"
	"os/signal"
)

func main() {
	dataDir := flag.String("data", defaultDataDir(), "directory containing the Kaggle CSV datasets")
	flag.Parse()

	store := NewStore()
	if err := store.LoadDir(*dataDir); err != nil {
		fmt.Fprintf(os.Stderr, "failed to load datasets from %s: %v\n", *dataDir, err)
		os.Exit(1)
	}
	fmt.Fprintf(os.Stderr, "brazilian-soccer-mcp: loaded %d matches and %d players from %s\n",
		len(store.Matches), len(store.Players), *dataDir)

	srv := NewServer(store)

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt)
	defer stop()

	if err := srv.Serve(ctx, os.Stdin, os.Stdout); err != nil && ctx.Err() == nil {
		fmt.Fprintf(os.Stderr, "server error: %v\n", err)
		os.Exit(1)
	}
}

func defaultDataDir() string {
	if d := os.Getenv("BRAZIL_SOCCER_DATA_DIR"); d != "" {
		return d
	}
	return "data/kaggle"
}
