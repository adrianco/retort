// Command brsoccer-mcp is an MCP stdio server answering questions about Brazilian soccer.
package main

import (
	"flag"
	"log"
	"os"

	"brsoccer/mcp"
	"brsoccer/soccer"
)

func main() {
	dir := flag.String("data", "data/kaggle", "directory containing the Kaggle CSV files")
	flag.Parse()
	log.SetOutput(os.Stderr)
	db, err := soccer.Load(*dir)
	if err != nil {
		log.Fatal(err)
	}
	if err := mcp.New(db).Serve(os.Stdin, os.Stdout); err != nil {
		log.Fatal(err)
	}
}
