// Brazilian Soccer MCP Server — entry point.
//
// Context: loads the six Kaggle CSV datasets (five match files + FIFA
// players) into memory and serves the MCP protocol over stdio so an LLM
// client (Claude Desktop, Claude Code, ...) can answer natural-language
// questions about Brazilian soccer. All logging goes to stderr; stdout is
// reserved for the JSON-RPC stream.
//
// Usage:
//
//	brazilian-soccer-mcp [-data path/to/data/kaggle] [-quiet]
//
// Claude Desktop config example:
//
//	{"mcpServers": {"brazilian-soccer": {"command": "/path/to/brazilian-soccer-mcp"}}}
package main

import (
	"flag"
	"fmt"
	"io"
	"log"
	"os"

	"brazilian-soccer-mcp/internal/data"
	"brazilian-soccer-mcp/internal/mcp"
	"brazilian-soccer-mcp/internal/query"
)

const version = "1.0.0"

func main() {
	dataDir := flag.String("data", "", "path to the data/kaggle directory (default: auto-detect from cwd or executable location)")
	quiet := flag.Bool("quiet", false, "suppress diagnostic logging on stderr")
	flag.Parse()

	logger := log.New(os.Stderr, "[brazilian-soccer-mcp] ", log.LstdFlags)
	if *quiet {
		logger.SetOutput(io.Discard)
	}

	dir := *dataDir
	if dir == "" {
		var err error
		if dir, err = locateData(); err != nil {
			logger.Fatalf("cannot locate datasets: %v (use -data to point at data/kaggle)", err)
		}
	}

	ds, err := data.LoadDataset(dir)
	if err != nil {
		logger.Fatalf("loading datasets: %v", err)
	}
	logger.Printf("loaded %d matches (%d duplicate fixtures merged) and %d players from %s",
		len(ds.Matches), ds.Duplicates, len(ds.Players), dir)

	server := mcp.NewServer("brazilian-soccer-mcp", version, mcp.BuildTools(query.New(ds)), logger)
	logger.Printf("serving MCP on stdio")
	if err := server.Serve(os.Stdin, os.Stdout); err != nil {
		logger.Fatalf("server error: %v", err)
	}
}

// locateData finds data/kaggle relative to the working directory first,
// then relative to the executable.
func locateData() (string, error) {
	if dir, err := data.FindDataDir("."); err == nil {
		return dir, nil
	}
	exe, err := os.Executable()
	if err != nil {
		return "", fmt.Errorf("data/kaggle not found from cwd and executable path unknown: %w", err)
	}
	return data.FindDataDir(exe)
}
