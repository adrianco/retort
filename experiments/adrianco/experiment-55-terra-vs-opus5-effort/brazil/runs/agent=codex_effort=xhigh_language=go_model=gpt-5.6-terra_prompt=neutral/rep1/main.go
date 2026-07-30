package main

import (
	"flag"
	"fmt"
	"os"
)

func main() {
	dataDir := flag.String("data-dir", "data/kaggle", "directory containing the six Kaggle CSV files")
	flag.Parse()
	data, err := LoadData(*dataDir)
	if err != nil {
		fmt.Fprintf(os.Stderr, "%s: failed to load data: %v\n", serverName, err)
		os.Exit(1)
	}
	if err := NewServer(data).RunServer(os.Stdin, os.Stdout); err != nil {
		fmt.Fprintf(os.Stderr, "%s: server error: %v\n", serverName, err)
		os.Exit(1)
	}
}
