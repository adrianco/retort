// main.go - entry point for the Brazilian Soccer MCP server.
//
// Context
// -------
// Loads the embedded Kaggle datasets into the in-memory knowledge graph,
// registers the soccer query tools on a stdio MCP server, and serves JSON-RPC
// requests on stdin/stdout. An optional -data flag allows pointing at a
// directory of CSVs on disk instead of the embedded copies (useful for refreshed
// data); -version prints build info and exits.
//
// All diagnostics go to stderr so they never corrupt the JSON-RPC stream on
// stdout.
package main

import (
	"flag"
	"fmt"
	"io/fs"
	"log"
	"os"

	"brazilian-soccer-mcp/internal/mcp"
	"brazilian-soccer-mcp/internal/soccer"
)

const (
	serverName    = "brazilian-soccer-mcp"
	serverVersion = "1.0.0"
)

func main() {
	dataDir := flag.String("data", "", "directory containing the CSV datasets (defaults to embedded data)")
	showVersion := flag.Bool("version", false, "print version and exit")
	flag.Parse()

	if *showVersion {
		fmt.Printf("%s %s\n", serverName, serverVersion)
		return
	}

	log.SetFlags(0)
	log.SetPrefix(serverName + ": ")
	log.SetOutput(os.Stderr)

	var source fs.FS
	if *dataDir != "" {
		source = os.DirFS(*dataDir)
		log.Printf("loading datasets from %s", *dataDir)
	} else {
		source = dataFS()
		log.Printf("loading embedded datasets")
	}

	db, err := soccer.Load(source)
	if err != nil {
		log.Fatalf("failed to load data: %v", err)
	}
	log.Printf("loaded %d matches and %d players", len(db.Matches), len(db.Players))

	server := mcp.NewServer(serverName, serverVersion)
	registerTools(server, db)

	if err := server.Serve(os.Stdin, os.Stdout); err != nil {
		log.Fatalf("server error: %v", err)
	}
}
