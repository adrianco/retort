// tools.go - MCP tool definitions: argument parsing and text formatting on top
// of the query engine.
package main

import (
	"fmt"
	"math"
	"sort"
	"strconv"
	"strings"
)

// Tool is one MCP tool.
type Tool struct {
	Name        string
	Description string
	Props       map[string]any
	Required    []string
	Handler     func(db *DB, a Args) (string, error)
}

// Args are decoded JSON tool arguments.
type Args map[string]any

func (a Args) str(k string) string {
	switch v := a[k].(type) {
	case string:
		return strings.TrimSpace(v)
	case float64:
		return strconv.FormatFloat(v, 'f', -1, 64)
	case bool:
		return strconv.FormatBool(v)
	}
	return ""
}

func (a Args) int(k string, def int) (int, error) {
	switch v := a[k].(type) {
	case nil:
		return def, nil
	case float64:
		if v != math.Trunc(v) {
			return 0, fmt.Errorf("%s must be an integer", k)
		}
		return int(v), nil
	case string:
		if strings.TrimSpace(v) == "" {
			return def, nil
		}
		n, err := strconv.Atoi(strings.TrimSpace(v))
		if err != nil {
			return 0, fmt.Errorf("%s must be an integer, got %q", k, v)
		}
		return n, nil
	}
	return 0, fmt.Errorf("%s must be an integer", k)
}

func (a Args) bool(k string) bool {
	switch v := a[k].(type) {
	case bool:
		return v
	case string:
		return strings.EqualFold(v, "true")
	}
	return false
}

func (a Args) limit(def int) (int, error) {
	n, err := a.int("limit", def)
	if err != nil {
		return 0, err
	}
	if n < 1 {
		n = def
	}
	if n > 500 {
		n = 500
	}
	return n, nil
}

func (a Args) filter() (MatchFilter, error) {
	season, err := a.int("season", 0)
	return MatchFilter{
		Team: a.str("team"), Opponent: a.str("opponent"), Venue: a.str("venue"),
		Competition: a.str("competition"), Season: season, From: a.str("date_from"), To: a.str("date_to"),
		Stage: a.str("stage"), Round: a.str("round"), Dataset: a.str("dataset"),
	}, err
}

func strProp(d string) map[string]any { return map[string]any{"type": "string", "description": d} }
func intProp(d string) map[string]any { return map[string]any{"type": "integer", "description": d} }

var (
	pTeam    = strProp("Team name; any spelling works (e.g. 'Flamengo', 'Flamengo-RJ', 'São Paulo', 'Sao Paulo FC', 'Atlético-MG').")
	pComp    = strProp("Competition: 'Brasileirão' (Serie A), 'Serie B', 'Serie C', 'Copa do Brasil' or 'Libertadores'. Omit for all.")
	pSeason  = intProp("Season year, e.g. 2019. Omit for all seasons.")
	pLimit   = intProp("Maximum number of rows to return.")
	pDataset = strProp("Optional: restrict to one source file ('brasileirao', 'copa_do_brasil', 'libertadores', 'extended', 'historical'). By default each competition-season is read from one preferred file so matches are not double counted. 'extended' includes corners/shots.")
	pVenue   = strProp("'home', 'away' or 'either' (default).")
)

func matchFilterProps(extra map[string]any) map[string]any {
	p := map[string]any{
		"competition": pComp, "season": pSeason,
		"date_from": strProp("Earliest date (YYYY-MM-DD or DD/MM/YYYY)."),
		"date_to":   strProp("Latest date, inclusive (YYYY-MM-DD or DD/MM/YYYY)."),
		"dataset":   pDataset,
	}
	for k, v := range extra {
		p[k] = v
	}
	return p
}

// ---- formatting helpers ----

func compLabel(m *Match) string {
	s := m.Competition
	if m.Season != 0 {
		s += " " + strconv.Itoa(m.Season)
	}
	if m.Stage != "" {
		s += ", " + m.Stage
	} else if m.Round != "" {
		s += ", Round " + m.Round
	}
	return s
}

func formatMatch(m *Match) string {
	date := "date unknown"
	if m.HasDate {
		date = m.Date.Format("2006-01-02")
	}
	score := "vs"
	if m.Played {
		score = fmt.Sprintf("%d-%d", m.HomeGoals, m.AwayGoals)
	}
	s := fmt.Sprintf("%s: %s %s %s (%s)", date, m.Home.Name, score, m.Away.Name, compLabel(m))
	if !m.Played {
		s += " [no result in data]"
	}
	if m.Arena != "" {
		s += " @ " + m.Arena
	}
	if e := m.Extra; e != nil {
		var x []string
		if e.HasCorners {
			x = append(x, fmt.Sprintf("corners %.0f-%.0f", e.HomeCorners, e.AwayCorners))
		}
		if e.HasShots {
			x = append(x, fmt.Sprintf("shots %.0f-%.0f", e.HomeShots, e.AwayShots))
		}
		if e.HasAttacks {
			x = append(x, fmt.Sprintf("attacks %.0f-%.0f", e.HomeAttacks, e.AwayAttacks))
		}
		if len(x) > 0 {
			s += " [" + strings.Join(x, ", ") + "]"
		}
	}
	return s
}

