package app

import (
	"encoding/json"
	"errors"
	"strings"

	"brazilian-soccer-mcp/internal/mcp"
	"brazilian-soccer-mcp/internal/store"
)

// ---------------------------------------------------------------------------
// Output DTOs (the domain-language JSON returned to MCP clients).
// ---------------------------------------------------------------------------

type matchOut struct {
	Date        string `json:"date"`
	Competition string `json:"competition"`
	HomeTeam    string `json:"home_team"`
	AwayTeam    string `json:"away_team"`
	HomeGoal    int    `json:"home_goal"`
	AwayGoal    int    `json:"away_goal"`
	Season      int    `json:"season"`
	Round       string `json:"round,omitempty"`
	Stage       string `json:"stage,omitempty"`
}

func toMatchOut(m store.Match) matchOut {
	return matchOut{
		Date:        m.DateString(),
		Competition: m.Competition,
		HomeTeam:    m.HomeTeam,
		AwayTeam:    m.AwayTeam,
		HomeGoal:    m.HomeGoals,
		AwayGoal:    m.AwayGoals,
		Season:      m.Season,
		Round:       m.Round,
		Stage:       m.Stage,
	}
}

// ---------------------------------------------------------------------------
// find_matches
// ---------------------------------------------------------------------------

func registerFindMatches(srv *mcp.Server, st *store.Store) {
	type args struct {
		Team        string  `json:"team"`
		Opponent    string  `json:"opponent"`
		Competition string  `json:"competition"`
		Season      flexInt `json:"season"`
		Venue       string  `json:"venue"`
		StartDate   string  `json:"start_date"`
		EndDate     string  `json:"end_date"`
		Limit       flexInt `json:"limit"`
	}
	type h2h struct {
		Team          string `json:"team"`
		Opponent      string `json:"opponent"`
		TeamWins      int    `json:"team_wins"`
		OpponentWins  int    `json:"opponent_wins"`
		Draws         int    `json:"draws"`
		TeamGoals     int    `json:"team_goals"`
		OpponentGoals int    `json:"opponent_goals"`
	}
	type out struct {
		Count      int        `json:"count"`
		Matches    []matchOut `json:"matches"`
		HeadToHead *h2h       `json:"head_to_head,omitempty"`
	}

	srv.AddTool(mcp.Tool{
		Name:        "find_matches",
		Description: "Find soccer matches by team, opponent, competition (Brasileirao, Copa do Brasil, Libertadores), season, venue (home/away/either) or date range. When both team and opponent are given, also returns the head-to-head record.",
		InputSchema: schemaObject(map[string]string{
			"team":        "string",
			"opponent":    "string",
			"competition": "string",
			"season":      "integer",
			"venue":       "string",
			"start_date":  "string",
			"end_date":    "string",
			"limit":       "integer",
		}),
		Handler: func(raw json.RawMessage) (string, error) {
			var a args
			if err := json.Unmarshal(raw, &a); err != nil {
				return "", err
			}
			f := store.MatchFilter{
				Team:        a.Team,
				Opponent:    a.Opponent,
				Competition: a.Competition,
				Season:      int(a.Season),
				Venue:       a.Venue,
				Limit:       int(a.Limit),
			}
			if t, ok := store.ParseDate(a.StartDate); ok {
				f.StartDate = &t
			}
			if t, ok := store.ParseDate(a.EndDate); ok {
				f.EndDate = &t
			}
			matches, head := st.FindMatches(f)

			res := out{Count: len(matches), Matches: []matchOut{}}
			for _, m := range matches {
				res.Matches = append(res.Matches, toMatchOut(m))
			}
			if head != nil {
				res.HeadToHead = &h2h{
					Team:          head.Team,
					Opponent:      head.Opponent,
					TeamWins:      head.TeamWins,
					OpponentWins:  head.OpponentWins,
					Draws:         head.Draws,
					TeamGoals:     head.TeamGoals,
					OpponentGoals: head.OpponentGoals,
				}
			}
			return mustJSON(res)
		},
	})
}

// ---------------------------------------------------------------------------
// get_team_stats
// ---------------------------------------------------------------------------

