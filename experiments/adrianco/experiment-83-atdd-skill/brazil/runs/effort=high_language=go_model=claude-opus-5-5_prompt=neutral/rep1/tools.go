// tools.go — the MCP tool catalogue and handlers.
//
// Each tool takes JSON arguments and returns human-readable text formatted
// for an LLM to relay (match lines, records, tables). Errors that the user
// can fix (unknown team, bad season) are returned as tool errors with a hint.
package main

import (
	"encoding/json"
	"fmt"
	"sort"
	"strconv"
	"strings"
	"time"
)

// Tool describes one MCP tool.
type Tool struct {
	Name        string         `json:"name"`
	Description string         `json:"description"`
	InputSchema map[string]any `json:"inputSchema"`
	handler     func(*Store, Args) (string, error)
}

// Args wraps decoded tool arguments with lenient accessors (numbers may be
// sent as strings and vice versa).
type Args map[string]any

func (a Args) Str(k string) string {
	switch v := a[k].(type) {
	case string:
		return strings.TrimSpace(v)
	case float64:
		return strconv.FormatFloat(v, 'f', -1, 64)
	case int:
		return strconv.Itoa(v)
	case json.Number:
		return v.String()
	case bool:
		return strconv.FormatBool(v)
	}
	return ""
}

func (a Args) Int(k string, def int) (int, error) {
	switch v := a[k].(type) {
	case nil:
		return def, nil
	case int:
		return v, nil
	case int64:
		return int(v), nil
	case float64:
		return int(v), nil
	case json.Number:
		n, err := v.Int64()
		return int(n), err
	case string:
		if strings.TrimSpace(v) == "" {
			return def, nil
		}
		n, err := strconv.Atoi(strings.TrimSpace(v))
		if err != nil {
			return 0, fmt.Errorf("%s must be a number, got %q", k, v)
		}
		return n, nil
	}
	return 0, fmt.Errorf("%s must be a number", k)
}

func (a Args) Bool(k string, def bool) bool {
	switch v := a[k].(type) {
	case bool:
		return v
	case string:
		b, err := strconv.ParseBool(v)
		if err == nil {
			return b
		}
	}
	return def
}

// IntList accepts [2018, 2019], "2018,2019" or "2018-2020".
func (a Args) IntList(k string) ([]int, error) {
	var out []int
	switch v := a[k].(type) {
	case nil:
		return nil, nil
	case []any:
		for _, x := range v {
			n, err := Args{"x": x}.Int("x", 0)
			if err != nil {
				return nil, fmt.Errorf("%s: %v", k, err)
			}
			out = append(out, n)
		}
	case float64:
		out = append(out, int(v))
	case int:
		out = append(out, v)
	case string:
		for _, part := range strings.Split(v, ",") {
			part = strings.TrimSpace(part)
			if lo, hi, ok := strings.Cut(part, "-"); ok {
				l, err1 := strconv.Atoi(strings.TrimSpace(lo))
				h, err2 := strconv.Atoi(strings.TrimSpace(hi))
				if err1 != nil || err2 != nil || h < l {
					return nil, fmt.Errorf("%s: bad range %q", k, part)
				}
				for y := l; y <= h; y++ {
					out = append(out, y)
				}
			} else if part != "" {
				n, err := strconv.Atoi(part)
				if err != nil {
					return nil, fmt.Errorf("%s: bad number %q", k, part)
				}
				out = append(out, n)
			}
		}
	}
	return out, nil
}

func itoa(n int) string { return strconv.Itoa(n) }

// schema helpers
func obj(props map[string]any, required ...string) map[string]any {
	s := map[string]any{"type": "object", "properties": props}
	if len(required) > 0 {
		s["required"] = required
	}
	return s
}
func str(desc string) map[string]any { return map[string]any{"type": "string", "description": desc} }
func num(desc string) map[string]any { return map[string]any{"type": "integer", "description": desc} }
func boolean(desc string) map[string]any {
	return map[string]any{"type": "boolean", "description": desc}
}
func enum(desc string, vals ...string) map[string]any {
	return map[string]any{"type": "string", "description": desc, "enum": vals}
}

const compDesc = "Competition: 'Brasileirão' (Série A), 'Série B', 'Série C', 'Copa do Brasil', 'Libertadores' or 'all'"

