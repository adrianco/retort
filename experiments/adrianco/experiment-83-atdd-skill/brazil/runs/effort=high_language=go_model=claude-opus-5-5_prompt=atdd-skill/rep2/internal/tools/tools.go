// Package tools defines the MCP tools through which a language model asks
// the Brazilian soccer knowledge base questions.
package tools

import (
	"fmt"
	"strings"
	"time"

	"brsoccer/internal/mcp"
	"brsoccer/internal/soccer"
)

func schema(props map[string]any, required ...string) map[string]any {
	s := map[string]any{"type": "object", "properties": props}
	if len(required) > 0 {
		s["required"] = required
	}
	return s
}

func str(desc string) map[string]any  { return map[string]any{"type": "string", "description": desc} }
func num(desc string) map[string]any  { return map[string]any{"type": "integer", "description": desc} }
func flag(desc string) map[string]any { return map[string]any{"type": "boolean", "description": desc} }
func enum(desc string, values ...string) map[string]any {
	return map[string]any{"type": "string", "description": desc, "enum": values}
}

const (
	teamDesc        = "Club name in any common form, e.g. 'Flamengo', 'Palmeiras-SP', 'Sao Paulo', 'Atlético-MG', 'Sport Club Corinthians Paulista'"
	competitionDesc = "Competition: 'Brasileirão' (Série A), 'Série B', 'Série C', 'Copa do Brasil' or 'Libertadores'. Omit for all."
	seasonDesc      = "Season year, e.g. 2019"
)