func registerTeamStats(srv *mcp.Server, st *store.Store) {
	type args struct {
		Team        string  `json:"team"`
		Competition string  `json:"competition"`
		Season      flexInt `json:"season"`
		Venue       string  `json:"venue"`
	}
	type out struct {
		Team           string  `json:"team"`
		Matches        int     `json:"matches"`
		Wins           int     `json:"wins"`
		Draws          int     `json:"draws"`
		Losses         int     `json:"losses"`
		GoalsFor       int     `json:"goals_for"`
		GoalsAgainst   int     `json:"goals_against"`
		GoalDifference int     `json:"goal_difference"`
		Points         int     `json:"points"`
		WinRate        float64 `json:"win_rate"`
	}

	srv.AddTool(mcp.Tool{
		Name:        "get_team_stats",
		Description: "Get a team's record (wins, draws, losses, goals for/against, points, win rate), optionally filtered by competition, season and venue (home/away).",
		InputSchema: schemaObject(map[string]string{
			"team":        "string",
			"competition": "string",
			"season":      "integer",
			"venue":       "string",
		}, "team"),
		Handler: func(raw json.RawMessage) (string, error) {
			var a args
			if err := json.Unmarshal(raw, &a); err != nil {
				return "", err
			}
			if strings.TrimSpace(a.Team) == "" {
				return "", errors.New("the 'team' argument is required")
			}
			ts := st.TeamStats(store.MatchFilter{
				Team:        a.Team,
				Competition: a.Competition,
				Season:      int(a.Season),
				Venue:       a.Venue,
			})
			return mustJSON(out{
				Team:           ts.Team,
				Matches:        ts.Matches,
				Wins:           ts.Wins,
				Draws:          ts.Draws,
				Losses:         ts.Losses,
				GoalsFor:       ts.GoalsFor,
				GoalsAgainst:   ts.GoalsAgainst,
				GoalDifference: ts.GoalDifference,
				Points:         ts.Points,
				WinRate:        ts.WinRate,
			})
		},
	})
}

// ---------------------------------------------------------------------------
// head_to_head
// ---------------------------------------------------------------------------

func registerHeadToHead(srv *mcp.Server, st *store.Store) {
	type args struct {
		TeamA string `json:"team_a"`
		TeamB string `json:"team_b"`
	}
	type out struct {
		TeamA      string `json:"team_a"`
		TeamB      string `json:"team_b"`
		Matches    int    `json:"matches"`
		TeamAWins  int    `json:"team_a_wins"`
		TeamBWins  int    `json:"team_b_wins"`
		Draws      int    `json:"draws"`
		TeamAGoals int    `json:"team_a_goals"`
		TeamBGoals int    `json:"team_b_goals"`
	}

	srv.AddTool(mcp.Tool{
		Name:        "head_to_head",
		Description: "Compare two teams head-to-head across all competitions: total meetings, wins for each side, draws and goals.",
		InputSchema: schemaObject(map[string]string{
			"team_a": "string",
			"team_b": "string",
		}, "team_a", "team_b"),
		Handler: func(raw json.RawMessage) (string, error) {
			var a args
			if err := json.Unmarshal(raw, &a); err != nil {
				return "", err
			}
			if strings.TrimSpace(a.TeamA) == "" || strings.TrimSpace(a.TeamB) == "" {
				return "", errors.New("both 'team_a' and 'team_b' are required")
			}
			h := st.HeadToHead(a.TeamA, a.TeamB)
			return mustJSON(out{
				TeamA:      h.Team,
				TeamB:      h.Opponent,
				Matches:    h.Matches,
				TeamAWins:  h.TeamWins,
				TeamBWins:  h.OpponentWins,
				Draws:      h.Draws,
				TeamAGoals: h.TeamGoals,
				TeamBGoals: h.OpponentGoals,
			})
		},
	})
}

// ---------------------------------------------------------------------------
// search_players
// ---------------------------------------------------------------------------

