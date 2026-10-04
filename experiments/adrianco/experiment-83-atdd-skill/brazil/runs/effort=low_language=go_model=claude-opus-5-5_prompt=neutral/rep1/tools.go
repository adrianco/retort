package main

import (
	"fmt"
	"sort"
	"strings"
)

// Args is the decoded tool argument object.
type Args map[string]any

func (a Args) Str(k string) string {
	if v, ok := a[k]; ok && v != nil {
		switch t := v.(type) {
		case string:
			return t
		case float64:
			return fmt.Sprintf("%g", t)
		}
		return fmt.Sprint(v)
	}
	return ""
}

func (a Args) Int(k string, def int) int {
	switch t := a[k].(type) {
	case float64:
		return int(t)
	case int:
		return t
	case string:
		if n := atoi(t); n >= 0 {
			return n
		}
	}
	return def
}

func (a Args) Bool(k string) bool {
	switch t := a[k].(type) {
	case bool:
		return t
	case string:
		return t == "true"
	}
	return false
}

// Tool describes an MCP tool.
type Tool struct {
	Name        string
	Description string
	Schema      map[string]any
	Handler     func(db *DB, a Args) (string, error)
}

func prop(typ, desc string) map[string]any { return map[string]any{"type": typ, "description": desc} }

func schema(props map[string]any, required ...string) map[string]any {
	s := map[string]any{"type": "object", "properties": props}
	if len(required) > 0 {
		s["required"] = required
	}
	return s
}

var (
	pTeam   = prop("string", "Team name (accents, state suffixes and variations accepted, e.g. 'Palmeiras', 'Palmeiras-SP', 'São Paulo')")
	pComp   = prop("string", "Competition: 'Brasileirão' (Serie A), 'Copa do Brasil', 'Libertadores', 'Serie B', 'Serie C'; empty = all")
	pSeason = prop("integer", "Season year, e.g. 2019")
	pLimit  = prop("integer", "Maximum number of results to list")
	pVenue  = prop("string", "'home', 'away' or empty for both")
)

// Tools is the registry of all MCP tools.
var Tools = []Tool{
	{"search_matches", "Find matches by team, opponent, competition, season, date range or stage (e.g. 'final'). Searches all match datasets.",
		schema(map[string]any{"team": pTeam, "opponent": pTeam, "venue": pVenue, "competition": pComp, "season": pSeason,
			"date_from": prop("string", "Start date (YYYY-MM-DD or DD/MM/YYYY)"), "date_to": prop("string", "End date"),
			"stage": prop("string", "Round/stage, e.g. 'final', 'semifinals', 'group stage', or round number"), "limit": pLimit,
			"order": prop("string", "'desc' (most recent first, default) or 'asc'")}), toolSearchMatches},
	{"head_to_head", "Head-to-head record and match list between two teams.",
		schema(map[string]any{"team1": pTeam, "team2": pTeam, "competition": pComp, "limit": pLimit}, "team1", "team2"), toolH2H},
	{"team_record", "Win/draw/loss record, goals for/against and win rate for a team, optionally by season, competition and venue.",
		schema(map[string]any{"team": pTeam, "season": pSeason, "competition": pComp, "venue": pVenue}, "team"), toolTeamRecord},
	{"team_overview", "Competitions and seasons a team appears in, with per-competition records, plus FIFA players at the club.",
		schema(map[string]any{"team": pTeam}, "team"), toolTeamOverview},
	{"standings", "League table for a season calculated from match results (champion, relegation zone).",
		schema(map[string]any{"season": pSeason, "competition": pComp, "limit": pLimit}, "season"), toolStandings},
	{"competition_stats", "Aggregate statistics: matches, goals per match, home/away win and draw rates; optionally per season. Set compare_seasons to compare several seasons.",
		schema(map[string]any{"competition": pComp, "season": pSeason, "compare_seasons": prop("string", "Comma-separated seasons, e.g. '2018,2019'")}), toolCompStats},
	{"biggest_wins", "Largest margin victories, optionally filtered by competition, season or team.",
		schema(map[string]any{"competition": pComp, "season": pSeason, "team": pTeam, "limit": pLimit}), toolBiggestWins},
	{"rank_teams", "Rank teams by a metric (win_rate, wins, goals_for, goals_against, points) over home, away or all matches.",
		schema(map[string]any{"metric": prop("string", "win_rate (default), wins, goals_for, goals_against, points"), "venue": pVenue,
			"competition": pComp, "season": pSeason, "min_matches": prop("integer", "Minimum matches to qualify (default 10)"), "limit": pLimit}), toolRankTeams},
	{"derbies", "List traditional derby matches (Fla-Flu, Grenal, Derby Paulista, ...), optionally by season or team.",
		schema(map[string]any{"season": pSeason, "team": pTeam, "competition": pComp, "limit": pLimit}), toolDerbies},
	{"search_players", "Search FIFA player database by name, nationality, club, position and minimum rating. Sorted by overall rating.",
		schema(map[string]any{"name": prop("string", "Player name substring"), "nationality": prop("string", "e.g. 'Brazil'"),
			"club": prop("string", "Club name"), "position": prop("string", "Position code (ST, GK, CAM...) or group (forward, midfielder, defender, goalkeeper)"),
			"min_overall": prop("integer", "Minimum overall rating"), "brazilian_clubs_only": prop("boolean", "Only players at clubs in the Brazilian match data"),
			"limit": pLimit}), toolSearchPlayers},
	{"players_by_club", "Group players (optionally filtered by nationality) by club with counts and average rating. Defaults to Brazilian players at Brazilian clubs.",
		schema(map[string]any{"nationality": prop("string", "Nationality filter (default Brazil)"), "brazilian_clubs_only": prop("boolean", "Default true"), "limit": pLimit}), toolPlayersByClub},
	{"dataset_info", "Describe the loaded datasets and record counts.", schema(map[string]any{}), toolInfo},
}