// Register adds every tool to the server.
func Register(s *mcp.Server, store *soccer.Store) {
	s.AddTool(mcp.Tool{
		Name: "find_matches",
		Description: "Find matches by team, opponent, competition, season, date range, venue or stage, newest first. " +
			"With both team and opponent it also returns the head-to-head summary. Use limit=1 for the most recent meeting. " +
			"Use stage='final' for finals (e.g. Copa do Brasil finals).",
		InputSchema: schema(map[string]any{
			"team": str(teamDesc), "opponent": str("Second club; only matches between the two. " + teamDesc),
			"competition": str(competitionDesc), "season": num(seasonDesc),
			"date_from": str("Earliest date, YYYY-MM-DD or DD/MM/YYYY"), "date_to": str("Latest date, YYYY-MM-DD or DD/MM/YYYY"),
			"venue": enum("Only the team's home or away matches", "home", "away", "any"),
			"stage": str("Knockout stage: 'final', 'semifinals', 'quarterfinals', 'round of 16', 'group stage' or 'knockout'"),
			"limit": num("Maximum matches to list (default 20)"), "oldest_first": flag("List oldest matches first"),
		}),
		Handler: func(a mcp.Args) (string, any, error) {
			q := soccer.MatchQuery{Team: a.String("team"), Opponent: a.String("opponent"), Stage: a.String("stage"),
				Venue: strings.ToLower(a.String("venue")), Oldest: a.Bool("oldest_first", false)}
			var err error
			if q.Competition, err = competition(a); err != nil {
				return "", nil, err
			}
			if q.Season, err = a.Int("season"); err != nil {
				return "", nil, err
			}
			if q.Limit, err = a.Int("limit"); err != nil {
				return "", nil, err
			}
			if q.From, err = date(a, "date_from"); err != nil {
				return "", nil, err
			}
			if q.To, err = date(a, "date_to"); err != nil {
				return "", nil, err
			}
			ans := store.FindMatches(q)
			return ans.Text(), ans, nil
		},
	})

	s.AddTool(mcp.Tool{
		Name:        "team_record",
		Description: "A club's win/draw/loss record, goals for and against, points and win rate; optionally for one season, competition, and home or away only.",
		InputSchema: schema(map[string]any{
			"team": str(teamDesc), "season": num(seasonDesc), "competition": str(competitionDesc),
			"venue": enum("home, away or all matches (default all)", "home", "away", "all"),
		}, "team"),
		Handler: func(a mcp.Args) (string, any, error) {
			comp, err := competition(a)
			if err != nil {
				return "", nil, err
			}
			season, err := a.Int("season")
			if err != nil {
				return "", nil, err
			}
			ans, err := store.TeamRecord(a.String("team"), comp, season, venue(a))
			return ans.Text(), ans, err
		},
	})

	s.AddTool(mcp.Tool{
		Name:        "head_to_head",
		Description: "Compare two clubs head-to-head: meetings, wins each, draws, goals, recent meetings and biggest wins.",
		InputSchema: schema(map[string]any{
			"team_a": str(teamDesc), "team_b": str(teamDesc), "competition": str(competitionDesc), "season": num(seasonDesc),
		}, "team_a", "team_b"),
		Handler: func(a mcp.Args) (string, any, error) {
			comp, err := competition(a)
			if err != nil {
				return "", nil, err
			}
			season, err := a.Int("season")
			if err != nil {
				return "", nil, err
			}
			ans, err := store.HeadToHead(a.String("team_a"), a.String("team_b"), comp, season)
			return ans.Text(), ans, err
		},
	})

	s.AddTool(mcp.Tool{
		Name: "rank_teams",
		Description: "Rank clubs by a metric over a competition/season/venue: e.g. most goals scored in Série A 2023, best home or away win rate. " +
			"Defaults to the Brasileirão Série A. Use min_matches to ignore clubs with few matches.",
		InputSchema: schema(map[string]any{
			"metric":      enum("What to rank by", "goals_for", "goals_against", "win_rate", "points", "wins", "goal_difference", "points_per_game"),
			"competition": str(competitionDesc + " Use 'all' for every competition."), "season": num(seasonDesc),
			"venue":       enum("home, away or all matches", "home", "away", "all"),
			"min_matches": num("Only clubs with at least this many matches"), "limit": num("How many clubs to list (default 10)"),
		}, "metric"),
		Handler: func(a mcp.Args) (string, any, error) {
			comp := soccer.SerieA
			if c := a.String("competition"); strings.EqualFold(c, "all") {
				comp = ""
			} else if c != "" {
				var err error
				if comp, err = competition(a); err != nil {
					return "", nil, err
				}
			}
			season, err := a.Int("season")
			if err != nil {
				return "", nil, err
			}
			minMatches, _ := a.Int("min_matches")
			limit, _ := a.Int("limit")
			ans, err := store.RankTeams(a.String("metric"), comp, season, venue(a), minMatches, limit)
			return ans.Text(), ans, err
		},
	})

	s.AddTool(mcp.Tool{
		Name:        "team_competitions",
		Description: "Which competitions a club has played in across all the match datasets, with matches, record and seasons for each.",
		InputSchema: schema(map[string]any{"team": str(teamDesc)}, "team"),
		Handler: func(a mcp.Args) (string, any, error) {
			ans, err := store.TeamCompetitions(a.String("team"))
			return ans.Text(), ans, err
		},
	})

	s.AddTool(mcp.Tool{
		Name:        "team_overview",
		Description: "Everything about a club: overall, home and away record, competitions, recent matches, and its squad from the FIFA player ratings.",
		InputSchema: schema(map[string]any{"team": str(teamDesc)}, "team"),
		Handler: func(a mcp.Args) (string, any, error) {
			ans, err := store.TeamOverview(a.String("team"))
			return ans.Text(), ans, err
		},
	})

	s.AddTool(mcp.Tool{
		Name:        "standings",
		Description: "League table for a season calculated from results (3 points per win), with the champion and, for Série A, the relegated bottom four.",
		InputSchema: schema(map[string]any{
			"season": num(seasonDesc + " (default: latest)"), "competition": str("League: 'Brasileirão' (default), 'Série B' or 'Série C'"),
		}),
		Handler: func(a mcp.Args) (string, any, error) {
			comp, err := competition(a)
			if err != nil {
				return "", nil, err
			}
			season, err := a.Int("season")
			if err != nil {
				return "", nil, err
			}
			ans, err := store.Standings(comp, season)
			return ans.Text(), ans, err
		},
	})

	s.AddTool(mcp.Tool{
		Name:        "knockout_bracket",
		Description: "Knockout bracket for a cup season: each stage's ties with aggregate scores and winners. Defaults to the Copa Libertadores.",
		InputSchema: schema(map[string]any{
			"competition": str("'Libertadores' (default) or 'Copa do Brasil'"), "season": num(seasonDesc),
		}),
		Handler: func(a mcp.Args) (string, any, error) {
			comp, err := competition(a)
			if err != nil {
				return "", nil, err
			}
			season, err := a.Int("season")
			if err != nil {
				return "", nil, err
			}
			ans, err := store.Bracket(comp, season)
			return ans.Text(), ans, err
		},
	})

	s.AddTool(mcp.Tool{
		Name:        "competition_stats",
		Description: "Aggregate statistics: matches, goals, average goals per match, home/draw/away win rates for a competition and/or season.",
		InputSchema: schema(map[string]any{"competition": str(competitionDesc), "season": num(seasonDesc)}),
		Handler: func(a mcp.Args) (string, any, error) {
			comp, err := competition(a)
			if err != nil {
				return "", nil, err
			}
			season, err := a.Int("season")
			if err != nil {
				return "", nil, err
			}
			ans := store.CompetitionStats(comp, season)
			return ans.Text(), ans, nil
		},
	})

	s.AddTool(mcp.Tool{
		Name:        "compare_seasons",
		Description: "Compare seasons of a competition side by side: goals per match, home advantage, champion and top-scoring team.",
		InputSchema: schema(map[string]any{
			"seasons":     map[string]any{"type": "array", "items": map[string]any{"type": "integer"}, "description": "Season years, e.g. [2018, 2019]"},
			"competition": str("Default 'Brasileirão'"),
		}, "seasons"),
		Handler: func(a mcp.Args) (string, any, error) {
			comp, err := competition(a)
			if err != nil {
				return "", nil, err
			}
			seasons, err := a.Ints("seasons")
			if err != nil {
				return "", nil, err
			}
			if len(seasons) == 0 {
				return "", nil, fmt.Errorf("name at least one season to compare")
			}
			ans := store.CompareSeasons(comp, seasons)
			return ans.Text(), ans, nil
		},
	})

	s.AddTool(mcp.Tool{
		Name:        "biggest_wins",
		Description: "The biggest victories by goal margin, optionally for a competition, season or club.",
		InputSchema: schema(map[string]any{
			"competition": str(competitionDesc), "season": num(seasonDesc), "team": str("Only this club's wins. " + teamDesc),
			"limit": num("How many (default 10)"),
		}),
		Handler: func(a mcp.Args) (string, any, error) {
			comp, err := competition(a)
			if err != nil {
				return "", nil, err
			}
			season, err := a.Int("season")
			if err != nil {
				return "", nil, err
			}
			limit, _ := a.Int("limit")
			ans, err := store.BiggestWins(comp, season, a.String("team"), limit)
			return ans.Text(), ans, err
		},
	})

	s.AddTool(mcp.Tool{
		Name:        "derbies",
		Description: "Matches between traditional rivals (Fla-Flu, Grenal, Derby Paulista, Clássico Mineiro, Ba-Vi, Atletiba...), optionally for a season, competition or club.",
		InputSchema: schema(map[string]any{"season": num(seasonDesc), "competition": str(competitionDesc), "team": str(teamDesc)}),
		Handler: func(a mcp.Args) (string, any, error) {
			comp, err := competition(a)
			if err != nil {
				return "", nil, err
			}
			season, err := a.Int("season")
			if err != nil {
				return "", nil, err
			}
			ans := store.Derbies(comp, season, a.String("team"))
			return ans.Text(), ans, nil
		},
	})

	s.AddTool(mcp.Tool{
		Name: "search_players",
		Description: "Search the FIFA player ratings by name, nationality, club, position and minimum rating; best rated first. " +
			"Position may be a code (ST, CAM, GK) or a group: forward, striker, winger, midfielder, defender, goalkeeper. " +
			"When no name matches, similar players are suggested.",
		InputSchema: schema(map[string]any{
			"name": str("Player name or part of it, accents optional"), "nationality": str("Country, e.g. 'Brazil' or 'Brazilian'"),
			"club": str("Club name, e.g. 'Santos', 'Grêmio'"), "position": str("Position code or group"),
			"min_overall": num("Minimum overall rating"), "limit": num("How many to list (default 25)"),
		}),
		Handler: func(a mcp.Args) (string, any, error) {
			minOverall, err := a.Int("min_overall")
			if err != nil {
				return "", nil, err
			}
			limit, err := a.Int("limit")
			if err != nil {
				return "", nil, err
			}
			ans := store.SearchPlayers(soccer.PlayerQuery{Name: a.String("name"), Nationality: a.String("nationality"),
				Club: a.String("club"), Position: a.String("position"), MinOverall: minOverall, Limit: limit})
			return ans.Text(), ans, nil
		},
	})

	s.AddTool(mcp.Tool{
		Name: "players_by_club",
		Description: "Count players per club with their average rating, e.g. Brazilian players at Brazilian clubs. " +
			"Brazilian clubs are those that have played in the Brasileirão Série A in the match data.",
		InputSchema: schema(map[string]any{
			"nationality":          str("Only players of this nationality (default Brazil; empty string for all)"),
			"brazilian_clubs_only": flag("Only clubs that played in the Brasileirão Série A (default true)"),
			"limit":                num("How many clubs to list"),
		}),
		Handler: func(a mcp.Args) (string, any, error) {
			nat := "Brazil"
			if _, given := a["nationality"]; given {
				nat = a.String("nationality")
			}
			limit, _ := a.Int("limit")
			ans := store.PlayersByClub(nat, a.Bool("brazilian_clubs_only", true), limit)
			return ans.Text(), ans, nil
		},
	})

	s.AddTool(mcp.Tool{
		Name:        "list_datasets",
		Description: "Which datasets are loaded, how many records each holds, and what they cover.",
		InputSchema: schema(map[string]any{}),
		Handler: func(a mcp.Args) (string, any, error) {
			ans := map[string]any{"datasets": store.Datasets, "matches": len(store.Matches),
				"fixtures_without_score": store.Unplayed, "players": len(store.Players)}
			return soccer.DatasetsText(store.Datasets, len(store.Matches), store.Unplayed, len(store.Players)), ans, nil
		},
	})
}

func competition(a mcp.Args) (string, error) {
	c := a.String("competition")
	if c == "" || strings.EqualFold(c, "all") {
		return "", nil
	}
	if parsed := soccer.ParseCompetition(c); parsed != "" {
		return parsed, nil
	}
	return "", fmt.Errorf("unknown competition %q; use Brasileirão, Série B, Série C, Copa do Brasil or Libertadores", c)
}

func venue(a mcp.Args) string {
	v := strings.ToLower(a.String("venue"))
	if v == "home" || v == "away" {
		return v
	}
	return "all"
}

func date(a mcp.Args, key string) (time.Time, error) {
	s := a.String(key)
	if s == "" {
		return time.Time{}, nil
	}
	if len(s) == 4 { // a bare year
		s += "-01-01"
		if key == "date_to" {
			s = s[:4] + "-12-31"
		}
	}
	t, ok := soccer.ParseDate(s)
	if !ok {
		return time.Time{}, fmt.Errorf("%s %q is not a date; use YYYY-MM-DD", key, a.String(key))
	}
	return t, nil
}
