// Context
// -------
// Tool catalog and dispatch. toolDefinitions() returns the MCP tool list
// (name, description, JSON-schema of arguments) advertised via tools/list, and
// callTool() decodes the arguments for a named tool and invokes the matching
// soccer query, formatting the result as text. Adding a capability means adding
// one entry to the catalog and one case to the dispatcher.
package mcp

import (
	"encoding/json"
	"fmt"
	"strings"

	"brazilian-soccer-mcp/internal/soccer"
)

// toolDefinitions returns the static catalog of tools exposed by the server.
func toolDefinitions() []Tool {
	return []Tool{
		{
			Name:        "search_matches",
			Description: "Search Brazilian soccer matches by team, opponent, competition, season and/or date range. Returns a chronological list of matches with scores and competition context.",
			InputSchema: schema(`{
				"type":"object",
				"properties":{
					"team":{"type":"string","description":"Team name (matches home or away). Handles name variations like 'Palmeiras' / 'Palmeiras-SP'."},
					"opponent":{"type":"string","description":"Optional second team; restricts to head-to-head fixtures between team and opponent."},
					"competition":{"type":"string","description":"Competition filter, e.g. 'Brasileirão', 'Copa do Brasil', 'Libertadores'."},
					"season":{"type":"integer","description":"Season year, e.g. 2019."},
					"date_from":{"type":"string","description":"Inclusive start date (YYYY-MM-DD)."},
					"date_to":{"type":"string","description":"Inclusive end date (YYYY-MM-DD)."},
					"limit":{"type":"integer","description":"Maximum matches to return (default 25)."}
				}
			}`),
		},
		{
			Name:        "head_to_head",
			Description: "Compute the all-competition head-to-head record between two teams: wins, draws, goals, and recent matches.",
			InputSchema: schema(`{
				"type":"object",
				"properties":{
					"team_a":{"type":"string"},
					"team_b":{"type":"string"},
					"limit":{"type":"integer","description":"Max recent matches to list (default 10)."}
				},
				"required":["team_a","team_b"]
			}`),
		},
		{
			Name:        "team_stats",
			Description: "Aggregate a team's record (played, wins, draws, losses, goals for/against, win rate), optionally filtered by season, competition, and home/away.",
			InputSchema: schema(`{
				"type":"object",
				"properties":{
					"team":{"type":"string"},
					"season":{"type":"integer"},
					"competition":{"type":"string"},
					"venue":{"type":"string","enum":["all","home","away"],"description":"Restrict to home or away matches (default all)."}
				},
				"required":["team"]
			}`),
		},
		{
			Name:        "standings",
			Description: "Compute a league table for a competition and season from match results (points, W/D/L, goal difference).",
			InputSchema: schema(`{
				"type":"object",
				"properties":{
					"competition":{"type":"string","description":"Competition name (default Brasileirão Série A)."},
					"season":{"type":"integer"},
					"limit":{"type":"integer","description":"Max rows (default all)."}
				},
				"required":["season"]
			}`),
		},
		{
			Name:        "search_players",
			Description: "Search FIFA player data by name, nationality (e.g. 'Brazil'), club, position, and minimum overall rating. Sorted by overall rating.",
			InputSchema: schema(`{
				"type":"object",
				"properties":{
					"name":{"type":"string"},
					"nationality":{"type":"string"},
					"club":{"type":"string"},
					"position":{"type":"string","description":"Exact position code, e.g. 'GK','LW','CDM','ST'."},
					"min_overall":{"type":"integer"},
					"limit":{"type":"integer","description":"Max players to return (default 25)."}
				}
			}`),
		},
		{
			Name:        "competition_stats",
			Description: "Aggregate statistics over a competition/season: match count, average goals per match, home/away/draw split, and the biggest victories.",
			InputSchema: schema(`{
				"type":"object",
				"properties":{
					"competition":{"type":"string"},
					"season":{"type":"integer"},
					"top_wins":{"type":"integer","description":"Number of biggest victories to list (default 10)."}
				}
			}`),
		},
		{
			Name:        "list_metadata",
			Description: "List the teams, competitions and seasons available in the dataset, plus overall counts. Useful for discovering valid filter values.",
			InputSchema: schema(`{"type":"object","properties":{}}`),
		},
	}
}

func schema(s string) json.RawMessage { return json.RawMessage(s) }

// callTool dispatches a tools/call to the right query and formats the result.
func (s *Server) callTool(p CallToolParams) CallToolResult {
	switch p.Name {
	case "search_matches":
		return s.toolSearchMatches(p.Arguments)
	case "head_to_head":
		return s.toolHeadToHead(p.Arguments)
	case "team_stats":
		return s.toolTeamStats(p.Arguments)
	case "standings":
		return s.toolStandings(p.Arguments)
	case "search_players":
		return s.toolSearchPlayers(p.Arguments)
	case "competition_stats":
		return s.toolCompetitionStats(p.Arguments)
	case "list_metadata":
		return s.toolListMetadata()
	default:
		return errorResult("unknown tool: " + p.Name)
	}
}

// --- argument structs ---

type searchMatchesArgs struct {
	Team        string `json:"team"`
	Opponent    string `json:"opponent"`
	Competition string `json:"competition"`
	Season      int    `json:"season"`
	DateFrom    string `json:"date_from"`
	DateTo      string `json:"date_to"`
	Limit       int    `json:"limit"`
}