// writeMatches lists matches most recent first, up to limit.
func writeMatches(b *strings.Builder, ms []*Match, limit int) {
	n := 0
	for i := len(ms) - 1; i >= 0 && n < limit; i-- {
		fmt.Fprintf(b, "- %s\n", formatMatch(ms[i]))
		n++
	}
	if rest := len(ms) - n; rest > 0 {
		fmt.Fprintf(b, "- ... (%d more matches in dataset)\n", rest)
	}
}

func describeFilter(f MatchFilter) string {
	var p []string
	if c := normalizeCompetition(f.Competition); c != "" {
		p = append(p, c)
	}
	if f.Season != 0 {
		p = append(p, strconv.Itoa(f.Season))
	}
	if f.Stage != "" {
		p = append(p, "stage "+f.Stage)
	}
	if f.Round != "" {
		p = append(p, "round "+f.Round)
	}
	if f.From != "" {
		p = append(p, "from "+f.From)
	}
	if f.To != "" {
		p = append(p, "to "+f.To)
	}
	if f.Dataset != "" {
		p = append(p, "dataset "+f.Dataset)
	}
	if len(p) == 0 {
		return "all competitions and seasons"
	}
	return strings.Join(p, ", ")
}

func writeRecord(b *strings.Builder, r Record) {
	fmt.Fprintf(b, "- Matches: %d\n- Wins: %d, Draws: %d, Losses: %d\n- Goals For: %d, Goals Against: %d (difference %+d)\n- Points: %d\n- Win rate: %.1f%%\n",
		r.Played, r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgainst, r.GoalDiff(), r.Points(), r.WinRate())
}

func formatPlayer(p *Player) string {
	club := p.Club
	if club == "" {
		club = "no club"
	}
	return fmt.Sprintf("%s - Overall: %d, Position: %s, Club: %s, Age: %d, Nationality: %s", p.Name, p.Overall, orDash(p.Position), club, p.Age, p.Nationality)
}

func orDash(s string) string {
	if s == "" {
		return "-"
	}
	return s
}

// ---- handlers ----

func toolFindMatches(db *DB, a Args) (string, error) {
	f, err := a.filter()
	if err != nil {
		return "", err
	}
	limit, err := a.limit(20)
	if err != nil {
		return "", err
	}
	ms, err := db.FindMatches(f)
	if err != nil {
		return "", err
	}
	var b strings.Builder
	title := "Matches"
	if f.Team != "" {
		title = teamNames(db.ResolveTeam(f.Team))
		if f.Opponent != "" {
			title += " vs " + teamNames(db.ResolveTeam(f.Opponent))
		}
		if v := fold(f.Venue); v == "home" || v == "away" {
			title += " (" + v + ")"
		}
	} else if f.Opponent != "" {
		title = teamNames(db.ResolveTeam(f.Opponent))
	}
	fmt.Fprintf(&b, "%s - %s: %d matches found (most recent first)\n", title, describeFilter(f), len(ms))
	if len(ms) == 0 {
		b.WriteString("No matches in the provided data match these criteria.\n")
		return b.String(), nil
	}
	writeMatches(&b, ms, limit)
	if f.Team != "" && f.Opponent != "" {
		h, _ := db.HeadToHead(f.Team, f.Opponent, f)
		if h != nil {
			fmt.Fprintf(&b, "\nHead-to-head in dataset: %s %d wins, %s %d wins, %d draws\n", teamNames(h.A), h.AWins, teamNames(h.B), h.BWins, h.Draws)
		}
	}
	return b.String(), nil
}

func toolHeadToHead(db *DB, a Args) (string, error) {
	f, err := a.filter()
	if err != nil {
		return "", err
	}
	limit, err := a.limit(10)
	if err != nil {
		return "", err
	}
	h, err := db.HeadToHead(a.str("team_a"), a.str("team_b"), f)
	if err != nil {
		return "", err
	}
	an, bn := teamNames(h.A), teamNames(h.B)
	var b strings.Builder
	fmt.Fprintf(&b, "%s vs %s", an, bn)
	if len(h.A) == 1 && len(h.B) == 1 {
		if d := DerbyName(h.A[0], h.B[0]); d != "" {
			fmt.Fprintf(&b, " (%s)", d)
		}
	}
	fmt.Fprintf(&b, " - %s\n", describeFilter(f))
	if len(h.Matches) == 0 {
		b.WriteString("No matches between these teams in the provided data.\n")
		return b.String(), nil
	}
	fmt.Fprintf(&b, "Head-to-head in dataset (%d matches): %s %d wins, %s %d wins, %d draws\n", len(h.Matches), an, h.AWins, bn, h.BWins, h.Draws)
	fmt.Fprintf(&b, "Goals: %s %d, %s %d\n", an, h.AGoals, bn, h.BGoals)
	for i := len(h.Matches) - 1; i >= 0; i-- {
		if h.Matches[i].Played {
			fmt.Fprintf(&b, "Most recent meeting: %s\n", formatMatch(h.Matches[i]))
			break
		}
	}
	b.WriteString("\nMatches (most recent first):\n")
	writeMatches(&b, h.Matches, limit)
	return b.String(), nil
}