func registerSearchPlayers(srv *mcp.Server, st *store.Store) {
	type args struct {
		Name        string  `json:"name"`
		Nationality string  `json:"nationality"`
		Club        string  `json:"club"`
		Position    string  `json:"position"`
		Limit       flexInt `json:"limit"`
	}
	type playerOut struct {
		Name        string `json:"name"`
		Age         int    `json:"age"`
		Nationality string `json:"nationality"`
		Overall     int    `json:"overall"`
		Potential   int    `json:"potential"`
		Club        string `json:"club"`
		Position    string `json:"position"`
	}
	type out struct {
		Count   int         `json:"count"`
		Players []playerOut `json:"players"`
	}

	srv.AddTool(mcp.Tool{
		Name:        "search_players",
		Description: "Search FIFA players by name, nationality (e.g. Brazil), club or position. Results are sorted by overall rating, highest first.",
		InputSchema: schemaObject(map[string]string{
			"name":        "string",
			"nationality": "string",
			"club":        "string",
			"position":    "string",
			"limit":       "integer",
		}),
		Handler: func(raw json.RawMessage) (string, error) {
			var a args
			if err := json.Unmarshal(raw, &a); err != nil {
				return "", err
			}
			players := st.SearchPlayers(store.PlayerFilter{
				Name:        a.Name,
				Nationality: a.Nationality,
				Club:        a.Club,
				Position:    a.Position,
				Limit:       int(a.Limit),
			})
			res := out{Count: len(players), Players: []playerOut{}}
			for _, p := range players {
				res.Players = append(res.Players, playerOut{
					Name:        p.Name,
					Age:         p.Age,
					Nationality: p.Nationality,
					Overall:     p.Overall,
					Potential:   p.Potential,
					Club:        p.Club,
					Position:    p.Position,
				})
			}
			return mustJSON(res)
		},
	})
}

// ---------------------------------------------------------------------------
// get_standings
// ---------------------------------------------------------------------------

func registerStandings(srv *mcp.Server, st *store.Store) {
	type args struct {
		Competition string  `json:"competition"`
		Season      flexInt `json:"season"`
	}
	type rowOut struct {
		Position       int    `json:"position"`
		Team           string `json:"team"`
		Points         int    `json:"points"`
		Played         int    `json:"played"`
		Wins           int    `json:"wins"`
		Draws          int    `json:"draws"`
		Losses         int    `json:"losses"`
		GoalsFor       int    `json:"goals_for"`
		GoalsAgainst   int    `json:"goals_against"`
		GoalDifference int    `json:"goal_difference"`
	}
	type out struct {
		Competition string   `json:"competition"`
		Season      int      `json:"season"`
		Standings   []rowOut `json:"standings"`
	}

	srv.AddTool(mcp.Tool{
		Name:        "get_standings",
		Description: "Calculate the final league table (standings) for a competition and season from match results. Position 1 is the champion.",
		InputSchema: schemaObject(map[string]string{
			"competition": "string",
			"season":      "integer",
		}, "season"),
		Handler: func(raw json.RawMessage) (string, error) {
			var a args
			if err := json.Unmarshal(raw, &a); err != nil {
				return "", err
			}
			comp := a.Competition
			if strings.TrimSpace(comp) == "" {
				comp = store.CompBrasileirao
			}
			table := st.Standings(comp, int(a.Season))
			res := out{
				Competition: store.NormalizeCompetition(comp),
				Season:      int(a.Season),
				Standings:   []rowOut{},
			}
			for _, r := range table {
				res.Standings = append(res.Standings, rowOut{
					Position:       r.Position,
					Team:           r.Team,
					Points:         r.Points,
					Played:         r.Played,
					Wins:           r.Wins,
					Draws:          r.Draws,
					Losses:         r.Losses,
					GoalsFor:       r.GoalsFor,
					GoalsAgainst:   r.GoalsAgainst,
					GoalDifference: r.GoalDifference,
				})
			}
			return mustJSON(res)
		},
	})
}

// ---------------------------------------------------------------------------
// league_stats
// ---------------------------------------------------------------------------

