package main

// MCP tool definitions: argument parsing and text formatting on top of the
// query layer.

import (
	"fmt"
	"sort"
	"strings"
)

// ---- schema helpers ----

type prop struct {
	name, typ, desc string
	enum            []string
}

func schema(required []string, props ...prop) map[string]any {
	ps := map[string]any{}
	for _, p := range props {
		m := map[string]any{"type": p.typ, "description": p.desc}
		if len(p.enum) > 0 {
			m["enum"] = p.enum
		}
		ps[p.name] = m
	}
	s := map[string]any{"type": "object", "properties": ps}
	if len(required) > 0 {
		s["required"] = required
	}
	return s
}

var (
	pCompetition = prop{name: "competition", typ: "string", desc: "Competition: 'Brasileirão' (Série A), 'Serie B', 'Serie C', 'Copa do Brasil' or 'Libertadores'. Omit for all."}
	pSeason      = prop{name: "season", typ: "integer", desc: "Season year, e.g. 2019. Omit for all seasons."}
	pLimit       = prop{name: "limit", typ: "integer", desc: "Maximum number of rows to list."}
	pVenue       = prop{name: "venue", typ: "string", desc: "Restrict to the team's home or away matches.", enum: []string{"home", "away", "all"}}
)

// ---- argument helpers ----

func teamArg(s *Store, a Args, k string, required bool) (string, error) {
	q := a.Str(k)
	if q == "" {
		if required {
			return "", fmt.Errorf("argument %q is required", k)
		}
		return "", nil
	}
	t, ok := s.Reg.Find(q)
	if !ok {
		return "", fmt.Errorf("team %q not found in the match data", q)
	}
	return t.Key, nil
}

// filterArgs builds a match Filter from the common tool arguments.
func filterArgs(s *Store, a Args) (Filter, error) {
	var f Filter
	var err error
	if f.Team, err = teamArg(s, a, "team", false); err != nil {
		return f, err
	}
	if f.Competition, err = ResolveCompetition(a.Str("competition")); err != nil {
		return f, err
	}
	if f.Season, err = a.Int("season", 0); err != nil {
		return f, err
	}
	switch v := strings.ToLower(a.Str("venue")); v {
	case "home", "away":
		f.Venue = v
	case "", "all", "either", "any":
	default:
		return f, fmt.Errorf("venue must be home, away or all, got %q", v)
	}
	if f.Venue != "" && f.Team == "" && a.Str("opponent") != "" {
		return f, fmt.Errorf("venue requires a team")
	}
	if v := a.Str("date_from"); v != "" {
		d, ok := parseDate(v)
		if !ok {
			return f, fmt.Errorf("invalid date_from %q (use YYYY-MM-DD or DD/MM/YYYY)", v)
		}
		f.From = d
	}
	if v := a.Str("date_to"); v != "" {
		d, ok := parseDate(v)
		if !ok {
			return f, fmt.Errorf("invalid date_to %q (use YYYY-MM-DD or DD/MM/YYYY)", v)
		}
		f.To = d
	}
	f.Stage = a.Str("stage")
	return f, nil
}

func limitArg(a Args, def int) (int, error) {
	n, err := a.Int("limit", def)
	if err != nil {
		return 0, err
	}
	if n <= 0 {
		n = def
	}
	return n, nil
}

// ---- formatting ----

func (s *Store) matchLine(m *Match) string {
	detail := fmt.Sprintf("%s %d", m.Competition, m.Season)
	if m.Stage != "" {
		detail += ", " + m.Stage
	} else if m.Round != "" {
		detail += ", Round " + m.Round
	}
	if m.Arena != "" {
		detail += ", " + m.Arena
	}
	return fmt.Sprintf("%s: %s %d-%d %s (%s)", m.Date.Format("2006-01-02"), s.TeamName(m.HomeKey), m.HomeGoals, m.AwayGoals, s.TeamName(m.AwayKey), detail)
}

func recordLines(r Record) string {
	return fmt.Sprintf("- Matches: %d\n- Wins: %d, Draws: %d, Losses: %d\n- Goals For: %d, Goals Against: %d (difference %+d)\n- Win rate: %.1f%%\n",
		r.Played, r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgainst, r.GoalDiff(), r.WinRate())
}

func recordShort(r Record) string {
	return fmt.Sprintf("%d matches: %dW %dD %dL, goals %d-%d, win rate %.1f%%", r.Played, r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgainst, r.WinRate())
}

// scope describes a filter in words, e.g. "Brasileirão Série A 2019".
func scope(f Filter) string {
	var parts []string
	if f.Competition != "" {
		parts = append(parts, f.Competition)
	}
	if f.Season != 0 {
		parts = append(parts, fmt.Sprint(f.Season))
	}
	if f.Stage != "" {
		parts = append(parts, "stage "+f.Stage)
	}
	if !f.From.IsZero() {
		parts = append(parts, "from "+f.From.Format("2006-01-02"))
	}
	if !f.To.IsZero() {
		parts = append(parts, "to "+f.To.Format("2006-01-02"))
	}
	if len(parts) == 0 {
		return "all competitions and seasons"
	}
	return strings.Join(parts, " ")
}

func (s *Store) headToHeadLine(a, b string, ms []*Match) string {
	ra := RecordFor(a, ms)
	return fmt.Sprintf("Head-to-head in dataset (%d matches): %s %d wins, %s %d wins, %d draws; goals %s %d, %s %d",
		ra.Played, s.TeamName(a), ra.Wins, s.TeamName(b), ra.Losses, ra.Draws, s.TeamName(a), ra.GoalsFor, s.TeamName(b), ra.GoalsAgainst)
}

