// Brazilian Soccer MCP server.
//
// Loads the Kaggle CSV datasets under -data (default data/kaggle) and serves
// match, team, player and competition queries to an MCP client over stdio.
//
//	go run . -data data/kaggle
//
// Logs go to stderr; stdout carries only protocol messages.

package main

import (
	"flag"
	"fmt"
	"log"
	"os"
)

const serverVersion = "1.0.0"

func main() {
	dataDir := flag.String("data", "data/kaggle", "directory containing the Kaggle CSV files")
	flag.Parse()

	log.SetOutput(os.Stderr)
	log.SetPrefix("brazilian-soccer-mcp: ")

	ds, err := LoadDataset(*dataDir)
	if err != nil {
		fmt.Fprintln(os.Stderr, "failed to load data:", err)
		os.Exit(1)
	}
	log.Printf("loaded %d matches and %d players", len(ds.Matches), len(ds.Players))

	h := &Handler{DS: ds}
	srv := &Server{
		Name:    "brazilian-soccer",
		Version: serverVersion,
		Tools:   Tools(),
		Call:    h.Call,
	}
	if err := srv.Serve(os.Stdin, os.Stdout); err != nil {
		log.Fatal(err)
	}
}