func registerLeagueStats(srv *mcp.Server, st *store.Store) {
	type args struct {
		Competition string  `json:"competition"`
		Season      flexInt `json:"season"`
	}
	type bigWin struct {
		Date        string `json:"date"`
		Competition string `json:"competition"`
		HomeTeam    string `json:"home_team"`
		AwayTeam    string `json:"away_team"`
		HomeGoal    int    `json:"home_goal"`
		AwayGoal    int    `json:"away_goal"`
		Margin      int    `json:"margin"`
	}
	type out struct {
		Competition      string   `json:"competition,omitempty"`
		Season           int      `json:"season,omitempty"`
		TotalMatches     int      `json:"total_matches"`
		TotalGoals       int      `json:"total_goals"`
		AvgGoalsPerMatch float64  `json:"avg_goals_per_match"`
		HomeWins         int      `json:"home_wins"`
		AwayWins         int      `json:"away_wins"`
		Draws            int      `json:"draws"`
		HomeWinRate      float64  `json:"home_win_rate"`
		BiggestWins      []bigWin `json:"biggest_wins"`
	}

	srv.AddTool(mcp.Tool{
		Name:        "league_stats",
		Description: "Compute aggregate statistics for a competition/season: total matches and goals, average goals per match, home/away/draw split, home win rate, and the biggest victories.",
		InputSchema: schemaObject(map[string]string{
			"competition": "string",
			"season":      "integer",
		}),
		Handler: func(raw json.RawMessage) (string, error) {
			var a args
			if err := json.Unmarshal(raw, &a); err != nil {
				return "", err
			}
			ls := st.LeagueStats(a.Competition, int(a.Season))
			res := out{
				Season:           int(a.Season),
				TotalMatches:     ls.TotalMatches,
				TotalGoals:       ls.TotalGoals,
				AvgGoalsPerMatch: ls.AvgGoalsPerMatch,
				HomeWins:         ls.HomeWins,
				AwayWins:         ls.AwayWins,
				Draws:            ls.Draws,
				HomeWinRate:      ls.HomeWinRate,
				BiggestWins:      []bigWin{},
			}
			if strings.TrimSpace(a.Competition) != "" {
				res.Competition = store.NormalizeCompetition(a.Competition)
			}
			for _, w := range ls.BiggestWins {
				res.BiggestWins = append(res.BiggestWins, bigWin{
					Date:        w.Match.DateString(),
					Competition: w.Match.Competition,
					HomeTeam:    w.Match.HomeTeam,
					AwayTeam:    w.Match.AwayTeam,
					HomeGoal:    w.Match.HomeGoals,
					AwayGoal:    w.Match.AwayGoals,
					Margin:      w.Margin,
				})
			}
			return mustJSON(res)
		},
	})
}

// ---------------------------------------------------------------------------
// team_rankings
// ---------------------------------------------------------------------------

func registerTeamRankings(srv *mcp.Server, st *store.Store) {
	type args struct {
		Competition string  `json:"competition"`
		Season      flexInt `json:"season"`
		Metric      string  `json:"metric"`
		Venue       string  `json:"venue"`
		Limit       flexInt `json:"limit"`
	}
	type rankOut struct {
		Team  string  `json:"team"`
		Value float64 `json:"value"`
	}
	type out struct {
		Metric   string    `json:"metric"`
		Venue    string    `json:"venue,omitempty"`
		Rankings []rankOut `json:"rankings"`
	}

	srv.AddTool(mcp.Tool{
		Name:        "team_rankings",
		Description: "Rank teams by a metric (goals_for, goals_against, wins, draws, losses, points, win_rate, matches), optionally restricted to a competition, season and venue (home/away). Useful for 'best home/away record' or 'most goals scored'.",
		InputSchema: schemaObject(map[string]string{
			"competition": "string",
			"season":      "integer",
			"metric":      "string",
			"venue":       "string",
			"limit":       "integer",
		}),
		Handler: func(raw json.RawMessage) (string, error) {
			var a args
			if err := json.Unmarshal(raw, &a); err != nil {
				return "", err
			}
			metric := strings.TrimSpace(a.Metric)
			if metric == "" {
				metric = "points"
			}
			ranks := st.TeamRankings(a.Competition, int(a.Season), metric, a.Venue, int(a.Limit))
			res := out{Metric: metric, Venue: strings.TrimSpace(a.Venue), Rankings: []rankOut{}}
			for _, r := range ranks {
				res.Rankings = append(res.Rankings, rankOut{Team: r.Team, Value: r.Value})
			}
			return mustJSON(res)
		},
	})
}
