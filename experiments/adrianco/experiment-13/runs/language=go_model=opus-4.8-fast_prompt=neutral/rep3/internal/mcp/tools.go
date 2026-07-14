// tools.go defines the MCP tools exposed by the server and the argument
// parsing + answer formatting that bridges JSON-RPC calls to the soccer engine.
package mcp

import (
	"fmt"
	"strings"
	"time"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/soccer"
)

// arg helpers tolerate the loose JSON typing produced by LLM clients.

func argStr(a map[string]interface{}, key string) string {
	if v, ok := a[key]; ok {
		if s, ok := v.(string); ok {
			return strings.TrimSpace(s)
		}
		if v != nil {
			return strings.TrimSpace(fmt.Sprintf("%v", v))
		}
	}
	return ""
}

func argInt(a map[string]interface{}, key string) int {
	switch v := a[key].(type) {
	case float64:
		return int(v)
	case int:
		return v
	case string:
		var n int
		s := strings.TrimSpace(v)
		if s == "" {
			return 0
		}
		fmt.Sscanf(s, "%d", &n)
		return n
	}
	return 0
}

func argBool(a map[string]interface{}, key string) bool {
	switch v := a[key].(type) {
	case bool:
		return v
	case string:
		return strings.EqualFold(v, "true") || v == "1"
	}
	return false
}

func parseArgDate(s string) time.Time {
	for _, l := range []string{"2006-01-02", "2006-01-02 15:04:05", "02/01/2006"} {
		if t, err := time.Parse(l, strings.TrimSpace(s)); err == nil {
			return t
		}
	}
	return time.Time{}
}

func obj(props map[string]interface{}, required ...string) map[string]interface{} {
	schema := map[string]interface{}{
		"type":       "object",
		"properties": props,
	}
	if len(required) > 0 {
		schema["required"] = required
	}
	return schema
}

func prop(typ, desc string) map[string]interface{} {
	return map[string]interface{}{"type": typ, "description": desc}
}

