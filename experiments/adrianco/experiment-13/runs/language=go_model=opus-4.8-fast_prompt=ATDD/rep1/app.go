// Package app wires the Brazilian soccer data Store to a set of MCP tools and
// exposes a ready-to-serve MCP server.
//
// The tools form the public, domain-language interface of the system:
//
//	find_matches    – find matches by team, opponent, competition, season,
//	                  venue or date range (with head-to-head when two teams given)
//	get_team_stats  – a team's win/draw/loss record and goals
//	head_to_head    – compare two teams across all competitions
//	search_players  – search players by name, nationality, club or position
//	get_standings   – a league table calculated from match results
//	league_stats    – competition-wide aggregate statistics
//	team_rankings   – rank teams by a metric (e.g. best home/away record)
package app

import (
	"context"
	"encoding/json"
	"fmt"
	"io"

	"brazilian-soccer-mcp/internal/mcp"
	"brazilian-soccer-mcp/internal/store"
)

const (
	serverName    = "brazilian-soccer-mcp"
	serverVersion = "1.0.0"
)

// NewMCPServer loads the datasets under <dataDir>/kaggle and returns an MCP
// server with all soccer tools registered.
func NewMCPServer(dataDir string) (*mcp.Server, error) {
	st, err := store.Load(dataDir)
	if err != nil {
		return nil, err
	}
	srv := mcp.NewServer(serverName, serverVersion)
	registerTools(srv, st)
	return srv, nil
}

// Run loads the datasets and serves the MCP protocol over the given streams
// (typically os.Stdin/os.Stdout).
func Run(ctx context.Context, dataDir string, in io.Reader, out io.Writer) error {
	srv, err := NewMCPServer(dataDir)
	if err != nil {
		return err
	}
	return srv.Serve(ctx, in, out)
}

// flexInt accepts a JSON number or a numeric string (datasets and clients use
// both for fields like "season").
type flexInt int

func (f *flexInt) UnmarshalJSON(b []byte) error {
	if len(b) == 0 || string(b) == "null" {
		return nil
	}
	if b[0] == '"' {
		var s string
		if err := json.Unmarshal(b, &s); err != nil {
			return err
		}
		if s == "" {
			return nil
		}
		var n int
		if _, err := fmt.Sscanf(s, "%d", &n); err != nil {
			return fmt.Errorf("invalid integer %q", s)
		}
		*f = flexInt(n)
		return nil
	}
	var n int
	if err := json.Unmarshal(b, &n); err != nil {
		return err
	}
	*f = flexInt(n)
	return nil
}

func mustJSON(v any) (string, error) {
	b, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return "", err
	}
	return string(b), nil
}

func registerTools(srv *mcp.Server, st *store.Store) {
	registerFindMatches(srv, st)
	registerTeamStats(srv, st)
	registerHeadToHead(srv, st)
	registerSearchPlayers(srv, st)
	registerStandings(srv, st)
	registerLeagueStats(srv, st)
	registerTeamRankings(srv, st)
}

// schemaObject builds a JSON-Schema object with string/integer properties.
func schemaObject(props map[string]string, required ...string) map[string]any {
	properties := map[string]any{}
	for name, typ := range props {
		properties[name] = map[string]any{"type": typ}
	}
	schema := map[string]any{
		"type":       "object",
		"properties": properties,
	}
	if len(required) > 0 {
		schema["required"] = required
	}
	return schema
}