// writeMatches lists up to limit matches, newest first.
func (s *Store) writeMatches(b *strings.Builder, ms []*Match, limit int) {
	for i := len(ms) - 1; i >= 0 && len(ms)-1-i < limit; i-- {
		b.WriteString("- " + s.matchLine(ms[i]) + "\n")
	}
	if len(ms) > limit {
		fmt.Fprintf(b, "- ... (%d more matches in dataset)\n", len(ms)-limit)
	}
}

// ---- tools ----

func buildTools() []Tool {
	return []Tool{
		{
			Name: "search_matches",
			Description: "Find matches by team, opponent, venue, competition, season, date range or cup stage. Results are listed newest first. " +
				"Use stage='final' for Copa do Brasil / Libertadores finals. With team and opponent it also reports the head-to-head record.",
			Schema: schema(nil,
				prop{name: "team", typ: "string", desc: "Team name, e.g. 'Flamengo', 'Palmeiras-SP', 'Atlético Mineiro'."},
				prop{name: "opponent", typ: "string", desc: "Second team; requires team."},
				pVenue, pCompetition, pSeason,
				prop{name: "date_from", typ: "string", desc: "Earliest match date (YYYY-MM-DD or DD/MM/YYYY)."},
				prop{name: "date_to", typ: "string", desc: "Latest match date, inclusive."},
				prop{name: "stage", typ: "string", desc: "Cup stage ('final', 'semifinals', 'quarterfinals', 'round of 16', 'group stage') or round number."},
				pLimit),
			Handler: toolSearchMatches,
		},
		{
			Name:        "head_to_head",
			Description: "Compare two teams head-to-head: wins, draws, goals, record per competition, biggest wins and the most recent meetings.",
			Schema: schema([]string{"team_a", "team_b"},
				prop{name: "team_a", typ: "string", desc: "First team."},
				prop{name: "team_b", typ: "string", desc: "Second team."},
				pCompetition, pSeason, pLimit),
			Handler: toolHeadToHead,
		},
		{
			Name:        "team_stats",
			Description: "Win/draw/loss record, goals and win rate for a team, with home/away split, per-competition breakdown and corner/shot averages where available.",
			Schema: schema([]string{"team"},
				prop{name: "team", typ: "string", desc: "Team name."}, pVenue, pCompetition, pSeason),
			Handler: toolTeamStats,
		},
		{
			Name:        "team_profile",
			Description: "Overview of a team across all files: competitions and seasons played, overall record, recent matches, rivals and its players in the FIFA dataset.",
			Schema:      schema([]string{"team"}, prop{name: "team", typ: "string", desc: "Team name."}),
			Handler:     toolTeamProfile,
		},
		{
			Name: "standings",
			Description: "League table for a season calculated from match results (3 points per win). Identifies the champion and, for a complete " +
				"Série A season, the relegated teams. Defaults to Brasileirão Série A.",
			Schema:  schema([]string{"season"}, pSeason, pCompetition, pLimit),
			Handler: toolStandings,
		},
		{
			Name:        "competition_bracket",
			Description: "Knockout matches of a Copa Libertadores or Copa do Brasil season grouped by stage, with the winner of the final when it can be determined.",
			Schema: schema([]string{"competition", "season"}, pCompetition, pSeason,
				prop{name: "include_all_rounds", typ: "boolean", desc: "Also list the Libertadores group stage / early Copa do Brasil rounds."}),
			Handler: toolBracket,
		},
		{
			Name:        "competition_stats",
			Description: "Aggregate statistics: matches, average goals per match, home win / draw / away win rates, average corners. Optionally filtered by competition, season or team.",
			Schema:      schema(nil, pCompetition, pSeason, prop{name: "team", typ: "string", desc: "Only matches involving this team."}),
			Handler:     toolCompetitionStats,
		},
		{
			Name:        "compare_seasons",
			Description: "Compare two seasons of a competition side by side: goals per match, home advantage, champion and top scoring team.",
			Schema: schema([]string{"season_a", "season_b"},
				prop{name: "season_a", typ: "integer", desc: "First season year."},
				prop{name: "season_b", typ: "integer", desc: "Second season year."}, pCompetition),
			Handler: toolCompareSeasons,
		},
		{
			Name: "team_rankings",
			Description: "Rank teams by a metric, e.g. best home record (venue=home, metric=win_rate), best away record, or most goals scored in a season " +
				"(metric=goals_for).",
			Schema: schema(nil,
				prop{name: "metric", typ: "string", desc: "Ranking metric (default win_rate).", enum: []string{"win_rate", "points_per_game", "points", "wins", "goals_for", "goals_against", "goal_difference"}},
				pVenue, pCompetition, pSeason,
				prop{name: "min_matches", typ: "integer", desc: "Minimum matches for a team to be ranked (default 10, or 5 with a season)."},
				pLimit),
			Handler: toolRankings,
		},
		{
			Name:        "biggest_wins",
			Description: "Largest margins of victory, optionally filtered by team, competition or season.",
			Schema:      schema(nil, prop{name: "team", typ: "string", desc: "Only matches involving this team."}, pCompetition, pSeason, pLimit),
			Handler:     toolBiggestWins,
		},
		{
			Name:        "derbies",
			Description: "Matches between traditional rivals (Fla-Flu, Grenal, Derby Paulista, ...), optionally for one season, team or competition.",
			Schema:      schema(nil, pSeason, prop{name: "team", typ: "string", desc: "Only derbies of this team."}, pCompetition, pLimit),
			Handler:     toolDerbies,
		},
		{
			Name: "search_players",
			Description: "Search the FIFA player database by name, nationality, club and position; sorted by overall rating. " +
				"Position accepts codes (ST, GK, CAM) or groups (forward, midfielder, defender, goalkeeper).",
			Schema: schema(nil,
				prop{name: "name", typ: "string", desc: "Player name or part of it (accents optional)."},
				prop{name: "nationality", typ: "string", desc: "Country, e.g. 'Brazil'."},
				prop{name: "club", typ: "string", desc: "Club name or part of it, e.g. 'Santos', 'Grêmio'."},
				prop{name: "position", typ: "string", desc: "Position code or group."},
				prop{name: "min_overall", typ: "integer", desc: "Minimum overall rating."},
				prop{name: "max_age", typ: "integer", desc: "Maximum age."},
				prop{name: "brazilian_clubs_only", typ: "boolean", desc: "Only players at Brazilian clubs that appear in the match data."},
				pLimit),
			Handler: toolSearchPlayers,
		},
		{
			Name:        "player_details",
			Description: "Full profile of a player: club, position, ratings, physical attributes and skill ratings. Lists candidates when the name is ambiguous.",
			Schema: schema(nil,
				prop{name: "name", typ: "string", desc: "Player name."},
				prop{name: "id", typ: "integer", desc: "FIFA player ID (alternative to name)."}),
			Handler: toolPlayerDetails,
		},
		{
			Name:        "players_by_club",
			Description: "Group players by club with squad size, average rating and best player, e.g. Brazilian players at Brazilian clubs.",
			Schema: schema(nil,
				prop{name: "nationality", typ: "string", desc: "Only players of this nationality."},
				prop{name: "brazilian_clubs_only", typ: "boolean", desc: "Only Brazilian clubs that appear in the match data."},
				pLimit),
			Handler: toolPlayersByClub,
		},
		{
			Name:        "dataset_info",
			Description: "Coverage of the loaded data: rows per CSV file, competitions with season ranges, number of teams and players.",
			Schema:      schema(nil),
			Handler:     toolDatasetInfo,
		},
	}
}

