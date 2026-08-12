package server

import (
	"context"
	"fmt"
	"sort"

	"brazilian-soccer-mcp/internal/soccer"
	"github.com/modelcontextprotocol/go-sdk/mcp"
)

type teamStatsInput struct {
	Team        string `json:"team" jsonschema:"team name"`
	Season      int    `json:"season,omitempty" jsonschema:"season year"`
	Competition string `json:"competition,omitempty" jsonschema:"competition filter"`
	Venue       string `json:"venue,omitempty" jsonschema:"all, home, or away"`
}
type h2hInput struct {
	TeamA       string `json:"team_a" jsonschema:"first team"`
	TeamB       string `json:"team_b" jsonschema:"second team"`
	Season      int    `json:"season,omitempty"`
	Competition string `json:"competition,omitempty"`
	Limit       int    `json:"limit,omitempty"`
}
type standingsInput struct {
	Competition string `json:"competition,omitempty" jsonschema:"defaults to Brasileirao Serie A"`
	Season      int    `json:"season" jsonschema:"required four-digit season"`
}
type aggregateInput struct {
	Competition      string `json:"competition,omitempty"`
	Season           int    `json:"season,omitempty"`
	BiggestWinsLimit int    `json:"biggest_wins_limit,omitempty"`
}
type clubInput struct {
	Team        string `json:"team"`
	Season      int    `json:"season,omitempty"`
	Competition string `json:"competition,omitempty"`
}
type sourceOutput struct {
	Sources      []soccer.SourceSummary `json:"sources"`
	TotalMatches int                    `json:"total_matches"`
	TotalPlayers int                    `json:"total_players"`
}

func New(c *soccer.Catalog) *mcp.Server {
	s := mcp.NewServer(&mcp.Implementation{Name: "brazilian-soccer", Version: "1.0.0"}, &mcp.ServerOptions{Instructions: "Answer questions using the provided Brazilian soccer datasets. Prefer structured tools over guessing. Explain that FIFA player data is a historical snapshot and standings are calculated from supplied completed matches."})
	readOnly := &mcp.ToolAnnotations{ReadOnlyHint: true, IdempotentHint: true}
	mcp.AddTool(s, &mcp.Tool{Name: "search_matches", Description: "Find matches by team, opponent, date range, season, competition, venue, or stage/round across all five match CSV files.", Annotations: readOnly}, func(ctx context.Context, req *mcp.CallToolRequest, in soccer.MatchQuery) (*mcp.CallToolResult, soccer.MatchSearchResult, error) {
		out, err := c.SearchMatches(in)
		return nil, out, err
	})
	mcp.AddTool(s, &mcp.Tool{Name: "team_statistics", Description: "Calculate wins, draws, losses, points, goals and win rate for a team, optionally at home/away, in a season or competition.", Annotations: readOnly}, func(ctx context.Context, req *mcp.CallToolRequest, in teamStatsInput) (*mcp.CallToolResult, soccer.TeamRecord, error) {
		out, err := c.TeamStatistics(in.Team, in.Season, in.Competition, in.Venue)
		return nil, out, err
	})
	mcp.AddTool(s, &mcp.Tool{Name: "head_to_head", Description: "Compare two teams with wins, draws, goals and recent meetings, normalized across spelling and state suffix variations.", Annotations: readOnly}, func(ctx context.Context, req *mcp.CallToolRequest, in h2hInput) (*mcp.CallToolResult, soccer.HeadToHeadResult, error) {
		out, err := c.HeadToHead(in.TeamA, in.TeamB, in.Season, in.Competition, in.Limit)
		return nil, out, err
	})
	mcp.AddTool(s, &mcp.Tool{Name: "search_players", Description: "Search the FIFA player snapshot by partial name, nationality, club, position group/code, and minimum overall rating; results are highest-rated first.", Annotations: readOnly}, func(ctx context.Context, req *mcp.CallToolRequest, in soccer.PlayerQuery) (*mcp.CallToolResult, soccer.PlayerSearchResult, error) {
		return nil, c.SearchPlayers(in), nil
	})
	mcp.AddTool(s, &mcp.Tool{Name: "competition_standings", Description: "Calculate a final/current table from match results for one competition and season. Supports Serie A/B/C, Copa do Brasil, and Libertadores, though league-style standings are most meaningful for round-robin competitions.", Annotations: readOnly}, func(ctx context.Context, req *mcp.CallToolRequest, in standingsInput) (*mcp.CallToolResult, soccer.StandingsResult, error) {
		out, err := c.Standings(in.Competition, in.Season)
		return nil, out, err
	})
	mcp.AddTool(s, &mcp.Tool{Name: "aggregate_statistics", Description: "Calculate goals per match, home/away/draw rates, and biggest victories for a season and/or competition.", Annotations: readOnly}, func(ctx context.Context, req *mcp.CallToolRequest, in aggregateInput) (*mcp.CallToolResult, soccer.AggregateResult, error) {
		out, err := c.Aggregate(in.Competition, in.Season, in.BiggestWinsLimit)
		return nil, out, err
	})
	mcp.AddTool(s, &mcp.Tool{Name: "club_overview", Description: "Cross-file query combining a club's match record with FIFA players registered to that club.", Annotations: readOnly}, func(ctx context.Context, req *mcp.CallToolRequest, in clubInput) (*mcp.CallToolResult, soccer.ClubOverview, error) {
		out, err := c.ClubOverview(in.Team, in.Season, in.Competition)
		return nil, out, err
	})
	mcp.AddTool(s, &mcp.Tool{Name: "dataset_sources", Description: "List all six loaded CSV sources and their record counts.", Annotations: readOnly}, func(ctx context.Context, req *mcp.CallToolRequest, in struct{}) (*mcp.CallToolResult, sourceOutput, error) {
		out := sourceOutput{TotalMatches: len(c.Matches), TotalPlayers: len(c.Players)}
		for _, v := range c.Sources {
			out.Sources = append(out.Sources, v)
		}
		sort.Slice(out.Sources, func(i, j int) bool { return out.Sources[i].File < out.Sources[j].File })
		return nil, out, nil
	})
	s.AddResource(&mcp.Resource{Name: "dataset-summary", Description: "Counts and provenance for the six loaded datasets", MIMEType: "text/plain", URI: "soccer://datasets/summary"}, func(ctx context.Context, req *mcp.ReadResourceRequest) (*mcp.ReadResourceResult, error) {
		text := fmt.Sprintf("Brazilian soccer catalog: %d matches from five CSV files and %d players from fifa_data.csv.", len(c.Matches), len(c.Players))
		return &mcp.ReadResourceResult{Contents: []*mcp.ResourceContents{{URI: req.Params.URI, MIMEType: "text/plain", Text: text}}}, nil
	})
	return s
}
