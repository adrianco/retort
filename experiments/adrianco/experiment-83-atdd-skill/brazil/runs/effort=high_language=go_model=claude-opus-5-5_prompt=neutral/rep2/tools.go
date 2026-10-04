// MCP tool definitions. Each tool validates its arguments, runs queries
// against the Store and returns a human-readable text answer that an LLM can
// relay directly or summarise.
package main

import (
	"fmt"
	"math"
	"sort"
	"strconv"
	"strings"
	"time"
)

// Args are the JSON arguments of a tools/call request.
type Args map[string]any

// Str returns a string argument (numbers are formatted).
func (a Args) Str(k string) string {
	switch v := a[k].(type) {
	case string:
		return strings.TrimSpace(v)
	case float64:
		return strconv.FormatFloat(v, 'f', -1, 64)
	case int:
		return strconv.Itoa(v)
	case bool:
		return strconv.FormatBool(v)
	}
	return ""
}

// Int returns an integer argument, 0 when absent.
func (a Args) Int(k string) (int, error) {
	switch v := a[k].(type) {
	case nil:
		return 0, nil
	case float64:
		if v != math.Trunc(v) {
			return 0, fmt.Errorf("%s must be an integer", k)
		}
		return int(v), nil
	case int:
		return v, nil
	case string:
		if strings.TrimSpace(v) == "" {
			return 0, nil
		}
		n, err := strconv.Atoi(strings.TrimSpace(v))
		if err != nil {
			return 0, fmt.Errorf("%s must be an integer, got %q", k, v)
		}
		return n, nil
	}
	return 0, fmt.Errorf("%s must be an integer", k)
}

// Bool returns a boolean argument with a default.
func (a Args) Bool(k string, def bool) bool {
	switch v := a[k].(type) {
	case bool:
		return v
	case string:
		if b, err := strconv.ParseBool(v); err == nil {
			return b
		}
	}
	return def
}

// Tool is an MCP tool.
type Tool struct {
	Name        string
	Description string
	InputSchema map[string]any
	Handler     func(s *Store, a Args) (string, error)
}

// schema property helpers
func pStr(desc string) map[string]any { return map[string]any{"type": "string", "description": desc} }
func pInt(desc string) map[string]any { return map[string]any{"type": "integer", "description": desc} }
func pEnum(desc string, vals ...string) map[string]any {
	return map[string]any{"type": "string", "description": desc, "enum": vals}
}

func obj(props map[string]any, required ...string) map[string]any {
	o := map[string]any{"type": "object", "properties": props}
	if len(required) > 0 {
		o["required"] = required
	}
	return o
}

const compDesc = "Competition: 'Brasileirão' / 'Serie A', 'Serie B', 'Serie C', 'Copa do Brasil' or 'Libertadores'. Omit for all."

func matchFilterProps() map[string]any {
	return map[string]any{
		"team":        pStr("Team name in any spelling, e.g. 'Flamengo', 'Palmeiras-SP', 'São Paulo FC'"),
		"opponent":    pStr("Only matches against this opponent"),
		"venue":       pEnum("Venue relative to 'team'", "home", "away", "any"),
		"competition": pStr(compDesc),
		"season":      pInt("Season year, e.g. 2019"),
		"season_from": pInt("First season (inclusive)"),
		"season_to":   pInt("Last season (inclusive)"),
		"date_from":   pStr("Earliest date, YYYY-MM-DD or DD/MM/YYYY"),
		"date_to":     pStr("Latest date, YYYY-MM-DD or DD/MM/YYYY"),
		"stage":       pStr("Cup stage: 'final', 'semifinals', 'quarterfinals', 'round of 16', 'group stage'"),
	}
}

// Tools returns all tools exposed by the server.
func Tools() []Tool {
	searchProps := matchFilterProps()
	searchProps["limit"] = pInt("Maximum matches to list (default 25)")
	searchProps["order"] = pEnum("Sort order (default recent first)", "recent", "oldest")
	return []Tool{
		{
			Name: "search_matches",
			Description: "Find matches across all match datasets (Brasileirão 2003-2023, Série B/C, Copa do Brasil, Libertadores) " +
				"by team, opponent, venue, competition, season, date range or cup stage. Returns scores plus the team's record in the selection. " +
				"Use for 'Show me all Flamengo vs Fluminense matches', 'What matches did Palmeiras play in 2023?', 'When did Flamengo last play Corinthians?'.",
			InputSchema: obj(searchProps),
			Handler:     toolSearchMatches,
		},
		{
			Name:        "head_to_head",
			Description: "Head-to-head record between two teams: wins/draws/goals, breakdown by competition, recent meetings and biggest wins. Recognises classic derbies (Fla-Flu, Grenal, Derby Paulista...).",
			InputSchema: obj(map[string]any{
				"team_a": pStr("First team"), "team_b": pStr("Second team"), "competition": pStr(compDesc),
				"season_from": pInt("First season"), "season_to": pInt("Last season"), "limit": pInt("Recent meetings to list (default 10)"),
			}, "team_a", "team_b"),
			Handler: toolHeadToHead,
		},
		{
			Name:        "team_record",
			Description: "Win/draw/loss record, goals for/against, win rate and points for a team, optionally filtered by season, competition and home/away. Use for 'What is Corinthians' home record in 2022?'.",
			InputSchema: obj(map[string]any{
				"team": pStr("Team name"), "season": pInt("Season year"), "season_from": pInt("First season"), "season_to": pInt("Last season"),
				"competition": pStr(compDesc), "venue": pEnum("Home or away only", "home", "away", "any"),
			}, "team"),
			Handler: toolTeamRecord,
		},
		{
			Name:        "team_overview",
			Description: "Profile of a club combining all files: name variants, competitions and seasons played with records, Série A finishing positions, home/away split, biggest wins, rivals and FIFA squad (cross-file). Use for 'What competitions has Palmeiras played in?'.",
			InputSchema: obj(map[string]any{"team": pStr("Team name")}, "team"),
			Handler:     toolTeamOverview,
		},
		{
			Name:        "standings",
			Description: "League table for a season calculated from match results (3 pts win, tie-breakers wins, goal difference, goals). Marks champion and relegated clubs. Use for 'Who won the 2019 Brasileirão?' or 'Which teams were relegated in 2020?'.",
			InputSchema: obj(map[string]any{
				"season": pInt("Season year (2003-2023 for Série A)"), "competition": pStr("League: Serie A (default), Serie B or Serie C"),
				"top": pInt("Only show the first N rows (default all)"),
			}, "season"),
			Handler: toolStandings,
		},
		{
			Name: "team_rankings",
			Description: "Rank teams by a statistic over a selection of matches: points, wins, goals_for, goals_against (fewest first), goal_difference, win_rate, points_rate, clean_sheets, goals_per_match. " +
				"Use for 'Which team scored the most goals in Serie A 2023?', 'Which team has the best home/away record?'.",
			InputSchema: obj(map[string]any{
				"metric":      pEnum("Statistic to rank by", "points", "wins", "goals_for", "goals_against", "goal_difference", "win_rate", "points_rate", "clean_sheets", "goals_per_match", "losses", "draws"),
				"competition": pStr(compDesc), "season": pInt("Season year"), "season_from": pInt("First season"), "season_to": pInt("Last season"),
				"venue":       pEnum("Count only home or away matches", "home", "away", "any"),
				"min_matches": pInt("Minimum matches to qualify (default 10 for one season, 50 otherwise)"),
				"order":       pEnum("Override sort direction", "desc", "asc"), "limit": pInt("Rows to show (default 10)"),
			}, "metric"),
			Handler: toolTeamRankings,
		},
		{
			Name:        "league_stats",
			Description: "Aggregate statistics: matches, average goals per match, home/draw/away win rates, common scorelines, highest-scoring match, corners/shots where available. Use for 'What's the average goals per match in the Brasileirão?'.",
			InputSchema: obj(map[string]any{
				"competition": pStr(compDesc), "season": pInt("Season year"), "season_from": pInt("First season"), "season_to": pInt("Last season"),
			}),
			Handler: toolLeagueStats,
		},
		{
			Name:        "compare_seasons",
			Description: "Compare two or more seasons of a competition side by side (goals per match, home win rate, champion, best attack/defence). Use for 'Compare the 2018 and 2019 seasons'.",
			InputSchema: obj(map[string]any{
				"seasons":     pStr("Comma-separated seasons, e.g. '2018,2019'"),
				"competition": pStr("Competition (default Serie A)"),
			}, "seasons"),
			Handler: toolCompareSeasons,
		},
		{
			Name:        "biggest_wins",
			Description: "Largest victories (by goal margin) or highest-scoring matches, optionally filtered by competition, season or team. Use for 'Show me the biggest wins in the dataset'.",
			InputSchema: obj(map[string]any{
				"competition": pStr(compDesc), "season": pInt("Season year"), "season_from": pInt("First season"), "season_to": pInt("Last season"),
				"team":    pStr("Only matches involving this team"),
				"sort_by": pEnum("Rank by goal margin (default) or total goals", "margin", "total_goals"),
				"limit":   pInt("Rows to show (default 10)"),
			}),
			Handler: toolBiggestWins,
		},
		{
			Name:        "knockout_matches",
			Description: "Knockout ties for Copa do Brasil or Copa Libertadores grouped by stage with aggregate scores (bracket view). Use for 'Find all Copa do Brasil finals' (stage=final, no season) or 'Show the 2018 Copa Libertadores bracket'.",
			InputSchema: obj(map[string]any{
				"competition": pStr("'Copa do Brasil' or 'Libertadores'"), "season": pInt("Season year (omit for all seasons)"),
				"stage": pStr("Only this stage: final, semifinals, quarterfinals, round of 16, group stage"),
				"team":  pStr("Only ties involving this team"),
			}, "competition"),
			Handler: toolKnockout,
		},
		{
			Name:        "find_derbies",
			Description: "Matches between traditional rivals (Fla-Flu, Derby Paulista, Grenal, Clássico Mineiro, Ba-Vi, Atletiba, Choque-Rei, Majestoso, ...) with a summary per derby. Use for 'Show me all derbies in 2023'.",
			InputSchema: obj(map[string]any{
				"season": pInt("Season year"), "competition": pStr(compDesc), "team": pStr("Only derbies involving this team"),
				"derby": pStr("Derby name filter, e.g. 'Grenal'"), "limit": pInt("Matches to list (default 30)"),
			}),
			Handler: toolDerbies,
		},
		{
			Name:        "search_players",
			Description: "Search the FIFA 19 player database (18,207 players) by name, nationality (e.g. 'Brazil' or 'Brazilian'), club, position (code like ST/GK or group like 'forwards', 'defenders'), minimum rating and age. Sorted by overall rating. Nationality Brazil also summarises Brazilian players at Brazilian clubs.",
			InputSchema: obj(map[string]any{
				"name": pStr("Name or part of it"), "nationality": pStr("Country or demonym"), "club": pStr("Club name"),
				"position": pStr("Position code(s) or group"), "min_overall": pInt("Minimum overall rating"), "max_age": pInt("Maximum age"),
				"sort_by": pEnum("Sort order (default overall)", "overall", "potential", "age", "name"),
				"limit":   pInt("Players to list (default 20)"),
			}),
			Handler: toolSearchPlayers,
		},
		{
			Name:        "get_player",
			Description: "Detailed FIFA profile for a player (ratings, position, club, contract, top attributes) plus, for Brazilian clubs, the club's record in the match data. Use for 'Who is Gabriel Jesus?'.",
			InputSchema: obj(map[string]any{"name": pStr("Player name")}, "name"),
			Handler:     toolGetPlayer,
		},
		{
			Name:        "club_squads",
			Description: "FIFA squads of Brazilian clubs that also appear in the match data: player counts, average rating and best player per club, optionally only players of one nationality.",
			InputSchema: obj(map[string]any{"nationality": pStr("Only count players of this nationality, e.g. 'Brazil'")}),
			Handler:     toolClubSquads,
		},
		{
			Name:        "list_teams",
			Description: "Search team names and show the canonical name, spelling variants found in the files and number of matches. Useful to check how a name is normalised.",
			InputSchema: obj(map[string]any{"query": pStr("Part of a team name (omit to list the most frequent teams)"), "competition": pStr(compDesc), "limit": pInt("Rows (default 30)")}),
			Handler:     toolListTeams,
		},
		{
			Name:        "dataset_info",
			Description: "Describe the loaded datasets: files, rows, de-duplication, coverage per competition and season.",
			InputSchema: obj(map[string]any{}),
			Handler:     toolDatasetInfo,
		},
	}
}

