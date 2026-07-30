package main

import (
	"flag"
	"fmt"
	"os"
)

func main() {
	dataDir := flag.String("data", "data/kaggle", "directory containing the supplied CSV files")
	flag.Parse()
	repo, err := NewRepository(*dataDir)
	if err != nil {
		fmt.Fprintln(os.Stderr, "load soccer data:", err)
		os.Exit(1)
	}
	if err := Serve(repo, os.Stdin, os.Stdout); err != nil {
		fmt.Fprintln(os.Stderr, "MCP server:", err)
		os.Exit(1)
	}
}
