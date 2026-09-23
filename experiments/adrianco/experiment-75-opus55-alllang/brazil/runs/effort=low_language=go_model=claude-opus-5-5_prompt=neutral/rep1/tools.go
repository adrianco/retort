package main

import (
	"fmt"
	"sort"
	"strings"
	"time"
)

// Tool describes an MCP tool.
type Tool struct {
	Name        string         `json:"name"`
	Description string         `json:"description"`
	InputSchema map[string]any `json:"inputSchema"`
	handler     func(db *DB, a Args) (string, error)
}

// Args wraps tool arguments with typed accessors.
type Args map[string]any

func (a Args) Str(k string) string {
	switch v := a[k].(type) {
	case string:
		return strings.TrimSpace(v)
	case float64:
		return fmt.Sprintf("%g", v)
	}
	return ""
}

func (a Args) Int(k string, def int) int {
	switch v := a[k].(type) {
	case float64:
		return int(v)
	case int:
		return v
	case string:
		if i := atoi(v); i >= 0 {
			return i
		}
	}
	return def
}

func (a Args) Date(k string) (time.Time, error) {
	s := a.Str(k)
	if s == "" {
		return time.Time{}, nil
	}
	t, _, err := ParseDate(s)
	return t, err
}

func prop(typ, desc string) map[string]any { return map[string]any{"type": typ, "description": desc} }

func schema(req []string, props map[string]any) map[string]any {
	s := map[string]any{"type": "object", "properties": props}
	if len(req) > 0 {
		s["required"] = req
	}
	return s
}

var (
	pTeam   = prop("string", "Team name (any variant, e.g. 'Palmeiras', 'Palmeiras-SP', 'São Paulo')")
	pComp   = prop("string", "Competition: 'Brasileirão' (Serie A), 'Copa do Brasil', 'Libertadores', 'Serie B', 'Serie C'. Omit for all.")
	pSeason = prop("integer", "Season year, e.g. 2019")
	pLimit  = prop("integer", "Maximum number of rows to return (default 20)")
)

func (db *DB) filterFromArgs(a Args) (MatchFilter, error) {
	from, err := a.Date("date_from")
	if err != nil {
		return MatchFilter{}, err
	}
	to, err := a.Date("date_to")
	if err != nil {
		return MatchFilter{}, err
	}
	return MatchFilter{Team: a.Str("team"), Opponent: a.Str("opponent"), Venue: strings.ToLower(a.Str("venue")),
		Competition: a.Str("competition"), Season: a.Int("season", 0), From: from, To: to, Stage: a.Str("stage")}, nil
}

func listMatches(db *DB, b *strings.Builder, ms []*Match, limit int) {
	for i, m := range ms {
		if i >= limit {
			fmt.Fprintf(b, "- ... (%d more matches in dataset)\n", len(ms)-limit)
			break
		}
		fmt.Fprintf(b, "- %s\n", db.FormatMatch(m))
	}
}

func unknownTeam(db *DB, name string) error {
	return fmt.Errorf("team %q not found in match data", name)
}