// Tools returns the tool catalogue.
func Tools() []Tool {
	return []Tool{
		{
			Name: "search_matches",
			Description: "Find matches by team (either side, home or away), opponent, competition, season, date range or knockout stage. " +
				"Searches all five match files (de-duplicated). Example: Flamengo vs Fluminense; Palmeiras matches in 2023; Copa do Brasil finals.",
			InputSchema: obj(map[string]any{
				"team":         str("Team name (any spelling, e.g. 'Flamengo', 'Palmeiras-SP', 'Atlético Mineiro')"),
				"opponent":     str("Only matches against this team"),
				"venue":        enum("Only home or away games of 'team'", "home", "away", "any"),
				"home_team":    str("Exact home side"),
				"away_team":    str("Exact away side"),
				"competition":  str(compDesc),
				"season":       num("Season year, e.g. 2019"),
				"season_from":  num("First season (inclusive)"),
				"season_to":    num("Last season (inclusive)"),
				"date_from":    str("Start date (YYYY-MM-DD or DD/MM/YYYY)"),
				"date_to":      str("End date (inclusive)"),
				"stage":        str("Knockout stage: 'final', 'semifinals', 'quarterfinals', 'round of 16', 'group stage'"),
				"round":        str("League/cup round number"),
				"derbies_only": boolean("Only traditional rivalry games (Fla-Flu, Grenal, Derby Paulista, ...)"),
				"order":        enum("Sort order by date (default newest first)", "newest", "oldest"),
				"limit":        num("Maximum matches to list (default 20, max 500)"),
			}),
			handler: toolSearchMatches,
		},
		{
			Name:        "head_to_head",
			Description: "Head-to-head record between two teams: wins, draws, goals, recent and biggest results. Optional competition/season filters.",
			InputSchema: obj(map[string]any{
				"team_a":      str("First team"),
				"team_b":      str("Second team"),
				"competition": str(compDesc),
				"season_from": num("First season"),
				"season_to":   num("Last season"),
				"limit":       num("Recent matches to list (default 10)"),
			}, "team_a", "team_b"),
			handler: toolHeadToHead,
		},
		{
			Name: "team_record",
			Description: "Win/draw/loss record, goals for/against and win rate for a team, optionally limited to a season, competition and home/away games. " +
				"Example: Corinthians home record in 2022.",
			InputSchema: obj(map[string]any{
				"team":        str("Team name"),
				"season":      num("Season year"),
				"season_from": num("First season"),
				"season_to":   num("Last season"),
				"competition": str(compDesc + " (default: all, with per-competition breakdown)"),
				"venue":       enum("home, away or any (default any)", "home", "away", "any"),
			}, "team"),
			handler: toolTeamRecord,
		},
		{
			Name: "team_overview",
			Description: "Everything known about a team across files: competitions and seasons played, overall record per competition, " +
				"league finishes, titles inferred from the data, and FIFA players at the club (cross-file query).",
			InputSchema: obj(map[string]any{"team": str("Team name")}, "team"),
			handler:     toolTeamOverview,
		},
		{
			Name: "standings",
			Description: "League table for a season calculated from match results (3 pts per win). Marks the champion and relegated teams. " +
				"Answers 'Who won the 2019 Brasileirão?' and 'Which teams were relegated in 2020?'.",
			InputSchema: obj(map[string]any{
				"season":      num("Season year (Série A 2003-2023, Série B/C 2014-2023)"),
				"competition": str("League: Brasileirão/Série A (default), Série B or Série C"),
				"limit":       num("Rows to show (default: all)"),
			}, "season"),
			handler: toolStandings,
		},
		{
			Name: "rank_teams",
			Description: "Rank teams by a statistic over a competition/season range: points, wins, win_rate, goals_for, goals_against, " +
				"goal_difference, goals_per_game, clean_sheets. Use venue=home/away for 'best home/away record'. " +
				"Example: which team scored the most goals in Serie A 2022?",
			InputSchema: obj(map[string]any{
				"metric":      enum("Statistic to rank by (default win_rate)", "points", "wins", "win_rate", "points_rate", "goals_for", "goals_against", "goal_difference", "goals_per_game", "clean_sheets", "losses", "draws"),
				"venue":       enum("home, away or any", "home", "away", "any"),
				"competition": str(compDesc + " (default Brasileirão)"),
				"season":      num("Season year"),
				"season_from": num("First season"),
				"season_to":   num("Last season"),
				"min_matches": num("Minimum games played to be ranked (default: 10 for rates)"),
				"ascending":   boolean("Lowest first (e.g. fewest goals conceded is handled automatically)"),
				"limit":       num("Rows (default 10)"),
			}),
			handler: toolRankTeams,
		},
		{
			Name:        "biggest_wins",
			Description: "Largest victory margins, optionally filtered by competition, season or team.",
			InputSchema: obj(map[string]any{
				"competition": str(compDesc),
				"season":      num("Season year"),
				"team":        str("Only wins by this team"),
				"limit":       num("Rows (default 10)"),
			}),
			handler: toolBiggestWins,
		},
		{
			Name: "competition_stats",
			Description: "Aggregate statistics: matches, average goals per match, home/away win and draw rates, home vs away goals, " +
				"corners and shots (where available), highest-scoring games. Pass several seasons to compare them side by side.",
			InputSchema: obj(map[string]any{
				"competition": str(compDesc + " (default Brasileirão)"),
				"season":      num("Single season"),
				"seasons":     str("Seasons to compare, e.g. '2018,2019' or '2015-2019'"),
			}),
			handler: toolCompetitionStats,
		},
		{
			Name: "knockout_bracket",
			Description: "Knockout ties (aggregate scores and winners) for Copa Libertadores or Copa do Brasil. " +
				"Give a season for a bracket, or a stage (e.g. 'final') without season to list it for every year.",
			InputSchema: obj(map[string]any{
				"competition": str("'Libertadores' or 'Copa do Brasil'"),
				"season":      num("Season year"),
				"stage":       str("Only this stage: final, semifinals, quarterfinals, round of 16"),
			}, "competition"),
			handler: toolKnockout,
		},
		{
			Name: "search_players",
			Description: "Search the FIFA 19 player database (18,207 players) by name, nationality, club, position and minimum rating, sorted by rating. " +
				"Brazilian clubs present: Grêmio, Atlético Mineiro, Cruzeiro, Fluminense, Santos, Internacional, América-MG, Botafogo, Bahia, Paraná, " +
				"Athletico-PR, Vitória, Sport, Chapecoense, Ceará.",
			InputSchema: obj(map[string]any{
				"name":                 str("Player name (accent-insensitive, partial)"),
				"nationality":          str("Nationality, e.g. 'Brazil'"),
				"club":                 str("Club name (Brazilian club names are normalised)"),
				"position":             str("FIFA code(s) like 'ST,CF' or a role: forward, midfielder, defender, goalkeeper, winger"),
				"min_overall":          num("Minimum overall rating"),
				"max_age":              num("Maximum age"),
				"brazilian_clubs_only": boolean("Only players at Brazilian clubs"),
				"sort_by":              str("overall (default), potential, age, name, or a skill such as Finishing"),
				"limit":                num("Rows (default 20)"),
			}),
			handler: toolSearchPlayers,
		},
		{
			Name:        "player_profile",
			Description: "Detailed FIFA profile for a player (ratings, position, club, physical data, top skills). Suggests close names when not found.",
			InputSchema: obj(map[string]any{"name": str("Player name")}, "name"),
			handler:     toolPlayerProfile,
		},
		{
			Name: "club_squads",
			Description: "Players grouped by club with counts and average rating, e.g. Brazilian players at Brazilian clubs, " +
				"or the nationalities in one club's squad.",
			InputSchema: obj(map[string]any{
				"nationality":          str("Only players of this nationality (e.g. 'Brazil')"),
				"brazilian_clubs_only": boolean("Only Brazilian clubs (default true)"),
				"limit":                num("Clubs to list (default 20)"),
			}),
			handler: toolClubSquads,
		},
		{
			Name:        "find_team",
			Description: "Resolve a team name and show how it is spelled in each file, its state and match count. Lists matches when the name is ambiguous.",
			InputSchema: obj(map[string]any{"query": str("Team name or fragment")}, "query"),
			handler:     toolFindTeam,
		},
		{
			Name:        "dataset_info",
			Description: "Which files are loaded, row counts, competitions and season coverage, and the list of recognised derbies.",
			InputSchema: obj(map[string]any{}),
			handler:     toolDatasetInfo,
		},
	}
}

// ---------- shared helpers ----------

func (s *Store) team(a Args, k string) (*Team, error) {
	q := a.Str(k)
	if q == "" {
		return nil, nil
	}
	t, _ := s.ResolveTeam(q)
	if t == nil {
		return nil, fmt.Errorf("no team matching %q found in the match data; try find_team", q)
	}
	return t, nil
}

func (s *Store) requireTeam(a Args, k string) (*Team, error) {
	t, err := s.team(a, k)
	if err == nil && t == nil {
		err = fmt.Errorf("%s is required", k)
	}
	return t, err
}

func parseDateArg(a Args, k string) (time.Time, error) {
	v := a.Str(k)
	if v == "" {
		return time.Time{}, nil
	}
	t, _, err := ParseDate(v)
	if err != nil {
		if y, e := strconv.Atoi(v); e == nil {
			return time.Date(y, 1, 1, 0, 0, 0, 0, time.UTC), nil
		}
		return t, fmt.Errorf("%s: %v", k, err)
	}
	return t, nil
}

func venueArg(a Args) (string, error) {
	switch v := Fold(a.Str("venue")); v {
	case "", "any", "all", "both":
		return "", nil
	case "home", "away":
		return v, nil
	}
	return "", fmt.Errorf("venue must be home, away or any")
}

func limitArg(a Args, def, max int) (int, error) {
	n, err := a.Int("limit", def)
	if err != nil {
		return 0, err
	}
	if n <= 0 {
		n = def
	}
	if n > max {
		n = max
	}
	return n, nil
}

// seasonRange reads season / season_from / season_to.
func seasonRange(a Args) (season, from, to int, err error) {
	if season, err = a.Int("season", 0); err != nil {
		return
	}
	if from, err = a.Int("season_from", 0); err != nil {
		return
	}
	to, err = a.Int("season_to", 0)
	return
}

// FormatMatch renders one match line.
func FormatMatch(m *Match) string {
	var extra []string
	extra = append(extra, ShortComp(m.Competition))
	if m.Competition == CompSerieA || m.Competition == CompSerieB || m.Competition == CompSerieC {
		if m.Round != "" {
			extra[0] += " Round " + m.Round
		} else {
			extra[0] += fmt.Sprintf(" %d", m.Season)
		}
	} else if m.Stage != "" {
		extra[0] += " " + m.Stage
	} else if m.Round != "" {
		extra[0] += " round " + m.Round
	}
	if m.Arena != "" {
		extra = append(extra, m.Arena)
	}
	line := fmt.Sprintf("%s: %s %d-%d %s (%s)", m.Date.Format("2006-01-02"), m.Home.Name, m.HomeGoals, m.AwayGoals, m.Away.Name, strings.Join(extra, ", "))
	if d := DerbyName(m.Home, m.Away); d != "" {
		line += " [" + d + "]"
	}
	if st := m.Stats; st != nil && st.HomeShots+st.AwayShots+st.HomeCorners+st.AwayCorners > 0 {
		line += fmt.Sprintf(" — shots %d-%d, corners %d-%d", st.HomeShots, st.AwayShots, st.HomeCorners, st.AwayCorners)
	}
	return line
}

