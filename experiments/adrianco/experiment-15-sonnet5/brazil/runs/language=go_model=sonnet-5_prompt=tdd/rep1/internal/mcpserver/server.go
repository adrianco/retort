package mcpserver

import (
	"context"
	"fmt"

	"brazilian-soccer-mcp/internal/soccer"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// New builds an MCP server exposing store's match and player data as tools.
func New(store *soccer.Store) *mcp.Server {
	server := mcp.NewServer(&mcp.Implementation{Name: "brazilian-soccer-mcp", Version: "v1.0.0"}, nil)

	type findMatchesArgs struct {
		Team        string `json:"team,omitempty" jsonschema:"team name (either home or away); normalized automatically"`
		Opponent    string `json:"opponent,omitempty" jsonschema:"opposing team name, to find matches between two specific teams"`
		Competition string `json:"competition,omitempty" jsonschema:"one of: Brasileirao, Copa do Brasil, Libertadores, Serie A, Serie B, Serie C, Brasileirao (Historical)"`
		Season      int    `json:"season,omitempty" jsonschema:"four digit year"`
		From        string `json:"from,omitempty" jsonschema:"start date (YYYY-MM-DD), inclusive"`
		To          string `json:"to,omitempty" jsonschema:"end date (YYYY-MM-DD), inclusive"`
		Limit       int    `json:"limit,omitempty" jsonschema:"maximum number of matches to return"`
	}
	mcp.AddTool(server, &mcp.Tool{
		Name:        "find_matches",
		Description: "Find matches by team, opponent, competition, season and/or date range.",
	}, func(ctx context.Context, req *mcp.CallToolRequest, args findMatchesArgs) (*mcp.CallToolResult, any, error) {
		filter := soccer.MatchFilter{
			Team:        args.Team,
			Opponent:    args.Opponent,
			Competition: args.Competition,
			Season:      args.Season,
			Limit:       args.Limit,
		}
		if args.From != "" {
			d, err := soccer.ParseDate(args.From)
			if err != nil {
				return errorResult("invalid from date: %v", err), nil, nil
			}
			filter.From = d
		}
		if args.To != "" {
			d, err := soccer.ParseDate(args.To)
			if err != nil {
				return errorResult("invalid to date: %v", err), nil, nil
			}
			filter.To = d
		}
		matches := store.FindMatches(filter)
		return textResult(FormatMatches(matches)), nil, nil
	})

	type headToHeadArgs struct {
		TeamA string `json:"team_a" jsonschema:"first team name"`
		TeamB string `json:"team_b" jsonschema:"second team name"`
	}
	mcp.AddTool(server, &mcp.Tool{
		Name:        "head_to_head",
		Description: "Get the head-to-head match history and win/draw record between two teams, across all competitions.",
	}, func(ctx context.Context, req *mcp.CallToolRequest, args headToHeadArgs) (*mcp.CallToolResult, any, error) {
		result := store.HeadToHead(args.TeamA, args.TeamB)
		return textResult(FormatHeadToHead(result)), nil, nil
	})

	type teamRecordArgs struct {
		Team        string `json:"team" jsonschema:"team name"`
		Season      int    `json:"season,omitempty" jsonschema:"four digit year; omit for all seasons"`
		Competition string `json:"competition,omitempty" jsonschema:"competition name; omit for all competitions"`
		Venue       string `json:"venue,omitempty" jsonschema:"one of: home, away; omit for both"`
	}
	mcp.AddTool(server, &mcp.Tool{
		Name:        "team_record",
		Description: "Get a team's win/draw/loss record and goals for/against, optionally scoped to a season, competition and/or venue.",
	}, func(ctx context.Context, req *mcp.CallToolRequest, args teamRecordArgs) (*mcp.CallToolResult, any, error) {
		rec := store.TeamRecord(soccer.TeamRecordFilter{
			Team:        args.Team,
			Season:      args.Season,
			Competition: args.Competition,
			Venue:       args.Venue,
		})
		return textResult(FormatTeamRecord(rec)), nil, nil
	})

	type standingsArgs struct {
		Competition string `json:"competition" jsonschema:"competition name, e.g. Brasileirao"`
		Season      int    `json:"season" jsonschema:"four digit year"`
	}
	mcp.AddTool(server, &mcp.Tool{
		Name:        "standings",
		Description: "Compute the final/current standings table for a competition and season from match results.",
	}, func(ctx context.Context, req *mcp.CallToolRequest, args standingsArgs) (*mcp.CallToolResult, any, error) {
		table := store.Standings(args.Competition, args.Season)
		return textResult(FormatStandings(table, args.Competition, args.Season)), nil, nil
	})

	type biggestWinsArgs struct {
		Competition string `json:"competition,omitempty" jsonschema:"competition name; omit for all competitions"`
		Season      int    `json:"season,omitempty" jsonschema:"four digit year; omit for all seasons"`
		Limit       int    `json:"limit,omitempty" jsonschema:"maximum number of results (default 10)"`
	}
	mcp.AddTool(server, &mcp.Tool{
		Name:        "biggest_wins",
		Description: "Find the most lopsided match results (largest goal difference), optionally scoped to a competition and/or season.",
	}, func(ctx context.Context, req *mcp.CallToolRequest, args biggestWinsArgs) (*mcp.CallToolResult, any, error) {
		limit := args.Limit
		if limit == 0 {
			limit = 10
		}
		matches := store.BiggestWins(soccer.BiggestWinsFilter{
			Competition: args.Competition,
			Season:      args.Season,
			Limit:       limit,
		})
		return textResult(FormatMatches(matches)), nil, nil
	})

	type statsSummaryArgs struct {
		Team        string `json:"team,omitempty" jsonschema:"team name; omit for all teams"`
		Competition string `json:"competition,omitempty" jsonschema:"competition name; omit for all competitions"`
		Season      int    `json:"season,omitempty" jsonschema:"four digit year; omit for all seasons"`
	}
	mcp.AddTool(server, &mcp.Tool{
		Name:        "stats_summary",
		Description: "Compute aggregate statistics (average goals per match, home/away/draw rates) over matches, optionally scoped to a team, competition and/or season.",
	}, func(ctx context.Context, req *mcp.CallToolRequest, args statsSummaryArgs) (*mcp.CallToolResult, any, error) {
		summary := store.StatsSummary(soccer.MatchFilter{
			Team:        args.Team,
			Competition: args.Competition,
			Season:      args.Season,
		})
		return textResult(FormatStatsSummary(summary)), nil, nil
	})

	type searchPlayersArgs struct {
		Name        string `json:"name,omitempty" jsonschema:"player name or substring"`
		Nationality string `json:"nationality,omitempty" jsonschema:"player nationality or substring"`
		Club        string `json:"club,omitempty" jsonschema:"club name or substring"`
		Position    string `json:"position,omitempty" jsonschema:"exact position abbreviation, e.g. GK, ST, CDM"`
		MinOverall  int    `json:"min_overall,omitempty" jsonschema:"minimum FIFA overall rating"`
		Limit       int    `json:"limit,omitempty" jsonschema:"maximum number of players to return (default 25)"`
	}
	mcp.AddTool(server, &mcp.Tool{
		Name:        "search_players",
		Description: "Search FIFA player data by name, nationality, club and/or position, sorted by overall rating descending. Also use this for 'top rated' player queries.",
	}, func(ctx context.Context, req *mcp.CallToolRequest, args searchPlayersArgs) (*mcp.CallToolResult, any, error) {
		limit := args.Limit
		if limit == 0 {
			limit = 25
		}
		players := store.SearchPlayers(soccer.PlayerFilter{
			Name:        args.Name,
			Nationality: args.Nationality,
			Club:        args.Club,
			Position:    args.Position,
			MinOverall:  args.MinOverall,
			Limit:       limit,
		})
		return textResult(FormatPlayers(players)), nil, nil
	})

	return server
}

func textResult(text string) *mcp.CallToolResult {
	return &mcp.CallToolResult{Content: []mcp.Content{&mcp.TextContent{Text: text}}}
}

func errorResult(format string, args ...any) *mcp.CallToolResult {
	res := textResult(fmt.Sprintf(format, args...))
	res.IsError = true
	return res
}