// registerTools defines every tool the server exposes.
func (s *Server) registerTools() {
	db := s.db

	s.addTool(Tool{
		Name: "search_matches",
		Description: "Search Brazilian soccer matches by team, opponent, competition, " +
			"season and/or date range. Returns matches most-recent first. Use this for " +
			"questions like 'Show me all Flamengo vs Fluminense matches' or 'What matches " +
			"did Palmeiras play in 2023?'.",
		InputSchema: obj(map[string]interface{}{
			"team":        prop("string", "Team name (matches home or away side). Variations like 'Palmeiras' or 'Palmeiras-SP' work."),
			"opponent":    prop("string", "Optional second team to find head-to-head fixtures."),
			"competition": prop("string", "Optional competition filter: Brasileirão, Copa do Brasil, Libertadores, Serie B, Serie C."),
			"season":      prop("integer", "Optional season/year, e.g. 2019."),
			"home_only":   prop("boolean", "Restrict 'team' to matches it played at home."),
			"away_only":   prop("boolean", "Restrict 'team' to matches it played away."),
			"start_date":  prop("string", "Optional start of date range (YYYY-MM-DD)."),
			"end_date":    prop("string", "Optional end of date range (YYYY-MM-DD)."),
			"limit":       prop("integer", "Maximum matches to return (default 20)."),
		}),
		handler: func(a map[string]interface{}) (string, error) {
			limit := argInt(a, "limit")
			if limit <= 0 {
				limit = 20
			}
			f := soccer.MatchFilter{
				Team:        argStr(a, "team"),
				Opponent:    argStr(a, "opponent"),
				Competition: argStr(a, "competition"),
				Season:      argInt(a, "season"),
				HomeOnly:    argBool(a, "home_only"),
				AwayOnly:    argBool(a, "away_only"),
				Start:       parseArgDate(argStr(a, "start_date")),
				End:         parseArgDate(argStr(a, "end_date")),
			}
			if f.Team == "" && f.Opponent == "" && f.Competition == "" && f.Season == 0 {
				return "", fmt.Errorf("provide at least one of: team, opponent, competition, season")
			}
			// Find all (no limit) to report the true total, then trim.
			all := db.FindMatches(f)
			total := len(all)
			shown := all
			if len(shown) > limit {
				shown = shown[:limit]
			}
			header := describeSearch(f)
			return db.FormatMatches(header, shown, total), nil
		},
	})

	s.addTool(Tool{
		Name: "head_to_head",
		Description: "Compare two teams head-to-head: total wins, draws and goals plus the " +
			"list of matches between them. Use for 'Compare Palmeiras and Santos head-to-head'.",
		InputSchema: obj(map[string]interface{}{
			"team_a": prop("string", "First team."),
			"team_b": prop("string", "Second team."),
			"limit":  prop("integer", "Maximum matches to list (default 20)."),
		}, "team_a", "team_b"),
		handler: func(a map[string]interface{}) (string, error) {
			ta, tb := argStr(a, "team_a"), argStr(a, "team_b")
			if ta == "" || tb == "" {
				return "", fmt.Errorf("both team_a and team_b are required")
			}
			limit := argInt(a, "limit")
			if limit <= 0 {
				limit = 20
			}
			return db.FormatH2H(db.HeadToHead(ta, tb), limit), nil
		},
	})

	s.addTool(Tool{
		Name: "team_record",
		Description: "Win/draw/loss record, goals and points for a team, optionally filtered " +
			"by season, competition and home/away. Use for 'What is Corinthians' home record in 2022?'.",
		InputSchema: obj(map[string]interface{}{
			"team":        prop("string", "Team name."),
			"season":      prop("integer", "Optional season/year."),
			"competition": prop("string", "Optional competition filter."),
			"home_only":   prop("boolean", "Only count home matches."),
			"away_only":   prop("boolean", "Only count away matches."),
		}, "team"),
		handler: func(a map[string]interface{}) (string, error) {
			team := argStr(a, "team")
			if team == "" {
				return "", fmt.Errorf("team is required")
			}
			f := soccer.MatchFilter{
				Team:        team,
				Season:      argInt(a, "season"),
				Competition: argStr(a, "competition"),
				HomeOnly:    argBool(a, "home_only"),
				AwayOnly:    argBool(a, "away_only"),
			}
			rec := db.TeamRecord(f)
			if rec.Played == 0 {
				return fmt.Sprintf("No matches with known scores found for %q under the given filters.", team), nil
			}
			return db.FormatRecord(describeRecord(f), rec), nil
		},
	})

	s.addTool(Tool{
		Name: "standings",
		Description: "Compute the league table for a competition and season from match results. " +
			"Use for 'Who won the 2019 Brasileirão?' or 'Which teams were relegated in 2020?'.",
		InputSchema: obj(map[string]interface{}{
			"competition": prop("string", "Competition name (default Brasileirão Série A)."),
			"season":      prop("integer", "Season/year, e.g. 2019."),
			"limit":       prop("integer", "Number of table rows to return (default all)."),
		}, "season"),
		handler: func(a map[string]interface{}) (string, error) {
			season := argInt(a, "season")
			if season == 0 {
				return "", fmt.Errorf("season is required")
			}
			comp := argStr(a, "competition")
			if comp == "" {
				comp = soccer.CompBrasileiraoA
			} else {
				comp = soccer.NormalizeCompetition(comp)
			}
			table := db.Standings(comp, season)
			return db.FormatStandings(comp, season, table, argInt(a, "limit")), nil
		},
	})

	s.addTool(Tool{
		Name: "search_players",
		Description: "Search the FIFA player database by name, nationality, club, position and/or " +
			"minimum overall rating; results are sorted by rating. Use for 'Find all Brazilian " +
			"players', 'Who are the highest-rated players at Flamengo?' or 'Who is Gabriel Barbosa?'.",
		InputSchema: obj(map[string]interface{}{
			"name":        prop("string", "Player name (substring match)."),
			"nationality": prop("string", "Nationality filter, e.g. Brazil."),
			"club":        prop("string", "Club filter (substring), e.g. Flamengo."),
			"position":    prop("string", "Position filter, e.g. ST, GK, LW."),
			"min_overall": prop("integer", "Minimum FIFA overall rating."),
			"limit":       prop("integer", "Maximum players to return (default 15)."),
		}),
		handler: func(a map[string]interface{}) (string, error) {
			f := soccer.PlayerFilter{
				Name:        argStr(a, "name"),
				Nationality: argStr(a, "nationality"),
				Club:        argStr(a, "club"),
				Position:    argStr(a, "position"),
				MinOverall:  argInt(a, "min_overall"),
			}
			if f.Name == "" && f.Nationality == "" && f.Club == "" && f.Position == "" && f.MinOverall == 0 {
				return "", fmt.Errorf("provide at least one of: name, nationality, club, position, min_overall")
			}
			limit := argInt(a, "limit")
			if limit <= 0 {
				limit = 15
			}
			all := db.SearchPlayers(f)
			total := len(all)
			shown := all
			if len(shown) > limit {
				shown = shown[:limit]
			}
			return db.FormatPlayers(describePlayerSearch(f), shown, total), nil
		},
	})

	s.addTool(Tool{
		Name: "competition_stats",
		Description: "Aggregate statistics for a competition (and optional season): matches, total " +
			"goals, average goals per match, home/away win rates and biggest victories. Use for " +
			"'What's the average goals per match in the Brasileirão?' or 'Show me the biggest wins'.",
		InputSchema: obj(map[string]interface{}{
			"competition": prop("string", "Competition filter (omit for all competitions)."),
			"season":      prop("integer", "Optional season/year (omit for all seasons)."),
			"top_n":       prop("integer", "How many biggest victories to list (default 5)."),
		}),
		handler: func(a map[string]interface{}) (string, error) {
			comp := argStr(a, "competition")
			if comp != "" {
				comp = soccer.NormalizeCompetition(comp)
			}
			topN := argInt(a, "top_n")
			if topN <= 0 {
				topN = 5
			}
			s := db.CompetitionStats(comp, argInt(a, "season"), topN)
			if s.Matches == 0 {
				return "No matches with known scores found for the given filters.", nil
			}
			return db.FormatStats(s), nil
		},
	})

	s.addTool(Tool{
		Name:        "list_competitions",
		Description: "List the competitions available in the dataset (use to discover valid competition filters).",
		InputSchema: obj(map[string]interface{}{}),
		handler: func(a map[string]interface{}) (string, error) {
			comps := db.Competitions()
			var b strings.Builder
			fmt.Fprintf(&b, "Competitions in dataset (%d matches, %d teams, %d players):\n",
				len(db.Matches), db.TeamCount(), len(db.Players))
			for _, c := range comps {
				fmt.Fprintf(&b, "- %s\n", c)
			}
			return strings.TrimRight(b.String(), "\n"), nil
		},
	})
}