func (s *Server) toolSearchMatches(raw json.RawMessage) CallToolResult {
	var a searchMatchesArgs
	if err := decode(raw, &a); err != nil {
		return errorResult(err.Error())
	}
	q := soccer.MatchQuery{
		Team:        a.Team,
		Team2:       a.Opponent,
		Competition: a.Competition,
		Season:      a.Season,
		Limit:       orDefault(a.Limit, 25),
	}
	if t, _, ok := soccer.ParseDate(a.DateFrom); ok {
		q.From = t
	}
	if t, _, ok := soccer.ParseDate(a.DateTo); ok {
		q.To = t
	}
	matches := s.graph.SearchMatches(q)
	header := "Matches"
	if a.Team != "" {
		header = a.Team
		if a.Opponent != "" {
			header += " vs " + a.Opponent
		}
	}
	body := fmt.Sprintf("%s (%d found):\n%s", header, len(matches), soccer.FormatMatches(matches, orDefault(a.Limit, 25)))
	return textResult(body)
}

type headToHeadArgs struct {
	TeamA string `json:"team_a"`
	TeamB string `json:"team_b"`
	Limit int    `json:"limit"`
}

func (s *Server) toolHeadToHead(raw json.RawMessage) CallToolResult {
	var a headToHeadArgs
	if err := decode(raw, &a); err != nil {
		return errorResult(err.Error())
	}
	if a.TeamA == "" || a.TeamB == "" {
		return errorResult("team_a and team_b are required")
	}
	h := s.graph.HeadToHead(a.TeamA, a.TeamB)
	return textResult(soccer.FormatH2H(h, orDefault(a.Limit, 10)))
}

type teamStatsArgs struct {
	Team        string `json:"team"`
	Season      int    `json:"season"`
	Competition string `json:"competition"`
	Venue       string `json:"venue"`
}

func (s *Server) toolTeamStats(raw json.RawMessage) CallToolResult {
	var a teamStatsArgs
	if err := decode(raw, &a); err != nil {
		return errorResult(err.Error())
	}
	if a.Team == "" {
		return errorResult("team is required")
	}
	rec := s.graph.TeamStats(a.Team, soccer.TeamStatsOptions{
		Season:      a.Season,
		Competition: a.Competition,
		Filter:      strings.ToLower(a.Venue),
	})
	if rec.Played == 0 {
		return textResult(fmt.Sprintf("No matches found for %q with the given filters.", a.Team))
	}
	return textResult(soccer.FormatTeamRecord(rec))
}

type standingsArgs struct {
	Competition string `json:"competition"`
	Season      int    `json:"season"`
	Limit       int    `json:"limit"`
}

func (s *Server) toolStandings(raw json.RawMessage) CallToolResult {
	var a standingsArgs
	if err := decode(raw, &a); err != nil {
		return errorResult(err.Error())
	}
	if a.Season == 0 {
		return errorResult("season is required")
	}
	comp := a.Competition
	if comp == "" {
		comp = soccer.CompBrasileirao
	}
	rows := s.graph.Standings(comp, a.Season)
	return textResult(soccer.FormatStandings(rows, comp, a.Season, a.Limit))
}

type searchPlayersArgs struct {
	Name        string `json:"name"`
	Nationality string `json:"nationality"`
	Club        string `json:"club"`
	Position    string `json:"position"`
	MinOverall  int    `json:"min_overall"`
	Limit       int    `json:"limit"`
}

func (s *Server) toolSearchPlayers(raw json.RawMessage) CallToolResult {
	var a searchPlayersArgs
	if err := decode(raw, &a); err != nil {
		return errorResult(err.Error())
	}
	limit := orDefault(a.Limit, 25)
	players := s.graph.SearchPlayers(soccer.PlayerQuery{
		Name:        a.Name,
		Nationality: a.Nationality,
		Club:        a.Club,
		Position:    a.Position,
		MinOverall:  a.MinOverall,
		Limit:       limit,
	})
	body := fmt.Sprintf("Players (%d shown):\n%s", len(players), soccer.FormatPlayers(players, limit))
	return textResult(body)
}

type competitionStatsArgs struct {
	Competition string `json:"competition"`
	Season      int    `json:"season"`
	TopWins     int    `json:"top_wins"`
}

func (s *Server) toolCompetitionStats(raw json.RawMessage) CallToolResult {
	var a competitionStatsArgs
	if err := decode(raw, &a); err != nil {
		return errorResult(err.Error())
	}
	cs := s.graph.Statistics(a.Competition, a.Season, orDefault(a.TopWins, 10))
	if cs.Matches == 0 {
		return textResult("No matches found for the given filters.")
	}
	return textResult(soccer.FormatStatistics(cs))
}

func (s *Server) toolListMetadata() CallToolResult {
	g := s.graph
	seasons := g.Seasons()
	var seasonStr string
	if len(seasons) > 0 {
		seasonStr = fmt.Sprintf("%d–%d", seasons[0], seasons[len(seasons)-1])
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Dataset summary: %s\n\n", g.Stats())
	fmt.Fprintf(&b, "Competitions:\n")
	for _, c := range g.Competitions() {
		fmt.Fprintf(&b, "- %s\n", c)
	}
	fmt.Fprintf(&b, "\nSeasons covered: %s\n", seasonStr)
	teams := g.Teams()
	fmt.Fprintf(&b, "\nTeams (%d total), e.g.:\n", len(teams))
	for i, t := range teams {
		if i >= 40 {
			fmt.Fprintf(&b, "- ... (%d more)\n", len(teams)-40)
			break
		}
		fmt.Fprintf(&b, "- %s\n", t)
	}
	return textResult(strings.TrimRight(b.String(), "\n"))
}

// --- helpers ---

// decode unmarshals tool arguments, tolerating missing/null arguments.
func decode(raw json.RawMessage, v interface{}) error {
	if len(raw) == 0 || string(raw) == "null" {
		return nil
	}
	if err := json.Unmarshal(raw, v); err != nil {
		return fmt.Errorf("invalid arguments: %w", err)
	}
	return nil
}

func orDefault(v, def int) int {
	if v <= 0 {
		return def
	}
	return v
}
