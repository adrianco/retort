// Package app wires the soccer query engine to the MCP server: it loads the
// datasets and registers one MCP tool per query capability described in the
// specification (match, team, player, competition and statistical queries).
package app

import (
	"encoding/json"
	"fmt"
	"io/fs"
	"strings"
	"time"

	"brazilian-soccer-mcp/internal/mcp"
	"brazilian-soccer-mcp/internal/soccer"
)

const (
	defaultMatchLimit  = 25
	defaultPlayerLimit = 25
)

// New loads the datasets under dir within fsys and returns a fully configured
// MCP server together with the underlying store (handy for tests).
func New(fsys fs.FS, dir string) (*mcp.Server, *soccer.Store, error) {
	store, err := soccer.Load(fsys, dir)
	if err != nil {
		return nil, nil, err
	}
	srv := mcp.NewServer("brazilian-soccer-mcp", "1.0.0")
	registerTools(srv, store)
	return srv, store, nil
}

// registerTools attaches every query tool to the server.
func registerTools(srv *mcp.Server, store *soccer.Store) {
	srv.AddTool(mcp.Tool{
		Name:        "search_matches",
		Description: "Search Brazilian football matches by team, opponent, venue, competition, season and/or date range. Returns matches most recent first.",
		InputSchema: objectSchema(map[string]any{
			"team":        strProp("Team name to search for (matches home or away side). Name variations like 'Palmeiras' / 'Palmeiras-SP' are handled."),
			"opponent":    strProp("Restrict to matches that also involve this team (use with 'team' for a specific fixture)."),
			"venue":       enumProp("Restrict 'team' to matches played at this venue.", "home", "away"),
			"competition": competitionProp(),
			"season":      intProp("Season year, e.g. 2019."),
			"date_from":   strProp("Inclusive lower bound date (YYYY-MM-DD)."),
			"date_to":     strProp("Inclusive upper bound date (YYYY-MM-DD)."),
			"limit":       intProp("Maximum matches to return (default 25)."),
		}, nil),
		Handler: handleSearchMatches(store),
	})

	srv.AddTool(mcp.Tool{
		Name:        "head_to_head",
		Description: "Summarise the all-time head-to-head record between two teams (wins, draws, goals) plus the list of meetings.",
		InputSchema: objectSchema(map[string]any{
			"team_a": strProp("First team."),
			"team_b": strProp("Second team."),
			"limit":  intProp("Maximum matches to list (default 25)."),
		}, []string{"team_a", "team_b"}),
		Handler: handleHeadToHead(store),
	})

	srv.AddTool(mcp.Tool{
		Name:        "team_stats",
		Description: "Compute a team's win/draw/loss record and goals for/against, optionally filtered by competition, season and venue (home/away).",
		InputSchema: objectSchema(map[string]any{
			"team":        strProp("Team name."),
			"competition": competitionProp(),
			"season":      intProp("Season year."),
			"venue":       enumProp("Restrict to home or away matches.", "home", "away"),
		}, []string{"team"}),
		Handler: handleTeamStats(store),
	})

	srv.AddTool(mcp.Tool{
		Name:        "search_players",
		Description: "Search the FIFA player database by name, nationality, club and/or position, sorted by rating. Useful for Brazilian players and players at Brazilian clubs.",
		InputSchema: objectSchema(map[string]any{
			"name":        strProp("Substring of the player's name."),
			"nationality": strProp("Nationality, e.g. 'Brazil'."),
			"club":        strProp("Club name substring, e.g. 'Flamengo'."),
			"position":    strProp("Playing position, e.g. 'ST', 'GK', 'CB'."),
			"min_overall": intProp("Minimum FIFA overall rating."),
			"sort_by":     enumProp("Sort order (default 'overall').", "overall", "potential", "age", "name"),
			"limit":       intProp("Maximum players to return (default 25)."),
		}, nil),
		Handler: handleSearchPlayers(store),
	})

	srv.AddTool(mcp.Tool{
		Name:        "players_by_club",
		Description: "Group players by club (optionally filtered by nationality) with counts and average rating, ordered by squad size.",
		InputSchema: objectSchema(map[string]any{
			"nationality": strProp("Optional nationality filter, e.g. 'Brazil'."),
			"limit":       intProp("Maximum clubs to return (default 25)."),
		}, nil),
		Handler: handlePlayersByClub(store),
	})

	srv.AddTool(mcp.Tool{
		Name:        "standings",
		Description: "Compute a league table for a competition and season from match results (3 points per win, 1 per draw), ordered by points then goal difference.",
		InputSchema: objectSchema(map[string]any{
			"competition": competitionProp(),
			"season":      intProp("Season year."),
			"limit":       intProp("Maximum teams to show (default all)."),
		}, []string{"competition", "season"}),
		Handler: handleStandings(store),
	})

	srv.AddTool(mcp.Tool{
		Name:        "competition_stats",
		Description: "Aggregate statistics for a competition/season: average goals per match, home/away/draw rates and the biggest victories by margin.",
		InputSchema: objectSchema(map[string]any{
			"competition": competitionProp(),
			"season":      intProp("Season year (omit for all seasons)."),
			"top_wins":    intProp("How many biggest victories to list (default 5)."),
		}, nil),
		Handler: handleCompetitionStats(store),
	})

	srv.AddTool(mcp.Tool{
		Name:        "list_competitions",
		Description: "List the competitions available in the loaded datasets.",
		InputSchema: objectSchema(map[string]any{}, nil),
		Handler: func(json.RawMessage) (string, error) {
			comps := store.Competitions()
			return "Available competitions:\n- " + strings.Join(comps, "\n- "), nil
		},
	})

	srv.AddTool(mcp.Tool{
		Name:        "list_seasons",
		Description: "List the seasons available, optionally for a single competition.",
		InputSchema: objectSchema(map[string]any{
			"competition": competitionProp(),
		}, nil),
		Handler: func(raw json.RawMessage) (string, error) {
			var a args
			if err := json.Unmarshal(raw, &a); err != nil {
				return "", err
			}
			seasons := store.Seasons(a.Competition)
			var sb strings.Builder
			scope := "all competitions"
			if a.Competition != "" {
				scope = a.Competition
			}
			fmt.Fprintf(&sb, "Seasons available for %s:\n", scope)
			for _, s := range seasons {
				fmt.Fprintf(&sb, "%d ", s)
			}
			return strings.TrimSpace(sb.String()), nil
		},
	})
}

