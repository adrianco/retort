package main

import (
	"flag"
	"fmt"
	"os"

	"brsoccer/internal/data"
	"brsoccer/internal/mcp"
)

func main() {
	dataDir := flag.String("data", "data", "data directory containing kaggle/ subdirectory")
	flag.Parse()

	db, err := data.Load(*dataDir)
	if err != nil {
		fmt.Fprintf(os.Stderr, "load data: %v\n", err)
		os.Exit(1)
	}
	fmt.Fprintf(os.Stderr, "brsoccer-mcp: loaded %d matches, %d players\n", len(db.Matches), len(db.Players))

	srv := mcp.NewServer("brsoccer-mcp", "0.1.0")
	mcp.RegisterSoccerTools(srv, db)

	if err := srv.Serve(os.Stdin, os.Stdout); err != nil {
		fmt.Fprintf(os.Stderr, "serve: %v\n", err)
		os.Exit(1)
	}
}