func writeMatches(b *strings.Builder, ms []*Match, limit int) {
	for i, m := range ms {
		if i >= limit {
			fmt.Fprintf(b, "- ... (%d more matches in dataset)\n", len(ms)-limit)
			break
		}
		fmt.Fprintf(b, "- %s\n", FormatMatch(m))
	}
}

func reverse(ms []*Match) []*Match {
	out := make([]*Match, len(ms))
	for i, m := range ms {
		out[len(ms)-1-i] = m
	}
	return out
}

func compLabel(comps []string) string {
	if len(comps) == 0 {
		return "all competitions"
	}
	var parts []string
	for _, c := range comps {
		parts = append(parts, c)
	}
	return strings.Join(parts, ", ")
}

func formatRecordBlock(b *strings.Builder, r Record) {
	fmt.Fprintf(b, "- Matches: %d\n", r.Played)
	fmt.Fprintf(b, "- Wins: %d, Draws: %d, Losses: %d\n", r.W, r.D, r.L)
	fmt.Fprintf(b, "- Goals For: %d, Goals Against: %d (difference %+d)\n", r.GF, r.GA, r.GD())
	fmt.Fprintf(b, "- Win rate: %.1f%%, Points: %d (%.1f%% of available)\n", r.WinRate(), r.Points(), r.PointsRate())
}

// ---------- handlers ----------

func toolSearchMatches(s *Store, a Args) (string, error) {
	var f MatchFilter
	var err error
	if f.Team, err = s.team(a, "team"); err != nil {
		return "", err
	}
	if f.Opponent, err = s.team(a, "opponent"); err != nil {
		return "", err
	}
	if f.Opponent != nil && f.Team == nil {
		f.Team, f.Opponent = f.Opponent, nil
	}
	if f.HomeTeam, err = s.team(a, "home_team"); err != nil {
		return "", err
	}
	if f.AwayTeam, err = s.team(a, "away_team"); err != nil {
		return "", err
	}
	if f.Venue, err = venueArg(a); err != nil {
		return "", err
	}
	if f.Competitions, err = ParseCompetition(a.Str("competition")); err != nil {
		return "", err
	}
	if f.Season, f.SeasonFrom, f.SeasonTo, err = seasonRange(a); err != nil {
		return "", err
	}
	if f.DateFrom, err = parseDateArg(a, "date_from"); err != nil {
		return "", err
	}
	if f.DateTo, err = parseDateArg(a, "date_to"); err != nil {
		return "", err
	}
	if v := a.Str("date_to"); len(v) == 4 { // a bare year means the whole year
		f.DateTo = f.DateTo.AddDate(1, 0, -1)
	}
	f.Stage = a.Str("stage")
	f.Round = a.Str("round")
	f.Derbies = a.Bool("derbies_only", false)
	limit, err := limitArg(a, 20, 500)
	if err != nil {
		return "", err
	}
	ms := s.Filter(f)
	if Fold(a.Str("order")) != "oldest" {
		ms = reverse(ms)
	}

	var b strings.Builder
	title := describeFilter(f)
	if len(ms) == 0 {
		return fmt.Sprintf("No matches found for %s.", title), nil
	}
	fmt.Fprintf(&b, "%s — %d matches found:\n", title, len(ms))
	writeMatches(&b, ms, limit)

	if f.Team != nil && f.Opponent != nil {
		h := s.HeadToHead(f.Team, f.Opponent, MatchFilter{Competitions: f.Competitions, Season: f.Season,
			SeasonFrom: f.SeasonFrom, SeasonTo: f.SeasonTo, DateFrom: f.DateFrom, DateTo: f.DateTo, Stage: f.Stage, Venue: f.Venue})
		fmt.Fprintf(&b, "\nHead-to-head in dataset: %s %d wins, %s %d wins, %d draws (goals %d-%d)\n",
			h.A.Name, h.AWins, h.B.Name, h.BWins, h.Draws, h.AGoals, h.BGoals)
	} else if f.Team != nil {
		r := TeamRecord(f.Team, ms)
		fmt.Fprintf(&b, "\n%s in these matches: %dW %dD %dL, goals %d-%d\n", f.Team.Name, r.W, r.D, r.L, r.GF, r.GA)
	}
	return b.String(), nil
}

func describeFilter(f MatchFilter) string {
	var parts []string
	switch {
	case f.Team != nil && f.Opponent != nil:
		t := f.Team.Name + " vs " + f.Opponent.Name
		if d := DerbyName(f.Team, f.Opponent); d != "" {
			t += " (" + d + ")"
		}
		parts = append(parts, t)
	case f.Team != nil:
		parts = append(parts, f.Team.Name+" matches")
	default:
		parts = append(parts, "Matches")
	}
	if f.Venue != "" {
		parts = append(parts, "("+f.Venue+" games)")
	}
	if f.HomeTeam != nil {
		parts = append(parts, "home side "+f.HomeTeam.Name)
	}
	if f.AwayTeam != nil {
		parts = append(parts, "away side "+f.AwayTeam.Name)
	}
	if f.Derbies {
		parts = append(parts, "(derbies)")
	}
	if len(f.Competitions) > 0 {
		parts = append(parts, "in "+compLabel(f.Competitions))
	}
	if f.Stage != "" {
		parts = append(parts, "stage '"+f.Stage+"'")
	}
	if f.Round != "" {
		parts = append(parts, "round "+f.Round)
	}
	if f.Season != 0 {
		parts = append(parts, fmt.Sprintf("season %d", f.Season))
	}
	if f.SeasonFrom != 0 || f.SeasonTo != 0 {
		parts = append(parts, fmt.Sprintf("seasons %s-%s", yearOrOpen(f.SeasonFrom), yearOrOpen(f.SeasonTo)))
	}
	if !f.DateFrom.IsZero() || !f.DateTo.IsZero() {
		from, to := "…", "…"
		if !f.DateFrom.IsZero() {
			from = f.DateFrom.Format("2006-01-02")
		}
		if !f.DateTo.IsZero() {
			to = f.DateTo.Format("2006-01-02")
		}
		parts = append(parts, "between "+from+" and "+to)
	}
	return strings.Join(parts, " ")
}

func yearOrOpen(y int) string {
	if y == 0 {
		return "…"
	}
	return itoa(y)
}

