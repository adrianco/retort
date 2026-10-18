// Command brazilian-soccer-mcp serves Brazilian soccer data to an LLM over the
// Model Context Protocol (stdio transport).
package main

import (
	"flag"
	"fmt"
	"os"

	"brazilian-soccer-mcp/internal/data"
	"brazilian-soccer-mcp/internal/mcp"
)

func main() {
	dir := flag.String("data", "data/kaggle", "directory containing the Kaggle CSV datasets")
	flag.Parse()

	store, err := data.LoadDir(*dir)
	if err != nil {
		fmt.Fprintln(os.Stderr, "loading data:", err)
		os.Exit(1)
	}
	// Logs go to stderr; stdout is reserved for the protocol.
	fmt.Fprintf(os.Stderr, "loaded %d matches and %d players from %s\n", store.MatchCount(), store.PlayerCount(), *dir)

	if err := mcp.NewServer(store).Serve(os.Stdin, os.Stdout); err != nil {
		fmt.Fprintln(os.Stderr, "server error:", err)
		os.Exit(1)
	}
}
