// Package app assembles the Brazilian soccer MCP server: it loads the
// datasets and offers the questions it can answer as MCP tools.
package app

import (
	"flag"
	"io"
	"log"
	"time"

	"brsoccer/internal/mcpserver"
	"brsoccer/internal/soccer"
)

const version = "1.0.0"

const instructions = `Answers questions about Brazilian soccer from Kaggle datasets: Brasileirão Série A ` +
	`(2003-2023), Série B and C, Copa do Brasil, Copa Libertadores, and FIFA player ratings. ` +
	`Team names may be written in any common form ("Palmeiras-SP", "Sao Paulo", "Atlético Mineiro"). ` +
	`Standings, champions and relegation are calculated from match results.`

// Run loads the data named on the command line and serves MCP requests
// from in to out until in closes. Diagnostics go to errs.
func Run(args []string, in io.Reader, out, errs io.Writer) error {
	flags := flag.NewFlagSet("brazilian-soccer-mcp", flag.ContinueOnError)
	flags.SetOutput(errs)
	dataDir := flags.String("data", "data/kaggle", "directory holding the provided CSV datasets")
	if err := flags.Parse(args); err != nil {
		return err
	}
	logger := log.New(errs, "brazilian-soccer-mcp: ", log.LstdFlags)

	started := time.Now()
	store, err := soccer.Load(*dataDir)
	if err != nil {
		return err
	}
	for _, d := range store.Datasets {
		if d.Error != "" {
			logger.Printf("%s not loaded: %s", d.File, d.Error)
		}
	}
	logger.Printf("loaded %d matches, %d teams and %d players in %s",
		len(store.Matches), len(store.Teams), len(store.Players), time.Since(started).Round(time.Millisecond))

	server := mcpserver.New("brazilian-soccer", version, instructions)
	for _, tool := range tools(store) {
		server.AddTool(tool)
	}
	return server.Serve(in, out)
}
