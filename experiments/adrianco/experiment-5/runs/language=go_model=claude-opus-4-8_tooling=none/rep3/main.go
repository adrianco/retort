// Command brazilian-soccer-mcp is an MCP (Model Context Protocol) server that
// exposes the bundled Brazilian soccer Kaggle datasets to an LLM.
//
// Context:
//   - On start it loads the six CSV datasets from the data directory (default
//     ./data/kaggle, overridable with -data or $BR_SOCCER_DATA) into memory.
//   - By default it then speaks MCP over stdin/stdout so it can be wired into an
//     MCP-capable client. Diagnostics go to stderr to keep stdout clean for the
//     JSON-RPC stream.
//   - The -info flag prints a one-shot dataset summary and exits, which is handy
//     for verifying the data loaded correctly without an MCP client.
package main

import (
	"flag"
	"fmt"
	"os"

	"brazilian-soccer-mcp/internal/mcpserver"
	"brazilian-soccer-mcp/internal/soccer"
)

func main() {
	dataDir := flag.String("data", defaultDataDir(), "directory containing the Kaggle CSV files")
	info := flag.Bool("info", false, "print a dataset summary to stdout and exit (no MCP server)")
	flag.Parse()

	store, err := soccer.LoadStore(*dataDir)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error loading data from %q: %v\n", *dataDir, err)
		os.Exit(1)
	}
	fmt.Fprintf(os.Stderr, "brazilian-soccer-mcp: loaded %d matches and %d players from %s\n",
		len(store.Matches), len(store.Players), *dataDir)

	if *info {
		printInfo(store)
		return
	}

	srv := mcpserver.NewServer(store)
	if err := srv.Serve(os.Stdin, os.Stdout); err != nil {
		fmt.Fprintf(os.Stderr, "server error: %v\n", err)
		os.Exit(1)
	}
}

// defaultDataDir honours $BR_SOCCER_DATA, falling back to ./data/kaggle.
func defaultDataDir() string {
	if d := os.Getenv("BR_SOCCER_DATA"); d != "" {
		return d
	}
	return "data/kaggle"
}

func printInfo(store *soccer.Store) {
	comps := map[string]int{}
	for _, m := range store.Matches {
		comps[m.Competition]++
	}
	fmt.Printf("Matches: %d\nPlayers: %d\n", len(store.Matches), len(store.Players))
	fmt.Println("Competitions:")
	for comp, n := range comps {
		fmt.Printf("  %-24s %d\n", comp, n)
	}
}
