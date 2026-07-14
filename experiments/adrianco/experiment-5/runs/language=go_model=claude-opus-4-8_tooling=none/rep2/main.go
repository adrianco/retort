// Command brazilian-soccer-mcp is an MCP (Model Context Protocol) server that
// exposes a knowledge interface over bundled Brazilian football datasets
// (Brasileirão, Copa do Brasil and Copa Libertadores matches, plus the FIFA
// player database). It speaks JSON-RPC 2.0 over stdio and registers tools for
// match, team, player, competition and statistical queries.
//
// The datasets are embedded into the binary so the server is fully
// self-contained. Set SOCCER_DATA_DIR to load CSVs from a directory on disk
// instead (useful for refreshed data).
package main

import (
	"embed"
	"fmt"
	"io/fs"
	"log"
	"os"

	"brazilian-soccer-mcp/internal/app"
)

//go:embed data/kaggle/*.csv
var embeddedData embed.FS

func main() {
	log.SetPrefix("brazilian-soccer-mcp: ")
	log.SetFlags(0)

	fsys, dir, err := dataSource()
	if err != nil {
		log.Fatal(err)
	}

	srv, store, err := app.New(fsys, dir)
	if err != nil {
		log.Fatalf("loading datasets: %v", err)
	}
	// Logs go to stderr so they never corrupt the stdio JSON-RPC stream.
	log.Printf("loaded %d matches and %d players; ready on stdio",
		len(store.Matches), len(store.Players))

	if err := srv.Serve(os.Stdin, os.Stdout); err != nil {
		log.Fatalf("serve: %v", err)
	}
}

// dataSource returns the filesystem and directory to load datasets from. When
// SOCCER_DATA_DIR is set it is used as an on-disk source; otherwise the
// embedded copy is used.
func dataSource() (fs.FS, string, error) {
	if dir := os.Getenv("SOCCER_DATA_DIR"); dir != "" {
		info, err := os.Stat(dir)
		if err != nil {
			return nil, "", fmt.Errorf("SOCCER_DATA_DIR %q: %w", dir, err)
		}
		if !info.IsDir() {
			return nil, "", fmt.Errorf("SOCCER_DATA_DIR %q is not a directory", dir)
		}
		return os.DirFS(dir), ".", nil
	}
	return embeddedData, "data/kaggle", nil
}
