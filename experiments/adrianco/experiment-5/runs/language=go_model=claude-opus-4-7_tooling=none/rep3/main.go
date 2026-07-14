// Brazilian Soccer MCP server entry point.
//
// Loads the Kaggle datasets from data/kaggle/ then serves the Model Context
// Protocol over stdio. The server exposes tools that an LLM can call to query
// matches, teams, players, competitions, and aggregate statistics.
package main

import (
	"flag"
	"log"
	"os"
	"path/filepath"

	"github.com/adrian/brazilian-soccer-mcp/internal/data"
	"github.com/adrian/brazilian-soccer-mcp/internal/mcp"
)

func main() {
	var dataDir string
	flag.StringVar(&dataDir, "data", defaultDataDir(), "directory containing kaggle CSV files")
	flag.Parse()

	log.SetOutput(os.Stderr)
	log.SetPrefix("[soccer-mcp] ")
	log.SetFlags(log.LstdFlags)

	log.Printf("loading datasets from %s", dataDir)
	ds, err := data.LoadAll(dataDir)
	if err != nil {
		log.Fatalf("data load failed: %v", err)
	}
	log.Printf("loaded %d matches and %d players", len(ds.Matches), len(ds.Players))

	s := mcp.NewServer("brazilian-soccer-mcp", "1.0.0")
	mcp.RegisterAll(s, ds)
	log.Printf("registered tools: %v", s.ToolNames())

	if err := s.Serve(os.Stdin, os.Stdout); err != nil {
		log.Fatalf("server error: %v", err)
	}
}

func defaultDataDir() string {
	candidates := []string{"data/kaggle"}
	if wd, err := os.Getwd(); err == nil {
		candidates = append(candidates, filepath.Join(wd, "data", "kaggle"))
	}
	for _, c := range candidates {
		if st, err := os.Stat(c); err == nil && st.IsDir() {
			return c
		}
	}
	return "data/kaggle"
}
