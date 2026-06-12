package main

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/mark3labs/mcp-go/mcp"
	"github.com/mark3labs/mcp-go/server"
)

// toJSON marshals a value to a pretty JSON string.
func toJSON(v interface{}) string {
	b, err := json.MarshalIndent(v, "", "  ")
	if err != nil {
		return fmt.Sprintf("%v", v)
	}
	return string(b)
}

// HandleSearchMatches handles the search_matches tool.
func HandleSearchMatches(db *Database) server.ToolHandlerFunc {
	return func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		team := req.GetString("team", "")
		homeTeam := req.GetString("home_team", "")
		awayTeam := req.GetString("away_team", "")
		competition := req.GetString("competition", "")
		season := req.GetInt("season", 0)
		dateFromStr := req.GetString("date_from", "")
		dateToStr := req.GetString("date_to", "")
		limit := req.GetInt("limit", 50)

		var dateFrom, dateTo time.Time
		if dateFromStr != "" {
			dateFrom, _ = ParseDate(dateFromStr)
		}
		if dateToStr != "" {
			dateTo, _ = ParseDate(dateToStr)
		}

		matches := SearchMatches(db, team, homeTeam, awayTeam, competition, season, dateFrom, dateTo, limit)

		type matchResult struct {
			DateTime    string `json:"datetime"`
			HomeTeam    string `json:"home_team"`
			AwayTeam    string `json:"away_team"`
			HomeGoals   int    `json:"home_goals"`
			AwayGoals   int    `json:"away_goals"`
			Season      int    `json:"season"`
			Round       string `json:"round,omitempty"`
			Stage       string `json:"stage,omitempty"`
			Competition string `json:"competition"`
		}

		results := make([]matchResult, 0, len(matches))
		for _, m := range matches {
			results = append(results, matchResult{
				DateTime:    m.DateTime.Format("2006-01-02 15:04:05"),
				HomeTeam:    m.HomeTeam,
				AwayTeam:    m.AwayTeam,
				HomeGoals:   m.HomeGoals,
				AwayGoals:   m.AwayGoals,
				Season:      m.Season,
				Round:       m.Round,
				Stage:       m.Stage,
				Competition: m.Competition,
			})
		}

		return mcp.NewToolResultText(fmt.Sprintf("Found %d matches:\n%s", len(results), toJSON(results))), nil
	}
}

// HandleHeadToHead handles the head_to_head tool.
func HandleHeadToHead(db *Database) server.ToolHandlerFunc {
	return func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		team1 := req.GetString("team1", "")
		team2 := req.GetString("team2", "")
		competition := req.GetString("competition", "")
		season := req.GetInt("season", 0)

		if team1 == "" || team2 == "" {
			return mcp.NewToolResultError("team1 and team2 are required"), nil
		}

		h2h := HeadToHead(db, team1, team2, competition, season)
		return mcp.NewToolResultText(toJSON(h2h)), nil
	}
}

// HandleTeamStats handles the team_stats tool.
func HandleTeamStats(db *Database) server.ToolHandlerFunc {
	return func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		team := req.GetString("team", "")
		competition := req.GetString("competition", "")
		season := req.GetInt("season", 0)

		if team == "" {
			return mcp.NewToolResultError("team is required"), nil
		}

		stats := GetTeamStats(db, team, competition, season)
		return mcp.NewToolResultText(toJSON(stats)), nil
	}
}

// HandleStandings handles the standings tool.
func HandleStandings(db *Database) server.ToolHandlerFunc {
	return func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		season := req.GetInt("season", 0)
		competition := req.GetString("competition", "")

		standings := GetStandings(db, season, competition)

		if len(standings) == 0 {
			return mcp.NewToolResultText("No standings data found for the given criteria."), nil
		}
		// Limit to top 20 by default
		if len(standings) > 20 {
			standings = standings[:20]
		}
		return mcp.NewToolResultText(toJSON(standings)), nil
	}
}

// HandleSearchPlayers handles the search_players tool.
func HandleSearchPlayers(db *Database) server.ToolHandlerFunc {
	return func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		name := req.GetString("name", "")
		nationality := req.GetString("nationality", "")
		club := req.GetString("club", "")
		position := req.GetString("position", "")
		minOverall := req.GetInt("min_overall", 0)
		limit := req.GetInt("limit", 20)

		players := SearchPlayers(db.Players, name, nationality, club, position, minOverall, limit)
		return mcp.NewToolResultText(fmt.Sprintf("Found %d players:\n%s", len(players), toJSON(players))), nil
	}
}

// HandleGetStatistics handles the get_statistics tool.
func HandleGetStatistics(db *Database) server.ToolHandlerFunc {
	return func(ctx context.Context, req mcp.CallToolRequest) (*mcp.CallToolResult, error) {
		competition := req.GetString("competition", "")
		season := req.GetInt("season", 0)
		statType := req.GetString("stat_type", "avg_goals")

		stats := GetStatistics(db, competition, season, statType)
		return mcp.NewToolResultText(toJSON(stats)), nil
	}
}
