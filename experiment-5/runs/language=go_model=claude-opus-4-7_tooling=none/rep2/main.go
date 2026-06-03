package main

import (
	"flag"
	"fmt"
	"os"
)

func main() {
	dataDir := flag.String("data", "data/kaggle", "Directory containing the Kaggle CSV files.")
	flag.Parse()

	ds, err := LoadDataset(*dataDir)
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to load dataset: %v\n", err)
		os.Exit(1)
	}
	fmt.Fprintf(os.Stderr, "Loaded %d matches and %d players from %s\n",
		len(ds.Matches), len(ds.Players), *dataDir)

	srv := NewServer(ds)
	if err := srv.Serve(os.Stdin, os.Stdout); err != nil {
		fmt.Fprintf(os.Stderr, "server error: %v\n", err)
		os.Exit(1)
	}
}