// args is the union of all tool argument fields; JSON unmarshalling ignores
// fields absent from a given tool's input.
type args struct {
	Team        string `json:"team"`
	Opponent    string `json:"opponent"`
	TeamA       string `json:"team_a"`
	TeamB       string `json:"team_b"`
	Venue       string `json:"venue"`
	Competition string `json:"competition"`
	Season      int    `json:"season"`
	DateFrom    string `json:"date_from"`
	DateTo      string `json:"date_to"`
	Name        string `json:"name"`
	Nationality string `json:"nationality"`
	Club        string `json:"club"`
	Position    string `json:"position"`
	MinOverall  int    `json:"min_overall"`
	SortBy      string `json:"sort_by"`
	TopWins     int    `json:"top_wins"`
	Limit       int    `json:"limit"`
}

func parseArgs(raw json.RawMessage) (args, error) {
	var a args
	if err := json.Unmarshal(raw, &a); err != nil {
		return a, fmt.Errorf("invalid arguments: %w", err)
	}
	return a, nil
}

func handleSearchMatches(store *soccer.Store) mcp.ToolHandler {
	return func(raw json.RawMessage) (string, error) {
		a, err := parseArgs(raw)
		if err != nil {
			return "", err
		}
		if a.Team == "" && a.Opponent == "" && a.Competition == "" && a.Season == 0 && a.DateFrom == "" && a.DateTo == "" {
			return "", fmt.Errorf("provide at least one filter (team, opponent, competition, season or date range)")
		}
		f := soccer.MatchFilter{
			Team:        a.Team,
			Opponent:    a.Opponent,
			Venue:       a.Venue,
			Competition: a.Competition,
			Season:      a.Season,
			Limit:       limitOr(a.Limit, 0),
		}
		if a.DateFrom != "" {
			t, err := time.Parse("2006-01-02", a.DateFrom)
			if err != nil {
				return "", fmt.Errorf("date_from must be YYYY-MM-DD: %w", err)
			}
			f.DateFrom = t
		}
		if a.DateTo != "" {
			t, err := time.Parse("2006-01-02", a.DateTo)
			if err != nil {
				return "", fmt.Errorf("date_to must be YYYY-MM-DD: %w", err)
			}
			f.DateTo = t
		}
		results := store.SearchMatches(f)
		return soccer.FormatMatches(matchHeading(a), results, defaultMatchLimit), nil
	}
}

func matchHeading(a args) string {
	var parts []string
	if a.Team != "" {
		parts = append(parts, a.Team)
	}
	if a.Opponent != "" {
		parts = append(parts, "vs "+a.Opponent)
	}
	if a.Competition != "" {
		parts = append(parts, a.Competition)
	}
	if a.Season != 0 {
		parts = append(parts, fmt.Sprintf("%d", a.Season))
	}
	if len(parts) == 0 {
		return "Matches:"
	}
	return "Matches — " + strings.Join(parts, " ") + ":"
}