func toolHeadToHead(s *Store, a Args) (string, error) {
	ta, err := s.requireTeam(a, "team_a")
	if err != nil {
		return "", err
	}
	tb, err := s.requireTeam(a, "team_b")
	if err != nil {
		return "", err
	}
	if ta == tb {
		return "", fmt.Errorf("team_a and team_b resolve to the same team (%s)", ta.Name)
	}
	var f MatchFilter
	if f.Competitions, err = ParseCompetition(a.Str("competition")); err != nil {
		return "", err
	}
	if _, f.SeasonFrom, f.SeasonTo, err = seasonRange(a); err != nil {
		return "", err
	}
	limit, err := limitArg(a, 10, 200)
	if err != nil {
		return "", err
	}
	h := s.HeadToHead(ta, tb, f)
	var b strings.Builder
	title := ta.Name + " vs " + tb.Name
	if d := DerbyName(ta, tb); d != "" {
		title += " (" + d + ")"
	}
	fmt.Fprintf(&b, "%s — head-to-head (%s):\n", title, compLabel(f.Competitions))
	if len(h.Matches) == 0 {
		b.WriteString("No meetings found in the dataset.\n")
		return b.String(), nil
	}
	fmt.Fprintf(&b, "- Meetings: %d (%s to %s)\n", len(h.Matches), h.Matches[0].Date.Format("2006-01-02"), h.Matches[len(h.Matches)-1].Date.Format("2006-01-02"))
	fmt.Fprintf(&b, "- %s wins: %d, %s wins: %d, Draws: %d\n", ta.Name, h.AWins, tb.Name, h.BWins, h.Draws)
	fmt.Fprintf(&b, "- Goals: %s %d, %s %d\n", ta.Name, h.AGoals, tb.Name, h.BGoals)
	byComp := map[string][3]int{}
	for _, m := range h.Matches {
		c := byComp[m.Competition]
		switch w := m.Winner(); w {
		case ta:
			c[0]++
		case tb:
			c[1]++
		default:
			c[2]++
		}
		byComp[m.Competition] = c
	}
	if len(byComp) > 1 {
		b.WriteString("- By competition:\n")
		for _, c := range AllCompetitions {
			if v, ok := byComp[c]; ok {
				fmt.Fprintf(&b, "  - %s: %s %d, %s %d, draws %d\n", c, ta.Name, v[0], tb.Name, v[1], v[2])
			}
		}
	}
	b.WriteString("\nMost recent meetings:\n")
	writeMatches(&b, reverse(h.Matches), limit)
	big := append([]*Match(nil), h.Matches...)
	SortBiggestWins(big)
	if len(big) > 0 && margin(big[0]) > 0 {
		b.WriteString("\nBiggest wins in the fixture:\n")
		n := 0
		for _, m := range big {
			if n == 3 || margin(m) == 0 {
				break
			}
			fmt.Fprintf(&b, "- %s\n", FormatMatch(m))
			n++
		}
	}
	return b.String(), nil
}

func toolTeamRecord(s *Store, a Args) (string, error) {
	t, err := s.requireTeam(a, "team")
	if err != nil {
		return "", err
	}
	f := MatchFilter{Team: t, Canonical: true}
	if f.Venue, err = venueArg(a); err != nil {
		return "", err
	}
	if f.Competitions, err = ParseCompetition(a.Str("competition")); err != nil {
		return "", err
	}
	if f.Season, f.SeasonFrom, f.SeasonTo, err = seasonRange(a); err != nil {
		return "", err
	}
	ms := s.Filter(f)
	var b strings.Builder
	label := t.Name
	if f.Venue != "" {
		label += " " + f.Venue
	}
	label += " record"
	var scope []string
	if f.Season != 0 {
		scope = append(scope, itoa(f.Season))
	}
	if f.SeasonFrom != 0 || f.SeasonTo != 0 {
		scope = append(scope, yearOrOpen(f.SeasonFrom)+"-"+yearOrOpen(f.SeasonTo))
	}
	if len(f.Competitions) > 0 {
		scope = append(scope, ShortComp(f.Competitions[0]))
	} else {
		scope = append(scope, "all competitions")
	}
	fmt.Fprintf(&b, "%s (%s):\n", label, strings.Join(scope, " "))
	if len(ms) == 0 {
		b.WriteString("No matches found.\n")
		return b.String(), nil
	}
	r := TeamRecord(t, ms)
	formatRecordBlock(&b, r)
	if f.Venue == "" {
		hr := TeamRecord(t, s.Filter(withVenue(f, "home")))
		ar := TeamRecord(t, s.Filter(withVenue(f, "away")))
		fmt.Fprintf(&b, "- Home: %dW %dD %dL (GF %d, GA %d, win rate %.1f%%)\n", hr.W, hr.D, hr.L, hr.GF, hr.GA, hr.WinRate())
		fmt.Fprintf(&b, "- Away: %dW %dD %dL (GF %d, GA %d, win rate %.1f%%)\n", ar.W, ar.D, ar.L, ar.GF, ar.GA, ar.WinRate())
	}
	if len(f.Competitions) == 0 {
		b.WriteString("\nBy competition:\n")
		for _, c := range AllCompetitions {
			cr := TeamRecord(t, filterComp(ms, c))
			if cr.Played > 0 {
				fmt.Fprintf(&b, "- %s: %d played, %dW %dD %dL, goals %d-%d\n", c, cr.Played, cr.W, cr.D, cr.L, cr.GF, cr.GA)
			}
		}
	}
	if f.Season != 0 && len(f.Competitions) <= 1 {
		for _, c := range []string{CompSerieA, CompSerieB, CompSerieC} {
			if len(f.Competitions) == 1 && f.Competitions[0] != c {
				continue
			}
			if pos, n := s.LeaguePosition(t, c, f.Season); pos > 0 {
				fmt.Fprintf(&b, "- League finish: %d of %d in %s %d (calculated)\n", pos, n, c, f.Season)
			}
		}
	}
	return b.String(), nil
}

func withVenue(f MatchFilter, v string) MatchFilter { f.Venue = v; return f }

func filterComp(ms []*Match, c string) []*Match {
	var out []*Match
	for _, m := range ms {
		if m.Competition == c {
			out = append(out, m)
		}
	}
	return out
}

// LeaguePosition returns t's final position in a league season (0 if absent).
func (s *Store) LeaguePosition(t *Team, comp string, season int) (int, int) {
	rs, _ := s.Standings(comp, season)
	for i, r := range rs {
		if r.Team == t {
			return i + 1, len(rs)
		}
	}
	return 0, len(rs)
}

// SeasonComplete reports whether every fixture of a league season is present.
func (s *Store) SeasonComplete(comp string, season int) bool {
	rs, ms := s.Standings(comp, season)
	return len(rs) > 1 && len(ms) >= len(rs)*(len(rs)-1)
}

// CupWinner returns the winner of a cup final tie for a season (nil if unknown).
func (s *Store) CupWinner(comp string, season int) (*Team, *Tie) {
	ties := Ties(s.Filter(MatchFilter{Competitions: []string{comp}, Season: season, Stage: "final"}))
	for i := range ties {
		if Fold(ties[i].Stage) == "final" {
			return ties[i].Winner(), &ties[i]
		}
	}
	return nil, nil
}

func toolTeamOverview(s *Store, a Args) (string, error) {
	t, err := s.requireTeam(a, "team")
	if err != nil {
		return "", err
	}
	all := s.Filter(MatchFilter{Team: t})
	var b strings.Builder
	fmt.Fprintf(&b, "%s", t.Name)
	if t.State != "" {
		fmt.Fprintf(&b, " (%s)", t.State)
	}
	fmt.Fprintf(&b, " — %d matches in the dataset\n", len(all))
	if len(all) > 0 {
		fmt.Fprintf(&b, "First match: %s\nLatest match: %s\n", FormatMatch(all[0]), FormatMatch(all[len(all)-1]))
	}
	b.WriteString("\nCompetitions played:\n")
	for _, c := range AllCompetitions {
		ms := filterComp(all, c)
		if len(ms) == 0 {
			continue
		}
		seasons := map[int]bool{}
		for _, m := range ms {
			seasons[m.Season] = true
		}
		r := TeamRecord(t, ms)
		fmt.Fprintf(&b, "- %s: %d matches over %d seasons (%s), %dW %dD %dL, goals %d-%d\n",
			c, r.Played, len(seasons), seasonSpan(seasons), r.W, r.D, r.L, r.GF, r.GA)
	}
	// League finishes.
	var finishes []string
	var titles []string
	for _, c := range []string{CompSerieA, CompSerieB, CompSerieC} {
		for _, y := range s.Seasons(c) {
			if pos, n := s.LeaguePosition(t, c, y); pos > 0 {
				finishes = append(finishes, fmt.Sprintf("%d %s: %d/%d", y, ShortComp(c), pos, n))
				if pos == 1 && c == CompSerieA && s.SeasonComplete(c, y) {
					titles = append(titles, fmt.Sprintf("Brasileirão %d", y))
				}
			}
		}
	}
	for _, c := range []string{CompCopaBrasil, CompLibertadores} {
		for _, y := range s.Seasons(c) {
			if w, _ := s.CupWinner(c, y); w == t {
				titles = append(titles, fmt.Sprintf("%s %d", c, y))
			}
		}
	}
	if len(finishes) > 0 {
		b.WriteString("\nLeague finishes (calculated from results):\n- " + strings.Join(finishes, "\n- ") + "\n")
	}
	if len(titles) > 0 {
		b.WriteString("\nTitles inferred from the data: " + strings.Join(titles, ", ") + "\n")
	}
	ps := s.FilterPlayers(PlayerFilter{ClubTeam: t})
	if len(ps) > 0 {
		SortPlayers(ps, "overall")
		fmt.Fprintf(&b, "\nFIFA 19 squad: %d players, average overall %.1f. Top players:\n", len(ps), avgOverall(ps))
		for i, p := range ps {
			if i == 5 {
				break
			}
			fmt.Fprintf(&b, "- %s - Overall: %d, Position: %s, Nationality: %s\n", p.Name, p.Overall, p.Position, p.Nationality)
		}
	} else {
		b.WriteString("\nNo FIFA 19 players are listed for this club (the game only licensed 15 Brazilian clubs).\n")
	}
	return b.String(), nil
}