func limit(a Args, def int) int {
	l := a.Int("limit", def)
	if l <= 0 {
		l = def
	}
	return l
}

func filterFromArgs(a Args) (MatchFilter, error) {
	f := MatchFilter{Team: a.Str("team"), Opponent: a.Str("opponent"), Venue: strings.ToLower(a.Str("venue")),
		Competition: a.Str("competition"), Season: a.Int("season", 0), Stage: a.Str("stage")}
	var err error
	if s := a.Str("date_from"); s != "" {
		if f.From, err = ParseDate(s); err != nil {
			return f, err
		}
	}
	if s := a.Str("date_to"); s != "" {
		if f.To, err = ParseDate(s); err != nil {
			return f, err
		}
	}
	return f, nil
}

func listMatches(b *strings.Builder, ms []*Match, n int, desc bool) {
	idx := func(i int) *Match {
		if desc {
			return ms[len(ms)-1-i]
		}
		return ms[i]
	}
	for i := 0; i < len(ms) && i < n; i++ {
		fmt.Fprintf(b, "- %s\n", FormatMatch(idx(i)))
	}
	if len(ms) > n {
		fmt.Fprintf(b, "- ... (%d more matches in dataset)\n", len(ms)-n)
	}
}

func toolSearchMatches(db *DB, a Args) (string, error) {
	f, err := filterFromArgs(a)
	if err != nil {
		return "", err
	}
	ms, err := db.Filter(f)
	if err != nil {
		return "", err
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Found %d matches", len(ms))
	if f.Team != "" {
		fmt.Fprintf(&b, " for %s", db.displayFor(f.Team))
	}
	if f.Opponent != "" {
		fmt.Fprintf(&b, " vs %s", db.displayFor(f.Opponent))
	}
	b.WriteString(":\n")
	listMatches(&b, ms, limit(a, 25), a.Str("order") != "asc")
	if f.Team != "" && len(ms) > 0 {
		var r Record
		tk := db.ResolveTeam(f.Team)
		for _, m := range ms {
			if tk[m.HomeKey] {
				r.add(m.HomeGoals, m.AwayGoals)
			} else {
				r.add(m.AwayGoals, m.HomeGoals)
			}
		}
		fmt.Fprintf(&b, "\nRecord in these matches: %dW %dD %dL, goals %d-%d\n", r.W, r.D, r.L, r.GF, r.GA)
	}
	return b.String(), nil
}

func toolH2H(db *DB, a Args) (string, error) {
	h, err := db.HeadToHead(a.Str("team1"), a.Str("team2"), a.Str("competition"))
	if err != nil {
		return "", err
	}
	var b strings.Builder
	title := fmt.Sprintf("%s vs %s", h.A, h.B)
	ka, kb := TeamKey(a.Str("team1")), TeamKey(a.Str("team2"))
	if d := DerbyName(ka, kb); d != "" {
		title += " (" + d + ")"
	}
	fmt.Fprintf(&b, "%s:\n", title)
	listMatches(&b, h.Matches, limit(a, 15), true)
	fmt.Fprintf(&b, "\nHead-to-head in dataset (%d matches): %s %d wins, %s %d wins, %d draws\n", len(h.Matches), h.A, h.AWins, h.B, h.BWins, h.Draws)
	fmt.Fprintf(&b, "Goals: %s %d, %s %d\n", h.A, h.AGoals, h.B, h.BGoals)
	return b.String(), nil
}

func describeScope(a Args) string {
	var parts []string
	if s := a.Int("season", 0); s != 0 {
		parts = append(parts, fmt.Sprint(s))
	}
	if c := NormalizeCompetition(a.Str("competition")); c != "" {
		parts = append(parts, c)
	}
	if len(parts) == 0 {
		return "all competitions"
	}
	return strings.Join(parts, " ")
}

func toolTeamRecord(db *DB, a Args) (string, error) {
	f, err := filterFromArgs(a)
	if err != nil {
		return "", err
	}
	if f.Team == "" {
		return "", fmt.Errorf("team is required")
	}
	r, _, err := db.TeamRecord(f)
	if err != nil {
		return "", err
	}
	v := ""
	if f.Venue == "home" || f.Venue == "away" {
		v = f.Venue + " "
	}
	return fmt.Sprintf("%s %srecord (%s):\n- Matches: %d\n- Wins: %d, Draws: %d, Losses: %d\n- Goals For: %d, Goals Against: %d\n- Points: %d\n- Win rate: %.1f%%\n",
		db.displayFor(f.Team), v, describeScope(a), r.Played, r.W, r.D, r.L, r.GF, r.GA, r.Points(), r.WinRate()), nil
}

func toolTeamOverview(db *DB, a Args) (string, error) {
	team := a.Str("team")
	ms, err := db.Filter(MatchFilter{Team: team})
	if err != nil {
		return "", err
	}
	tk := db.ResolveTeam(team)
	type agg struct {
		r       Record
		seasons map[int]bool
	}
	by := map[string]*agg{}
	for _, m := range ms {
		g := by[m.Competition]
		if g == nil {
			g = &agg{seasons: map[int]bool{}}
			by[m.Competition] = g
		}
		g.seasons[m.Season] = true
		if tk[m.HomeKey] {
			g.r.add(m.HomeGoals, m.AwayGoals)
		} else {
			g.r.add(m.AwayGoals, m.HomeGoals)
		}
	}
	var comps []string
	for c := range by {
		comps = append(comps, c)
	}
	sort.Strings(comps)
	var b strings.Builder
	fmt.Fprintf(&b, "%s - competitions in dataset (%d matches total):\n", db.displayFor(team), len(ms))
	for _, c := range comps {
		g := by[c]
		var ss []int
		for s := range g.seasons {
			ss = append(ss, s)
		}
		sort.Ints(ss)
		fmt.Fprintf(&b, "- %s: %d matches, %dW %dD %dL, goals %d-%d, seasons %d-%d (%d seasons)\n", c, g.r.Played, g.r.W, g.r.D, g.r.L, g.r.GF, g.r.GA, ss[0], ss[len(ss)-1], len(ss))
	}
	ps := db.SearchPlayers(PlayerFilter{Club: team})
	if len(ps) > 0 {
		fmt.Fprintf(&b, "\nFIFA players at club (%d):\n", len(ps))
		for i, p := range ps {
			if i >= 10 {
				break
			}
			fmt.Fprintf(&b, "%d. %s\n", i+1, FormatPlayer(p))
		}
	}
	return b.String(), nil
}

func toolStandings(db *DB, a Args) (string, error) {
	season := a.Int("season", 0)
	comp := NormalizeCompetition(a.Str("competition"))
	if comp == "" {
		comp = CompBrasileirao
	}
	if comp == CompCopaBrasil || comp == CompLibertad {
		return "", fmt.Errorf("%s is a knockout competition; use search_matches with stage='final' instead", comp)
	}
	t := db.Standings(comp, season)
	if len(t) == 0 {
		return "", fmt.Errorf("no %s matches found for season %d", comp, season)
	}
	n := limit(a, len(t))
	var b strings.Builder
	fmt.Fprintf(&b, "%d %s Final Standings (calculated from matches):\n", season, comp)
	for i, r := range t {
		if i >= n {
			break
		}
		note := ""
		if i == 0 {
			note = " - Champion"
		} else if comp == CompBrasileirao && len(t) >= 20 && i >= len(t)-4 {
			note = " - Relegated"
		}
		fmt.Fprintf(&b, "%d. %s - %d pts (%dW, %dD, %dL, GF %d, GA %d, GD %+d)%s\n", i+1, r.Team, r.Points(), r.W, r.D, r.L, r.GF, r.GA, r.GD(), note)
	}
	return b.String(), nil
}

func statsLine(s CompStats) string {
	avg := 0.0
	if s.Matches > 0 {
		avg = float64(s.Goals) / float64(s.Matches)
	}
	return fmt.Sprintf("Matches: %d, Goals: %d, Average goals per match: %.2f, Home win rate: %.1f%%, Away win rate: %.1f%%, Draw rate: %.1f%%",
		s.Matches, s.Goals, avg, pct(s.HomeWins, s.Matches), pct(s.AwayWins, s.Matches), pct(s.Draws, s.Matches))
}

func toolCompStats(db *DB, a Args) (string, error) {
	var b strings.Builder
	comp := a.Str("competition")
	if cs := a.Str("compare_seasons"); cs != "" {
		for _, s := range strings.Split(cs, ",") {
			season := atoi(s)
			ms, _ := db.Filter(MatchFilter{Competition: comp, Season: season})
			fmt.Fprintf(&b, "%d %s: %s\n", season, describeComp(comp), statsLine(Summarize(ms)))
			if NormalizeCompetition(comp) == CompBrasileirao || comp == "" {
				if t := db.Standings(CompBrasileirao, season); len(t) > 0 {
					fmt.Fprintf(&b, "  Brasileirão champion: %s (%d pts)\n", t[0].Team, t[0].Points())
				}
			}
		}
		return b.String(), nil
	}
	ms, err := db.Filter(MatchFilter{Competition: comp, Season: a.Int("season", 0)})
	if err != nil {
		return "", err
	}
	fmt.Fprintf(&b, "Statistics (%s):\n%s\n", describeScope(a), statsLine(Summarize(ms)))
	return b.String(), nil
}

func describeComp(c string) string {
	if n := NormalizeCompetition(c); n != "" {
		return n
	}
	return "all competitions"
}

func toolBiggestWins(db *DB, a Args) (string, error) {
	f, _ := filterFromArgs(a)
	ms, err := db.Filter(f)
	if err != nil {
		return "", err
	}
	ms = append([]*Match(nil), ms...)
	abs := func(x int) int {
		if x < 0 {
			return -x
		}
		return x
	}
	sort.SliceStable(ms, func(i, j int) bool {
		di, dj := abs(ms[i].HomeGoals-ms[i].AwayGoals), abs(ms[j].HomeGoals-ms[j].AwayGoals)
		if di != dj {
			return di > dj
		}
		return ms[i].HomeGoals+ms[i].AwayGoals > ms[j].HomeGoals+ms[j].AwayGoals
	})
	var b strings.Builder
	fmt.Fprintf(&b, "Biggest victories (%s):\n", describeScope(a))
	for i := 0; i < len(ms) && i < limit(a, 10); i++ {
		fmt.Fprintf(&b, "%d. %s\n", i+1, FormatMatch(ms[i]))
	}
	return b.String(), nil
}

func toolRankTeams(db *DB, a Args) (string, error) {
	f, _ := filterFromArgs(a)
	f.Team, f.Venue = "", ""
	ms, err := db.Filter(f)
	if err != nil {
		return "", err
	}
	venue := strings.ToLower(a.Str("venue"))
	recs := db.TeamRecords(ms, venue)
	minM := a.Int("min_matches", 10)
	metric := strings.ToLower(a.Str("metric"))
	if metric == "" {
		metric = "win_rate"
	}
	val := func(r Record) float64 {
		switch metric {
		case "wins":
			return float64(r.W)
		case "goals_for", "goals", "goals_scored":
			return float64(r.GF)
		case "goals_against", "goals_conceded":
			return -float64(r.GA)
		case "points":
			return float64(r.Points())
		}
		return r.WinRate()
	}
	var q []Record
	for _, r := range recs {
		if r.Played >= minM {
			q = append(q, r)
		}
	}
	sort.SliceStable(q, func(i, j int) bool {
		if val(q[i]) != val(q[j]) {
			return val(q[i]) > val(q[j])
		}
		return q[i].Team < q[j].Team
	})
	v := "overall"
	if venue == "home" || venue == "away" {
		v = venue
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Teams ranked by %s (%s matches, %s, min %d matches):\n", metric, v, describeScope(a), minM)
	for i := 0; i < len(q) && i < limit(a, 10); i++ {
		r := q[i]
		fmt.Fprintf(&b, "%d. %s - %d matches, %dW %dD %dL, GF %d, GA %d, win rate %.1f%%\n", i+1, r.Team, r.Played, r.W, r.D, r.L, r.GF, r.GA, r.WinRate())
	}
	return b.String(), nil
}

func toolDerbies(db *DB, a Args) (string, error) {
	f, err := filterFromArgs(a)
	if err != nil {
		return "", err
	}
	ms, err := db.Filter(f)
	if err != nil {
		return "", err
	}
	var b strings.Builder
	var ds []*Match
	for _, m := range ms {
		if DerbyName(m.HomeKey, m.AwayKey) != "" {
			ds = append(ds, m)
		}
	}
	fmt.Fprintf(&b, "Derby matches (%s): %d found\n", describeScope(a), len(ds))
	n := limit(a, 50)
	for i := 0; i < len(ds) && i < n; i++ {
		m := ds[len(ds)-1-i]
		fmt.Fprintf(&b, "- [%s] %s\n", DerbyName(m.HomeKey, m.AwayKey), FormatMatch(m))
	}
	if len(ds) > n {
		fmt.Fprintf(&b, "- ... (%d more)\n", len(ds)-n)
	}
	return b.String(), nil
}

func toolSearchPlayers(db *DB, a Args) (string, error) {
	ps := db.SearchPlayers(PlayerFilter{Name: a.Str("name"), Nationality: a.Str("nationality"), Club: a.Str("club"),
		Position: a.Str("position"), MinOverall: a.Int("min_overall", 0), BrazilianClubsOnly: a.Bool("brazilian_clubs_only")})
	var b strings.Builder
	if len(ps) == 0 && len(strings.Fields(a.Str("name"))) > 1 {
		// fall back to partial-name suggestions (e.g. surname only)
		seen := map[int]bool{}
		for _, w := range strings.Fields(a.Str("name")) {
			for _, p := range db.SearchPlayers(PlayerFilter{Name: w, Nationality: a.Str("nationality"), Club: a.Str("club")}) {
				if !seen[p.ID] {
					seen[p.ID] = true
					ps = append(ps, p)
				}
			}
		}
		sort.SliceStable(ps, func(i, j int) bool { return ps[i].Overall > ps[j].Overall })
		fmt.Fprintf(&b, "No exact match for %q; partial name matches:\n", a.Str("name"))
	}
	fmt.Fprintf(&b, "Found %d players:\n", len(ps))
	n := limit(a, 25)
	for i := 0; i < len(ps) && i < n; i++ {
		fmt.Fprintf(&b, "%d. %s\n", i+1, FormatPlayer(ps[i]))
	}
	if len(ps) > n {
		fmt.Fprintf(&b, "... (%d more)\n", len(ps)-n)
	}
	return b.String(), nil
}

func toolPlayersByClub(db *DB, a Args) (string, error) {
	nat := a.Str("nationality")
	if _, ok := a["nationality"]; !ok {
		nat = "Brazil"
	}
	brOnly := true
	if _, ok := a["brazilian_clubs_only"]; ok {
		brOnly = a.Bool("brazilian_clubs_only")
	}
	ps := db.SearchPlayers(PlayerFilter{Nationality: nat, BrazilianClubsOnly: brOnly})
	type g struct {
		club       string
		n, sum, mx int
		best       string
	}
	by := map[string]*g{}
	for _, p := range ps {
		if p.Club == "" {
			continue
		}
		x := by[p.Club]
		if x == nil {
			x = &g{club: p.Club}
			by[p.Club] = x
		}
		x.n++
		x.sum += p.Overall
		if p.Overall > x.mx {
			x.mx, x.best = p.Overall, p.Name
		}
	}
	var gs []*g
	for _, x := range by {
		gs = append(gs, x)
	}
	sort.Slice(gs, func(i, j int) bool {
		if gs[i].n != gs[j].n {
			return gs[i].n > gs[j].n
		}
		return gs[i].club < gs[j].club
	})
	var b strings.Builder
	fmt.Fprintf(&b, "%s players by club (%d players, %d clubs):\n", strings.TrimSpace(nat+" "), len(ps), len(gs))
	for i := 0; i < len(gs) && i < limit(a, 30); i++ {
		x := gs[i]
		fmt.Fprintf(&b, "- %s: %d players (avg rating: %.0f, best: %s %d)\n", x.club, x.n, float64(x.sum)/float64(x.n), x.best, x.mx)
	}
	return b.String(), nil
}

func toolInfo(db *DB, a Args) (string, error) {
	var b strings.Builder
	b.WriteString("Loaded datasets:\n")
	for _, f := range []string{SrcBrasileirao, SrcCup, SrcLib, SrcBRFootball, SrcHistorical, SrcFIFA} {
		fmt.Fprintf(&b, "- %s: %d records\n", f, db.Counts[f])
	}
	fmt.Fprintf(&b, "Unique matches after cross-dataset de-duplication: %d\nDistinct teams: %d\n", len(db.Unique()), len(db.TeamNames))
	return b.String(), nil
}
