// Command brazilian-soccer-mcp is an MCP server that answers questions
// about Brazilian soccer — matches, teams, players and competitions —
// from the provided Kaggle datasets.
//
// It speaks MCP over standard input and output, so an LLM host starts it
// as a subprocess:
//
//	brazilian-soccer-mcp -data data/kaggle
package main

import (
	"fmt"
	"os"

	"brsoccer/internal/app"
)

func main() {
	if err := app.Run(os.Args[1:], os.Stdin, os.Stdout, os.Stderr); err != nil {
		fmt.Fprintln(os.Stderr, "brazilian-soccer-mcp:", err)
		os.Exit(1)
	}
}