func seasonSpan(seasons map[int]bool) string {
	var ys []int
	for y := range seasons {
		ys = append(ys, y)
	}
	sort.Ints(ys)
	var parts []string
	for i := 0; i < len(ys); {
		j := i
		for j+1 < len(ys) && ys[j+1] == ys[j]+1 {
			j++
		}
		if i == j {
			parts = append(parts, itoa(ys[i]))
		} else {
			parts = append(parts, fmt.Sprintf("%d-%d", ys[i], ys[j]))
		}
		i = j + 1
	}
	return strings.Join(parts, ", ")
}

func avgOverall(ps []*Player) float64 {
	if len(ps) == 0 {
		return 0
	}
	sum := 0
	for _, p := range ps {
		sum += p.Overall
	}
	return float64(sum) / float64(len(ps))
}

func toolStandings(s *Store, a Args) (string, error) {
	season, err := a.Int("season", 0)
	if err != nil {
		return "", err
	}
	if season == 0 {
		return "", fmt.Errorf("season is required")
	}
	comps, err := ParseCompetition(a.Str("competition"))
	if err != nil {
		return "", err
	}
	comp := CompSerieA
	if len(comps) == 1 {
		comp = comps[0]
	}
	if comp == CompCopaBrasil || comp == CompLibertadores {
		return "", fmt.Errorf("%s is a knockout competition; use knockout_bracket", comp)
	}
	limit, err := limitArg(a, 100, 100)
	if err != nil {
		return "", err
	}
	rs, ms := s.Standings(comp, season)
	if len(rs) == 0 {
		return fmt.Sprintf("No %s matches found for %d. Série A data covers 2003-2023; Série B and C cover 2014-2023.", comp, season), nil
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%d %s Final Standings (calculated from %d matches; source: %s):\n", season, comp, len(ms), SourceSummary(ms))
	releg := RelegationSpots(comp, season, len(rs))
	expected := len(rs) * (len(rs) - 1)
	for i, r := range rs {
		if i >= limit && i < len(rs)-releg {
			continue
		}
		note := ""
		if i == 0 && len(ms) >= expected {
			note = " - Champion"
		} else if i == 0 {
			note = " - Leader"
		}
		if releg > 0 && i >= len(rs)-releg {
			note = " - Relegated"
		}
		fmt.Fprintf(&b, "%d. %s - %d pts (%dW, %dD, %dL, GF %d, GA %d, GD %+d)%s\n",
			i+1, r.Team.Name, r.Points(), r.W, r.D, r.L, r.GF, r.GA, r.GD(), note)
	}
	if len(ms) < expected {
		fmt.Fprintf(&b, "\nNote: only %d of %d fixtures are in the data, so the table may be incomplete.\n", len(ms), expected)
	}
	if releg > 0 {
		var down []string
		for _, r := range rs[len(rs)-releg:] {
			down = append(down, r.Team.Name)
		}
		fmt.Fprintf(&b, "\nRelegated (bottom %d): %s\n", releg, strings.Join(down, ", "))
	}
	if comp == CompSerieA && len(rs) > 0 {
		if len(ms) >= expected {
			fmt.Fprintf(&b, "Champion: %s with %d points\n", rs[0].Team.Name, rs[0].Points())
		} else {
			fmt.Fprintf(&b, "Leader in the available data: %s with %d points (incomplete season data — the real champion may differ)\n", rs[0].Team.Name, rs[0].Points())
		}
	}
	return b.String(), nil
}

type metricDef struct {
	label string
	value func(Record) float64
	asc   bool // lower is better
	rate  bool
	fmt   string
}

var metrics = map[string]metricDef{
	"points":          {"points", func(r Record) float64 { return float64(r.Points()) }, false, false, "%.0f"},
	"wins":            {"wins", func(r Record) float64 { return float64(r.W) }, false, false, "%.0f"},
	"draws":           {"draws", func(r Record) float64 { return float64(r.D) }, false, false, "%.0f"},
	"losses":          {"losses", func(r Record) float64 { return float64(r.L) }, false, false, "%.0f"},
	"win_rate":        {"win rate", func(r Record) float64 { return r.WinRate() }, false, true, "%.1f%%"},
	"points_rate":     {"points won", func(r Record) float64 { return r.PointsRate() }, false, true, "%.1f%%"},
	"goals_for":       {"goals scored", func(r Record) float64 { return float64(r.GF) }, false, false, "%.0f"},
	"goals_against":   {"goals conceded", func(r Record) float64 { return float64(r.GA) }, true, false, "%.0f"},
	"goal_difference": {"goal difference", func(r Record) float64 { return float64(r.GD()) }, false, false, "%+.0f"},
	"goals_per_game":  {"goals per game", func(r Record) float64 { return ratio(r.GF, r.Played) }, false, true, "%.2f"},
	"clean_sheets":    {"clean sheets", func(r Record) float64 { return float64(r.CleanSheets) }, false, false, "%.0f"},
}

func toolRankTeams(s *Store, a Args) (string, error) {
	mname := strings.ReplaceAll(Fold(a.Str("metric")), " ", "_")
	if mname == "" {
		mname = "win_rate"
	}
	md, ok := metrics[mname]
	if !ok {
		var names []string
		for k := range metrics {
			names = append(names, k)
		}
		sort.Strings(names)
		return "", fmt.Errorf("unknown metric %q; use one of %s", a.Str("metric"), strings.Join(names, ", "))
	}
	f := MatchFilter{Canonical: true}
	var err error
	if f.Competitions, err = ParseCompetition(a.Str("competition")); err != nil {
		return "", err
	}
	if a.Str("competition") == "" {
		f.Competitions = []string{CompSerieA}
	}
	if f.Season, f.SeasonFrom, f.SeasonTo, err = seasonRange(a); err != nil {
		return "", err
	}
	venue, err := venueArg(a)
	if err != nil {
		return "", err
	}
	limit, err := limitArg(a, 10, 200)
	if err != nil {
		return "", err
	}
	defMin := 1
	if md.rate {
		defMin = 10
	}
	minM, err := a.Int("min_matches", defMin)
	if err != nil {
		return "", err
	}
	ms := s.Filter(f)
	rs := Records(ms, venue)
	var kept []Record
	for _, r := range rs {
		if r.Played >= minM {
			kept = append(kept, r)
		}
	}
	asc := md.asc != a.Bool("ascending", false)
	sort.SliceStable(kept, func(i, j int) bool {
		vi, vj := md.value(kept[i]), md.value(kept[j])
		if vi != vj {
			if asc {
				return vi < vj
			}
			return vi > vj
		}
		if kept[i].Played != kept[j].Played {
			return kept[i].Played > kept[j].Played
		}
		return kept[i].Team.Name < kept[j].Team.Name
	})
	var b strings.Builder
	scope := compLabel(f.Competitions)
	if f.Season != 0 {
		scope += fmt.Sprintf(" %d", f.Season)
	}
	if f.SeasonFrom != 0 || f.SeasonTo != 0 {
		scope += " " + yearOrOpen(f.SeasonFrom) + "-" + yearOrOpen(f.SeasonTo)
	}
	vlabel := ""
	if venue != "" {
		vlabel = " (" + venue + " games only)"
	}
	order := "highest"
	if asc {
		order = "lowest"
	}
	fmt.Fprintf(&b, "Teams ranked by %s, %s first%s — %s, %d matches, min %d games:\n", md.label, order, vlabel, scope, len(ms), minM)
	if len(kept) == 0 {
		b.WriteString("No teams found.\n")
		return b.String(), nil
	}
	for i, r := range kept {
		if i >= limit {
			break
		}
		fmt.Fprintf(&b, "%d. %s - "+md.fmt+" %s (%d played: %dW %dD %dL, GF %d, GA %d, win rate %.1f%%)\n",
			i+1, r.Team.Name, md.value(r), md.label, r.Played, r.W, r.D, r.L, r.GF, r.GA, r.WinRate())
	}
	return b.String(), nil
}

func toolBiggestWins(s *Store, a Args) (string, error) {
	var f MatchFilter
	var err error
	if f.Competitions, err = ParseCompetition(a.Str("competition")); err != nil {
		return "", err
	}
	if f.Season, f.SeasonFrom, f.SeasonTo, err = seasonRange(a); err != nil {
		return "", err
	}
	t, err := s.team(a, "team")
	if err != nil {
		return "", err
	}
	f.Team = t
	limit, err := limitArg(a, 10, 100)
	if err != nil {
		return "", err
	}
	var ms []*Match
	for _, m := range s.Filter(f) {
		if margin(m) == 0 || (t != nil && m.Winner() != t) {
			continue
		}
		ms = append(ms, m)
	}
	SortBiggestWins(ms)
	var b strings.Builder
	scope := compLabel(f.Competitions)
	if f.Season != 0 {
		scope += fmt.Sprintf(" %d", f.Season)
	}
	if t != nil {
		scope = t.Name + ", " + scope
	}
	fmt.Fprintf(&b, "Biggest victories (%s):\n", scope)
	if len(ms) == 0 {
		b.WriteString("No wins found.\n")
	}
	for i, m := range ms {
		if i >= limit {
			break
		}
		fmt.Fprintf(&b, "%d. %s — margin %d\n", i+1, FormatMatch(m), margin(m))
	}
	return b.String(), nil
}

func writeAggregate(b *strings.Builder, label string, ms []*Match) {
	ag := Summarise(ms)
	fmt.Fprintf(b, "%s:\n", label)
	if ag.Matches == 0 {
		b.WriteString("- No matches\n")
		return
	}
	fmt.Fprintf(b, "- Matches: %d, Goals: %d\n", ag.Matches, ag.Goals)
	fmt.Fprintf(b, "- Average goals per match: %.2f (home %.2f, away %.2f)\n", ratio(ag.Goals, ag.Matches), ratio(ag.HomeGoals, ag.Matches), ratio(ag.AwayGoals, ag.Matches))
	fmt.Fprintf(b, "- Home win rate: %.1f%%, Away win rate: %.1f%%, Draw rate: %.1f%%\n", pct(ag.HomeWins, ag.Matches), pct(ag.AwayWins, ag.Matches), pct(ag.Draws, ag.Matches))
	if ag.StatsMatches > 0 {
		fmt.Fprintf(b, "- Extended stats (%d matches): %.1f corners and %.1f shots per match\n", ag.StatsMatches, ratio(ag.Corners, ag.StatsMatches), ratio(ag.Shots, ag.StatsMatches))
	}
	big := append([]*Match(nil), ms...)
	SortBiggestWins(big)
	fmt.Fprintf(b, "- Biggest win: %s\n", FormatMatch(big[0]))
	hs := append([]*Match(nil), ms...)
	sort.SliceStable(hs, func(i, j int) bool {
		return hs[i].HomeGoals+hs[i].AwayGoals > hs[j].HomeGoals+hs[j].AwayGoals
	})
	fmt.Fprintf(b, "- Highest scoring: %s\n", FormatMatch(hs[0]))
}

func toolCompetitionStats(s *Store, a Args) (string, error) {
	comps, err := ParseCompetition(a.Str("competition"))
	if err != nil {
		return "", err
	}
	if a.Str("competition") == "" {
		comps = []string{CompSerieA}
	}
	season, err := a.Int("season", 0)
	if err != nil {
		return "", err
	}
	seasons, err := a.IntList("seasons")
	if err != nil {
		return "", err
	}
	if season != 0 {
		seasons = append([]int{season}, seasons...)
	}
	var b strings.Builder
	if len(seasons) == 0 {
		ms := s.Filter(MatchFilter{Competitions: comps, Canonical: true})
		writeAggregate(&b, compLabel(comps)+" — all seasons in the data", ms)
		// Per-season trend line.
		bySeason := map[int][]*Match{}
		for _, m := range ms {
			bySeason[m.Season] = append(bySeason[m.Season], m)
		}
		var ys []int
		for y := range bySeason {
			ys = append(ys, y)
		}
		sort.Ints(ys)
		b.WriteString("\nGoals per match by season:\n")
		for _, y := range ys {
			ag := Summarise(bySeason[y])
			fmt.Fprintf(&b, "- %d: %.2f (%d matches, home wins %.1f%%)\n", y, ratio(ag.Goals, ag.Matches), ag.Matches, pct(ag.HomeWins, ag.Matches))
		}
		return b.String(), nil
	}
	for i, y := range seasons {
		if i > 0 {
			b.WriteString("\n")
		}
		ms := s.Filter(MatchFilter{Competitions: comps, Season: y, Canonical: true})
		writeAggregate(&b, fmt.Sprintf("%s %d", compLabel(comps), y), ms)
		if len(comps) == 1 && (comps[0] == CompSerieA || comps[0] == CompSerieB || comps[0] == CompSerieC) && len(ms) > 0 {
			rs, _ := s.Standings(comps[0], y)
			fmt.Fprintf(&b, "- Champion (calculated): %s, %d pts\n", rs[0].Team.Name, rs[0].Points())
			best := append([]Record(nil), rs...)
			sort.SliceStable(best, func(i, j int) bool { return best[i].GF > best[j].GF })
			fmt.Fprintf(&b, "- Top scoring team: %s, %d goals\n", best[0].Team.Name, best[0].GF)
		}
		if len(comps) == 1 && (comps[0] == CompCopaBrasil || comps[0] == CompLibertadores) {
			if w, _ := s.CupWinner(comps[0], y); w != nil {
				fmt.Fprintf(&b, "- Winner: %s\n", w.Name)
			}
		}
	}
	if len(seasons) > 1 {
		b.WriteString("\nComparison:\n")
		fmt.Fprintf(&b, "| Season | Matches | Goals/match | Home win %% | Draw %% | Away win %% |\n|---|---|---|---|---|---|\n")
		for _, y := range seasons {
			ag := Summarise(s.Filter(MatchFilter{Competitions: comps, Season: y, Canonical: true}))
			fmt.Fprintf(&b, "| %d | %d | %.2f | %.1f | %.1f | %.1f |\n", y, ag.Matches, ratio(ag.Goals, ag.Matches), pct(ag.HomeWins, ag.Matches), pct(ag.Draws, ag.Matches), pct(ag.AwayWins, ag.Matches))
		}
	}
	return b.String(), nil
}

func toolKnockout(s *Store, a Args) (string, error) {
	comps, err := ParseCompetition(a.Str("competition"))
	if err != nil {
		return "", err
	}
	if len(comps) != 1 || (comps[0] != CompLibertadores && comps[0] != CompCopaBrasil) {
		return "", fmt.Errorf("competition must be Libertadores or Copa do Brasil")
	}
	comp := comps[0]
	season, err := a.Int("season", 0)
	if err != nil {
		return "", err
	}
	stage := a.Str("stage")
	f := MatchFilter{Competitions: comps, Season: season, Stage: stage}
	ms := s.Filter(f)
	ties := Ties(ms)
	var keep []Tie
	for _, t := range ties {
		if stage == "" || NormalizeStage(t.Stage) == NormalizeStage(stage) {
			keep = append(keep, t)
		}
	}
	// Order: season, stage, first leg.
	sort.SliceStable(keep, func(i, j int) bool {
		si, sj := keep[i].Legs[0].Season, keep[j].Legs[0].Season
		if si != sj {
			return si < sj
		}
		if oi, oj := StageOrder(keep[i].Stage), StageOrder(keep[j].Stage); oi != oj {
			return oi < oj
		}
		return keep[i].FirstLeg.Before(keep[j].FirstLeg)
	})
	var b strings.Builder
	title := comp
	if season != 0 {
		title = fmt.Sprintf("%d %s", season, comp)
	}
	if stage != "" {
		title += " — " + stage
	}
	fmt.Fprintf(&b, "%s knockout ties (aggregate scores from the data):\n", title)
	if len(keep) == 0 {
		b.WriteString("No knockout matches found. Libertadores covers 2013-2022; Copa do Brasil stages are labelled for 2012-2021.\n")
		return b.String(), nil
	}
	lastSeason, lastStage := 0, ""
	for _, t := range keep {
		y := t.Legs[0].Season
		if y != lastSeason || t.Stage != lastStage {
			if season == 0 && y != lastSeason {
				fmt.Fprintf(&b, "\n%d:\n", y)
			}
			if season != 0 || stage == "" {
				fmt.Fprintf(&b, "\n%s:\n", titleCase(t.Stage))
			}
			lastSeason, lastStage = y, t.Stage
		}
		winner := "level on aggregate (decided on penalties/away goals — not in data)"
		if w := t.Winner(); w != nil {
			winner = w.Name + " advance"
			if Fold(t.Stage) == "final" {
				winner = w.Name + " win the title"
			}
		}
		var legs []string
		for _, m := range t.Legs {
			legs = append(legs, fmt.Sprintf("%s %s %d-%d %s", m.Date.Format("2006-01-02"), m.Home.Name, m.HomeGoals, m.AwayGoals, m.Away.Name))
		}
		fmt.Fprintf(&b, "- %s %d-%d %s on aggregate → %s [%s]\n", t.A.Name, t.AGoals, t.BGoals, t.B.Name, winner, strings.Join(legs, "; "))
	}
	return b.String(), nil
}

func titleCase(s string) string {
	if s == "" {
		return s
	}
	return strings.ToUpper(s[:1]) + s[1:]
}

func toolSearchPlayers(s *Store, a Args) (string, error) {
	f := PlayerFilter{Name: a.Str("name"), Nationality: a.Str("nationality"), BrazilianClubsOnly: a.Bool("brazilian_clubs_only", false)}
	if pos := a.Str("position"); pos != "" {
		f.Positions = PositionCodes(pos)
	}
	var err error
	if f.MinOverall, err = a.Int("min_overall", 0); err != nil {
		return "", err
	}
	if f.MaxAge, err = a.Int("max_age", 0); err != nil {
		return "", err
	}
	limit, err := limitArg(a, 20, 500)
	if err != nil {
		return "", err
	}
	var clubNote string
	if c := a.Str("club"); c != "" {
		f.Club = c
		// Prefer the FIFA club whose name matches directly; otherwise map a
		// Brazilian club name through the team registry.
		direct := s.FilterPlayers(PlayerFilter{Club: c})
		if len(direct) == 0 {
			if t, _ := s.ResolveTeam(c); t != nil {
				f.ClubTeam = t
				if len(s.FilterPlayers(PlayerFilter{ClubTeam: t})) == 0 {
					clubNote = fmt.Sprintf("%s has no players in FIFA 19 — the game only licensed 15 Brazilian clubs (%s).",
						t.Name, strings.Join(brazilianFIFAClubs, ", "))
				}
			}
		} else if t, _ := s.ResolveTeam(c); t != nil && t.State != "" && brStates[t.State] {
			// Santos (SP) must not match Santos Laguna; use the mapping.
			if len(s.FilterPlayers(PlayerFilter{ClubTeam: t})) > 0 {
				f.ClubTeam = t
			}
		}
	}
	ps := s.FilterPlayers(f)
	SortPlayers(ps, a.Str("sort_by"))
	var b strings.Builder
	var crit []string
	if f.Name != "" {
		crit = append(crit, "name '"+f.Name+"'")
	}
	if f.Nationality != "" {
		crit = append(crit, "nationality "+f.Nationality)
	}
	if f.ClubTeam != nil {
		crit = append(crit, "club "+f.ClubTeam.Name)
	} else if f.Club != "" {
		crit = append(crit, "club '"+f.Club+"'")
	}
	if a.Str("position") != "" {
		crit = append(crit, "position "+a.Str("position"))
	}
	if f.MinOverall > 0 {
		crit = append(crit, fmt.Sprintf("overall ≥ %d", f.MinOverall))
	}
	if f.MaxAge > 0 {
		crit = append(crit, fmt.Sprintf("age ≤ %d", f.MaxAge))
	}
	if f.BrazilianClubsOnly {
		crit = append(crit, "Brazilian clubs only")
	}
	if len(crit) == 0 {
		crit = append(crit, "all players")
	}
	fmt.Fprintf(&b, "FIFA 19 players (%s): %d found\n", strings.Join(crit, ", "), len(ps))
	if clubNote != "" {
		b.WriteString(clubNote + "\n")
	}
	for i, p := range ps {
		if i >= limit {
			fmt.Fprintf(&b, "... (%d more)\n", len(ps)-limit)
			break
		}
		fmt.Fprintf(&b, "%d. %s - Overall: %d, Potential: %d, Position: %s, Age: %d, Nationality: %s, Club: %s\n",
			i+1, p.Name, p.Overall, p.Potential, orDash(p.Position), p.Age, p.Nationality, orDash(p.Club))
	}
	if len(ps) == 0 && f.Name != "" {
		if sug := s.FuzzyPlayers(f.Name, 5); len(sug) > 0 {
			b.WriteString("Similar names:\n")
			for _, p := range sug {
				fmt.Fprintf(&b, "- %s (%s, %s, overall %d)\n", p.Name, orDash(p.Club), p.Nationality, p.Overall)
			}
		}
	}
	if len(ps) > 1 {
		fmt.Fprintf(&b, "Average overall: %.1f\n", avgOverall(ps))
	}
	return b.String(), nil
}

func orDash(s string) string {
	if s == "" {
		return "-"
	}
	return s
}

func toolPlayerProfile(s *Store, a Args) (string, error) {
	name := a.Str("name")
	if name == "" {
		return "", fmt.Errorf("name is required")
	}
	ps := s.FilterPlayers(PlayerFilter{Name: name})
	// Prefer exact (folded) name matches.
	var exact []*Player
	for _, p := range ps {
		if Fold(p.Name) == Fold(name) {
			exact = append(exact, p)
		}
	}
	if len(exact) > 0 {
		ps = exact
	}
	SortPlayers(ps, "overall")
	var b strings.Builder
	if len(ps) == 0 {
		fmt.Fprintf(&b, "No player named %q in the FIFA 19 data.\n", name)
		if sug := s.FuzzyPlayers(name, 8); len(sug) > 0 {
			b.WriteString("Closest names:\n")
			for _, p := range sug {
				fmt.Fprintf(&b, "- %s (%s, %s, %s, overall %d)\n", p.Name, orDash(p.Position), orDash(p.Club), p.Nationality, p.Overall)
			}
		}
		return b.String(), nil
	}
	if len(ps) > 1 {
		fmt.Fprintf(&b, "%d players match %q; showing the highest rated. Others:\n", len(ps), name)
		for i, p := range ps[1:] {
			if i == 10 {
				break
			}
			fmt.Fprintf(&b, "- %s (%s, %s, overall %d)\n", p.Name, orDash(p.Club), p.Nationality, p.Overall)
		}
		b.WriteString("\n")
	}
	p := ps[0]
	fmt.Fprintf(&b, "%s\n", p.Name)
	fmt.Fprintf(&b, "- Nationality: %s, Age: %d\n", p.Nationality, p.Age)
	fmt.Fprintf(&b, "- Club: %s", orDash(p.Club))
	if p.ClubTeam != nil {
		fmt.Fprintf(&b, " (Brazilian club, %d matches in the match data)", s.MatchCount(p.ClubTeam))
	}
	b.WriteString("\n")
	fmt.Fprintf(&b, "- Position: %s, Jersey: %s, Preferred foot: %s\n", orDash(p.Position), orDash(p.JerseyNumber), orDash(p.PreferredFoot))
	fmt.Fprintf(&b, "- Overall: %d, Potential: %d\n", p.Overall, p.Potential)
	fmt.Fprintf(&b, "- Height: %s, Weight: %s\n", orDash(p.Height), orDash(p.Weight))
	fmt.Fprintf(&b, "- Value: %s, Wage: %s, Joined: %s, Contract until: %s\n", orDash(p.Value), orDash(p.Wage), orDash(p.Joined), orDash(p.ContractUntil))
	if sk := TopSkills(p, 6); len(sk) > 0 {
		fmt.Fprintf(&b, "- Top attributes: %s\n", strings.Join(sk, ", "))
	}
	return b.String(), nil
}

func toolClubSquads(s *Store, a Args) (string, error) {
	brOnly := a.Bool("brazilian_clubs_only", true)
	limit, err := limitArg(a, 20, 1000)
	if err != nil {
		return "", err
	}
	ps := s.FilterPlayers(PlayerFilter{Nationality: a.Str("nationality"), BrazilianClubsOnly: brOnly})
	type agg struct {
		name string
		n    int
		sum  int
		best *Player
	}
	by := map[string]*agg{}
	for _, p := range ps {
		if p.Club == "" {
			continue
		}
		name := p.Club
		if p.ClubTeam != nil {
			name = p.ClubTeam.Name
		}
		g := by[name]
		if g == nil {
			g = &agg{name: name}
			by[name] = g
		}
		g.n++
		g.sum += p.Overall
		if g.best == nil || p.Overall > g.best.Overall {
			g.best = p
		}
	}
	var list []*agg
	for _, g := range by {
		list = append(list, g)
	}
	sort.Slice(list, func(i, j int) bool {
		if list[i].n != list[j].n {
			return list[i].n > list[j].n
		}
		ai, aj := ratio(list[i].sum, list[i].n), ratio(list[j].sum, list[j].n)
		if ai != aj {
			return ai > aj
		}
		return list[i].name < list[j].name
	})
	var b strings.Builder
	who := "Players"
	if n := a.Str("nationality"); n != "" {
		who = n + " players"
	}
	where := "all clubs"
	if brOnly {
		where = "Brazilian clubs"
	}
	fmt.Fprintf(&b, "%s at %s (FIFA 19): %d players in %d clubs\n", who, where, len(ps), len(list))
	for i, g := range list {
		if i >= limit {
			fmt.Fprintf(&b, "- ... (%d more clubs)\n", len(list)-limit)
			break
		}
		fmt.Fprintf(&b, "- %s: %d players (avg rating: %.0f, best: %s %d)\n", g.name, g.n, ratio(g.sum, g.n), g.best.Name, g.best.Overall)
	}
	if brOnly {
		b.WriteString("Note: Flamengo, Palmeiras, Corinthians and São Paulo are not in the FIFA 19 database.\n")
	}
	return b.String(), nil
}

func toolFindTeam(s *Store, a Args) (string, error) {
	q := a.Str("query")
	if q == "" {
		return "", fmt.Errorf("query is required")
	}
	_, hits := s.ResolveTeam(q)
	if len(hits) == 0 {
		return fmt.Sprintf("No team matches %q.", q), nil
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Teams matching %q (best first):\n", q)
	for i, t := range hits {
		if i == 15 {
			fmt.Fprintf(&b, "... (%d more)\n", len(hits)-15)
			break
		}
		var raws []string
		for r := range t.RawNames {
			raws = append(raws, r)
		}
		sort.Strings(raws)
		comps := map[string]int{}
		for _, m := range s.Filter(MatchFilter{Team: t}) {
			comps[ShortComp(m.Competition)]++
		}
		var cl []string
		for _, c := range AllCompetitions {
			if n := comps[ShortComp(c)]; n > 0 {
				cl = append(cl, fmt.Sprintf("%s %d", ShortComp(c), n))
			}
		}
		fmt.Fprintf(&b, "%d. %s [state/country: %s] — %d matches (%s)\n   spellings in data: %s\n",
			i+1, t.Name, orDash(t.State), s.MatchCount(t), strings.Join(cl, ", "), strings.Join(raws, " | "))
	}
	return b.String(), nil
}

func toolDatasetInfo(s *Store, a Args) (string, error) {
	var b strings.Builder
	b.WriteString("Loaded files (data/kaggle):\n")
	for _, src := range s.Sources {
		fmt.Fprintf(&b, "- %s: %d rows, %d loaded", src.File, src.Rows, src.Loaded)
		if src.Notes != "" {
			fmt.Fprintf(&b, " (%s)", src.Notes)
		}
		b.WriteString("\n")
	}
	fmt.Fprintf(&b, "\nAfter de-duplicating games present in several files: %d unique matches, %d teams, %d players.\n",
		len(s.Matches), len(s.Teams.Teams()), len(s.Players))
	b.WriteString("\nCoverage by competition:\n")
	for _, c := range AllCompetitions {
		seasons := map[int]bool{}
		n := 0
		for _, m := range s.Matches {
			if m.Competition == c {
				seasons[m.Season] = true
				n++
			}
		}
		fmt.Fprintf(&b, "- %s: %d matches, seasons %s\n", c, n, seasonSpan(seasons))
	}
	b.WriteString("\nRecognised derbies: ")
	var names []string
	for _, d := range derbies {
		names = append(names, fmt.Sprintf("%s (%s v %s)", d.Name, s.Teams.Get(d.A).Name, s.Teams.Get(d.B).Name))
	}
	b.WriteString(strings.Join(names, "; ") + "\n")
	return b.String(), nil
}

// CallTool runs a tool by name.
func CallTool(s *Store, name string, args Args) (string, error) {
	for _, t := range Tools() {
		if t.Name == name {
			if args == nil {
				args = Args{}
			}
			return t.handler(s, args)
		}
	}
	return "", fmt.Errorf("unknown tool %q", name)
}
