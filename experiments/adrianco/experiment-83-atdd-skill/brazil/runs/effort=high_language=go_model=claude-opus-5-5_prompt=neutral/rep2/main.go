// Command brazilian-soccer-mcp is an MCP server answering questions about
// Brazilian soccer from the bundled Kaggle datasets.
//
// Usage:
//
//	brazilian-soccer-mcp                         # MCP server on stdio
//	brazilian-soccer-mcp -list                   # list tools
//	brazilian-soccer-mcp -tool standings -args '{"season":2019}'
//
// The data directory defaults to $BRAZIL_SOCCER_DATA, then ./data/kaggle,
// then data/kaggle next to the executable.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"log"
	"os"
	"path/filepath"
)

func defaultDataDir() string {
	if d := os.Getenv("BRAZIL_SOCCER_DATA"); d != "" {
		return d
	}
	candidates := []string{filepath.Join("data", "kaggle")}
	if exe, err := os.Executable(); err == nil {
		candidates = append(candidates, filepath.Join(filepath.Dir(exe), "data", "kaggle"))
	}
	for _, c := range candidates {
		if _, err := os.Stat(filepath.Join(c, SrcBrasileirao)); err == nil {
			return c
		}
	}
	return candidates[0]
}

func main() {
	dataDir := flag.String("data", defaultDataDir(), "directory containing the Kaggle CSV files")
	list := flag.Bool("list", false, "list available tools and exit")
	tool := flag.String("tool", "", "run a single tool and print its answer (CLI mode)")
	args := flag.String("args", "{}", "JSON arguments for -tool")
	quiet := flag.Bool("quiet", false, "disable request logging on stderr")
	flag.Parse()

	logger := log.New(os.Stderr, "[brazilian-soccer-mcp] ", log.LstdFlags)
	if *quiet {
		logger = nil
	}
	if *list {
		for _, t := range Tools() {
			fmt.Printf("%-18s %s\n", t.Name, t.Description)
		}
		return
	}
	store, err := LoadStore(*dataDir)
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to load data from %s: %v\n", *dataDir, err)
		os.Exit(1)
	}
	if logger != nil {
		logger.Printf("loaded %d matches, %d teams, %d players in %s", len(store.Matches), len(store.Teams), len(store.Players), store.LoadTime)
	}
	srv := NewServer(store, logger)
	if *tool != "" {
		var a map[string]any
		if err := json.Unmarshal([]byte(*args), &a); err != nil {
			fmt.Fprintf(os.Stderr, "invalid -args JSON: %v\n", err)
			os.Exit(2)
		}
		srv.logger = nil
		out, err := srv.CallTool(*tool, a)
		if err != nil {
			fmt.Fprintf(os.Stderr, "error: %v\n", err)
			os.Exit(1)
		}
		fmt.Print(out)
		return
	}
	if err := srv.Serve(os.Stdin, os.Stdout); err != nil {
		fmt.Fprintf(os.Stderr, "server error: %v\n", err)
		os.Exit(1)
	}
}
