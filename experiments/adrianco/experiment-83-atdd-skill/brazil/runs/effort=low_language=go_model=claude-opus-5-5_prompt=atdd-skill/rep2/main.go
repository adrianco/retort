// Command brsoccer is an MCP server (stdio) answering questions about Brazilian soccer.
package main

import (
	"flag"
	"log"
	"os"
)

func main() {
	dir := flag.String("data", "data/kaggle", "directory containing the Kaggle CSV files")
	flag.Parse()
	store, err := Load(*dir)
	if err != nil {
		log.Fatal(err)
	}
	if err := NewServer(store).Serve(os.Stdin, os.Stdout); err != nil {
		log.Fatal(err)
	}
}