// Tools returns the full tool list.
func Tools() []Tool {
	return []Tool{
		{Name: "search_matches", Description: "Find matches by team, opponent, venue, competition, season, date range or stage (e.g. 'final'). Sources: all match CSVs, deduplicated.",
			InputSchema: schema(nil, map[string]any{"team": pTeam, "opponent": prop("string", "Opponent team (requires team)"),
				"venue": prop("string", "'home' or 'away' relative to team"), "competition": pComp, "season": pSeason,
				"date_from": prop("string", "Start date (YYYY-MM-DD or DD/MM/YYYY)"), "date_to": prop("string", "End date"),
				"stage": prop("string", "Stage/round, e.g. 'final', 'semifinals', 'group stage', '5'"), "limit": pLimit}),
			handler: toolSearchMatches},
		{Name: "head_to_head", Description: "Head-to-head record and match list between two teams.",
			InputSchema: schema([]string{"team_a", "team_b"}, map[string]any{"team_a": pTeam, "team_b": pTeam, "competition": pComp, "season": pSeason, "limit": pLimit}),
			handler:     toolHeadToHead},
		{Name: "team_stats", Description: "Win/draw/loss record, goals for/against and win rate for a team, optionally by season, competition and venue; includes per-competition breakdown.",
			InputSchema: schema([]string{"team"}, map[string]any{"team": pTeam, "season": pSeason, "competition": pComp, "venue": prop("string", "'home', 'away' or omit for all")}),
			handler:     toolTeamStats},
		{Name: "standings", Description: "League table for a season calculated from match results (default Brasileirão). Shows champion and relegated teams.",
			InputSchema: schema([]string{"season"}, map[string]any{"season": pSeason, "competition": pComp}),
			handler:     toolStandings},
		{Name: "competition_stats", Description: "Aggregate statistics: matches, average goals per match, home/away win and draw rates, and biggest wins. Optionally per competition/season/team.",
			InputSchema: schema(nil, map[string]any{"competition": pComp, "season": pSeason, "team": pTeam, "limit": pLimit}),
			handler:     toolCompetitionStats},
		{Name: "team_rankings", Description: "Rank teams by a metric: 'home_record', 'away_record', 'win_rate', 'goals_scored', 'goals_conceded', 'points'.",
			InputSchema: schema([]string{"metric"}, map[string]any{"metric": prop("string", "Ranking metric"), "competition": pComp, "season": pSeason,
				"min_matches": prop("integer", "Minimum matches to qualify (default 10)"), "limit": pLimit}),
			handler: toolRankings},
		{Name: "compare_seasons", Description: "Compare aggregate statistics and champions across seasons.",
			InputSchema: schema([]string{"seasons"}, map[string]any{"seasons": prop("string", "Comma separated years, e.g. '2018,2019'"), "competition": pComp}),
			handler:     toolCompareSeasons},
		{Name: "team_competitions", Description: "List the competitions (and seasons) a team appears in across all match files.",
			InputSchema: schema([]string{"team"}, map[string]any{"team": pTeam}), handler: toolTeamCompetitions},
		{Name: "derbies", Description: "List traditional derby (rivalry) matches, optionally for a season or a specific team.",
			InputSchema: schema(nil, map[string]any{"season": pSeason, "team": pTeam, "competition": pComp, "limit": pLimit}), handler: toolDerbies},
		{Name: "search_players", Description: "Search FIFA player database by name, nationality, club, position (code like 'ST' or group 'forward'/'midfielder'/'defender'/'goalkeeper') and minimum overall. Sorted by rating.",
			InputSchema: schema(nil, map[string]any{"name": prop("string", "Player name (partial)"), "nationality": prop("string", "e.g. 'Brazil'"),
				"club": prop("string", "Club name (partial)"), "position": prop("string", "Position code or group"),
				"min_overall": prop("integer", "Minimum overall rating"), "limit": pLimit}), handler: toolSearchPlayers},
		{Name: "player_details", Description: "Full profile of a player including skill ratings.",
			InputSchema: schema([]string{"name"}, map[string]any{"name": prop("string", "Player name")}), handler: toolPlayerDetails},
		{Name: "brazilian_clubs_players", Description: "Summarize FIFA players at Brazilian clubs (clubs that appear in match data): player count and average rating per club. Optionally only Brazilian nationals.",
			InputSchema: schema(nil, map[string]any{"brazilian_only": prop("boolean", "Only Brazilian nationality players"), "limit": pLimit}), handler: toolBrazilianClubs},
		{Name: "team_profile", Description: "Cross-file profile of a club: overall match record, competitions, and top FIFA-rated players at the club.",
			InputSchema: schema([]string{"team"}, map[string]any{"team": pTeam}), handler: toolTeamProfile},
		{Name: "dataset_info", Description: "Describe loaded datasets and row counts.", InputSchema: schema(nil, map[string]any{}), handler: toolDatasetInfo},
	}
}

