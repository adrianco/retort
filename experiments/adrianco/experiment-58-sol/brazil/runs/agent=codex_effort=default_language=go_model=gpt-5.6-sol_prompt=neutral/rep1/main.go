package main

import (
	"context"
	"flag"
	"fmt"
	"os"
)

func main() {
	dataDir := flag.String("data", "data/kaggle", "directory containing the six CSV datasets")
	flag.Parse()
	store, err := LoadStore(*dataDir)
	if err != nil {
		fmt.Fprintln(os.Stderr, "brazilian-soccer-mcp:", err)
		os.Exit(1)
	}
	if err := NewServer(store).Serve(context.Background(), os.Stdin, os.Stdout); err != nil {
		fmt.Fprintln(os.Stderr, "brazilian-soccer-mcp:", err)
		os.Exit(1)
	}
}
