// Command brazilian-soccer-mcp is an MCP (Model Context Protocol) server that
// answers natural-language questions about Brazilian soccer — matches, teams,
// players, competitions and statistics — from the bundled Kaggle datasets.
//
// It speaks JSON-RPC 2.0 over stdio, so it can be attached to any MCP-capable
// LLM client (e.g. Claude Desktop) with a config entry such as:
//
//	{
//	  "mcpServers": {
//	    "brazilian-soccer": {
//	      "command": "/path/to/brazilian-soccer-mcp",
//	      "args": ["-data", "/path/to/data/kaggle"]
//	    }
//	  }
//	}
//
// Diagnostics go to stderr; the stdio channel carries only protocol messages.
package main

import (
	"flag"
	"fmt"
	"log"
	"os"

	"brazilian-soccer-mcp/internal/mcp"
	"brazilian-soccer-mcp/internal/soccer"
)

func main() {
	dataDir := flag.String("data", "data/kaggle", "directory containing the Kaggle CSV datasets")
	flag.Parse()

	log.SetOutput(os.Stderr)
	log.SetPrefix("brazilian-soccer-mcp: ")
	log.SetFlags(0)

	log.Printf("loading data from %s ...", *dataDir)
	store, err := soccer.LoadDir(*dataDir)
	if err != nil {
		fmt.Fprintf(os.Stderr, "fatal: failed to load data: %v\n", err)
		os.Exit(1)
	}
	log.Printf("loaded %d matches and %d players", len(store.Matches), len(store.Players))
	for _, w := range store.Warnings {
		log.Printf("warning: %s", w)
	}

	server := mcp.NewServer(store)
	log.Printf("serving %d tools over stdio", len(server.Tools()))
	if err := server.Serve(os.Stdin, os.Stdout); err != nil {
		fmt.Fprintf(os.Stderr, "fatal: serve error: %v\n", err)
		os.Exit(1)
	}
}