func toolSearchMatches(s *Store, a Args) (string, error) {
	f, err := filterArgs(s, a)
	if err != nil {
		return "", err
	}
	if a.Str("opponent") != "" {
		if f.Team == "" {
			return "", fmt.Errorf("opponent requires team")
		}
		if f.Opponent, err = teamArg(s, a, "opponent", true); err != nil {
			return "", err
		}
	}
	limit, err := limitArg(a, 20)
	if err != nil {
		return "", err
	}
	ms := s.FindMatches(f)
	var b strings.Builder
	title := "Matches"
	if f.Team != "" {
		title = s.TeamName(f.Team)
		if f.Opponent != "" {
			title += " vs " + s.TeamName(f.Opponent)
			if d := s.DerbyName(f.Team, f.Opponent); d != "" {
				title += " (" + d + ")"
			}
		}
		if f.Venue != "" {
			title += ", " + f.Venue + " matches"
		}
	}
	fmt.Fprintf(&b, "%s — %s: %d matches found\n", title, scope(f), len(ms))
	if len(ms) == 0 {
		return b.String(), nil
	}
	s.writeMatches(&b, ms, limit)
	if f.Opponent != "" {
		b.WriteString("\n" + s.headToHeadLine(f.Team, f.Opponent, ms) + "\n")
	} else if f.Team != "" {
		fmt.Fprintf(&b, "\n%s record in these matches: %s\n", s.TeamName(f.Team), recordShort(RecordFor(f.Team, ms)))
	}
	return b.String(), nil
}

func toolHeadToHead(s *Store, a Args) (string, error) {
	ta, err := teamArg(s, a, "team_a", true)
	if err != nil {
		return "", err
	}
	tb, err := teamArg(s, a, "team_b", true)
	if err != nil {
		return "", err
	}
	if ta == tb {
		return "", fmt.Errorf("team_a and team_b resolve to the same team (%s)", s.TeamName(ta))
	}
	f, err := filterArgs(s, a)
	if err != nil {
		return "", err
	}
	f.Team, f.Opponent = ta, tb
	limit, err := limitArg(a, 10)
	if err != nil {
		return "", err
	}
	ms := s.FindMatches(f)
	na, nb := s.TeamName(ta), s.TeamName(tb)
	var b strings.Builder
	fmt.Fprintf(&b, "%s vs %s", na, nb)
	if d := s.DerbyName(ta, tb); d != "" {
		fmt.Fprintf(&b, " (%s)", d)
	}
	fmt.Fprintf(&b, " — %s\n", scope(f))
	if len(ms) == 0 {
		b.WriteString("No matches between these teams in the dataset.\n")
		return b.String(), nil
	}
	b.WriteString(s.headToHeadLine(ta, tb, ms) + "\n")
	var home []*Match
	for _, m := range ms {
		if m.HomeKey == ta {
			home = append(home, m)
		}
	}
	fmt.Fprintf(&b, "- %s at home: %s\n", na, recordShort(RecordFor(ta, home)))
	var away []*Match
	for _, m := range ms {
		if m.HomeKey == tb {
			away = append(away, m)
		}
	}
	fmt.Fprintf(&b, "- %s at home: %s\n", nb, recordShort(RecordFor(tb, away)))

	b.WriteString("\nBy competition:\n")
	for _, c := range allCompetitions {
		var cm []*Match
		for _, m := range ms {
			if m.Competition == c {
				cm = append(cm, m)
			}
		}
		if len(cm) > 0 {
			r := RecordFor(ta, cm)
			fmt.Fprintf(&b, "- %s: %d matches — %s %d wins, %s %d wins, %d draws\n", c, r.Played, na, r.Wins, nb, r.Losses, r.Draws)
		}
	}
	last := ms[len(ms)-1]
	fmt.Fprintf(&b, "\nMost recent meeting: %s\n", s.matchLine(last))
	big := s.BiggestWins(f, 1)[0]
	if big.HomeGoals != big.AwayGoals {
		fmt.Fprintf(&b, "Biggest win: %s\n", s.matchLine(big))
	}
	b.WriteString("\nRecent matches:\n")
	s.writeMatches(&b, ms, limit)
	return b.String(), nil
}

