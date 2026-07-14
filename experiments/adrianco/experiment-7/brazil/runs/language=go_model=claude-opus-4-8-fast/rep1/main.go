// Command brazilian-soccer-mcp is an MCP (Model Context Protocol) server that
// answers natural-language questions about Brazilian soccer over a stdio
// JSON-RPC transport.
//
// Context:
//   - On startup it loads the six bundled Kaggle CSV datasets (match results
//     across Brasileirão, Copa do Brasil, Libertadores, plus a FIFA player
//     database) from a data directory (default "data/kaggle", overridable with
//     -data or the SOCCER_DATA_DIR env var).
//   - It then registers the soccer query tools (see internal/server) and serves
//     MCP requests on stdin/stdout. Logs go to stderr so they don't corrupt the
//     JSON-RPC stream.
//   - Run directly with `go run .` to use as an MCP server; connect it from any
//     MCP-capable client. See README.md for configuration.
package main

import (
	"flag"
	"log"
	"os"

	"brazilian-soccer-mcp/internal/mcp"
	"brazilian-soccer-mcp/internal/server"
	"brazilian-soccer-mcp/internal/store"
)

const version = "1.0.0"

func main() {
	dataDir := flag.String("data", defaultDataDir(), "directory containing the Kaggle CSV datasets")
	flag.Parse()

	log.SetOutput(os.Stderr)
	log.SetPrefix("[brazilian-soccer-mcp] ")

	log.Printf("loading datasets from %s ...", *dataDir)
	st, err := store.Load(*dataDir)
	if err != nil {
		log.Fatalf("failed to load data: %v", err)
	}
	log.Printf("loaded %d matches and %d players", len(st.Matches), len(st.Players))

	srv := mcp.NewServer("brazilian-soccer-mcp", version)
	server.Register(srv, st)

	log.Printf("MCP server ready on stdio")
	if err := srv.Serve(os.Stdin, os.Stdout); err != nil {
		log.Fatalf("server error: %v", err)
	}
}

// defaultDataDir resolves the dataset directory, preferring SOCCER_DATA_DIR.
func defaultDataDir() string {
	if d := os.Getenv("SOCCER_DATA_DIR"); d != "" {
		return d
	}
	return "data/kaggle"
}
