// Command bsmcp runs the Brazilian Soccer MCP server over stdio.
//
// Usage:
//
//	bsmcp [-data <dir>]
//
// It reads JSON-RPC 2.0 / MCP requests from stdin and writes responses to
// stdout, exposing tools for querying Brazilian soccer matches, teams, players,
// competitions and statistics loaded from the CSV datasets under <dir>/kaggle.
package main

import (
	"context"
	"flag"
	"fmt"
	"os"
	"os/signal"

	app "brazilian-soccer-mcp"
)

func main() {
	dataDir := flag.String("data", "data", "directory containing the kaggle/ datasets")
	flag.Parse()

	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt)
	defer stop()

	if err := app.Run(ctx, *dataDir, os.Stdin, os.Stdout); err != nil {
		fmt.Fprintln(os.Stderr, "bsmcp:", err)
		os.Exit(1)
	}
}