func describeSearch(f soccer.MatchFilter) string {
	var parts []string
	if f.Team != "" {
		t := f.Team
		switch {
		case f.HomeOnly:
			t += " (home)"
		case f.AwayOnly:
			t += " (away)"
		}
		parts = append(parts, t)
	}
	if f.Opponent != "" {
		parts = append(parts, "vs "+f.Opponent)
	}
	if f.Competition != "" {
		parts = append(parts, "in "+f.Competition)
	}
	if f.Season != 0 {
		parts = append(parts, fmt.Sprintf("season %d", f.Season))
	}
	if parts == nil {
		return "Matches:"
	}
	return "Matches — " + strings.Join(parts, " ") + ":"
}

func describeRecord(f soccer.MatchFilter) string {
	title := f.Team + " record"
	var qual []string
	if f.HomeOnly {
		qual = append(qual, "home")
	}
	if f.AwayOnly {
		qual = append(qual, "away")
	}
	if f.Competition != "" {
		qual = append(qual, f.Competition)
	}
	if f.Season != 0 {
		qual = append(qual, fmt.Sprintf("%d", f.Season))
	}
	if len(qual) > 0 {
		title += " (" + strings.Join(qual, ", ") + ")"
	}
	return title
}

func describePlayerSearch(f soccer.PlayerFilter) string {
	var parts []string
	if f.Name != "" {
		parts = append(parts, fmt.Sprintf("name~%q", f.Name))
	}
	if f.Nationality != "" {
		parts = append(parts, f.Nationality)
	}
	if f.Club != "" {
		parts = append(parts, "at "+f.Club)
	}
	if f.Position != "" {
		parts = append(parts, "position "+f.Position)
	}
	if f.MinOverall != 0 {
		parts = append(parts, fmt.Sprintf("overall>=%d", f.MinOverall))
	}
	if parts == nil {
		return "Players:"
	}
	return "Players — " + strings.Join(parts, ", ") + ":"
}