func toolSearchMatches(db *DB, a Args) (string, error) {
	f, err := db.filterFromArgs(a)
	if err != nil {
		return "", err
	}
	if f.Team != "" && len(db.ResolveTeam(f.Team)) == 0 {
		return "", unknownTeam(db, f.Team)
	}
	ms := db.Find(f)
	var b strings.Builder
	fmt.Fprintf(&b, "Found %d matches", len(ms))
	if f.Team != "" {
		fmt.Fprintf(&b, " for %s", db.Name(db.ResolveTeam(f.Team)[0]))
		if f.Opponent != "" && len(db.ResolveTeam(f.Opponent)) > 0 {
			fmt.Fprintf(&b, " vs %s", db.Name(db.ResolveTeam(f.Opponent)[0]))
		}
	}
	b.WriteString(":\n")
	listMatches(db, &b, ms, a.Int("limit", 20))
	return b.String(), nil
}

func toolHeadToHead(db *DB, a Args) (string, error) {
	ta, tb := a.Str("team_a"), a.Str("team_b")
	ka, kb := db.ResolveTeam(ta), db.ResolveTeam(tb)
	if len(ka) == 0 {
		return "", unknownTeam(db, ta)
	}
	if len(kb) == 0 {
		return "", unknownTeam(db, tb)
	}
	ms := db.Find(MatchFilter{Team: ta, Opponent: tb, Competition: a.Str("competition"), Season: a.Int("season", 0)})
	setA := map[string]bool{}
	for _, k := range ka {
		setA[k] = true
	}
	var wa, wb, d, ga, gb int
	for _, m := range ms {
		hg, ag := m.HomeGoals, m.AwayGoals
		if !setA[m.HomeKey] {
			hg, ag = ag, hg
		}
		ga += hg
		gb += ag
		switch {
		case hg > ag:
			wa++
		case hg < ag:
			wb++
		default:
			d++
		}
	}
	na, nb := db.Name(ka[0]), db.Name(kb[0])
	var b strings.Builder
	fmt.Fprintf(&b, "%s vs %s", na, nb)
	if r := RivalryName(ka[0], kb[0]); r != "" {
		fmt.Fprintf(&b, " (%s)", r)
	}
	b.WriteString(":\n")
	listMatches(db, &b, ms, a.Int("limit", 20))
	fmt.Fprintf(&b, "\nHead-to-head in dataset (%d matches): %s %d wins, %s %d wins, %d draws\n", len(ms), na, wa, nb, wb, d)
	fmt.Fprintf(&b, "Goals: %s %d, %s %d\n", na, ga, nb, gb)
	return b.String(), nil
}

func formatRecord(b *strings.Builder, r Record) {
	fmt.Fprintf(b, "- Matches: %d\n- Wins: %d, Draws: %d, Losses: %d\n- Goals For: %d, Goals Against: %d\n- Win rate: %.1f%%\n",
		r.Played, r.W, r.D, r.L, r.GF, r.GA, r.WinRate())
}

