// tools.go: wiring between the MCP protocol layer (package mcp) and the soccer
// query API (package soccer). registerTools declares one MCP tool per query
// capability in the spec — match, team, player, competition and statistical
// queries — each with a JSON-Schema for its arguments and a thin handler that
// unmarshals the arguments and calls the corresponding Store method.
package main

import (
	"encoding/json"
	"strings"

	"brazilian-soccer-mcp/mcp"
	"brazilian-soccer-mcp/soccer"
)

// obj/props/prop are small helpers for writing JSON-Schema inline.
func obj(props map[string]any, required ...string) map[string]any {
	m := map[string]any{"type": "object", "properties": props}
	if len(required) > 0 {
		m["required"] = required
	}
	return m
}
func strProp(desc string) map[string]any {
	return map[string]any{"type": "string", "description": desc}
}
func intProp(desc string) map[string]any {
	return map[string]any{"type": "integer", "description": desc}
}

// parseVenue maps a free-text venue argument to a soccer.Venue.
func parseVenue(s string) soccer.Venue {
	switch strings.ToLower(strings.TrimSpace(s)) {
	case "home":
		return soccer.VenueHome
	case "away":
		return soccer.VenueAway
	default:
		return soccer.VenueAll
	}
}

// registerTools declares every MCP tool against the given store.
func registerTools(srv *mcp.Server, store *soccer.Store) {
	// 1. search_matches -----------------------------------------------------
	srv.AddTool("search_matches",
		"Search match results by team, opponent, competition, season or date range. "+
			"Set both 'team' and 'opponent' to get a head-to-head summary. "+
			"Competitions: Brasileirão Série A/B/C, Copa do Brasil, Copa Libertadores.",
		obj(map[string]any{
			"team":        strProp("Team name (matches home or away)."),
			"opponent":    strProp("Opponent team name (use together with 'team')."),
			"home_team":   strProp("Restrict to matches where this team played at home."),
			"away_team":   strProp("Restrict to matches where this team played away."),
			"competition": strProp("Competition filter, e.g. 'Brasileirão', 'Copa do Brasil', 'Libertadores'."),
			"season":      intProp("Season year, e.g. 2019."),
			"season_min":  intProp("Earliest season year (inclusive)."),
			"season_max":  intProp("Latest season year (inclusive)."),
			"date_from":   strProp("Start date YYYY-MM-DD (inclusive)."),
			"date_to":     strProp("End date YYYY-MM-DD (inclusive)."),
			"limit":       intProp("Maximum matches to list (default 25)."),
		}),
		func(args json.RawMessage) (string, error) {
			var a struct {
				Team        string `json:"team"`
				Opponent    string `json:"opponent"`
				HomeTeam    string `json:"home_team"`
				AwayTeam    string `json:"away_team"`
				Competition string `json:"competition"`
				Season      int    `json:"season"`
				SeasonMin   int    `json:"season_min"`
				SeasonMax   int    `json:"season_max"`
				DateFrom    string `json:"date_from"`
				DateTo      string `json:"date_to"`
				Limit       int    `json:"limit"`
			}
			if err := unmarshal(args, &a); err != nil {
				return "", err
			}
			return store.SearchMatches(soccer.MatchQuery{
				Team: a.Team, Opponent: a.Opponent, HomeTeam: a.HomeTeam, AwayTeam: a.AwayTeam,
				Competition: a.Competition, Season: a.Season, SeasonMin: a.SeasonMin,
				SeasonMax: a.SeasonMax, DateFrom: a.DateFrom, DateTo: a.DateTo, Limit: a.Limit,
			}), nil
		})

	// 2. head_to_head -------------------------------------------------------
	srv.AddTool("head_to_head",
		"Compare two teams head-to-head: matches, wins, draws and goals, plus recent meetings.",
		obj(map[string]any{
			"team_a":      strProp("First team."),
			"team_b":      strProp("Second team."),
			"competition": strProp("Optional competition filter."),
			"season":      intProp("Optional season filter."),
			"limit":       intProp("How many recent meetings to list (default 10)."),
		}, "team_a", "team_b"),
		func(args json.RawMessage) (string, error) {
			var a struct {
				TeamA       string `json:"team_a"`
				TeamB       string `json:"team_b"`
				Competition string `json:"competition"`
				Season      int    `json:"season"`
				Limit       int    `json:"limit"`
			}
			if err := unmarshal(args, &a); err != nil {
				return "", err
			}
			return store.HeadToHeadQuery(a.TeamA, a.TeamB, a.Competition, a.Season, a.Limit), nil
		})

	// 3. team_record --------------------------------------------------------
	srv.AddTool("team_record",
		"Win/draw/loss record, goals and points for a team, optionally filtered by "+
			"competition, season and venue (home/away/all).",
		obj(map[string]any{
			"team":        strProp("Team name."),
			"competition": strProp("Optional competition filter."),
			"season":      intProp("Optional season year."),
			"venue":       map[string]any{"type": "string", "enum": []string{"all", "home", "away"}, "description": "Venue filter (default all)."},
		}, "team"),
		func(args json.RawMessage) (string, error) {
			var a struct {
				Team        string `json:"team"`
				Competition string `json:"competition"`
				Season      int    `json:"season"`
				Venue       string `json:"venue"`
			}
			if err := unmarshal(args, &a); err != nil {
				return "", err
			}
			return store.TeamRecordQuery(a.Team, a.Competition, a.Season, parseVenue(a.Venue)), nil
		})

	// 4. team_competitions --------------------------------------------------
	srv.AddTool("team_competitions",
		"List which competitions a team appears in, with match counts and season ranges.",
		obj(map[string]any{"team": strProp("Team name.")}, "team"),
		func(args json.RawMessage) (string, error) {
			var a struct {
				Team string `json:"team"`
			}
			if err := unmarshal(args, &a); err != nil {
				return "", err
			}
			return store.TeamCompetitionsQuery(a.Team), nil
		})

	// 5. standings ----------------------------------------------------------
	srv.AddTool("standings",
		"Compute the league table for a competition + season from match results "+
			"(points, W/D/L, goal difference). Defaults to Brasileirão Série A.",
		obj(map[string]any{
			"competition": strProp("Competition (default Brasileirão Série A)."),
			"season":      intProp("Season year (required)."),
			"limit":       intProp("Number of rows to show (0 = full table)."),
		}, "season"),
		func(args json.RawMessage) (string, error) {
			var a struct {
				Competition string `json:"competition"`
				Season      int    `json:"season"`
				Limit       int    `json:"limit"`
			}
			if err := unmarshal(args, &a); err != nil {
				return "", err
			}
			return store.StandingsQuery(a.Competition, a.Season, a.Limit), nil
		})

	// 6. competition_stats --------------------------------------------------
	srv.AddTool("competition_stats",
		"Aggregate statistics for a competition/season: matches, total goals, "+
			"average goals per match, home/away win and draw rates.",
		obj(map[string]any{
			"competition": strProp("Optional competition filter."),
			"season":      intProp("Optional season year."),
		}),
		func(args json.RawMessage) (string, error) {
			var a struct {
				Competition string `json:"competition"`
				Season      int    `json:"season"`
			}
			if err := unmarshal(args, &a); err != nil {
				return "", err
			}
			return store.CompetitionStatsQuery(a.Competition, a.Season), nil
		})

	// 7. biggest_wins -------------------------------------------------------
	srv.AddTool("biggest_wins",
		"List the largest-margin victories for a competition/season.",
		obj(map[string]any{
			"competition": strProp("Optional competition filter."),
			"season":      intProp("Optional season year."),
			"limit":       intProp("How many matches to list (default 10)."),
		}),
		func(args json.RawMessage) (string, error) {
			var a struct {
				Competition string `json:"competition"`
				Season      int    `json:"season"`
				Limit       int    `json:"limit"`
			}
			if err := unmarshal(args, &a); err != nil {
				return "", err
			}
			return store.BiggestWinsQuery(a.Competition, a.Season, a.Limit), nil
		})

	// 8. top_scoring_teams --------------------------------------------------
	srv.AddTool("top_scoring_teams",
		"Rank teams by total goals scored in a competition/season.",
		obj(map[string]any{
			"competition": strProp("Optional competition filter."),
			"season":      intProp("Optional season year."),
			"limit":       intProp("How many teams to list (default 10)."),
		}),
		func(args json.RawMessage) (string, error) {
			var a struct {
				Competition string `json:"competition"`
				Season      int    `json:"season"`
				Limit       int    `json:"limit"`
			}
			if err := unmarshal(args, &a); err != nil {
				return "", err
			}
			return store.TopScoringTeamsQuery(a.Competition, a.Season, a.Limit), nil
		})

	// 9. search_players -----------------------------------------------------
	srv.AddTool("search_players",
		"Search the FIFA player database by name, nationality (e.g. 'Brazil'), "+
			"club, position and minimum overall rating. Results are sorted by rating.",
		obj(map[string]any{
			"name":        strProp("Player name (substring match)."),
			"nationality": strProp("Nationality, e.g. 'Brazil'."),
			"club":        strProp("Club name (substring match)."),
			"position":    strProp("Position code, e.g. 'GK', 'ST', 'CDM'."),
			"min_overall": intProp("Minimum FIFA overall rating."),
			"limit":       intProp("Maximum players to list (default 25)."),
		}),
		func(args json.RawMessage) (string, error) {
			var a struct {
				Name        string `json:"name"`
				Nationality string `json:"nationality"`
				Club        string `json:"club"`
				Position    string `json:"position"`
				MinOverall  int    `json:"min_overall"`
				Limit       int    `json:"limit"`
			}
			if err := unmarshal(args, &a); err != nil {
				return "", err
			}
			return store.SearchPlayersQuery(a.Name, a.Nationality, a.Club, a.Position, a.MinOverall, a.Limit), nil
		})

	// 10. player_info -------------------------------------------------------
	srv.AddTool("player_info",
		"Detailed card for a single player (best name match): ratings, position, "+
			"club, nationality and physical attributes.",
		obj(map[string]any{"name": strProp("Player name.")}, "name"),
		func(args json.RawMessage) (string, error) {
			var a struct {
				Name string `json:"name"`
			}
			if err := unmarshal(args, &a); err != nil {
				return "", err
			}
			return store.PlayerInfoQuery(a.Name), nil
		})

	// 11. club_players ------------------------------------------------------
	srv.AddTool("club_players",
		"List players at a club (top-rated first) with the squad's average rating.",
		obj(map[string]any{
			"club":  strProp("Club name."),
			"limit": intProp("Maximum players to list (default 25)."),
		}, "club"),
		func(args json.RawMessage) (string, error) {
			var a struct {
				Club  string `json:"club"`
				Limit int    `json:"limit"`
			}
			if err := unmarshal(args, &a); err != nil {
				return "", err
			}
			return store.ClubPlayersQuery(a.Club, a.Limit), nil
		})

	// 12. dataset_overview --------------------------------------------------
	srv.AddTool("dataset_overview",
		"Summary of everything loaded: match/player/team counts and per-competition "+
			"match counts and season ranges. Useful to discover what can be queried.",
		obj(map[string]any{}),
		func(args json.RawMessage) (string, error) {
			return store.DatasetOverview(), nil
		})
}

// unmarshal decodes tool arguments, tolerating an empty/absent argument object.
func unmarshal(args json.RawMessage, v any) error {
	if len(strings.TrimSpace(string(args))) == 0 || string(args) == "null" {
		return nil
	}
	return json.Unmarshal(args, v)
}
