// Command brazilian-soccer-mcp is an MCP (Model Context Protocol) server
// that exposes the Brazilian soccer datasets under data/kaggle/ as a set of
// query tools (matches, teams, head-to-head, standings, stats, players) over
// the MCP stdio transport.
package main

import (
	"flag"
	"log"
	"os"
	"path/filepath"
)

func resolveDataDir(flagValue string) (string, error) {
	if flagValue != "" {
		return flagValue, nil
	}
	if env := os.Getenv("BRAZIL_MCP_DATA_DIR"); env != "" {
		return env, nil
	}
	candidates := []string{filepath.Join(".", "data", "kaggle")}
	if exe, err := os.Executable(); err == nil {
		candidates = append(candidates, filepath.Join(filepath.Dir(exe), "data", "kaggle"))
	}
	for _, c := range candidates {
		if info, err := os.Stat(c); err == nil && info.IsDir() {
			return c, nil
		}
	}
	return candidates[0], nil
}

func main() {
	dataDirFlag := flag.String("data-dir", "", "path to the directory containing the Kaggle CSVs (default: ./data/kaggle)")
	flag.Parse()

	logger := log.New(os.Stderr, "brazilian-soccer-mcp: ", log.LstdFlags)

	dataDir, err := resolveDataDir(*dataDirFlag)
	if err != nil {
		logger.Fatalf("resolving data directory: %v", err)
	}

	store, err := LoadStore(dataDir)
	if err != nil {
		logger.Fatalf("loading data from %s: %v", dataDir, err)
	}
	logger.Printf("loaded data from %s: %s", dataDir, store.summary())
	for _, w := range store.LoadWarnings {
		logger.Printf("warning: %s", w)
	}

	server := NewServer(logger)
	RegisterTools(server, store)

	logger.Printf("MCP server ready on stdio")
	if err := server.Run(os.Stdin, os.Stdout); err != nil {
		logger.Fatalf("server error: %v", err)
	}
}
