package main

import (
	"flag"
	"fmt"
	"os"
)

func main() {
	dataDir := flag.String("data-dir", defaultDataDir(), "directory containing the six supplied CSV files")
	flag.Parse()

	database, err := LoadDatabase(*dataDir)
	if err != nil {
		fmt.Fprintf(os.Stderr, "%s: %v\n", serverName, err)
		os.Exit(1)
	}
	if err := NewMCPServer(database).Serve(os.Stdin, os.Stdout); err != nil {
		fmt.Fprintf(os.Stderr, "%s: %v\n", serverName, err)
		os.Exit(1)
	}
}

func defaultDataDir() string {
	if directory := os.Getenv("BRAZILIAN_SOCCER_DATA_DIR"); directory != "" {
		return directory
	}
	return "data/kaggle"
}