func toolTeamStats(db *DB, a Args) (string, error) {
	f, err := db.filterFromArgs(a)
	if err != nil {
		return "", err
	}
	keys := db.ResolveTeam(f.Team)
	if len(keys) == 0 {
		return "", unknownTeam(db, f.Team)
	}
	r, _ := db.TeamRecord(f)
	var b strings.Builder
	title := db.Name(keys[0])
	if f.Venue == "home" || f.Venue == "away" {
		title += " " + f.Venue
	}
	title += " record"
	var qual []string
	if f.Season != 0 {
		qual = append(qual, fmt.Sprint(f.Season))
	}
	if c := NormalizeCompetition(f.Competition); c != "" {
		qual = append(qual, c)
	}
	if len(qual) > 0 {
		title += " (" + strings.Join(qual, " ") + ")"
	}
	b.WriteString(title + ":\n")
	formatRecord(&b, r)
	if r.Played > 0 {
		fmt.Fprintf(&b, "- Points (3/1/0): %d\n", r.Points())
	}
	if NormalizeCompetition(f.Competition) == "" && r.Played > 0 {
		b.WriteString("\nBy competition:\n")
		for _, c := range []string{CompBrasileirao, CompCopaBrasil, CompLibertad, CompSerieB, CompSerieC} {
			g := f
			g.Competition = c
			if cr, _ := db.TeamRecord(g); cr.Played > 0 {
				fmt.Fprintf(&b, "- %s: %d matches, %dW %dD %dL, GF %d GA %d\n", c, cr.Played, cr.W, cr.D, cr.L, cr.GF, cr.GA)
			}
		}
	}
	return b.String(), nil
}

func relegationCount(season int) int {
	if season >= 2006 {
		return 4 // 20-team era
	}
	return 0 // 2003-2005 varied; don't guess
}