func toolTeamStats(db *DB, a Args) (string, error) {
	f, err := a.filter()
	if err != nil {
		return "", err
	}
	total, byComp, teams, err := db.TeamRecord(f)
	if err != nil {
		return "", err
	}
	venue := ""
	if v := fold(f.Venue); v == "home" || v == "away" {
		venue = v + " "
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s %srecord (%s):\n", teamNames(teams), venue, describeFilter(f))
	if total.Played == 0 {
		b.WriteString("No played matches in the provided data match these criteria.\n")
		return b.String(), nil
	}
	writeRecord(&b, total)
	if len(byComp) > 1 {
		b.WriteString("\nBy competition:\n")
		comps := make([]string, 0, len(byComp))
		for c := range byComp {
			comps = append(comps, c)
		}
		sort.Strings(comps)
		for _, c := range comps {
			r := byComp[c]
			fmt.Fprintf(&b, "- %s: %d matches, %dW %dD %dL, goals %d-%d, win rate %.1f%%\n", c, r.Played, r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgainst, r.WinRate())
		}
	}
	if venue == "" {
		for _, v := range []string{"home", "away"} {
			g := f
			g.Venue = v
			if r, _, _, err := db.TeamRecord(g); err == nil && r.Played > 0 {
				fmt.Fprintf(&b, "%s: %d matches, %dW %dD %dL, goals %d-%d, win rate %.1f%%\n", titleCase(v), r.Played, r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgainst, r.WinRate())
			}
		}
	}
	return b.String(), nil
}

func relegationSpots(comp string, season, teams int) int {
	if comp != CompSerieA && comp != CompSerieB {
		return 0
	}
	if comp == CompSerieA && season == 2003 {
		return 2
	}
	if teams < 12 {
		return 0
	}
	return 4
}

func toolStandings(db *DB, a Args) (string, error) {
	season, err := a.int("season", 0)
	if err != nil {
		return "", err
	}
	comp := a.str("competition")
	if c := normalizeCompetition(comp); c == CompLibertadores || c == CompCopaDoBrasil {
		return toolBracket(db, a)
	}
	rows, complete, err := db.Standings(comp, season)
	if err != nil {
		return "", err
	}
	limit, err := a.limit(len(rows))
	if err != nil {
		return "", err
	}
	cn := normalizeCompetition(comp)
	if cn == "" {
		cn = CompSerieA
	}
	var b strings.Builder
	kind := "Final Standings"
	if !complete {
		kind = "Standings (season incomplete in data)"
	}
	fmt.Fprintf(&b, "%d %s %s (calculated from matches):\n", season, cn, kind)
	releg := relegationSpots(cn, season, len(rows))
	for i, r := range rows {
		if i >= limit && i < len(rows)-releg {
			continue
		}
		tag := ""
		if complete && i == 0 {
			tag = " - Champion"
		} else if complete && releg > 0 && i >= len(rows)-releg {
			tag = " - Relegated"
		}
		fmt.Fprintf(&b, "%d. %s - %d pts (%dW, %dD, %dL) GF %d GA %d GD %+d%s\n", i+1, r.Team.Name, r.Points(), r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgainst, r.GoalDiff(), tag)
	}
	b.WriteString("\nNote: computed purely from match results (3 pts/win; ties by wins, goal difference, goals scored). Points deductions and other off-pitch rulings are not in the data.\n")
	return b.String(), nil
}

func toolBracket(db *DB, a Args) (string, error) {
	season, err := a.int("season", 0)
	if err != nil {
		return "", err
	}
	if season == 0 {
		return "", fmt.Errorf("season is required")
	}
	comp := a.str("competition")
	if comp == "" {
		comp = CompLibertadores
	}
	ties, err := db.Bracket(comp, season)
	if err != nil {
		return "", err
	}
	cn := normalizeCompetition(comp)
	var b strings.Builder
	fmt.Fprintf(&b, "%d %s knockout bracket (from match data):\n", season, cn)
	if len(ties) == 0 {
		b.WriteString("No knockout-stage information for this season in the provided data.\n")
		return b.String(), nil
	}
	stage := ""
	var final *Tie
	for _, t := range ties {
		if t.Stage != stage {
			stage = t.Stage
			fmt.Fprintf(&b, "\n%s:\n", titleCase(stage))
		}
		var legs []string
		unplayed := false
		for _, m := range t.Matches {
			if m.Played {
				legs = append(legs, fmt.Sprintf("%s %d-%d %s", m.Home.Name, m.HomeGoals, m.AwayGoals, m.Away.Name))
			} else {
				unplayed = true
			}
		}
		res := "no result in data"
		if len(legs) > 0 {
			res = fmt.Sprintf("aggregate %d-%d", t.AGoals, t.BGoals)
			switch {
			case unplayed:
				res += ", tie incomplete in data"
			case t.Winner != nil:
				res += ", " + t.Winner.Name + " advance"
			default:
				res += ", level - decided by away goals/penalties (not in data)"
			}
			res += " [" + strings.Join(legs, "; ") + "]"
		}
		fmt.Fprintf(&b, "- %s vs %s: %s\n", t.A.Name, t.B.Name, res)
		if t.Stage == "final" {
			final = t
		}
	}
	switch {
	case final == nil:
		b.WriteString("\nThe final of this season is not identifiable in the provided data.\n")
	case final.Winner != nil:
		unplayed := false
		for _, m := range final.Matches {
			unplayed = unplayed || !m.Played
		}
		if unplayed {
			b.WriteString("\nFinal result incomplete in the provided data.\n")
		} else {
			fmt.Fprintf(&b, "\nChampion: %s\n", final.Winner.Name)
		}
	default:
		b.WriteString("\nChampion: not determinable from the data (final unplayed in data or level on aggregate).\n")
	}
	return b.String(), nil
}

func toolRankTeams(db *DB, a Args) (string, error) {
	f, err := a.filter()
	if err != nil {
		return "", err
	}
	limit, err := a.limit(10)
	if err != nil {
		return "", err
	}
	metric := strings.ReplaceAll(fold(a.str("metric")), " ", "_")
	if metric == "" {
		metric = "win_rate"
	}
	def := 1
	if metricIsRate(metric) {
		def = 10
		if f.Season == 0 {
			def = 30
		}
	}
	minM, err := a.int("min_matches", def)
	if err != nil {
		return "", err
	}
	venue := fold(a.str("venue"))
	f.Venue = ""
	asc := strings.HasPrefix(fold(a.str("order")), "asc") || fold(a.str("order")) == "worst"
	rows, err := db.RankTeams(metric, f, venue, minM, asc)
	if err != nil {
		return "", err
	}
	var b strings.Builder
	v := "all"
	if venue == "home" || venue == "away" {
		v = venue
	}
	fmt.Fprintf(&b, "Teams ranked by %s (%s matches, %s, min %d matches):\n", metric, v, describeFilter(f), minM)
	if len(rows) == 0 {
		b.WriteString("No teams match these criteria.\n")
	}
	for i, r := range rows {
		if i >= limit {
			break
		}
		val := rankMetrics[metric](r)
		vs := strconv.FormatFloat(val, 'f', 2, 64)
		if val == math.Trunc(val) && !metricIsRate(metric) {
			vs = strconv.Itoa(int(val))
		} else if metric == "win_rate" {
			vs = fmt.Sprintf("%.1f%%", val)
		}
		fmt.Fprintf(&b, "%d. %s - %s: %s (%d matches: %dW %dD %dL, goals %d-%d)\n", i+1, r.Team.Name, metric, vs, r.Played, r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgainst)
	}
	return b.String(), nil
}

func toolBiggestWins(db *DB, a Args) (string, error) {
	f, err := a.filter()
	if err != nil {
		return "", err
	}
	limit, err := a.limit(10)
	if err != nil {
		return "", err
	}
	ms, err := db.BiggestWins(f, limit)
	if err != nil {
		return "", err
	}
	var b strings.Builder
	scope := describeFilter(f)
	if f.Team != "" {
		scope = teamNames(db.ResolveTeam(f.Team)) + ", " + scope
	}
	fmt.Fprintf(&b, "Biggest victories (%s):\n", scope)
	if len(ms) == 0 {
		b.WriteString("No played matches match these criteria.\n")
	}
	for i, m := range ms {
		fmt.Fprintf(&b, "%d. %s\n", i+1, formatMatch(m))
	}
	return b.String(), nil
}

func writeStats(b *strings.Builder, label string, s SeasonStats) {
	fmt.Fprintf(b, "%s:\n- Matches: %d, Goals: %d\n- Average goals per match: %.2f (home %.2f, away %.2f)\n- Home win rate: %.1f%%, Draws: %.1f%%, Away win rate: %.1f%%\n",
		label, s.Matches, s.Goals, s.AvgGoals(), ratio(float64(s.HomeGoals), float64(s.Matches)), ratio(float64(s.AwayGoals), float64(s.Matches)),
		pct(s.HomeWins, s.Matches), pct(s.Draws, s.Matches), pct(s.AwayWins, s.Matches))
	if s.CornerMatches > 0 {
		fmt.Fprintf(b, "- Average corners per match: %.2f (over %.0f matches with data)\n", s.Corners/s.CornerMatches, s.CornerMatches)
	}
	if s.ShotMatches > 0 {
		fmt.Fprintf(b, "- Average shots per match: %.2f (over %.0f matches with data)\n", s.Shots/s.ShotMatches, s.ShotMatches)
	}
}

func toolLeagueStats(db *DB, a Args) (string, error) {
	f, err := a.filter()
	if err != nil {
		return "", err
	}
	var seasons []int
	if raw, ok := a["seasons"].([]any); ok {
		for _, v := range raw {
			n, err := Args{"s": v}.int("s", 0)
			if err != nil || n == 0 {
				return "", fmt.Errorf("seasons must be a list of years")
			}
			seasons = append(seasons, n)
		}
	}
	if len(seasons) == 0 {
		seasons = []int{f.Season}
	}
	var b strings.Builder
	for i, s := range seasons {
		g := f
		g.Season = s
		st, err := db.Stats(g)
		if err != nil {
			return "", err
		}
		if i > 0 {
			b.WriteString("\n")
		}
		label := "Statistics for " + describeFilter(g)
		if g.Team != "" {
			label += " (matches involving " + teamNames(db.ResolveTeam(g.Team)) + ")"
		}
		if st.Matches == 0 {
			fmt.Fprintf(&b, "%s:\nNo played matches in the provided data.\n", label)
			continue
		}
		writeStats(&b, label, st)
		if c := normalizeCompetition(g.Competition); s != 0 && (c == CompSerieA || c == CompSerieB || c == CompSerieC) && g.Team == "" {
			if rows, complete, err := db.Standings(c, s); err == nil {
				lead := "Leader"
				if complete {
					lead = "Champion"
				}
				fmt.Fprintf(&b, "- %s: %s (%d pts)\n", lead, rows[0].Team.Name, rows[0].Points())
				top, _ := db.RankTeams("goals_for", MatchFilter{Competition: c, Season: s, Dataset: g.Dataset}, "", 1, false)
				if len(top) > 0 {
					fmt.Fprintf(&b, "- Most goals scored: %s (%d)\n", top[0].Team.Name, top[0].GoalsFor)
				}
			}
		}
	}
	return b.String(), nil
}

func toolDerbies(db *DB, a Args) (string, error) {
	f, err := a.filter()
	if err != nil {
		return "", err
	}
	limit, err := a.limit(30)
	if err != nil {
		return "", err
	}
	ms, err := db.Derbies(f)
	if err != nil {
		return "", err
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Derbies (matches between traditional rivals) - %s: %d found (most recent first)\n", describeFilter(f), len(ms))
	n := 0
	for i := len(ms) - 1; i >= 0 && n < limit; i-- {
		fmt.Fprintf(&b, "- %s - %s\n", formatMatch(ms[i]), DerbyName(ms[i].Home, ms[i].Away))
		n++
	}
	if rest := len(ms) - n; rest > 0 {
		fmt.Fprintf(&b, "- ... (%d more derbies in dataset)\n", rest)
	}
	return b.String(), nil
}

func (a Args) playerFilter() (PlayerFilter, error) {
	minO, err := a.int("min_overall", 0)
	if err != nil {
		return PlayerFilter{}, err
	}
	maxAge, err := a.int("max_age", 0)
	return PlayerFilter{Name: a.str("name"), Nationality: a.str("nationality"), Club: a.str("club"),
		Position: a.str("position"), MinOverall: minO, MaxAge: maxAge, SortBy: a.str("sort_by")}, err
}

func toolSearchPlayers(db *DB, a Args) (string, error) {
	f, err := a.playerFilter()
	if err != nil {
		return "", err
	}
	limit, err := a.limit(15)
	if err != nil {
		return "", err
	}
	ps, err := db.SearchPlayers(f)
	if err != nil {
		return "", err
	}
	var crit []string
	for _, kv := range [][2]string{{"name", f.Name}, {"nationality", f.Nationality}, {"club", f.Club}, {"position", f.Position}} {
		if kv[1] != "" {
			crit = append(crit, kv[0]+" "+strconv.Quote(kv[1]))
		}
	}
	if f.MinOverall > 0 {
		crit = append(crit, fmt.Sprintf("overall >= %d", f.MinOverall))
	}
	if f.MaxAge > 0 {
		crit = append(crit, fmt.Sprintf("age <= %d", f.MaxAge))
	}
	if len(crit) == 0 {
		crit = []string{"all players"}
	}
	sortBy := f.SortBy
	if sortBy == "" {
		sortBy = "overall"
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Players (%s): %d found, sorted by %s\n", strings.Join(crit, ", "), len(ps), sortBy)
	if len(ps) == 0 {
		b.WriteString("No players in the FIFA dataset match these criteria.")
		if f.Club != "" {
			b.WriteString(" Note: the FIFA file only licenses some Brazilian clubs (e.g. Flamengo, Palmeiras, Corinthians and São Paulo are absent).")
		}
		b.WriteString("\n")
		return b.String(), nil
	}
	attr := attributeByName(f.SortBy)
	for i, p := range ps {
		if i >= limit {
			fmt.Fprintf(&b, "... (%d more players)\n", len(ps)-limit)
			break
		}
		line := formatPlayer(p)
		if attr != "" {
			line += fmt.Sprintf(", %s: %d", attr, p.Attributes[attr])
		}
		fmt.Fprintf(&b, "%d. %s\n", i+1, line)
	}
	if a.bool("group_by_club") {
		b.WriteString("\nBy club:\n")
		for i, g := range GroupByClub(ps) {
			if i >= limit {
				break
			}
			fmt.Fprintf(&b, "- %s: %d players (avg rating: %.0f, best: %s %d)\n", g.Club, g.Count, g.AvgOverall, g.Best.Name, g.Best.Overall)
		}
	}
	return b.String(), nil
}

func toolPlayerDetails(db *DB, a Args) (string, error) {
	name := a.str("name")
	id, err := a.int("id", 0)
	if err != nil {
		return "", err
	}
	if name == "" && id == 0 {
		return "", fmt.Errorf("name or id is required")
	}
	var ps []*Player
	if id != 0 {
		for _, p := range db.Players {
			if p.ID == id {
				ps = append(ps, p)
			}
		}
	} else {
		ps, _ = db.SearchPlayers(PlayerFilter{Name: name})
		for _, p := range ps { // an exact name match wins
			if p.foldName == fold(name) {
				ps = []*Player{p}
				break
			}
		}
	}
	if len(ps) == 0 {
		return fmt.Sprintf("No player matching %q found in the FIFA dataset.\n", name+a.str("id")), nil
	}
	p := ps[0]
	var b strings.Builder
	fmt.Fprintf(&b, "%s (FIFA ID %d)\n- Age: %d, Nationality: %s\n- Club: %s, Position: %s, Jersey: %s\n- Overall: %d, Potential: %d\n- Height: %s, Weight: %s, Preferred foot: %s\n- Value: %s, Wage: %s\n",
		p.Name, p.ID, p.Age, p.Nationality, orDash(p.Club), orDash(p.Position), orDash(p.Jersey), p.Overall, p.Potential,
		orDash(p.Height), orDash(p.Weight), orDash(p.Foot), orDash(p.Value), orDash(p.Wage))
	var attrs []string
	for _, c := range attributeColumns {
		if v, ok := p.Attributes[c]; ok {
			attrs = append(attrs, fmt.Sprintf("%s %d", c, v))
		}
	}
	if len(attrs) > 0 {
		fmt.Fprintf(&b, "- Attributes: %s\n", strings.Join(attrs, ", "))
	}
	if t := db.Teams[p.ClubKey]; t != nil {
		if r, _, _, err := db.TeamRecord(MatchFilter{Team: t.Name}); err == nil && r.Played > 0 {
			fmt.Fprintf(&b, "- Club in match data: %s - %d matches, %dW %dD %dL\n", t.Name, r.Played, r.Wins, r.Draws, r.Losses)
		}
	}
	if len(ps) > 1 {
		fmt.Fprintf(&b, "\nOther players matching %q:\n", name)
		for i, o := range ps[1:] {
			if i >= 9 {
				fmt.Fprintf(&b, "... (%d more)\n", len(ps)-10)
				break
			}
			fmt.Fprintf(&b, "- %s\n", formatPlayer(o))
		}
	}
	return b.String(), nil
}

func toolBrazilianClubPlayers(db *DB, a Args) (string, error) {
	limit, err := a.limit(30)
	if err != nil {
		return "", err
	}
	ps, err := db.SearchPlayers(PlayerFilter{Nationality: a.str("nationality")})
	if err != nil {
		return "", err
	}
	var in []*Player
	for _, p := range ps {
		if t := db.Teams[p.ClubKey]; t != nil && brStates[t.State] {
			in = append(in, p)
		}
	}
	who := "Players"
	if n := a.str("nationality"); n != "" {
		who = n + " players"
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s at Brazilian clubs (FIFA dataset clubs that also appear in the match data): %d players\n", who, len(in))
	for i, g := range GroupByClub(in) {
		if i >= limit {
			break
		}
		fmt.Fprintf(&b, "- %s: %d players (avg rating: %.0f, best: %s %d)\n", g.Club, g.Count, g.AvgOverall, g.Best.Name, g.Best.Overall)
	}
	return b.String(), nil
}

func toolTeamProfile(db *DB, a Args) (string, error) {
	ts := db.ResolveTeam(a.str("team"))
	if len(ts) == 0 {
		return "", fmt.Errorf("no team matching %q found in the data", a.str("team"))
	}
	if len(ts) > 1 {
		return fmt.Sprintf("%q is ambiguous; matching teams: %s\n", a.str("team"), teamNames(ts)), nil
	}
	t := ts[0]
	var b strings.Builder
	fmt.Fprintf(&b, "%s", t.Name)
	if t.State != "" {
		fmt.Fprintf(&b, " (%s)", t.State)
	}
	b.WriteString("\n\nCompetitions played (in provided data):\n")
	type cs struct {
		rec    Record
		lo, hi int
	}
	comps := map[string]*cs{}
	var last *Match
	for _, m := range db.Matches {
		if !db.IsPrimary(m) || (m.Home != t && m.Away != t) {
			continue
		}
		c := comps[m.Competition]
		if c == nil {
			c = &cs{lo: m.Season, hi: m.Season}
			comps[m.Competition] = c
		}
		if m.Season < c.lo {
			c.lo = m.Season
		}
		if m.Season > c.hi {
			c.hi = m.Season
		}
		if m.Played {
			if m.Home == t {
				c.rec.add(m.HomeGoals, m.AwayGoals)
			} else {
				c.rec.add(m.AwayGoals, m.HomeGoals)
			}
			last = m
		}
	}
	names := make([]string, 0, len(comps))
	for c := range comps {
		names = append(names, c)
	}
	sort.Strings(names)
	for _, n := range names {
		c := comps[n]
		fmt.Fprintf(&b, "- %s (%d-%d): %d matches, %dW %dD %dL, goals %d-%d\n", n, c.lo, c.hi, c.rec.Played, c.rec.Wins, c.rec.Draws, c.rec.Losses, c.rec.GoalsFor, c.rec.GoalsAgainst)
	}
	if last != nil {
		fmt.Fprintf(&b, "\nMost recent match in data: %s\n", formatMatch(last))
	}
	var rivals []string
	for _, d := range derbies {
		o := ""
		if d.A == t.Key {
			o = d.B
		} else if d.B == t.Key {
			o = d.A
		}
		if ot := db.Teams[o]; ot != nil {
			rivals = append(rivals, fmt.Sprintf("%s (%s)", ot.Name, d.Name))
		}
	}
	if len(rivals) > 0 {
		fmt.Fprintf(&b, "Traditional rivals: %s\n", strings.Join(rivals, ", "))
	}
	var squad []*Player
	for _, p := range db.Players {
		if p.ClubKey == t.Key {
			squad = append(squad, p)
		}
	}
	sort.SliceStable(squad, func(i, j int) bool { return squad[i].Overall > squad[j].Overall })
	if len(squad) == 0 {
		b.WriteString("\nFIFA squad: this club is not in the FIFA player dataset.\n")
	} else {
		sum := 0
		for _, p := range squad {
			sum += p.Overall
		}
		fmt.Fprintf(&b, "\nFIFA squad (%s): %d players, avg overall %.1f. Top rated:\n", squad[0].Club, len(squad), float64(sum)/float64(len(squad)))
		for i, p := range squad {
			if i >= 5 {
				break
			}
			fmt.Fprintf(&b, "%d. %s\n", i+1, formatPlayer(p))
		}
	}
	return b.String(), nil
}

func toolListTeams(db *DB, a Args) (string, error) {
	limit, err := a.limit(50)
	if err != nil {
		return "", err
	}
	season, err := a.int("season", 0)
	if err != nil {
		return "", err
	}
	comp := ""
	if c := a.str("competition"); c != "" {
		if comp = normalizeCompetition(c); comp == "" {
			return "", fmt.Errorf("unknown competition %q", c)
		}
	}
	q := fold(a.str("query"))
	counts := map[*Team]int{}
	for _, m := range db.Matches {
		if !db.IsPrimary(m) || (comp != "" && m.Competition != comp) || (season != 0 && m.Season != season) {
			continue
		}
		counts[m.Home]++
		counts[m.Away]++
	}
	var ts []*Team
	for t := range counts {
		if q == "" || strings.Contains(db.teamFolds[t.Key], q) || strings.Contains(t.Key, q) {
			ts = append(ts, t)
		}
	}
	sort.Slice(ts, func(i, j int) bool {
		if counts[ts[i]] != counts[ts[j]] {
			return counts[ts[i]] > counts[ts[j]]
		}
		return ts[i].Name < ts[j].Name
	})
	var b strings.Builder
	fmt.Fprintf(&b, "Teams: %d found (ordered by matches in data)\n", len(ts))
	for i, t := range ts {
		if i >= limit {
			fmt.Fprintf(&b, "... (%d more teams)\n", len(ts)-limit)
			break
		}
		st := ""
		if t.State != "" {
			st = " [" + t.State + "]"
		}
		fmt.Fprintf(&b, "- %s%s: %d matches\n", t.Name, st, counts[t])
	}
	return b.String(), nil
}

func toolDatasetInfo(db *DB, _ Args) (string, error) {
	var b strings.Builder
	b.WriteString("Brazilian soccer knowledge graph - loaded data:\n")
	for _, s := range []string{SrcBrasileirao, SrcCup, SrcLibertadores, SrcExtended, SrcHistorical} {
		fmt.Fprintf(&b, "- %s (%s): %d rows\n", sourceFiles[s], s, db.Counts[s])
	}
	fmt.Fprintf(&b, "- fifa_data.csv (players): %d rows\n", db.Counts["fifa"])
	fmt.Fprintf(&b, "\nTeams: %d, Matches: %d, Players: %d\n\nCoverage by competition (de-duplicated view):\n", len(db.Teams), len(db.Matches), len(db.Players))
	type cov struct{ n, lo, hi int }
	cs := map[string]*cov{}
	for _, m := range db.Matches {
		if !db.IsPrimary(m) {
			continue
		}
		c := cs[m.Competition]
		if c == nil {
			c = &cov{lo: m.Season, hi: m.Season}
			cs[m.Competition] = c
		}
		c.n++
		if m.Season < c.lo {
			c.lo = m.Season
		}
		if m.Season > c.hi {
			c.hi = m.Season
		}
	}
	names := make([]string, 0, len(cs))
	for c := range cs {
		names = append(names, c)
	}
	sort.Strings(names)
	for _, n := range names {
		fmt.Fprintf(&b, "- %s: %d matches, seasons %d-%d\n", n, cs[n].n, cs[n].lo, cs[n].hi)
	}
	b.WriteString("\nMatches that appear in several files are counted once: each competition-season is read from one preferred file unless a 'dataset' is given.\n")
	return b.String(), nil
}

// Tools is the MCP tool catalogue.
var Tools = []Tool{
	{Name: "find_matches", Description: "Search matches by team, opponent, venue, competition, season, date range, stage or round. Returns dates, scores and competition, most recent first (so limit=1 answers 'when did X last play Y?'). With both team and opponent it also adds the head-to-head tally. Use stage='final' for cup finals.",
		Props: matchFilterProps(map[string]any{"team": pTeam, "opponent": strProp("Optional second team (matches between the two)."), "venue": pVenue,
			"stage": strProp("Cup stage: 'group stage', 'round of 16', 'quarterfinals', 'semifinals' or 'final'."), "round": strProp("Round number (league round or Copa do Brasil round)."), "limit": pLimit}),
		Handler: toolFindMatches},
	{Name: "head_to_head", Description: "Compare two teams head-to-head: wins for each, draws, goals, most recent meeting and the list of matches.",
		Props: matchFilterProps(map[string]any{"team_a": pTeam, "team_b": pTeam, "limit": pLimit}), Required: []string{"team_a", "team_b"}, Handler: toolHeadToHead},
	{Name: "team_stats", Description: "Win/draw/loss record, goals for/against, points and win rate for a team, optionally filtered by season, competition, venue (home/away) or dates, with a per-competition breakdown.",
		Props: matchFilterProps(map[string]any{"team": pTeam, "venue": pVenue, "opponent": strProp("Optional: only matches against this team.")}), Required: []string{"team"}, Handler: toolTeamStats},
	{Name: "team_profile", Description: "Cross-dataset overview of a club: which competitions it played and its record in each, most recent match, traditional rivals, and its squad in the FIFA player data.",
		Props: map[string]any{"team": pTeam}, Required: []string{"team"}, Handler: toolTeamProfile},
	{Name: "standings", Description: "League table for a season calculated from match results (champion, points, W/D/L, goals, relegation zone). Default competition is Brasileirão Série A; Serie B and Serie C are also available. For Copa do Brasil/Libertadores it returns the knockout bracket instead.",
		Props: map[string]any{"season": pSeason, "competition": pComp, "limit": intProp("Show only the top N (the relegation zone is always shown).")}, Required: []string{"season"}, Handler: toolStandings},
	{Name: "knockout_bracket", Description: "Knockout-stage ties (round of 16 to final, with aggregate scores and the champion when determinable) for a Copa Libertadores or Copa do Brasil season.",
		Props: map[string]any{"season": pSeason, "competition": strProp("'Libertadores' (default) or 'Copa do Brasil'.")}, Required: []string{"season"}, Handler: toolBracket},
	{Name: "rank_teams", Description: "Rank teams by a metric: points, wins, draws, losses, goals_for, goals_against, goal_difference, win_rate, points_per_match, goals_per_match, goals_against_per_match. Filter by competition/season and by venue (home/away) - e.g. best home record, most goals in Serie A 2023, best away record.",
		Props: matchFilterProps(map[string]any{"metric": strProp("Metric to rank by (default win_rate)."), "venue": strProp("'home' = home records, 'away' = away records, omit for all matches."),
			"min_matches": intProp("Minimum matches played to be ranked (default 30 for rate metrics over all seasons, 10 within a season, else 1)."), "order": strProp("'desc' (default, best first) or 'asc'."), "limit": pLimit}),
		Handler: toolRankTeams},
	{Name: "biggest_wins", Description: "Matches with the largest winning margins, optionally filtered by team, competition, season or dates.",
		Props: matchFilterProps(map[string]any{"team": pTeam, "limit": pLimit}), Handler: toolBiggestWins},
	{Name: "league_stats", Description: "Aggregate statistics: matches, goals, average goals per match, home/draw/away rates (plus corners and shots when available). Pass 'seasons' (e.g. [2018, 2019]) to compare seasons side by side.",
		Props:   matchFilterProps(map[string]any{"team": strProp("Optional: only matches involving this team."), "seasons": map[string]any{"type": "array", "items": map[string]any{"type": "integer"}, "description": "Several seasons to compare."}}),
		Handler: toolLeagueStats},
	{Name: "list_derbies", Description: "Matches between traditional rivals (Fla-Flu, Derby Paulista, Grenal, Clássico Mineiro, ...), filtered by season, competition, team or dates.",
		Props: matchFilterProps(map[string]any{"team": pTeam, "limit": pLimit}), Handler: toolDerbies},
	{Name: "search_players", Description: "Search the FIFA player database by name, nationality (e.g. 'Brazil'), club, position (forward, midfielder, defender, goalkeeper or codes like ST, CB) and minimum rating. Sorted by overall rating by default. Set group_by_club to add a per-club summary.",
		Props: map[string]any{"name": strProp("Full or partial player name (accents optional)."), "nationality": strProp("Country, e.g. 'Brazil'."), "club": strProp("Club name, e.g. 'Santos', 'Grêmio'."),
			"position": strProp("Position group or code."), "min_overall": intProp("Minimum overall rating."), "max_age": intProp("Maximum age."),
			"sort_by": strProp("overall (default), potential, age, name, or an attribute such as Finishing, Dribbling, SprintSpeed."), "group_by_club": map[string]any{"type": "boolean", "description": "Add a count/average rating per club."}, "limit": pLimit},
		Handler: toolSearchPlayers},
	{Name: "player_details", Description: "Full profile of one player from the FIFA data: age, nationality, club, position, ratings, physical data and skill attributes.",
		Props: map[string]any{"name": strProp("Player name (full or partial)."), "id": intProp("FIFA player ID (alternative to name).")}, Handler: toolPlayerDetails},
	{Name: "players_at_brazilian_clubs", Description: "Per-club summary (count, average rating, best player) of players at Brazilian clubs, linking the FIFA data to clubs in the match data. Optionally filter by nationality.",
		Props: map[string]any{"nationality": strProp("Optional nationality filter, e.g. 'Brazil'."), "limit": pLimit}, Handler: toolBrazilianClubPlayers},
	{Name: "list_teams", Description: "List or search team names known to the server, optionally for one competition and season.",
		Props: map[string]any{"query": strProp("Substring of the team name."), "competition": pComp, "season": pSeason, "limit": pLimit}, Handler: toolListTeams},
	{Name: "dataset_info", Description: "Describe the loaded datasets: files, row counts, competitions and seasons covered.", Props: map[string]any{}, Handler: toolDatasetInfo},
}

// CallTool runs a tool by name.
func CallTool(db *DB, name string, args Args) (string, error) {
	for _, t := range Tools {
		if t.Name == name {
			for _, r := range t.Required {
				if args.str(r) == "" {
					return "", fmt.Errorf("missing required argument %q", r)
				}
			}
			return t.Handler(db, args)
		}
	}
	return "", fmt.Errorf("unknown tool %q", name)
}

func titleCase(s string) string {
	if s == "" {
		return s
	}
	return strings.ToUpper(s[:1]) + s[1:]
}
