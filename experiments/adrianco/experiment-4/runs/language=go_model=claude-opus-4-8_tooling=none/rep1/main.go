// Command brazilian-soccer-mcp is an MCP (Model Context Protocol) server that
// answers natural-language questions about Brazilian soccer using the bundled
// Kaggle datasets.
//
// Context
// -------
// On startup it loads all six CSV datasets from data/kaggle (located by walking
// up from the working directory, or from -data) into an in-memory knowledge
// graph, then speaks the MCP stdio transport (newline-delimited JSON-RPC 2.0)
// on stdin/stdout. Diagnostic output goes to stderr so it never corrupts the
// protocol stream.
//
// Usage:
//
//	brazilian-soccer-mcp [-data path/to/data/kaggle]
//
// The server exposes tools for match search, head-to-head records, team
// statistics, league standings, player search and competition-wide statistics.
package main

import (
	"flag"
	"fmt"
	"os"

	"brazilian-soccer-mcp/internal/mcp"
	"brazilian-soccer-mcp/internal/soccer"
)

func main() {
	dataFlag := flag.String("data", "", "path to data/kaggle directory (auto-detected if empty)")
	flag.Parse()

	dataDir := *dataFlag
	if dataDir == "" {
		if found, ok := soccer.FindDataDir(""); ok {
			dataDir = found
		} else {
			fmt.Fprintln(os.Stderr, "error: could not locate data/kaggle directory; pass -data")
			os.Exit(1)
		}
	}

	fmt.Fprintf(os.Stderr, "[brazilian-soccer-mcp] loading datasets from %s ...\n", dataDir)
	graph, err := soccer.LoadGraph(dataDir)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error loading data: %v\n", err)
		os.Exit(1)
	}
	fmt.Fprintf(os.Stderr, "[brazilian-soccer-mcp] loaded %s\n", graph.Stats())
	fmt.Fprintln(os.Stderr, "[brazilian-soccer-mcp] ready on stdio (MCP)")

	server := mcp.NewServer(graph)
	if err := server.Serve(os.Stdin, os.Stdout); err != nil {
		fmt.Fprintf(os.Stderr, "server error: %v\n", err)
		os.Exit(1)
	}
}