func toolStandings(db *DB, a Args) (string, error) {
	season := a.Int("season", 0)
	if season == 0 {
		return "", fmt.Errorf("season is required")
	}
	comp := NormalizeCompetition(a.Str("competition"))
	if comp == "" {
		comp = CompBrasileirao
	}
	if comp == CompCopaBrasil || comp == CompLibertad {
		return "", fmt.Errorf("standings only apply to league competitions; use search_matches with stage for cups")
	}
	table := db.Standings(season, comp)
	if len(table) == 0 {
		return "", fmt.Errorf("no %s matches for %d", comp, season)
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%d %s Final Standings (calculated from matches):\n", season, comp)
	rel := 0
	if comp == CompBrasileirao {
		rel = relegationCount(season)
	}
	for i, r := range table {
		fmt.Fprintf(&b, "%d. %s - %d pts (%dW, %dD, %dL) GF %d GA %d GD %+d, %d played", i+1, db.Name(r.Team), r.Points(), r.W, r.D, r.L, r.GF, r.GA, r.GD(), r.Played)
		switch {
		case i == 0:
			b.WriteString(" - Champion")
		case rel > 0 && i >= len(table)-rel:
			b.WriteString(" - Relegated")
		}
		b.WriteString("\n")
	}
	return b.String(), nil
}

func toolCompetitionStats(db *DB, a Args) (string, error) {
	f, err := db.filterFromArgs(a)
	if err != nil {
		return "", err
	}
	ms := db.Find(f)
	if len(ms) == 0 {
		return "No matches found for the given filters.", nil
	}
	s := Summarize(ms)
	var b strings.Builder
	label := NormalizeCompetition(f.Competition)
	if label == "" {
		label = "all competitions"
	}
	if f.Season != 0 {
		label += fmt.Sprintf(" %d", f.Season)
	}
	fmt.Fprintf(&b, "Statistics for %s (provided data):\n", label)
	fmt.Fprintf(&b, "- Matches: %d\n- Total goals: %d\n- Average goals per match: %.2f\n- Home win rate: %.1f%%\n- Away win rate: %.1f%%\n- Draw rate: %.1f%%\n",
		s.Matches, s.Goals, s.AvgGoals(), s.HomeWinPct(), s.AwayWinPct(), s.DrawPct())
	b.WriteString("\nBiggest victories:\n")
	for i, m := range BiggestWins(ms, a.Int("limit", 10)) {
		fmt.Fprintf(&b, "%d. %s\n", i+1, db.FormatMatch(m))
	}
	return b.String(), nil
}

func toolRankings(db *DB, a Args) (string, error) {
	metric := strings.ToLower(a.Str("metric"))
	venue := ""
	switch metric {
	case "home_record":
		venue = "home"
	case "away_record":
		venue = "away"
	case "win_rate", "goals_scored", "goals_conceded", "points":
	default:
		return "", fmt.Errorf("unknown metric %q", metric)
	}
	f, err := db.filterFromArgs(a)
	if err != nil {
		return "", err
	}
	f.Team = ""
	minM := a.Int("min_matches", 10)
	if f.Season != 0 && minM > 5 {
		minM = 5
	}
	var rs []*Record
	for _, r := range Records(db.Find(f), venue) {
		if r.Played >= minM {
			rs = append(rs, r)
		}
	}
	sort.Slice(rs, func(i, j int) bool {
		x, y := rs[i], rs[j]
		switch metric {
		case "goals_scored":
			if x.GF != y.GF {
				return x.GF > y.GF
			}
		case "goals_conceded":
			if x.GA != y.GA {
				return x.GA < y.GA
			}
		case "points":
			if x.Points() != y.Points() {
				return x.Points() > y.Points()
			}
		default:
			if x.WinRate() != y.WinRate() {
				return x.WinRate() > y.WinRate()
			}
		}
		if x.Played != y.Played {
			return x.Played > y.Played
		}
		return x.Team < y.Team
	})
	var b strings.Builder
	fmt.Fprintf(&b, "Team ranking by %s (min %d matches):\n", metric, minM)
	limit := a.Int("limit", 10)
	for i, r := range rs {
		if i >= limit {
			break
		}
		fmt.Fprintf(&b, "%d. %s - %d matches, %dW %dD %dL, GF %d GA %d, win rate %.1f%%, %d pts\n",
			i+1, db.Name(r.Team), r.Played, r.W, r.D, r.L, r.GF, r.GA, r.WinRate(), r.Points())
	}
	return b.String(), nil
}

func toolCompareSeasons(db *DB, a Args) (string, error) {
	comp := NormalizeCompetition(a.Str("competition"))
	if comp == "" {
		comp = CompBrasileirao
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s season comparison:\n", comp)
	for _, part := range strings.Split(a.Str("seasons"), ",") {
		y := atoi(part)
		if y <= 0 {
			continue
		}
		ms := db.Find(MatchFilter{Competition: comp, Season: y})
		s := Summarize(ms)
		fmt.Fprintf(&b, "\n%d:\n- Matches: %d\n- Goals: %d (%.2f per match)\n- Home wins %.1f%%, Away wins %.1f%%, Draws %.1f%%\n",
			y, s.Matches, s.Goals, s.AvgGoals(), s.HomeWinPct(), s.AwayWinPct(), s.DrawPct())
		if comp != CompCopaBrasil && comp != CompLibertad {
			if t := db.Standings(y, comp); len(t) > 0 {
				fmt.Fprintf(&b, "- Champion: %s (%d pts)\n", db.Name(t[0].Team), t[0].Points())
				best := t[0]
				for _, r := range t {
					if r.GF > best.GF {
						best = r
					}
				}
				fmt.Fprintf(&b, "- Top scoring team: %s (%d goals)\n", db.Name(best.Team), best.GF)
			}
		}
	}
	return b.String(), nil
}

func toolTeamCompetitions(db *DB, a Args) (string, error) {
	team := a.Str("team")
	keys := db.ResolveTeam(team)
	if len(keys) == 0 {
		return "", unknownTeam(db, team)
	}
	seasons := map[string]map[int]int{}
	for _, m := range db.Find(MatchFilter{Team: team}) {
		if seasons[m.Competition] == nil {
			seasons[m.Competition] = map[int]int{}
		}
		seasons[m.Competition][m.Season]++
	}
	comps := make([]string, 0, len(seasons))
	for c := range seasons {
		comps = append(comps, c)
	}
	sort.Strings(comps)
	var b strings.Builder
	fmt.Fprintf(&b, "Competitions for %s:\n", db.Name(keys[0]))
	for _, c := range comps {
		var ys []int
		n := 0
		for y, k := range seasons[c] {
			ys = append(ys, y)
			n += k
		}
		sort.Ints(ys)
		fmt.Fprintf(&b, "- %s: %d matches, seasons %v\n", c, n, ys)
	}
	return b.String(), nil
}

func toolDerbies(db *DB, a Args) (string, error) {
	f, err := db.filterFromArgs(a)
	if err != nil {
		return "", err
	}
	var ms []*Match
	for _, m := range db.Find(f) {
		if RivalryName(m.HomeKey, m.AwayKey) != "" {
			ms = append(ms, m)
		}
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Found %d derby matches:\n", len(ms))
	limit := a.Int("limit", 30)
	for i, m := range ms {
		if i >= limit {
			fmt.Fprintf(&b, "- ... (%d more)\n", len(ms)-limit)
			break
		}
		fmt.Fprintf(&b, "- [%s] %s\n", RivalryName(m.HomeKey, m.AwayKey), db.FormatMatch(m))
	}
	return b.String(), nil
}

func toolSearchPlayers(db *DB, a Args) (string, error) {
	ps := db.FindPlayers(PlayerFilter{Name: a.Str("name"), Nationality: a.Str("nationality"), Club: a.Str("club"),
		Position: a.Str("position"), MinOverall: a.Int("min_overall", 0)})
	var b strings.Builder
	fmt.Fprintf(&b, "Found %d players:\n", len(ps))
	if len(ps) == 0 {
		b.WriteString(db.noPlayerHint(a.Str("name"), a.Str("club")))
	}
	limit := a.Int("limit", 20)
	for i, p := range ps {
		if i >= limit {
			fmt.Fprintf(&b, "... (%d more)\n", len(ps)-limit)
			break
		}
		fmt.Fprintf(&b, "%d. %s\n", i+1, p)
	}
	return b.String(), nil
}

func toolPlayerDetails(db *DB, a Args) (string, error) {
	ps := db.FindPlayers(PlayerFilter{Name: a.Str("name")})
	if len(ps) == 0 {
		return fmt.Sprintf("No player named %q in the FIFA dataset.\n", a.Str("name")) + db.noPlayerHint(a.Str("name"), ""), nil
	}
	p := ps[0]
	var b strings.Builder
	fmt.Fprintf(&b, "%s (ID %d)\n- Age: %d\n- Nationality: %s\n- Club: %s\n- Position: %s, Jersey: %s\n- Overall: %d, Potential: %d\n- Height: %s, Weight: %s, Preferred foot: %s\n- Value: %s\n",
		p.Name, p.ID, p.Age, p.Nationality, orNone(p.Club), p.Position, p.Jersey, p.Overall, p.Potential, p.Height, p.Weight, p.Foot, p.Value)
	b.WriteString("- Skills:")
	for _, k := range skillCols {
		if v, ok := p.Skills[k]; ok {
			fmt.Fprintf(&b, " %s %d,", k, v)
		}
	}
	b.WriteString("\n")
	if len(ps) > 1 {
		fmt.Fprintf(&b, "\nOther matches: ")
		for i, q := range ps[1:] {
			if i >= 5 {
				break
			}
			fmt.Fprintf(&b, "%s (%s); ", q.Name, orNone(q.Club))
		}
		b.WriteString("\n")
	}
	return b.String(), nil
}

// brazilianClubKeys are teams appearing in domestic Brazilian competitions.
func (db *DB) brazilianClubKeys() map[string]bool {
	out := map[string]bool{}
	for _, m := range db.Matches {
		if m.Competition == CompBrasileirao || m.Competition == CompSerieB {
			out[m.HomeKey], out[m.AwayKey] = true, true
		}
	}
	return out
}

func toolBrazilianClubs(db *DB, a Args) (string, error) {
	br := db.brazilianClubKeys()
	onlyBR, _ := a["brazilian_only"].(bool)
	type agg struct {
		club   string
		n, sum int
	}
	clubs := map[string]*agg{}
	for _, p := range db.Players {
		if p.Club == "" || !br[NormalizeTeam(p.Club)] {
			continue
		}
		if onlyBR && p.Nationality != "Brazil" {
			continue
		}
		c := clubs[p.Club]
		if c == nil {
			c = &agg{club: p.Club}
			clubs[p.Club] = c
		}
		c.n++
		c.sum += p.Overall
	}
	list := make([]*agg, 0, len(clubs))
	for _, c := range clubs {
		list = append(list, c)
	}
	sort.Slice(list, func(i, j int) bool {
		if list[i].n != list[j].n {
			return list[i].n > list[j].n
		}
		return list[i].club < list[j].club
	})
	var b strings.Builder
	if onlyBR {
		b.WriteString("Brazilian players at Brazilian clubs:\n")
	} else {
		b.WriteString("Players at Brazilian clubs:\n")
	}
	limit := a.Int("limit", 30)
	for i, c := range list {
		if i >= limit {
			break
		}
		fmt.Fprintf(&b, "- %s: %d players (avg rating: %.0f)\n", c.club, c.n, float64(c.sum)/float64(c.n))
	}
	return b.String(), nil
}

func toolTeamProfile(db *DB, a Args) (string, error) {
	team := a.Str("team")
	keys := db.ResolveTeam(team)
	if len(keys) == 0 {
		return "", unknownTeam(db, team)
	}
	stats, _ := toolTeamStats(db, Args{"team": team})
	comps, _ := toolTeamCompetitions(db, Args{"team": team})
	ps := db.FindPlayers(PlayerFilter{Club: db.Name(keys[0])})
	var b strings.Builder
	b.WriteString(stats + "\n" + comps + "\n")
	fmt.Fprintf(&b, "FIFA players at %s: %d\n", db.Name(keys[0]), len(ps))
	for i, p := range ps {
		if i >= 10 {
			break
		}
		fmt.Fprintf(&b, "%d. %s\n", i+1, p)
	}
	return b.String(), nil
}

func toolDatasetInfo(db *DB, a Args) (string, error) {
	var b strings.Builder
	b.WriteString("Loaded datasets:\n")
	files := make([]string, 0, len(db.Files))
	for f := range db.Files {
		files = append(files, f)
	}
	sort.Strings(files)
	for _, f := range files {
		fmt.Fprintf(&b, "- %s: %d rows\n", f, db.Files[f])
	}
	fmt.Fprintf(&b, "Total matches: %d, players: %d, distinct teams: %d\n", len(db.Matches), len(db.Players), len(db.TeamNames))
	return b.String(), nil
}

// noPlayerHint explains empty player results: similar names, or clubs absent from FIFA data.
func (db *DB) noPlayerHint(name, club string) string {
	var b strings.Builder
	if club != "" {
		fmt.Fprintf(&b, "Note: the FIFA dataset has no players listed at a club matching %q (some Brazilian clubs are not licensed in FIFA 19).\n", club)
	}
	if name == "" {
		return b.String()
	}
	seen := map[*Player]bool{}
	var sugg []*Player
	for _, tok := range strings.Fields(name) {
		if len(tok) < 3 {
			continue
		}
		for _, p := range db.FindPlayers(PlayerFilter{Name: tok}) {
			if !seen[p] {
				seen[p] = true
				sugg = append(sugg, p)
			}
		}
	}
	sort.SliceStable(sugg, func(i, j int) bool { return sugg[i].Overall > sugg[j].Overall })
	if len(sugg) > 0 {
		b.WriteString("Similar names:\n")
		for i, p := range sugg {
			if i >= 5 {
				break
			}
			fmt.Fprintf(&b, "- %s\n", p)
		}
	}
	return b.String()
}