// ---------- shared helpers ----------

func (s *Store) optTeam(a Args, k string) (*Team, error) {
	if a.Str(k) == "" {
		return nil, nil
	}
	return s.ResolveTeam(a.Str(k))
}

func optDate(a Args, k string) (time.Time, error) {
	if a.Str(k) == "" {
		return time.Time{}, nil
	}
	t, _, err := parseDate(a.Str(k))
	if err != nil {
		return t, fmt.Errorf("%s: %w", k, err)
	}
	return truncDay(t), nil
}

func (s *Store) filterFromArgs(a Args) (MatchFilter, error) {
	var f MatchFilter
	var err error
	if f.Team, err = s.optTeam(a, "team"); err != nil {
		return f, err
	}
	if f.Opponent, err = s.optTeam(a, "opponent"); err != nil {
		return f, err
	}
	if f.Competition, err = normalizeCompetition(a.Str("competition")); err != nil {
		return f, err
	}
	for k, dst := range map[string]*int{"season": &f.Season, "season_from": &f.SeasonFrom, "season_to": &f.SeasonTo} {
		if *dst, err = a.Int(k); err != nil {
			return f, err
		}
	}
	if f.DateFrom, err = optDate(a, "date_from"); err != nil {
		return f, err
	}
	if f.DateTo, err = optDate(a, "date_to"); err != nil {
		return f, err
	}
	switch v := strings.ToLower(a.Str("venue")); v {
	case "", "any", "all", "both":
	case "home", "away":
		if f.Team == nil {
			return f, fmt.Errorf("venue requires a team")
		}
		f.Venue = v
	default:
		return f, fmt.Errorf("venue must be home, away or any")
	}
	f.Stage = normalizeStage(a.Str("stage"))
	return f, nil
}

func describeFilter(f MatchFilter) string {
	var parts []string
	if f.Team != nil {
		t := f.Team.Name
		if f.Venue != "" {
			t += " (" + f.Venue + ")"
		}
		parts = append(parts, t)
	}
	if f.Opponent != nil {
		parts = append(parts, "vs "+f.Opponent.Name)
	}
	if f.Competition != "" {
		parts = append(parts, f.Competition)
	}
	if f.Season != 0 {
		parts = append(parts, "season "+strconv.Itoa(f.Season))
	}
	if f.SeasonFrom != 0 || f.SeasonTo != 0 {
		parts = append(parts, fmt.Sprintf("seasons %s-%s", yearOr(f.SeasonFrom, "…"), yearOr(f.SeasonTo, "…")))
	}
	if !f.DateFrom.IsZero() {
		parts = append(parts, "from "+f.DateFrom.Format("2006-01-02"))
	}
	if !f.DateTo.IsZero() {
		parts = append(parts, "to "+f.DateTo.Format("2006-01-02"))
	}
	if f.Stage != "" {
		parts = append(parts, "stage "+f.Stage)
	}
	if len(parts) == 0 {
		return "all matches"
	}
	return strings.Join(parts, ", ")
}

func yearOr(y int, def string) string {
	if y == 0 {
		return def
	}
	return strconv.Itoa(y)
}

// matchContext renders "(Brasileirão Série A 2023, Round 22)".
func matchContext(m *Match) string {
	c := fmt.Sprintf("%s %d", m.Competition, m.Season)
	switch {
	case m.Stage != "":
		c += ", " + m.Stage
	case m.Round != "":
		c += ", Round " + m.Round
	}
	return c
}

// fmtMatch renders "2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Série A 2023, Round 22)".
func fmtMatch(m *Match) string {
	return fmt.Sprintf("%s: %s %d-%d %s (%s)", m.Date.Format("2006-01-02"), m.Home.Name, m.HomeGoals, m.AwayGoals, m.Away.Name, matchContext(m))
}

func fmtRecordLine(r Record) string {
	return fmt.Sprintf("%d matches: %dW %dD %dL, goals %d-%d", r.Played, r.Won, r.Drawn, r.Lost, r.GF, r.GA)
}

func signed(n int) string {
	if n > 0 {
		return "+" + strconv.Itoa(n)
	}
	return strconv.Itoa(n)
}

func limitArg(a Args, def int) (int, error) {
	n, err := a.Int("limit")
	if err != nil {
		return 0, err
	}
	if n <= 0 {
		return def, nil
	}
	return n, nil
}

