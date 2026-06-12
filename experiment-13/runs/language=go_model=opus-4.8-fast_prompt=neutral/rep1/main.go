// Command brazilian-soccer-mcp is an MCP (Model Context Protocol) server that
// exposes a knowledge graph over the provided Brazilian-soccer datasets
// (Brasileirão, Copa do Brasil, Copa Libertadores match results and the FIFA
// player database). An LLM client connects over stdio and calls the registered
// tools to answer natural-language questions about matches, teams, players,
// competitions and statistics.
//
// Usage:
//
//	brazilian-soccer-mcp                 # serve MCP over stdio (default)
//	brazilian-soccer-mcp -data <dir>     # point at the CSV directory
//	brazilian-soccer-mcp -demo           # print answers to sample questions and exit
//
// All match datasets are normalized into one model, team names are normalized
// for consistent matching, and fixtures that appear in more than one source are
// de-duplicated.
package main

import (
	"flag"
	"fmt"
	"os"

	"brazilian-soccer-mcp/mcp"
	"brazilian-soccer-mcp/soccer"
)

const (
	serverName    = "brazilian-soccer-mcp"
	serverVersion = "1.0.0"
)

func main() {
	dataDir := flag.String("data", "data/kaggle", "directory containing the Kaggle CSV files")
	demo := flag.Bool("demo", false, "print answers to sample questions and exit (no MCP server)")
	flag.Parse()

	store, rep, err := soccer.LoadAll(*dataDir)
	if err != nil {
		fmt.Fprintf(os.Stderr, "failed to load data from %q: %v\n", *dataDir, err)
		os.Exit(1)
	}
	// Loader diagnostics go to stderr so they never corrupt the stdio JSON-RPC
	// stream on stdout.
	logLoadReport(rep, *dataDir)
	if len(rep.Files) == 0 {
		fmt.Fprintf(os.Stderr, "no datasets found in %q — check the -data path\n", *dataDir)
		os.Exit(1)
	}

	if *demo {
		runDemo(store)
		return
	}

	srv := mcp.NewServer(serverName, serverVersion)
	registerTools(srv, store)

	fmt.Fprintf(os.Stderr, "%s %s ready (stdio); %d matches, %d players loaded\n",
		serverName, serverVersion, len(store.Matches), len(store.Players))

	if err := srv.Serve(os.Stdin, os.Stdout); err != nil {
		fmt.Fprintf(os.Stderr, "server error: %v\n", err)
		os.Exit(1)
	}
}

func logLoadReport(rep *soccer.LoadReport, dir string) {
	fmt.Fprintf(os.Stderr, "loading datasets from %s\n", dir)
	for _, f := range rep.Files {
		fmt.Fprintf(os.Stderr, "  %-34s %6d rows\n", f.File, f.Rows)
	}
	for _, m := range rep.Missing {
		fmt.Fprintf(os.Stderr, "  %-34s MISSING\n", m)
	}
	fmt.Fprintf(os.Stderr, "  -> %d match rows (%d exact duplicates dropped), %d players\n",
		rep.Matches, rep.Duplicates, rep.Players)
}

// runDemo answers a representative set of the spec's sample questions, so the
// implementation can be verified end-to-end without an MCP client.
func runDemo(store *soccer.Store) {
	type q struct {
		title  string
		answer string
	}
	demos := []q{
		{"Dataset overview", store.DatasetOverview()},
		{"Flamengo vs Fluminense (Fla-Flu)", store.SearchMatches(soccer.MatchQuery{Team: "Flamengo", Opponent: "Fluminense", Limit: 5})},
		{"Palmeiras matches in 2019", store.SearchMatches(soccer.MatchQuery{Team: "Palmeiras", Season: 2019, Limit: 5})},
		{"Corinthians home record in 2019 Brasileirão", store.TeamRecordQuery("Corinthians", "Brasileirão", 2019, soccer.VenueHome)},
		{"Compare Palmeiras and Santos head-to-head", store.HeadToHeadQuery("Palmeiras", "Santos", "", 0, 5)},
		{"2019 Brasileirão standings (top 5)", store.StandingsQuery("Brasileirão", 2019, 5)},
		{"Average goals per match in the Brasileirão", store.CompetitionStatsQuery("Brasileirão", 0)},
		{"Biggest wins overall", store.BiggestWinsQuery("", 0, 5)},
		{"Top scoring teams, 2019 Brasileirão", store.TopScoringTeamsQuery("Brasileirão", 2019, 5)},
		{"Top Brazilian players", store.SearchPlayersQuery("", "Brazil", "", "", 0, 5)},
		{"Who is Neymar?", store.PlayerInfoQuery("Neymar")},
		{"Highest-rated players at Santos", store.ClubPlayersQuery("Santos", 8)},
		{"What competitions has Palmeiras played in?", store.TeamCompetitionsQuery("Palmeiras")},
	}
	for _, d := range demos {
		fmt.Printf("### %s\n%s\n\n", d.title, d.answer)
	}
}