func toolTeamStats(s *Store, a Args) (string, error) {
	f, err := filterArgs(s, a)
	if err != nil {
		return "", err
	}
	if f.Team == "" {
		return "", fmt.Errorf("argument \"team\" is required")
	}
	ms := s.FindMatches(f)
	name := s.TeamName(f.Team)
	label := "record"
	if f.Venue != "" {
		label = f.Venue + " record"
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s %s (%s):\n", name, label, scope(f))
	if len(ms) == 0 {
		b.WriteString("No matches found in the dataset.\n")
		return b.String(), nil
	}
	b.WriteString(recordLines(RecordFor(f.Team, ms)))
	if f.Venue == "" {
		var home, away []*Match
		for _, m := range ms {
			if m.HomeKey == f.Team {
				home = append(home, m)
			} else {
				away = append(away, m)
			}
		}
		fmt.Fprintf(&b, "\nHome: %s\nAway: %s\n", recordShort(RecordFor(f.Team, home)), recordShort(RecordFor(f.Team, away)))
	}
	if f.Competition == "" {
		b.WriteString("\nBy competition:\n")
		for _, c := range allCompetitions {
			var cm []*Match
			for _, m := range ms {
				if m.Competition == c {
					cm = append(cm, m)
				}
			}
			if len(cm) > 0 {
				fmt.Fprintf(&b, "- %s: %s\n", c, recordShort(RecordFor(f.Team, cm)))
			}
		}
	}
	var n, ns int
	var corners, shots float64
	for _, m := range ms {
		if m.Ext == nil {
			continue
		}
		n++
		home := m.HomeKey == f.Team
		if home {
			corners += m.Ext.HomeCorners
		} else {
			corners += m.Ext.AwayCorners
		}
		if m.Ext.HasShots {
			ns++
			if home {
				shots += m.Ext.HomeShots
			} else {
				shots += m.Ext.AwayShots
			}
		}
	}
	if n > 0 {
		fmt.Fprintf(&b, "\nExtended statistics (%d matches with data): %.1f corners per match", n, corners/float64(n))
		if ns > 0 {
			fmt.Fprintf(&b, ", %.1f shots per match (%d matches)", shots/float64(ns), ns)
		}
		b.WriteString("\n")
	}
	return b.String(), nil
}

func seasonRange(ms []*Match) string {
	lo, hi := 0, 0
	for _, m := range ms {
		if lo == 0 || m.Season < lo {
			lo = m.Season
		}
		if m.Season > hi {
			hi = m.Season
		}
	}
	if lo == hi {
		return fmt.Sprint(lo)
	}
	return fmt.Sprintf("%d-%d", lo, hi)
}

func countSeasons(ms []*Match) int {
	set := map[int]bool{}
	for _, m := range ms {
		set[m.Season] = true
	}
	return len(set)
}

func toolTeamProfile(s *Store, a Args) (string, error) {
	key, err := teamArg(s, a, "team", true)
	if err != nil {
		return "", err
	}
	t := s.Reg.Teams[key]
	ms := s.FindMatches(Filter{Team: key})
	var b strings.Builder
	fmt.Fprintf(&b, "%s", t.Name)
	if t.State != "" {
		fmt.Fprintf(&b, " (%s)", t.State)
	}
	fmt.Fprintf(&b, "\nOverall record in dataset: %s\n\nCompetitions played:\n", recordShort(RecordFor(key, ms)))
	for _, c := range allCompetitions {
		var cm []*Match
		for _, m := range ms {
			if m.Competition == c {
				cm = append(cm, m)
			}
		}
		if len(cm) > 0 {
			fmt.Fprintf(&b, "- %s: %d seasons (%s), %s\n", c, countSeasons(cm), seasonRange(cm), recordShort(RecordFor(key, cm)))
		}
	}
	var rivals []string
	for k, n := range s.Reg.derbies {
		if p := strings.SplitN(k, "\x00", 2); p[0] == key {
			rivals = append(rivals, fmt.Sprintf("%s (%s)", s.TeamName(p[1]), n))
		}
	}
	if len(rivals) > 0 {
		sort.Strings(rivals)
		fmt.Fprintf(&b, "\nTraditional rivals: %s\n", strings.Join(rivals, ", "))
	}
	b.WriteString("\nMost recent matches:\n")
	s.writeMatches(&b, ms, 5)

	var squad []*Player
	for _, p := range s.Players {
		if p.ClubKey == key {
			squad = append(squad, p)
		}
	}
	if len(squad) == 0 {
		b.WriteString("\nNo players of this club in the FIFA dataset.\n")
	} else {
		fmt.Fprintf(&b, "\nFIFA dataset squad (%s, %d players, avg overall %.1f) — top rated:\n", squad[0].Club, len(squad), ClubSummaries(squad)[0].Avg)
		for i, p := range squad {
			if i == 10 {
				break
			}
			fmt.Fprintf(&b, "%d. %s\n", i+1, playerLine(p))
		}
	}
	return b.String(), nil
}

// leagueComplete reports whether rows form a full double round-robin.
func leagueComplete(rows []TeamRow) bool {
	n := len(rows)
	if n < 2 {
		return false
	}
	for _, r := range rows {
		if r.Played != 2*(n-1) {
			return false
		}
	}
	return true
}

func toolStandings(s *Store, a Args) (string, error) {
	comp, err := ResolveCompetition(a.Str("competition"))
	if err != nil {
		return "", err
	}
	if comp == "" {
		comp = CompSerieA
	}
	season, err := a.Int("season", 0)
	if err != nil {
		return "", err
	}
	if season == 0 {
		return "", fmt.Errorf("argument \"season\" is required")
	}
	limit, err := limitArg(a, 100)
	if err != nil {
		return "", err
	}
	rows := s.Standings(comp, season)
	if len(rows) == 0 {
		return fmt.Sprintf("No %s matches for season %d in the dataset.\n", comp, season), nil
	}
	complete := leagueComplete(rows)
	league := comp == CompSerieA || comp == CompSerieB
	var b strings.Builder
	fmt.Fprintf(&b, "%d %s standings (calculated from matches):\n", season, comp)
	for i, r := range rows {
		if i >= limit {
			fmt.Fprintf(&b, "... (%d more teams)\n", len(rows)-limit)
			break
		}
		note := ""
		if league && complete {
			switch {
			case i == 0:
				note = " - Champion"
			case comp == CompSerieA && len(rows) >= 20 && i >= len(rows)-4:
				note = " - Relegated"
			}
		}
		fmt.Fprintf(&b, "%d. %s - %d pts (%dW, %dD, %dL), goals %d-%d (%+d), %d played%s\n",
			i+1, s.TeamName(r.Team), r.Points(), r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgainst, r.GoalDiff(), r.Played, note)
	}
	b.WriteString("\n")
	switch {
	case league && complete:
		fmt.Fprintf(&b, "Champion: %s.", s.TeamName(rows[0].Team))
		if comp == CompSerieA && len(rows) >= 20 {
			var rel []string
			for _, r := range rows[len(rows)-4:] {
				rel = append(rel, s.TeamName(r.Team))
			}
			fmt.Fprintf(&b, " Relegated (bottom four): %s.", strings.Join(rel, ", "))
		}
		b.WriteString(" Ties are broken by wins, goal difference and goals scored; points deductions are not in the data.\n")
	case league:
		b.WriteString("Note: the dataset does not contain every match of this season, so the table is partial and the leader may not be the actual champion.\n")
	default:
		b.WriteString("Note: this competition is not a single round-robin league; the table simply aggregates all its matches in the season. Use competition_bracket for knockout results.\n")
	}
	return b.String(), nil
}

var stageOrder = []string{"group stage", "round of 16", "quarterfinals", "semifinals", "final"}

// finalWinner decides a final over one or two legs on aggregate goals.
func (s *Store) finalWinner(ms []*Match) string {
	if len(ms) == 0 || len(ms) > 2 {
		return ""
	}
	a, b := ms[0].HomeKey, ms[0].AwayKey
	r := RecordFor(a, ms)
	if r.Played != len(ms) {
		return ""
	}
	switch {
	case r.GoalsFor > r.GoalsAgainst:
		return fmt.Sprintf("%s (%d-%d on aggregate)", s.TeamName(a), r.GoalsFor, r.GoalsAgainst)
	case r.GoalsFor < r.GoalsAgainst:
		return fmt.Sprintf("%s (%d-%d on aggregate)", s.TeamName(b), r.GoalsAgainst, r.GoalsFor)
	}
	return fmt.Sprintf("undetermined — %d-%d on aggregate; the tie-breaker (away goals/penalties) is not in the data", r.GoalsFor, r.GoalsAgainst)
}

func toolBracket(s *Store, a Args) (string, error) {
	comp, err := ResolveCompetition(a.Str("competition"))
	if err != nil {
		return "", err
	}
	if comp != CompLibertadores && comp != CompCup {
		return "", fmt.Errorf("competition_bracket supports Copa Libertadores and Copa do Brasil; use standings for leagues")
	}
	season, err := a.Int("season", 0)
	if err != nil {
		return "", err
	}
	if season == 0 {
		return "", fmt.Errorf("argument \"season\" is required")
	}
	ms := s.FindMatches(Filter{Competition: comp, Season: season})
	if len(ms) == 0 {
		return fmt.Sprintf("No %s matches for season %d in the dataset.\n", comp, season), nil
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%d %s (%d matches in dataset):\n", season, comp, len(ms))
	group := func(title, stage string, sel []*Match, list bool) {
		if len(sel) == 0 {
			return
		}
		fmt.Fprintf(&b, "\n%s (%d matches):\n", title, len(sel))
		if !list {
			fmt.Fprintf(&b, "- not listed; set include_all_rounds=true or use search_matches with stage='%s'\n", stage)
			return
		}
		for _, m := range sel {
			fmt.Fprintf(&b, "- %s: %s %d-%d %s\n", m.Date.Format("2006-01-02"), s.TeamName(m.HomeKey), m.HomeGoals, m.AwayGoals, s.TeamName(m.AwayKey))
		}
	}
	var final []*Match
	if comp == CompLibertadores {
		for _, st := range stageOrder {
			var sel []*Match
			for _, m := range ms {
				if m.Stage == st {
					sel = append(sel, m)
				}
			}
			group(strings.Title(st), st, sel, st != "group stage" || a.Bool("include_all_rounds")) //nolint:staticcheck
			if st == "final" {
				final = sel
			}
		}
	} else {
		maxRound, unrounded := 0, []*Match(nil)
		for _, m := range ms {
			if r := atoi(m.Round); r > maxRound {
				maxRound = r
			}
			if m.Round == "" {
				unrounded = append(unrounded, m)
			}
		}
		for r := 1; r <= maxRound; r++ {
			var sel []*Match
			isFinal := false
			for _, m := range ms {
				if m.Round != "" && atoi(m.Round) == r {
					sel = append(sel, m)
					isFinal = isFinal || m.Stage == "final"
				}
			}
			title := fmt.Sprintf("Round %d", r)
			if isFinal {
				title += " - Final"
				final = sel
			}
			group(title, fmt.Sprint(r), sel, r >= maxRound-3 || a.Bool("include_all_rounds"))
		}
		group("Matches without round information", "", unrounded, true)
	}
	if w := s.finalWinner(final); w != "" {
		fmt.Fprintf(&b, "\nWinner: %s\n", w)
	} else {
		b.WriteString("\nThe final of this season is not (fully) in the dataset.\n")
	}
	return b.String(), nil
}

func summaryLines(a Summary) string {
	out := fmt.Sprintf("- Matches: %d\n- Goals: %d (average %.2f per match; home %.2f, away %.2f)\n- Home win rate: %.1f%%, draws: %.1f%%, away win rate: %.1f%%\n",
		a.Matches, a.Goals, a.AvgGoals(), float64(a.HomeGoals)/float64(max(a.Matches, 1)), float64(a.AwayGoals)/float64(max(a.Matches, 1)),
		a.pct(a.HomeWins), a.pct(a.Draws), a.pct(a.AwayWins))
	if a.CornerMatches > 0 {
		out += fmt.Sprintf("- Average corners per match: %.1f (%d matches with data)\n", a.Corners/float64(a.CornerMatches), a.CornerMatches)
	}
	return out
}

func toolCompetitionStats(s *Store, a Args) (string, error) {
	f, err := filterArgs(s, a)
	if err != nil {
		return "", err
	}
	ms := s.FindMatches(f)
	var b strings.Builder
	title := "Statistics"
	if f.Team != "" {
		title += " for matches involving " + s.TeamName(f.Team)
	}
	fmt.Fprintf(&b, "%s (%s):\n", title, scope(f))
	if len(ms) == 0 {
		b.WriteString("No matches found in the dataset.\n")
		return b.String(), nil
	}
	b.WriteString(summaryLines(Summarize(ms)))
	if f.Competition == "" {
		b.WriteString("\nBy competition:\n")
		for _, c := range allCompetitions {
			g := f
			g.Competition = c
			if sm := Summarize(s.FindMatches(g)); sm.Matches > 0 {
				fmt.Fprintf(&b, "- %s: %d matches, %.2f goals per match, home win rate %.1f%%\n", c, sm.Matches, sm.AvgGoals(), sm.pct(sm.HomeWins))
			}
		}
	}
	if big := s.BiggestWins(f, 1); len(big) > 0 {
		fmt.Fprintf(&b, "\nBiggest win: %s\n", s.matchLine(big[0]))
	}
	return b.String(), nil
}

func toolCompareSeasons(s *Store, a Args) (string, error) {
	comp, err := ResolveCompetition(a.Str("competition"))
	if err != nil {
		return "", err
	}
	if comp == "" {
		comp = CompSerieA
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Season comparison — %s:\n", comp)
	for _, k := range []string{"season_a", "season_b"} {
		season, err := a.Int(k, 0)
		if err != nil {
			return "", err
		}
		if season == 0 {
			return "", fmt.Errorf("argument %q is required", k)
		}
		f := Filter{Competition: comp, Season: season}
		ms := s.FindMatches(f)
		fmt.Fprintf(&b, "\n%d:\n", season)
		if len(ms) == 0 {
			b.WriteString("- No matches in the dataset.\n")
			continue
		}
		b.WriteString(summaryLines(Summarize(ms)))
		rows := s.Standings(comp, season)
		if comp == CompLibertadores || comp == CompCup {
			var final []*Match
			for _, m := range ms {
				if m.Stage == "final" {
					final = append(final, m)
				}
			}
			if w := s.finalWinner(final); w != "" {
				fmt.Fprintf(&b, "- Winner: %s\n", w)
			}
		} else if leagueComplete(rows) {
			fmt.Fprintf(&b, "- Champion: %s (%d pts)\n", s.TeamName(rows[0].Team), rows[0].Points())
		} else {
			fmt.Fprintf(&b, "- Leader of partial table: %s (%d pts; season incomplete in dataset)\n", s.TeamName(rows[0].Team), rows[0].Points())
		}
		if top, _ := s.Rankings(f, "", "goals_for", 1); len(top) > 0 {
			fmt.Fprintf(&b, "- Most goals scored: %s (%d)\n", s.TeamName(top[0].Team), top[0].GoalsFor)
		}
		if def, _ := s.Rankings(f, "", "goals_against", 1); len(def) > 0 && comp != CompLibertadores && comp != CompCup {
			fmt.Fprintf(&b, "- Fewest goals conceded: %s (%d)\n", s.TeamName(def[0].Team), def[0].GoalsAgainst)
		}
		fmt.Fprintf(&b, "- Biggest win: %s\n", s.matchLine(s.BiggestWins(f, 1)[0]))
	}
	return b.String(), nil
}

func toolRankings(s *Store, a Args) (string, error) {
	f, err := filterArgs(s, a)
	if err != nil {
		return "", err
	}
	f.Team = "" // rankings cover all teams
	venue := strings.ToLower(a.Str("venue"))
	if venue != "home" && venue != "away" {
		venue = ""
	}
	f.Venue = ""
	metric := a.Str("metric")
	if metric == "" {
		metric = "win_rate"
	}
	def := 10
	if f.Season != 0 {
		def = 5
	}
	minMatches, err := a.Int("min_matches", def)
	if err != nil {
		return "", err
	}
	limit, err := limitArg(a, 10)
	if err != nil {
		return "", err
	}
	rows, err := s.Rankings(f, venue, metric, minMatches)
	if err != nil {
		return "", err
	}
	where := "overall"
	if venue != "" {
		where = venue
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Team ranking by %s, %s matches (%s; minimum %d matches):\n", metric, where, scope(f), minMatches)
	if len(rows) == 0 {
		b.WriteString("No teams qualify.\n")
	}
	for i, r := range rows {
		if i >= limit {
			break
		}
		fmt.Fprintf(&b, "%d. %s - %s, %.2f points per game\n", i+1, s.TeamName(r.Team), recordShort(r.Record), r.PointsPerGame())
	}
	return b.String(), nil
}

func toolBiggestWins(s *Store, a Args) (string, error) {
	f, err := filterArgs(s, a)
	if err != nil {
		return "", err
	}
	limit, err := limitArg(a, 10)
	if err != nil {
		return "", err
	}
	title := "Biggest victories"
	if f.Team != "" {
		title += " in matches involving " + s.TeamName(f.Team)
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s (%s):\n", title, scope(f))
	ms := s.BiggestWins(f, limit)
	if len(ms) == 0 {
		b.WriteString("No matches found in the dataset.\n")
		return b.String(), nil
	}
	for i, m := range ms {
		fmt.Fprintf(&b, "%d. %s\n", i+1, s.matchLine(m))
	}
	sm := Summarize(s.FindMatches(f))
	fmt.Fprintf(&b, "\nAverage goals per match: %.2f\nHome win rate: %.1f%%\n", sm.AvgGoals(), sm.pct(sm.HomeWins))
	return b.String(), nil
}

func toolDerbies(s *Store, a Args) (string, error) {
	f, err := filterArgs(s, a)
	if err != nil {
		return "", err
	}
	limit, err := limitArg(a, 50)
	if err != nil {
		return "", err
	}
	ms := s.Derbies(f)
	var b strings.Builder
	title := "Derbies"
	if f.Team != "" {
		title += " of " + s.TeamName(f.Team)
	}
	fmt.Fprintf(&b, "%s (%s): %d matches between traditional rivals\n", title, scope(f), len(ms))
	for i := len(ms) - 1; i >= 0 && len(ms)-1-i < limit; i-- {
		m := ms[i]
		fmt.Fprintf(&b, "- [%s] %s\n", s.DerbyName(m.HomeKey, m.AwayKey), s.matchLine(m))
	}
	if len(ms) > limit {
		fmt.Fprintf(&b, "- ... (%d more matches in dataset)\n", len(ms)-limit)
	}
	return b.String(), nil
}

func playerLine(p *Player) string {
	club := p.Club
	if club == "" {
		club = "no club"
	}
	pos := p.Position
	if pos == "" {
		pos = "n/a"
	}
	return fmt.Sprintf("%s - Overall: %d, Potential: %d, Position: %s, Age: %d, Nationality: %s, Club: %s", p.Name, p.Overall, p.Potential, pos, p.Age, p.Nationality, club)
}

func playerFilterArgs(a Args) (PlayerFilter, error) {
	f := PlayerFilter{
		Name: a.Str("name"), Nationality: a.Str("nationality"), Club: a.Str("club"),
		Position: a.Str("position"), BrazilianClubs: a.Bool("brazilian_clubs_only"),
	}
	var err error
	if f.MinOverall, err = a.Int("min_overall", 0); err != nil {
		return f, err
	}
	f.MaxAge, err = a.Int("max_age", 0)
	return f, err
}

func describePlayerFilter(f PlayerFilter) string {
	var parts []string
	add := func(k, v string) {
		if v != "" {
			parts = append(parts, k+" "+v)
		}
	}
	add("name", f.Name)
	add("nationality", f.Nationality)
	add("club", f.Club)
	add("position", f.Position)
	if f.MinOverall > 0 {
		parts = append(parts, fmt.Sprintf("overall >= %d", f.MinOverall))
	}
	if f.MaxAge > 0 {
		parts = append(parts, fmt.Sprintf("age <= %d", f.MaxAge))
	}
	if f.BrazilianClubs {
		parts = append(parts, "Brazilian clubs only")
	}
	if len(parts) == 0 {
		return "all players"
	}
	return strings.Join(parts, ", ")
}

func (s *Store) noClubHint(club string) string {
	if club == "" {
		return ""
	}
	return fmt.Sprintf("The FIFA dataset has no club matching %q. Brazilian clubs it does include: %s.\n", club, strings.Join(s.BrazilianFIFAClubs(), ", "))
}

func toolSearchPlayers(s *Store, a Args) (string, error) {
	f, err := playerFilterArgs(a)
	if err != nil {
		return "", err
	}
	limit, err := limitArg(a, 20)
	if err != nil {
		return "", err
	}
	ps := s.SearchPlayers(f)
	var b strings.Builder
	fmt.Fprintf(&b, "Players (%s): %d found, sorted by overall rating\n", describePlayerFilter(f), len(ps))
	if len(ps) == 0 {
		b.WriteString(s.noClubHint(f.Club))
		return b.String(), nil
	}
	for i, p := range ps {
		if i >= limit {
			fmt.Fprintf(&b, "... (%d more players in dataset)\n", len(ps)-limit)
			break
		}
		fmt.Fprintf(&b, "%d. %s\n", i+1, playerLine(p))
	}
	sum := 0
	for _, p := range ps {
		sum += p.Overall
	}
	fmt.Fprintf(&b, "\nAverage overall rating: %.1f\n", float64(sum)/float64(len(ps)))
	return b.String(), nil
}

func toolPlayerDetails(s *Store, a Args) (string, error) {
	id, err := a.Int("id", 0)
	if err != nil {
		return "", err
	}
	name := a.Str("name")
	var ps []*Player
	switch {
	case id != 0:
		for _, p := range s.Players {
			if p.ID == id {
				ps = append(ps, p)
			}
		}
	case name != "":
		ps = s.SearchPlayers(PlayerFilter{Name: name})
		for _, p := range ps { // an exact name match wins over partial ones
			if fold(p.Name) == fold(name) {
				exact := []*Player{}
				for _, q := range ps {
					if fold(q.Name) == fold(name) {
						exact = append(exact, q)
					}
				}
				ps = exact
				break
			}
		}
	default:
		return "", fmt.Errorf("provide name or id")
	}
	if len(ps) == 0 {
		var b strings.Builder
		b.WriteString("No player with that exact name in the FIFA dataset. Names are stored in FIFA style (e.g. 'Neymar Jr', 'Gabriel Jesus', 'R. Firmino').\n")
		seen := map[int]bool{}
		var near []*Player
		for _, tok := range strings.Fields(fold(name)) {
			if len(tok) < 4 {
				continue
			}
			for _, p := range s.SearchPlayers(PlayerFilter{Name: tok}) {
				if !seen[p.ID] {
					seen[p.ID] = true
					near = append(near, p)
				}
			}
		}
		sort.SliceStable(near, func(i, j int) bool { return near[i].Overall > near[j].Overall })
		if len(near) > 0 {
			b.WriteString("Closest matches by part of the name:\n")
			for i, p := range near {
				if i == 10 {
					fmt.Fprintf(&b, "- ... (%d more)\n", len(near)-10)
					break
				}
				fmt.Fprintf(&b, "- %s (id %d)\n", playerLine(p), p.ID)
			}
		}
		return b.String(), nil
	}
	var b strings.Builder
	if len(ps) > 1 {
		fmt.Fprintf(&b, "%d players match; showing the highest rated. Other matches:\n", len(ps))
		for i, p := range ps[1:] {
			if i == 10 {
				fmt.Fprintf(&b, "- ... (%d more)\n", len(ps)-11)
				break
			}
			fmt.Fprintf(&b, "- %s (id %d)\n", playerLine(p), p.ID)
		}
		b.WriteString("\n")
	}
	p := ps[0]
	fmt.Fprintf(&b, "%s (FIFA id %d)\n", p.Name, p.ID)
	fmt.Fprintf(&b, "- Age: %d, Nationality: %s\n- Club: %s, Position: %s, Jersey: %s\n- Overall: %d, Potential: %d\n- Height: %s, Weight: %s, Preferred foot: %s\n- Value: %s, Wage: %s\n",
		p.Age, p.Nationality, orNA(p.Club), orNA(p.Position), orNA(p.Jersey), p.Overall, p.Potential, orNA(p.Height), orNA(p.Weight), orNA(p.Foot), orNA(p.Value), orNA(p.Wage))
	var skills []string
	for _, c := range skillColumns {
		if v, ok := p.Skills[c]; ok {
			skills = append(skills, fmt.Sprintf("%s %d", c, v))
		}
	}
	if len(skills) > 0 {
		fmt.Fprintf(&b, "- Skills: %s\n", strings.Join(skills, ", "))
	}
	if p.ClubKey != "" {
		ms := s.FindMatches(Filter{Team: p.ClubKey})
		fmt.Fprintf(&b, "- Club in match data: %s (%s)\n", s.TeamName(p.ClubKey), recordShort(RecordFor(p.ClubKey, ms)))
	}
	return b.String(), nil
}

func orNA(v string) string {
	if strings.TrimSpace(v) == "" {
		return "n/a"
	}
	return v
}

func toolPlayersByClub(s *Store, a Args) (string, error) {
	f, err := playerFilterArgs(a)
	if err != nil {
		return "", err
	}
	limit, err := limitArg(a, 25)
	if err != nil {
		return "", err
	}
	ps := s.SearchPlayers(f)
	cs := ClubSummaries(ps)
	var b strings.Builder
	fmt.Fprintf(&b, "Players by club (%s): %d players at %d clubs\n", describePlayerFilter(f), len(ps), len(cs))
	for i, c := range cs {
		if i >= limit {
			fmt.Fprintf(&b, "- ... (%d more clubs)\n", len(cs)-limit)
			break
		}
		fmt.Fprintf(&b, "- %s: %d players (avg rating: %.1f; best: %s, %d)\n", c.Club, c.Players, c.Avg, c.Best.Name, c.Best.Overall)
	}
	return b.String(), nil
}

func toolDatasetInfo(s *Store, _ Args) (string, error) {
	var b strings.Builder
	b.WriteString("Loaded files:\n")
	for _, f := range []string{FileBrasileirao, FileCup, FileLibertadores, FileExtended, FileHistorical} {
		fi := s.Files[f]
		fmt.Fprintf(&b, "- %s: %d rows, %d played matches (%d without a score skipped, %d merged with the same match from another file)\n", f, fi.Rows, fi.Loaded, fi.Unplayed, fi.Merged)
	}
	fmt.Fprintf(&b, "- %s: %d rows, %d players\n", FileFIFA, s.Files[FileFIFA].Rows, len(s.Players))
	fmt.Fprintf(&b, "\nUnique matches: %d, teams: %d\n\nCompetitions:\n", len(s.Matches), len(s.Reg.Teams))
	for _, c := range allCompetitions {
		ms := s.FindMatches(Filter{Competition: c})
		if len(ms) > 0 {
			fmt.Fprintf(&b, "- %s: %d matches, seasons %s, %s to %s\n", c, len(ms), seasonRange(ms), ms[0].Date.Format("2006-01-02"), ms[len(ms)-1].Date.Format("2006-01-02"))
		}
	}
	br := s.SearchPlayers(PlayerFilter{Nationality: "Brazil"})
	fmt.Fprintf(&b, "\nPlayers: %d (FIFA 19 snapshot), of which %d Brazilian. Brazilian clubs with squads: %s\n", len(s.Players), len(br), strings.Join(s.BrazilianFIFAClubs(), ", "))
	return b.String(), nil
}