func reversed(ms []*Match) []*Match {
	out := make([]*Match, len(ms))
	for i, m := range ms {
		out[len(ms)-1-i] = m
	}
	return out
}

func writeMatches(b *strings.Builder, ms []*Match, limit int) {
	for i, m := range ms {
		if i == limit {
			fmt.Fprintf(b, "- ... (%d more matches in dataset)\n", len(ms)-limit)
			break
		}
		fmt.Fprintf(b, "- %s\n", fmtMatch(m))
	}
}

// ---------- match tools ----------

func toolSearchMatches(s *Store, a Args) (string, error) {
	f, err := s.filterFromArgs(a)
	if err != nil {
		return "", err
	}
	limit, err := limitArg(a, 25)
	if err != nil {
		return "", err
	}
	ms := s.FindMatches(f)
	var b strings.Builder
	title := describeFilter(f)
	if d := DerbyName(f.Team, f.Opponent); d != "" {
		title += " (" + d + ")"
	}
	if len(ms) == 0 {
		return fmt.Sprintf("No matches found for %s.", title), nil
	}
	fmt.Fprintf(&b, "%d matches found for %s:\n", len(ms), title)
	if strings.ToLower(a.Str("order")) != "oldest" {
		ms = reversed(ms)
	}
	writeMatches(&b, ms, limit)
	if f.Team != nil {
		r := TeamRecord(f.Team, ms)
		fmt.Fprintf(&b, "\n%s record in these matches: %s (win rate %.1f%%)\n", f.Team.Name, fmtRecordLine(r), r.WinRate())
		if f.Opponent != nil {
			fmt.Fprintf(&b, "Head-to-head in selection: %s %d wins, %s %d wins, %d draws\n", f.Team.Name, r.Won, f.Opponent.Name, r.Lost, r.Drawn)
		}
	}
	return b.String(), nil
}

func toolHeadToHead(s *Store, a Args) (string, error) {
	ta, err := s.ResolveTeam(a.Str("team_a"))
	if err != nil {
		return "", err
	}
	tb, err := s.ResolveTeam(a.Str("team_b"))
	if err != nil {
		return "", err
	}
	if ta == tb {
		return "", fmt.Errorf("team_a and team_b both resolve to %s", ta.Name)
	}
	comp, err := normalizeCompetition(a.Str("competition"))
	if err != nil {
		return "", err
	}
	from, err := a.Int("season_from")
	if err != nil {
		return "", err
	}
	to, err := a.Int("season_to")
	if err != nil {
		return "", err
	}
	limit, err := limitArg(a, 10)
	if err != nil {
		return "", err
	}
	ms := s.FindMatches(MatchFilter{Team: ta, Opponent: tb, Competition: comp, SeasonFrom: from, SeasonTo: to})
	var b strings.Builder
	title := ta.Name + " vs " + tb.Name
	if d := DerbyName(ta, tb); d != "" {
		title += " (" + d + ")"
	}
	if comp != "" {
		title += ", " + comp
	}
	if len(ms) == 0 {
		return fmt.Sprintf("%s: no meetings found in the dataset.", title), nil
	}
	r := TeamRecord(ta, ms)
	fmt.Fprintf(&b, "%s - %d matches in dataset (%s to %s)\n", title, len(ms), ms[0].Date.Format("2006-01-02"), ms[len(ms)-1].Date.Format("2006-01-02"))
	fmt.Fprintf(&b, "Head-to-head in dataset: %s %d wins, %s %d wins, %d draws\n", ta.Name, r.Won, tb.Name, r.Lost, r.Drawn)
	fmt.Fprintf(&b, "Goals: %s %d - %d %s\n", ta.Name, r.GF, r.GA, tb.Name)
	home := TeamRecord(ta, s.FindMatches(MatchFilter{Team: ta, Opponent: tb, Venue: "home", Competition: comp, SeasonFrom: from, SeasonTo: to}))
	away := TeamRecord(ta, s.FindMatches(MatchFilter{Team: ta, Opponent: tb, Venue: "away", Competition: comp, SeasonFrom: from, SeasonTo: to}))
	fmt.Fprintf(&b, "%s at home: %dW %dD %dL | %s away: %dW %dD %dL\n", ta.Name, home.Won, home.Drawn, home.Lost, ta.Name, away.Won, away.Drawn, away.Lost)
	byComp := map[string][]*Match{}
	for _, m := range ms {
		byComp[m.Competition] = append(byComp[m.Competition], m)
	}
	if len(byComp) > 1 {
		b.WriteString("By competition:\n")
		for _, c := range allCompetitions {
			if list := byComp[c]; len(list) > 0 {
				cr := TeamRecord(ta, list)
				fmt.Fprintf(&b, "- %s: %d matches (%s %d wins, %s %d wins, %d draws)\n", c, len(list), ta.Name, cr.Won, tb.Name, cr.Lost, cr.Drawn)
			}
		}
	}
	b.WriteString("Most recent meetings:\n")
	writeMatches(&b, reversed(ms), limit)
	for _, t := range []*Team{ta, tb} {
		var best *Match
		for _, m := range ms {
			if m.Winner() == t && (best == nil || m.Margin() > best.Margin()) {
				best = m
			}
		}
		if best != nil {
			fmt.Fprintf(&b, "Biggest %s win: %s\n", t.Name, fmtMatch(best))
		}
	}
	return b.String(), nil
}

// ---------- team tools ----------

func toolTeamRecord(s *Store, a Args) (string, error) {
	if a.Str("team") == "" {
		return "", fmt.Errorf("team is required")
	}
	f, err := s.filterFromArgs(a)
	if err != nil {
		return "", err
	}
	ms := s.FindMatches(f)
	t := f.Team
	var b strings.Builder
	label := t.Name
	if f.Venue != "" {
		label += " " + f.Venue
	}
	var scope []string
	if f.Season != 0 {
		scope = append(scope, strconv.Itoa(f.Season))
	}
	if f.SeasonFrom != 0 || f.SeasonTo != 0 {
		scope = append(scope, fmt.Sprintf("%s-%s", yearOr(f.SeasonFrom, "…"), yearOr(f.SeasonTo, "…")))
	}
	if f.Competition != "" {
		scope = append(scope, f.Competition)
	} else {
		scope = append(scope, "all competitions")
	}
	fmt.Fprintf(&b, "%s record (%s):\n", label, strings.Join(scope, " "))
	if len(ms) == 0 {
		b.WriteString("- No matches found for this selection.\n")
		return b.String(), nil
	}
	r := TeamRecord(t, ms)
	fmt.Fprintf(&b, "- Matches: %d\n", r.Played)
	fmt.Fprintf(&b, "- Wins: %d, Draws: %d, Losses: %d\n", r.Won, r.Drawn, r.Lost)
	fmt.Fprintf(&b, "- Goals For: %d, Goals Against: %d (GD %s)\n", r.GF, r.GA, signed(r.GD()))
	fmt.Fprintf(&b, "- Win rate: %.1f%%\n", r.WinRate())
	fmt.Fprintf(&b, "- Points: %d (%.1f%% of available), clean sheets: %d\n", r.Points(), r.PointsRate(), r.CleanSheets)
	fmt.Fprintf(&b, "- Goals per match: %.2f scored, %.2f conceded\n", ratio(r.GF, r.Played), ratio(r.GA, r.Played))
	if f.Competition == "" {
		byComp := map[string][]*Match{}
		for _, m := range ms {
			byComp[m.Competition] = append(byComp[m.Competition], m)
		}
		if len(byComp) > 1 {
			b.WriteString("By competition:\n")
			for _, c := range allCompetitions {
				if list := byComp[c]; len(list) > 0 {
					fmt.Fprintf(&b, "- %s: %s\n", c, fmtRecordLine(TeamRecord(t, list)))
				}
			}
		}
	}
	if f.Season == 0 {
		bySeason := map[int][]*Match{}
		for _, m := range ms {
			bySeason[m.Season] = append(bySeason[m.Season], m)
		}
		if len(bySeason) > 1 {
			b.WriteString("By season:\n")
			var years []int
			for y := range bySeason {
				years = append(years, y)
			}
			sort.Ints(years)
			for _, y := range years {
				fmt.Fprintf(&b, "- %d: %s\n", y, fmtRecordLine(TeamRecord(t, bySeason[y])))
			}
		}
	}
	return b.String(), nil
}