func handleHeadToHead(store *soccer.Store) mcp.ToolHandler {
	return func(raw json.RawMessage) (string, error) {
		a, err := parseArgs(raw)
		if err != nil {
			return "", err
		}
		if a.TeamA == "" || a.TeamB == "" {
			return "", fmt.Errorf("team_a and team_b are required")
		}
		h := store.HeadToHead(a.TeamA, a.TeamB)
		return soccer.FormatHeadToHead(h, limitOr(a.Limit, defaultMatchLimit)), nil
	}
}

func handleTeamStats(store *soccer.Store) mcp.ToolHandler {
	return func(raw json.RawMessage) (string, error) {
		a, err := parseArgs(raw)
		if err != nil {
			return "", err
		}
		if a.Team == "" {
			return "", fmt.Errorf("team is required")
		}
		rec := store.TeamStats(a.Team, a.Competition, a.Season, a.Venue)
		if rec.Played == 0 {
			return fmt.Sprintf("No matches found for %q with the given filters.", a.Team), nil
		}
		return soccer.FormatTeamRecord(rec, a.Competition, a.Season, a.Venue), nil
	}
}

func handleSearchPlayers(store *soccer.Store) mcp.ToolHandler {
	return func(raw json.RawMessage) (string, error) {
		a, err := parseArgs(raw)
		if err != nil {
			return "", err
		}
		if a.Name == "" && a.Nationality == "" && a.Club == "" && a.Position == "" && a.MinOverall == 0 {
			return "", fmt.Errorf("provide at least one filter (name, nationality, club, position or min_overall)")
		}
		f := soccer.PlayerFilter{
			Name:        a.Name,
			Nationality: a.Nationality,
			Club:        a.Club,
			Position:    a.Position,
			MinOverall:  a.MinOverall,
			SortBy:      a.SortBy,
			Limit:       limitOr(a.Limit, 0),
		}
		players := store.SearchPlayers(f)
		return soccer.FormatPlayers("Players:", players, defaultPlayerLimit), nil
	}
}

func handlePlayersByClub(store *soccer.Store) mcp.ToolHandler {
	return func(raw json.RawMessage) (string, error) {
		a, err := parseArgs(raw)
		if err != nil {
			return "", err
		}
		summaries := store.PlayersByClub(a.Nationality)
		heading := "Players by club:"
		if a.Nationality != "" {
			heading = fmt.Sprintf("%s players by club:", a.Nationality)
		}
		return soccer.FormatClubSummaries(heading, summaries, limitOr(a.Limit, defaultPlayerLimit)), nil
	}
}

func handleStandings(store *soccer.Store) mcp.ToolHandler {
	return func(raw json.RawMessage) (string, error) {
		a, err := parseArgs(raw)
		if err != nil {
			return "", err
		}
		if a.Competition == "" || a.Season == 0 {
			return "", fmt.Errorf("competition and season are required")
		}
		records := store.Standings(a.Competition, a.Season)
		return soccer.FormatStandings(records, a.Competition, a.Season, limitOr(a.Limit, 0)), nil
	}
}

func handleCompetitionStats(store *soccer.Store) mcp.ToolHandler {
	return func(raw json.RawMessage) (string, error) {
		a, err := parseArgs(raw)
		if err != nil {
			return "", err
		}
		stats := store.Stats(a.Competition, a.Season, a.TopWins)
		return soccer.FormatStats(stats), nil
	}
}

func limitOr(v, def int) int {
	if v <= 0 {
		return def
	}
	return v
}

// --- JSON-schema helpers ---

func objectSchema(props map[string]any, required []string) map[string]any {
	schema := map[string]any{
		"type":       "object",
		"properties": props,
	}
	if len(required) > 0 {
		schema["required"] = required
	}
	return schema
}

func strProp(desc string) map[string]any {
	return map[string]any{"type": "string", "description": desc}
}

func intProp(desc string) map[string]any {
	return map[string]any{"type": "integer", "description": desc}
}

func enumProp(desc string, values ...string) map[string]any {
	return map[string]any{"type": "string", "description": desc, "enum": values}
}

func competitionProp() map[string]any {
	return map[string]any{
		"type":        "string",
		"description": "Competition name.",
		"enum": []string{
			soccer.CompSerieA, soccer.CompSerieB, soccer.CompSerieC,
			soccer.CompCopaBrasil, soccer.CompLibertadores,
		},
	}
}
