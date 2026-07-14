package main

import (
	"fmt"
	"log"
	"os"

	"brazilian-soccer-mcp/mcp"
)

func main() {
	dataDir := "data/kaggle"
	if len(os.Args) > 1 {
		dataDir = os.Args[1]
	}

	srv, err := mcp.NewServer(dataDir)
	if err != nil {
		log.Fatalf("failed to load data: %v", err)
	}

	if err := srv.ServeStdio(); err != nil {
		fmt.Fprintf(os.Stderr, "server error: %v\n", err)
		os.Exit(1)
	}
}