// seriesAPosition returns a team's finishing position in a Série A season.
func (s *Store) seriesAPosition(t *Team, season int) (pos, of int) {
	rows, _, _ := s.Standings(CompSerieA, season)
	for i, r := range rows {
		if r.Team == t {
			return i + 1, len(rows)
		}
	}
	return 0, len(rows)
}

func ordinal(n int) string {
	suffix := "th"
	if n%100 < 11 || n%100 > 13 {
		switch n % 10 {
		case 1:
			suffix = "st"
		case 2:
			suffix = "nd"
		case 3:
			suffix = "rd"
		}
	}
	return strconv.Itoa(n) + suffix
}

func toolTeamOverview(s *Store, a Args) (string, error) {
	t, err := s.ResolveTeam(a.Str("team"))
	if err != nil {
		return "", err
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s", t.Name)
	if t.Region != "" {
		fmt.Fprintf(&b, " (%s)", strings.ToUpper(t.Region))
	}
	b.WriteString("\n")
	var variants []string
	for v := range t.Variants {
		variants = append(variants, v)
	}
	sort.Strings(variants)
	fmt.Fprintf(&b, "Name variants in data: %s\n", strings.Join(variants, "; "))
	if len(t.Matches) == 0 {
		b.WriteString("No matches in dataset.\n")
		return b.String(), nil
	}
	total := TeamRecord(t, t.Matches)
	fmt.Fprintf(&b, "Matches in dataset: %d (%s to %s)\n", len(t.Matches), t.Matches[0].Date.Format("2006-01-02"), t.Matches[len(t.Matches)-1].Date.Format("2006-01-02"))
	fmt.Fprintf(&b, "Overall: %s, win rate %.1f%%\n", fmtRecordLine(total), total.WinRate())
	home := TeamRecord(t, s.FindMatches(MatchFilter{Team: t, Venue: "home"}))
	away := TeamRecord(t, s.FindMatches(MatchFilter{Team: t, Venue: "away"}))
	fmt.Fprintf(&b, "Home: %s (win rate %.1f%%)\nAway: %s (win rate %.1f%%)\n", fmtRecordLine(home), home.WinRate(), fmtRecordLine(away), away.WinRate())
	b.WriteString("Competitions played:\n")
	for _, c := range allCompetitions {
		ms := s.FindMatches(MatchFilter{Team: t, Competition: c})
		if len(ms) == 0 {
			continue
		}
		seasons := map[int]bool{}
		for _, m := range ms {
			seasons[m.Season] = true
		}
		var ys []int
		for y := range seasons {
			ys = append(ys, y)
		}
		sort.Ints(ys)
		fmt.Fprintf(&b, "- %s: %s; seasons %s\n", c, fmtRecordLine(TeamRecord(t, ms)), compactYears(ys))
	}
	var finishes []string
	for _, y := range s.Seasons(CompSerieA) {
		if pos, of := s.seriesAPosition(t, y); pos > 0 {
			label := fmt.Sprintf("%d: %s/%d", y, ordinal(pos), of)
			if pos == 1 {
				label += " (champion)"
			}
			finishes = append(finishes, label)
		}
	}
	if len(finishes) > 0 {
		fmt.Fprintf(&b, "Série A finishes (calculated): %s\n", strings.Join(finishes, ", "))
	}
	var best, worst *Match
	for _, m := range t.Matches {
		gf, ga := m.GoalsFor(t)
		if gf > ga && (best == nil || m.Margin() > best.Margin()) {
			best = m
		}
		if ga > gf && (worst == nil || m.Margin() > worst.Margin()) {
			worst = m
		}
	}
	if best != nil {
		fmt.Fprintf(&b, "Biggest win: %s\n", fmtMatch(best))
	}
	if worst != nil {
		fmt.Fprintf(&b, "Heaviest defeat: %s\n", fmtMatch(worst))
	}
	if rivals := s.Rivals(t); len(rivals) > 0 {
		fmt.Fprintf(&b, "Rivals: %s\n", strings.Join(rivals, ", "))
	}
	if len(t.Players) > 0 {
		sum := 0
		for _, p := range t.Players {
			sum += p.Overall
		}
		fmt.Fprintf(&b, "FIFA 19 squad: %d players (avg rating %.1f). Top players:\n", len(t.Players), float64(sum)/float64(len(t.Players)))
		for i, p := range t.Players {
			if i == 5 {
				break
			}
			fmt.Fprintf(&b, "- %s - Overall: %d, Position: %s, Age: %d, Nationality: %s\n", p.Name, p.Overall, p.Position, p.Age, p.Nationality)
		}
	} else {
		b.WriteString("FIFA 19 squad: not present in the FIFA player dataset.\n")
	}
	return b.String(), nil
}

// compactYears renders [2012 2013 2014 2016] as "2012-2014, 2016".
func compactYears(ys []int) string {
	var parts []string
	for i := 0; i < len(ys); {
		j := i
		for j+1 < len(ys) && ys[j+1] == ys[j]+1 {
			j++
		}
		if j > i {
			parts = append(parts, fmt.Sprintf("%d-%d", ys[i], ys[j]))
		} else {
			parts = append(parts, strconv.Itoa(ys[i]))
		}
		i = j + 1
	}
	return strings.Join(parts, ", ")
}

// ---------- competition tools ----------

func toolStandings(s *Store, a Args) (string, error) {
	season, err := a.Int("season")
	if err != nil {
		return "", err
	}
	if season == 0 {
		return "", fmt.Errorf("season is required")
	}
	comp, err := normalizeCompetition(a.Str("competition"))
	if err != nil {
		return "", err
	}
	if comp == "" {
		comp = CompSerieA
	}
	if !isLeague(comp) {
		return "", fmt.Errorf("%s is a knockout competition; use knockout_matches instead", comp)
	}
	top, err := a.Int("top")
	if err != nil {
		return "", err
	}
	rows, source, n := s.Standings(comp, season)
	if len(rows) == 0 {
		return fmt.Sprintf("No %s matches for %d in the dataset. Available seasons: %s.", comp, season, compactYears(s.Seasons(comp))), nil
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%d %s Final Standings (calculated from %d matches in %s):\n", season, comp, n, source)
	expected := len(rows) * (len(rows) - 1)
	incomplete := comp != CompSerieC && n < expected
	if comp == CompSerieC {
		b.WriteString("Note: Série C uses a group stage plus playoffs, so this aggregated table does not determine the champion.\n")
	} else if incomplete {
		var short []string
		for _, r := range rows {
			if r.Played < 2*(len(rows)-1) {
				short = append(short, fmt.Sprintf("%s (%d played)", r.Team.Name, r.Played))
			}
		}
		fmt.Fprintf(&b, "WARNING: the dataset is missing %d of the %d matches of this season (incomplete: %s), "+
			"so the order below may differ from the official final table.\n", expected-n, expected, strings.Join(short, ", "))
	}
	relegated := 0
	if comp == CompSerieA {
		relegated = relegationSpots(season)
	}
	for i, r := range rows {
		if top > 0 && i >= top {
			fmt.Fprintf(&b, "... (%d more teams)\n", len(rows)-top)
			break
		}
		label := ""
		switch {
		case i == 0 && comp != CompSerieC:
			label = " - Champion"
		case comp == CompSerieB && i < 4:
			label = " - Promoted"
		case relegated > 0 && i >= len(rows)-relegated:
			label = " - Relegated"
		}
		if incomplete && label != "" {
			label = map[string]string{" - Champion": " - Leader in dataset", " - Promoted": " - Promotion zone in dataset",
				" - Relegated": " - Relegation zone in dataset"}[label]
		}
		fmt.Fprintf(&b, "%d. %s - %d pts (%dW, %dD, %dL) GF %d, GA %d, GD %s%s\n", i+1, r.Team.Name, r.Points(), r.Won, r.Drawn, r.Lost, r.GF, r.GA, signed(r.GD()), label)
	}
	if relegated > 0 && top > 0 && top < len(rows) {
		var names []string
		for _, r := range rows[len(rows)-relegated:] {
			names = append(names, r.Team.Name)
		}
		if incomplete {
			fmt.Fprintf(&b, "Relegation zone in (incomplete) dataset: %s\n", strings.Join(names, ", "))
		} else {
			fmt.Fprintf(&b, "Relegated: %s\n", strings.Join(names, ", "))
		}
	}
	return b.String(), nil
}

var rankingMetrics = map[string]struct {
	label string
	asc   bool
	value func(r Record) float64
	fmt   func(r Record) string
}{
	"points":          {"points", false, func(r Record) float64 { return float64(r.Points()) }, func(r Record) string { return fmt.Sprintf("%d pts", r.Points()) }},
	"wins":            {"wins", false, func(r Record) float64 { return float64(r.Won) }, func(r Record) string { return fmt.Sprintf("%d wins", r.Won) }},
	"losses":          {"losses", false, func(r Record) float64 { return float64(r.Lost) }, func(r Record) string { return fmt.Sprintf("%d losses", r.Lost) }},
	"draws":           {"draws", false, func(r Record) float64 { return float64(r.Drawn) }, func(r Record) string { return fmt.Sprintf("%d draws", r.Drawn) }},
	"goals_for":       {"goals scored", false, func(r Record) float64 { return float64(r.GF) }, func(r Record) string { return fmt.Sprintf("%d goals scored", r.GF) }},
	"goals_against":   {"fewest goals conceded", true, func(r Record) float64 { return float64(r.GA) }, func(r Record) string { return fmt.Sprintf("%d goals conceded", r.GA) }},
	"goal_difference": {"goal difference", false, func(r Record) float64 { return float64(r.GD()) }, func(r Record) string { return "GD " + signed(r.GD()) }},
	"win_rate":        {"win rate", false, func(r Record) float64 { return r.WinRate() }, func(r Record) string { return fmt.Sprintf("%.1f%% wins", r.WinRate()) }},
	"points_rate":     {"points won (% of available)", false, func(r Record) float64 { return r.PointsRate() }, func(r Record) string { return fmt.Sprintf("%.1f%% of points", r.PointsRate()) }},
	"clean_sheets":    {"clean sheets", false, func(r Record) float64 { return float64(r.CleanSheets) }, func(r Record) string { return fmt.Sprintf("%d clean sheets", r.CleanSheets) }},
	"goals_per_match": {"goals scored per match", false, func(r Record) float64 { return ratio(r.GF, r.Played) }, func(r Record) string { return fmt.Sprintf("%.2f goals/match", ratio(r.GF, r.Played)) }},
}

func toolTeamRankings(s *Store, a Args) (string, error) {
	metricName := strings.ToLower(a.Str("metric"))
	metric, ok := rankingMetrics[metricName]
	if !ok {
		var names []string
		for k := range rankingMetrics {
			names = append(names, k)
		}
		sort.Strings(names)
		return "", fmt.Errorf("unknown metric %q; use one of %s", metricName, strings.Join(names, ", "))
	}
	var f MatchFilter
	var err error
	if f.Competition, err = normalizeCompetition(a.Str("competition")); err != nil {
		return "", err
	}
	if f.Season, err = a.Int("season"); err != nil {
		return "", err
	}
	if f.SeasonFrom, err = a.Int("season_from"); err != nil {
		return "", err
	}
	if f.SeasonTo, err = a.Int("season_to"); err != nil {
		return "", err
	}
	venue := strings.ToLower(a.Str("venue"))
	if venue == "any" {
		venue = ""
	}
	if venue != "" && venue != "home" && venue != "away" {
		return "", fmt.Errorf("venue must be home, away or any")
	}
	minMatches, err := a.Int("min_matches")
	if err != nil {
		return "", err
	}
	if minMatches <= 0 {
		minMatches = 50
		if f.Season != 0 {
			minMatches = 10
			if venue != "" {
				minMatches = 5
			}
		}
	}
	limit, err := limitArg(a, 10)
	if err != nil {
		return "", err
	}
	asc := metric.asc
	switch strings.ToLower(a.Str("order")) {
	case "asc":
		asc = true
	case "desc":
		asc = false
	}
	table := TeamTable(s.FindMatches(f), venue)
	var rows []StandingRow
	for t, r := range table {
		if r.Played >= minMatches {
			rows = append(rows, StandingRow{Team: t, Record: *r})
		}
	}
	sort.Slice(rows, func(i, j int) bool {
		vi, vj := metric.value(rows[i].Record), metric.value(rows[j].Record)
		if vi != vj {
			if asc {
				return vi < vj
			}
			return vi > vj
		}
		if rows[i].Played != rows[j].Played {
			return rows[i].Played > rows[j].Played
		}
		return rows[i].Team.Name < rows[j].Team.Name
	})
	scope := describeFilter(f)
	if venue != "" {
		scope += ", " + venue + " matches only"
	}
	var b strings.Builder
	dir := "highest"
	if asc != metric.asc {
		dir = "reverse order"
	} else if asc {
		dir = "best"
	}
	fmt.Fprintf(&b, "Teams ranked by %s (%s; %s; min %d matches):\n", metric.label, dir, scope, minMatches)
	if len(rows) == 0 {
		b.WriteString("No teams meet the criteria.\n")
		return b.String(), nil
	}
	for i, r := range rows {
		if i == limit {
			break
		}
		fmt.Fprintf(&b, "%d. %s - %s (%s)\n", i+1, r.Team.Name, metric.fmt(r.Record), fmtRecordLine(r.Record))
	}
	return b.String(), nil
}

// matchSummary aggregates a set of matches.
type matchSummary struct {
	n, goals, homeGoals, awayGoals int
	homeWins, draws, awayWins      int
	statsN, corners, shots         int
	scorelines                     map[string]int
	highest                        *Match
}

func summarize(ms []*Match) matchSummary {
	sum := matchSummary{scorelines: map[string]int{}}
	for _, m := range ms {
		sum.n++
		sum.goals += m.TotalGoals()
		sum.homeGoals += m.HomeGoals
		sum.awayGoals += m.AwayGoals
		switch {
		case m.HomeGoals > m.AwayGoals:
			sum.homeWins++
		case m.HomeGoals < m.AwayGoals:
			sum.awayWins++
		default:
			sum.draws++
		}
		sum.scorelines[fmt.Sprintf("%d-%d", m.HomeGoals, m.AwayGoals)]++
		if sum.highest == nil || m.TotalGoals() > sum.highest.TotalGoals() {
			sum.highest = m
		}
		if m.Stats != nil && m.Stats.HomeCorners+m.Stats.AwayCorners+m.Stats.HomeShots+m.Stats.AwayShots > 0 {
			sum.statsN++
			sum.corners += m.Stats.HomeCorners + m.Stats.AwayCorners
			sum.shots += m.Stats.HomeShots + m.Stats.AwayShots
		}
	}
	return sum
}

func (sum matchSummary) avgGoals() float64 { return ratio(sum.goals, sum.n) }

func toolLeagueStats(s *Store, a Args) (string, error) {
	f, err := s.filterFromArgs(Args{"competition": a["competition"], "season": a["season"], "season_from": a["season_from"], "season_to": a["season_to"]})
	if err != nil {
		return "", err
	}
	ms := s.FindMatches(f)
	if len(ms) == 0 {
		return fmt.Sprintf("No matches found for %s.", describeFilter(f)), nil
	}
	sum := summarize(ms)
	var b strings.Builder
	fmt.Fprintf(&b, "Statistics for %s (%d matches, seasons %s):\n", describeFilter(f), sum.n, compactYears(seasonsOf(ms)))
	fmt.Fprintf(&b, "- Total goals: %d\n", sum.goals)
	fmt.Fprintf(&b, "- Average goals per match: %.2f (home %.2f, away %.2f)\n", sum.avgGoals(), ratio(sum.homeGoals, sum.n), ratio(sum.awayGoals, sum.n))
	fmt.Fprintf(&b, "- Home win rate: %.1f%%, Draws: %.1f%%, Away win rate: %.1f%%\n", pct(sum.homeWins, sum.n), pct(sum.draws, sum.n), pct(sum.awayWins, sum.n))
	type sc struct {
		s string
		n int
	}
	var scs []sc
	for k, v := range sum.scorelines {
		scs = append(scs, sc{k, v})
	}
	sort.Slice(scs, func(i, j int) bool { return scs[i].n > scs[j].n || scs[i].n == scs[j].n && scs[i].s < scs[j].s })
	var top []string
	for i := 0; i < len(scs) && i < 5; i++ {
		top = append(top, fmt.Sprintf("%s (%d, %.1f%%)", scs[i].s, scs[i].n, pct(scs[i].n, sum.n)))
	}
	fmt.Fprintf(&b, "- Most common scorelines (home-away): %s\n", strings.Join(top, ", "))
	fmt.Fprintf(&b, "- Highest-scoring match: %s\n", fmtMatch(sum.highest))
	if sum.statsN > 0 {
		fmt.Fprintf(&b, "- Matches with extended stats: %d (avg corners %.1f, avg shots %.1f per match)\n", sum.statsN, ratio(sum.corners, sum.statsN), ratio(sum.shots, sum.statsN))
	}
	if f.Competition == "" {
		byComp := map[string][]*Match{}
		for _, m := range ms {
			byComp[m.Competition] = append(byComp[m.Competition], m)
		}
		b.WriteString("By competition:\n")
		for _, c := range allCompetitions {
			if list := byComp[c]; len(list) > 0 {
				cs := summarize(list)
				fmt.Fprintf(&b, "- %s: %d matches, %.2f goals/match, home wins %.1f%%, draws %.1f%%, away wins %.1f%%\n", c, cs.n, cs.avgGoals(), pct(cs.homeWins, cs.n), pct(cs.draws, cs.n), pct(cs.awayWins, cs.n))
			}
		}
	}
	return b.String(), nil
}

func seasonsOf(ms []*Match) []int {
	set := map[int]bool{}
	for _, m := range ms {
		set[m.Season] = true
	}
	var out []int
	for y := range set {
		out = append(out, y)
	}
	sort.Ints(out)
	return out
}

func toolCompareSeasons(s *Store, a Args) (string, error) {
	var seasons []int
	for _, part := range strings.FieldsFunc(a.Str("seasons"), func(r rune) bool { return r == ',' || r == ' ' || r == ';' }) {
		if strings.Contains(part, "-") { // range like 2015-2019
			ends := strings.SplitN(part, "-", 2)
			lo, err1 := strconv.Atoi(ends[0])
			hi, err2 := strconv.Atoi(ends[1])
			if err1 != nil || err2 != nil || hi < lo {
				return "", fmt.Errorf("invalid season range %q", part)
			}
			for y := lo; y <= hi; y++ {
				seasons = append(seasons, y)
			}
			continue
		}
		y, err := strconv.Atoi(part)
		if err != nil {
			return "", fmt.Errorf("invalid season %q", part)
		}
		seasons = append(seasons, y)
	}
	if len(seasons) < 2 {
		return "", fmt.Errorf("give at least two seasons, e.g. '2018,2019'")
	}
	comp, err := normalizeCompetition(a.Str("competition"))
	if err != nil {
		return "", err
	}
	if comp == "" {
		comp = CompSerieA
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s season comparison:\n", comp)
	for _, y := range seasons {
		ms := s.FindMatches(MatchFilter{Competition: comp, Season: y})
		if len(ms) == 0 {
			fmt.Fprintf(&b, "\n%d: no matches in dataset\n", y)
			continue
		}
		sum := summarize(ms)
		fmt.Fprintf(&b, "\n%d (%d matches):\n", y, sum.n)
		fmt.Fprintf(&b, "- Goals: %d total, %.2f per match\n", sum.goals, sum.avgGoals())
		fmt.Fprintf(&b, "- Home wins %.1f%%, draws %.1f%%, away wins %.1f%%\n", pct(sum.homeWins, sum.n), pct(sum.draws, sum.n), pct(sum.awayWins, sum.n))
		if isLeague(comp) && comp != CompSerieC {
			rows, _, _ := s.Standings(comp, y)
			if len(rows) > 0 {
				c := rows[0]
				label := "Champion (calculated)"
				if n := len(rows); sum.n < n*(n-1) {
					label = fmt.Sprintf("Leader in dataset (season incomplete: %d of %d matches)", sum.n, n*(n-1))
				}
				fmt.Fprintf(&b, "- %s: %s, %d pts (%dW, %dD, %dL)\n", label, c.Team.Name, c.Points(), c.Won, c.Drawn, c.Lost)
				att, def := rows[0], rows[0]
				for _, r := range rows {
					if r.GF > att.GF {
						att = r
					}
					if r.GA < def.GA {
						def = r
					}
				}
				fmt.Fprintf(&b, "- Best attack: %s (%d goals); best defence: %s (%d conceded)\n", att.Team.Name, att.GF, def.Team.Name, def.GA)
			}
		}
		var big *Match
		for _, m := range ms {
			if big == nil || m.Margin() > big.Margin() {
				big = m
			}
		}
		fmt.Fprintf(&b, "- Biggest win: %s\n", fmtMatch(big))
	}
	return b.String(), nil
}

func toolBiggestWins(s *Store, a Args) (string, error) {
	f, err := s.filterFromArgs(Args{"competition": a["competition"], "season": a["season"], "season_from": a["season_from"], "season_to": a["season_to"], "team": a["team"]})
	if err != nil {
		return "", err
	}
	limit, err := limitArg(a, 10)
	if err != nil {
		return "", err
	}
	byTotal := strings.ToLower(a.Str("sort_by")) == "total_goals"
	ms := append([]*Match(nil), s.FindMatches(f)...)
	sort.SliceStable(ms, func(i, j int) bool {
		x, y := ms[i], ms[j]
		if byTotal {
			if x.TotalGoals() != y.TotalGoals() {
				return x.TotalGoals() > y.TotalGoals()
			}
			return x.Date.Before(y.Date)
		}
		if x.Margin() != y.Margin() {
			return x.Margin() > y.Margin()
		}
		if x.TotalGoals() != y.TotalGoals() {
			return x.TotalGoals() > y.TotalGoals()
		}
		return x.Date.Before(y.Date)
	})
	var b strings.Builder
	kind := "Biggest victories"
	if byTotal {
		kind = "Highest-scoring matches"
	}
	fmt.Fprintf(&b, "%s (%s):\n", kind, describeFilter(f))
	if len(ms) == 0 {
		b.WriteString("No matches found.\n")
		return b.String(), nil
	}
	for i, m := range ms {
		if i == limit {
			break
		}
		fmt.Fprintf(&b, "%d. %s\n", i+1, fmtMatch(m))
	}
	sum := summarize(ms)
	fmt.Fprintf(&b, "\nAverage goals per match: %.2f\nHome win rate: %.1f%%\n", sum.avgGoals(), pct(sum.homeWins, sum.n))
	return b.String(), nil
}

var stageOrder = []string{"group stage", "round 1", "round 2", "round 3", "round 4", "round 5", "round 6", "round 7", "round 8", "round of 16", "quarterfinals", "semifinals", "final"}

func stageRank(st string) int {
	for i, s := range stageOrder {
		if s == st {
			return i
		}
	}
	return len(stageOrder)
}

// tie groups the legs played between two teams in one stage.
type tie struct {
	a, b *Team
	legs []*Match
}

func toolKnockout(s *Store, a Args) (string, error) {
	comp, err := normalizeCompetition(a.Str("competition"))
	if err != nil {
		return "", err
	}
	if comp != CompCopaBrasil && comp != CompLibertadores {
		return "", fmt.Errorf("competition must be Copa do Brasil or Libertadores")
	}
	season, err := a.Int("season")
	if err != nil {
		return "", err
	}
	team, err := s.optTeam(a, "team")
	if err != nil {
		return "", err
	}
	stage := normalizeStage(a.Str("stage"))
	ms := s.FindMatches(MatchFilter{Competition: comp, Season: season, Stage: stage, Team: team})
	var b strings.Builder
	title := comp
	if season != 0 {
		title = fmt.Sprintf("%d %s", season, comp)
	}
	if stage != "" {
		title += " - " + stage
	} else {
		title += " knockout bracket"
	}
	if team != nil {
		title += " (" + team.Name + ")"
	}
	fmt.Fprintf(&b, "%s:\n", title)
	// season -> stage -> ties
	type key struct {
		season int
		stage  string
	}
	groups := map[key][]*tie{}
	for _, m := range ms {
		if m.Stage == "" || (stage == "" && m.Stage == "group stage") {
			continue
		}
		k := key{m.Season, m.Stage}
		var found *tie
		for _, t := range groups[k] {
			if (t.a == m.Home && t.b == m.Away) || (t.a == m.Away && t.b == m.Home) {
				found = t
				break
			}
		}
		if found == nil {
			found = &tie{a: m.Home, b: m.Away}
			groups[k] = append(groups[k], found)
		}
		found.legs = append(found.legs, m)
	}
	if len(groups) == 0 {
		b.WriteString("No knockout matches found for this selection.")
		if season != 0 {
			fmt.Fprintf(&b, " Seasons with data: %s.", compactYears(s.Seasons(comp)))
		}
		b.WriteString("\n")
		return b.String(), nil
	}
	var keys []key
	for k := range groups {
		keys = append(keys, k)
	}
	sort.Slice(keys, func(i, j int) bool {
		if keys[i].season != keys[j].season {
			return keys[i].season < keys[j].season
		}
		return stageRank(keys[i].stage) < stageRank(keys[j].stage)
	})
	lastSeason := 0
	for _, k := range keys {
		if k.season != lastSeason && season == 0 {
			fmt.Fprintf(&b, "\n%d:\n", k.season)
		}
		lastSeason = k.season
		fmt.Fprintf(&b, "%s:\n", strings.ToUpper(k.stage[:1])+k.stage[1:])
		for _, t := range groups[k] {
			ga, gb := 0, 0
			var legs []string
			for _, m := range t.legs {
				x, y := m.GoalsFor(t.a)
				ga += x
				gb += y
				legs = append(legs, fmt.Sprintf("%s %s %d-%d %s", m.Date.Format("2006-01-02"), m.Home.Name, m.HomeGoals, m.AwayGoals, m.Away.Name))
			}
			result := ""
			switch {
			case ga > gb:
				result = t.a.Name + " advanced"
			case gb > ga:
				result = t.b.Name + " advanced"
			default:
				result = "level on aggregate (decided by away goals or penalties, not in data)"
			}
			if k.stage == "final" {
				result = strings.Replace(result, "advanced", "won the title", 1)
			}
			fmt.Fprintf(&b, "- %s %d-%d %s on aggregate: %s [%s]\n", t.a.Name, ga, gb, t.b.Name, result, strings.Join(legs, "; "))
		}
	}
	return b.String(), nil
}

func toolDerbies(s *Store, a Args) (string, error) {
	f, err := s.filterFromArgs(Args{"competition": a["competition"], "season": a["season"], "team": a["team"]})
	if err != nil {
		return "", err
	}
	limit, err := limitArg(a, 30)
	if err != nil {
		return "", err
	}
	want := foldText(a.Str("derby"))
	var ms []*Match
	perDerby := map[string][]*Match{}
	for _, m := range s.FindMatches(f) {
		d := DerbyName(m.Home, m.Away)
		if d == "" || (want != "" && !strings.Contains(foldText(d), want)) {
			continue
		}
		ms = append(ms, m)
		perDerby[d] = append(perDerby[d], m)
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Derby matches (%s): %d found\n", describeFilter(f), len(ms))
	if len(ms) == 0 {
		return b.String(), nil
	}
	var names []string
	for d := range perDerby {
		names = append(names, d)
	}
	sort.Slice(names, func(i, j int) bool {
		return len(perDerby[names[i]]) > len(perDerby[names[j]]) || len(perDerby[names[i]]) == len(perDerby[names[j]]) && names[i] < names[j]
	})
	b.WriteString("Summary by derby:\n")
	for _, d := range names {
		list := perDerby[d]
		x := list[0].Home
		r := TeamRecord(x, list)
		fmt.Fprintf(&b, "- %s (%s vs %s): %d matches - %s %d wins, %s %d wins, %d draws\n", d, x.Name, list[0].Away.Name, len(list), x.Name, r.Won, list[0].Away.Name, r.Lost, r.Drawn)
	}
	b.WriteString("Matches (most recent first):\n")
	for i, m := range reversed(ms) {
		if i == limit {
			fmt.Fprintf(&b, "- ... (%d more)\n", len(ms)-limit)
			break
		}
		fmt.Fprintf(&b, "- %s [%s]\n", fmtMatch(m), DerbyName(m.Home, m.Away))
	}
	return b.String(), nil
}

// ---------- player tools ----------

func fmtPlayer(p *Player) string {
	return fmt.Sprintf("%s - Overall: %d, Potential: %d, Position: %s, Club: %s, Age: %d, Nationality: %s",
		p.Name, p.Overall, p.Potential, orDash(p.Position), orDash(p.Club), p.Age, p.Nationality)
}

func orDash(s string) string {
	if s == "" {
		return "-"
	}
	return s
}

func toolSearchPlayers(s *Store, a Args) (string, error) {
	pf := PlayerFilter{Name: a.Str("name"), Nationality: a.Str("nationality"), Club: a.Str("club"), Position: a.Str("position")}
	var err error
	if pf.MinOverall, err = a.Int("min_overall"); err != nil {
		return "", err
	}
	if pf.MaxAge, err = a.Int("max_age"); err != nil {
		return "", err
	}
	limit, err := limitArg(a, 20)
	if err != nil {
		return "", err
	}
	var clubTeam *Team
	if pf.Club != "" {
		if t, err := s.ResolveTeam(pf.Club); err == nil {
			clubTeam = t
			if len(t.Players) > 0 { // exact club link: avoid "Santos" matching "Santos Laguna"
				pf.ClubTeam, pf.Club = t, ""
			}
		}
	}
	ps := s.FindPlayers(pf)
	switch strings.ToLower(a.Str("sort_by")) {
	case "potential":
		sort.SliceStable(ps, func(i, j int) bool { return ps[i].Potential > ps[j].Potential })
	case "age":
		sort.SliceStable(ps, func(i, j int) bool { return ps[i].Age < ps[j].Age })
	case "name":
		sort.SliceStable(ps, func(i, j int) bool { return ps[i].Name < ps[j].Name })
	}
	var desc []string
	for _, kv := range [][2]string{{"name", a.Str("name")}, {"nationality", a.Str("nationality")}, {"club", a.Str("club")}, {"position", a.Str("position")}} {
		if kv[1] != "" {
			desc = append(desc, kv[0]+"="+kv[1])
		}
	}
	if pf.MinOverall > 0 {
		desc = append(desc, fmt.Sprintf("overall>=%d", pf.MinOverall))
	}
	if pf.MaxAge > 0 {
		desc = append(desc, fmt.Sprintf("age<=%d", pf.MaxAge))
	}
	if len(desc) == 0 {
		desc = append(desc, "all players")
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%d players found (%s) in FIFA 19 data:\n", len(ps), strings.Join(desc, ", "))
	for i, p := range ps {
		if i == limit {
			fmt.Fprintf(&b, "... (%d more)\n", len(ps)-limit)
			break
		}
		fmt.Fprintf(&b, "%d. %s\n", i+1, fmtPlayer(p))
	}
	if len(ps) > 0 {
		sum := 0
		for _, p := range ps {
			sum += p.Overall
		}
		fmt.Fprintf(&b, "Average overall rating: %.1f\n", float64(sum)/float64(len(ps)))
	}
	if len(ps) == 0 && a.Str("club") != "" {
		if clubTeam != nil {
			fmt.Fprintf(&b, "Note: %s appears in the match data but has no squad in the FIFA 19 dataset.\n", clubTeam.Name)
		}
		fmt.Fprintf(&b, "Brazilian clubs with FIFA squads: %s\n", strings.Join(s.squadClubNames(), ", "))
	}
	if normalizeNationality(pf.Nationality) == "brazil" && pf.Club == "" && pf.ClubTeam == nil {
		b.WriteString("\nBrazilian players at Brazilian clubs:\n")
		b.WriteString(s.squadSummary("Brazil"))
	}
	return b.String(), nil
}

func (s *Store) squadTeams() []*Team {
	var ts []*Team
	for _, t := range s.Teams {
		if len(t.Players) > 0 {
			ts = append(ts, t)
		}
	}
	sort.Slice(ts, func(i, j int) bool { return ts[i].Name < ts[j].Name })
	return ts
}

func (s *Store) squadClubNames() []string {
	var out []string
	for _, t := range s.squadTeams() {
		out = append(out, t.Name)
	}
	return out
}

// squadSummary lists Brazilian clubs with player counts and average rating.
func (s *Store) squadSummary(nationality string) string {
	nat := normalizeNationality(nationality)
	type row struct {
		t    *Team
		n    int
		avg  float64
		best *Player
	}
	var rows []row
	for _, t := range s.squadTeams() {
		r := row{t: t}
		sum := 0
		for _, p := range t.Players {
			if nat != "" && foldText(p.Nationality) != nat {
				continue
			}
			r.n++
			sum += p.Overall
			if r.best == nil || p.Overall > r.best.Overall {
				r.best = p
			}
		}
		if r.n > 0 {
			r.avg = float64(sum) / float64(r.n)
			rows = append(rows, r)
		}
	}
	sort.Slice(rows, func(i, j int) bool {
		if rows[i].avg != rows[j].avg {
			return rows[i].avg > rows[j].avg
		}
		return rows[i].t.Name < rows[j].t.Name
	})
	var b strings.Builder
	for _, r := range rows {
		fmt.Fprintf(&b, "- %s: %d players (avg rating: %.1f, best: %s %d)\n", r.t.Name, r.n, r.avg, r.best.Name, r.best.Overall)
	}
	if len(rows) > 0 {
		b.WriteString(fifaBrazilNote)
	}
	return b.String()
}

// fifaBrazilNote explains a quirk of the FIFA 19 data.
const fifaBrazilNote = "Note: FIFA 19 had no player-likeness licence for Brazilian clubs, so their squads use generated player names; " +
	"Flamengo, Palmeiras, Corinthians and São Paulo are absent.\n"

func toolClubSquads(s *Store, a Args) (string, error) {
	nat := a.Str("nationality")
	var b strings.Builder
	if nat != "" {
		fmt.Fprintf(&b, "Players of nationality %q at Brazilian clubs (FIFA 19):\n", nat)
	} else {
		b.WriteString("Brazilian club squads in FIFA 19 data:\n")
	}
	sum := s.squadSummary(nat)
	if sum == "" {
		sum = "- none\n"
	}
	b.WriteString(sum)
	return b.String(), nil
}

func toolGetPlayer(s *Store, a Args) (string, error) {
	name := a.Str("name")
	if name == "" {
		return "", fmt.Errorf("name is required")
	}
	folded := foldText(name)
	var exact []*Player
	for _, p := range s.Players {
		if p.nameFold == folded {
			exact = append(exact, p)
		}
	}
	matches := exact
	if len(matches) == 0 {
		matches = s.FindPlayers(PlayerFilter{Name: name})
	}
	var b strings.Builder
	if len(matches) == 0 {
		// Suggest players sharing any name token, e.g. "Gabriel Barbosa"
		// (listed differently in FIFA 19) -> players named Gabriel / Barbosa.
		seen := map[*Player]bool{}
		var sugg []*Player
		for _, tok := range strings.Fields(folded) {
			if len(tok) < 3 {
				continue
			}
			for _, p := range s.FindPlayers(PlayerFilter{Name: tok}) {
				if !seen[p] {
					seen[p] = true
					sugg = append(sugg, p)
				}
			}
		}
		sort.SliceStable(sugg, func(i, j int) bool { return sugg[i].Overall > sugg[j].Overall })
		fmt.Fprintf(&b, "No player named %q in the FIFA 19 dataset.\n", name)
		if len(sugg) > 0 {
			b.WriteString("Players with similar names:\n")
			for i, p := range sugg {
				if i == 10 {
					break
				}
				fmt.Fprintf(&b, "- %s\n", fmtPlayer(p))
			}
		}
		return b.String(), nil
	}
	if len(matches) > 1 && len(exact) == 0 {
		fmt.Fprintf(&b, "%d players match %q; showing the highest rated. Others:\n", len(matches), name)
		for i, p := range matches[1:] {
			if i == 10 {
				fmt.Fprintf(&b, "- ... (%d more)\n", len(matches)-11)
				break
			}
			fmt.Fprintf(&b, "- %s\n", fmtPlayer(p))
		}
		b.WriteString("\n")
		matches = matches[:1]
	}
	for i, p := range matches {
		if i > 0 {
			b.WriteString("\n")
		}
		writePlayerProfile(&b, p)
	}
	return b.String(), nil
}

func writePlayerProfile(b *strings.Builder, p *Player) {
	fmt.Fprintf(b, "%s (FIFA 19 ID %d)\n", p.Name, p.ID)
	fmt.Fprintf(b, "- Age: %d, Nationality: %s\n", p.Age, p.Nationality)
	fmt.Fprintf(b, "- Club: %s, Position: %s, Jersey: %s\n", orDash(p.Club), orDash(p.Position), orDash(p.Jersey))
	if p.LoanedFrom != "" {
		fmt.Fprintf(b, "- On loan from: %s\n", p.LoanedFrom)
	}
	fmt.Fprintf(b, "- Overall: %d, Potential: %d\n", p.Overall, p.Potential)
	fmt.Fprintf(b, "- Height: %s, Weight: %s, Preferred foot: %s, Weak foot: %s, Skill moves: %s, Work rate: %s\n",
		orDash(p.Height), orDash(p.Weight), orDash(p.PreferredFoot), orDash(p.WeakFoot), orDash(p.SkillMoves), orDash(p.WorkRate))
	fmt.Fprintf(b, "- Value: %s, Wage: %s, Release clause: %s, Contract until: %s\n", orDash(p.Value), orDash(p.Wage), orDash(p.ReleaseClause), orDash(p.ContractUntil))
	skills := append([]Skill(nil), p.Skills...)
	sort.SliceStable(skills, func(i, j int) bool { return skills[i].Value > skills[j].Value })
	var top []string
	for i, sk := range skills {
		if i == 6 {
			break
		}
		top = append(top, fmt.Sprintf("%s %d", sk.Name, sk.Value))
	}
	if len(top) > 0 {
		fmt.Fprintf(b, "- Top attributes: %s\n", strings.Join(top, ", "))
	}
	if t := p.Team; t != nil {
		r := TeamRecord(t, t.Matches)
		fmt.Fprintf(b, "- Club in match data: %s - %s (win rate %.1f%%)\n", t.Name, fmtRecordLine(r), r.WinRate())
	}
}

// ---------- reference tools ----------

func toolListTeams(s *Store, a Args) (string, error) {
	comp, err := normalizeCompetition(a.Str("competition"))
	if err != nil {
		return "", err
	}
	limit, err := limitArg(a, 30)
	if err != nil {
		return "", err
	}
	q := foldText(a.Str("query"))
	type row struct {
		t *Team
		n int
	}
	var rows []row
	for _, t := range s.Teams {
		if q != "" {
			hay := t.Key + " " + foldText(t.Name)
			for v := range t.Variants {
				hay += " " + foldText(v)
			}
			if !strings.Contains(hay, q) {
				continue
			}
		}
		n := 0
		for _, m := range t.Matches {
			if comp == "" || m.Competition == comp {
				n++
			}
		}
		if n > 0 {
			rows = append(rows, row{t, n})
		}
	}
	sort.Slice(rows, func(i, j int) bool {
		return rows[i].n > rows[j].n || rows[i].n == rows[j].n && rows[i].t.Name < rows[j].t.Name
	})
	var b strings.Builder
	fmt.Fprintf(&b, "%d teams found:\n", len(rows))
	for i, r := range rows {
		if i == limit {
			fmt.Fprintf(&b, "... (%d more)\n", len(rows)-limit)
			break
		}
		var vs []string
		for v := range r.t.Variants {
			vs = append(vs, v)
		}
		sort.Strings(vs)
		fmt.Fprintf(&b, "- %s [id %s] - %d matches; spellings: %s\n", r.t.Name, r.t.Key, r.n, strings.Join(vs, "; "))
	}
	return b.String(), nil
}

func toolDatasetInfo(s *Store, a Args) (string, error) {
	var b strings.Builder
	fmt.Fprintf(&b, "Brazilian soccer knowledge graph (loaded from %s in %s)\n", s.DataDir, s.LoadTime.Round(time.Millisecond))
	fmt.Fprintf(&b, "Unique matches: %d, teams: %d, FIFA players: %d\n", len(s.Matches), len(s.Teams), len(s.Players))
	b.WriteString("Files:\n")
	for _, f := range s.Files {
		fmt.Fprintf(&b, "- %s: %d rows, %d loaded", f.Name, f.Rows, f.Loaded)
		if f.Skipped > 0 {
			fmt.Fprintf(&b, ", %d skipped (missing scores/fields)", f.Skipped)
		}
		if f.Merged > 0 {
			fmt.Fprintf(&b, ", %d merged as duplicates of fixtures from other files", f.Merged)
		}
		b.WriteString("\n")
	}
	b.WriteString("Coverage:\n")
	for _, c := range allCompetitions {
		ms := s.FindMatches(MatchFilter{Competition: c})
		fmt.Fprintf(&b, "- %s: %d matches, seasons %s\n", c, len(ms), compactYears(seasonsOf(ms)))
	}
	b.WriteString("Notes: standings are calculated from results (3/1/0 points); player data is FIFA 19 (2018/19 squads); individual goal scorers are not in the data.\n")
	return b.String(), nil
}
