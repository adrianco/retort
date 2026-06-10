// tools.go defines the MCP tools exposed by the server and their
// implementations: match search, team statistics, head-to-head comparison,
// player search, standings, and competition-level statistics.
package main

import (
	"fmt"
	"sort"
	"strings"
	"time"
)

// Tool is one MCP tool: its advertised schema plus its handler.
type Tool struct {
	Name        string
	Description string
	InputSchema map[string]any
	Handler     func(s *Store, args map[string]any) (string, error)
}

// ---------------------------------------------------------------------------
// Argument helpers (JSON object decoded into map[string]any)
// ---------------------------------------------------------------------------

func argString(args map[string]any, key string) string {
	if v, ok := args[key].(string); ok {
		return strings.TrimSpace(v)
	}
	return ""
}

func argInt(args map[string]any, key string) (int, bool) {
	switch v := args[key].(type) {
	case float64:
		return int(v), true
	case int:
		return v, true
	case string:
		return parseIntField(v)
	}
	return 0, false
}

func argBool(args map[string]any, key string) bool {
	v, _ := args[key].(bool)
	return v
}

func prop(typ, desc string) map[string]any {
	return map[string]any{"type": typ, "description": desc}
}

func schema(required []string, props map[string]any) map[string]any {
	s := map[string]any{"type": "object", "properties": props}
	if len(required) > 0 {
		s["required"] = required
	}
	return s
}

// ---------------------------------------------------------------------------
// Match filtering shared by several tools
// ---------------------------------------------------------------------------

type matchFilter struct {
	team        *teamMatcher
	opponent    *teamMatcher
	competition string
	season      int
	stage       string
	from, to    time.Time
}

func buildMatchFilter(s *Store, args map[string]any) (*matchFilter, error) {
	f := &matchFilter{}
	if t := argString(args, "team"); t != "" {
		f.team = s.newTeamMatcher(t)
	}
	if t := argString(args, "opponent"); t != "" {
		f.opponent = s.newTeamMatcher(t)
	}
	if c := argString(args, "competition"); c != "" {
		f.competition = canonicalCompetition(c)
		if f.competition == "" {
			return nil, fmt.Errorf("unknown competition %q (try: Brasileirão, Série B, Série C, Copa do Brasil, Libertadores)", c)
		}
	}
	if n, ok := argInt(args, "season"); ok {
		f.season = n
	}
	f.stage = normalizeText(argString(args, "stage"))
	if d := argString(args, "date_from"); d != "" {
		t, ok := parseDate(d)
		if !ok {
			return nil, fmt.Errorf("invalid date_from %q (use YYYY-MM-DD)", d)
		}
		f.from = t
	}
	if d := argString(args, "date_to"); d != "" {
		t, ok := parseDate(d)
		if !ok {
			return nil, fmt.Errorf("invalid date_to %q (use YYYY-MM-DD)", d)
		}
		f.to = t
	}
	return f, nil
}

func stageMatches(query, round string) bool {
	if query == "" {
		return true
	}
	r := normalizeText(round)
	q := strings.TrimSuffix(query, "s")
	r = strings.TrimSuffix(r, "s")
	return q == r
}

func (f *matchFilter) matches(m *Match) bool {
	if f.competition != "" && m.Competition != f.competition {
		return false
	}
	if f.season != 0 && m.Season != f.season {
		return false
	}
	if !f.from.IsZero() && m.Date.Before(f.from) {
		return false
	}
	if !f.to.IsZero() && m.Date.After(f.to.Add(24*time.Hour-time.Second)) {
		return false
	}
	if !stageMatches(f.stage, m.Round) {
		return false
	}
	homeIsTeam := f.team != nil && f.team.matches(m.HomeKey)
	awayIsTeam := f.team != nil && f.team.matches(m.AwayKey)
	if f.team != nil && !homeIsTeam && !awayIsTeam {
		return false
	}
	if f.opponent != nil {
		if f.team != nil {
			// Opponent must be on the other side of the team.
			if homeIsTeam && f.opponent.matches(m.AwayKey) {
				return true
			}
			if awayIsTeam && f.opponent.matches(m.HomeKey) {
				return true
			}
			return false
		}
		if !f.opponent.matches(m.HomeKey) && !f.opponent.matches(m.AwayKey) {
			return false
		}
	}
	return true
}

func (s *Store) filterMatches(f *matchFilter) []*Match {
	var out []*Match
	for _, m := range s.Matches { // already sorted newest first
		if f.matches(m) {
			out = append(out, m)
		}
	}
	return out
}

func formatMatch(m *Match, withStats bool) string {
	ctx := m.Competition
	if m.Season != 0 {
		ctx += fmt.Sprintf(" %d", m.Season)
	}
	if m.Round != "" {
		ctx += ", " + m.Round
	}
	line := fmt.Sprintf("%s: %s %d-%d %s (%s)",
		m.Date.Format("2006-01-02"), m.HomeTeam, m.HomeGoals, m.AwayGoals, m.AwayTeam, ctx)
	if m.Stadium != "" {
		line += " @ " + m.Stadium
	}
	if withStats && m.HasStats() {
		var parts []string
		if m.HomeShots >= 0 {
			parts = append(parts, fmt.Sprintf("shots %d-%d", m.HomeShots, m.AwayShots))
		}
		if m.HomeCorners >= 0 {
			parts = append(parts, fmt.Sprintf("corners %d-%d", m.HomeCorners, m.AwayCorners))
		}
		if m.HomeAttacks >= 0 {
			parts = append(parts, fmt.Sprintf("attacks %d-%d", m.HomeAttacks, m.AwayAttacks))
		}
		if len(parts) > 0 {
			line += " [" + strings.Join(parts, ", ") + "]"
		}
	}
	return line
}

// displayName returns the most common display name used in the matched
// matches for teams accepted by the matcher (falls back to the raw query).
func displayName(matches []*Match, tm *teamMatcher, fallback string) string {
	counts := map[string]int{}
	for _, m := range matches {
		if tm.matches(m.HomeKey) {
			counts[m.HomeTeam]++
		}
		if tm.matches(m.AwayKey) {
			counts[m.AwayTeam]++
		}
	}
	best, n := fallback, 0
	for name, c := range counts {
		if c > n {
			best, n = name, c
		}
	}
	return best
}

// ---------------------------------------------------------------------------
// Tool: search_matches
// ---------------------------------------------------------------------------

func toolSearchMatches(s *Store, args map[string]any) (string, error) {
	f, err := buildMatchFilter(s, args)
	if err != nil {
		return "", err
	}
	limit := 20
	if n, ok := argInt(args, "limit"); ok && n > 0 {
		if n > 200 {
			n = 200
		}
		limit = n
	}
	matches := s.filterMatches(f)
	if len(matches) == 0 {
		return "No matches found for the given criteria.", nil
	}
	withStats := argBool(args, "include_stats")
	var b strings.Builder
	fmt.Fprintf(&b, "Found %d matches", len(matches))
	if len(matches) > limit {
		fmt.Fprintf(&b, " (showing the %d most recent; raise 'limit' or narrow the filters for more)", limit)
	}
	b.WriteString(":\n")
	for i, m := range matches {
		if i >= limit {
			break
		}
		b.WriteString("- " + formatMatch(m, withStats) + "\n")
	}
	if f.team != nil && f.opponent != nil {
		b.WriteString("\n" + headToHeadSummary(matches, f.team, f.opponent,
			displayName(matches, f.team, argString(args, "team")),
			displayName(matches, f.opponent, argString(args, "opponent"))))
	}
	return strings.TrimRight(b.String(), "\n"), nil
}

// ---------------------------------------------------------------------------
// Tool: get_team_stats
// ---------------------------------------------------------------------------

type record struct {
	played, wins, draws, losses int
	goalsFor, goalsAgainst      int
}

func (r *record) addMatch(gf, ga int) {
	r.played++
	r.goalsFor += gf
	r.goalsAgainst += ga
	switch {
	case gf > ga:
		r.wins++
	case gf < ga:
		r.losses++
	default:
		r.draws++
	}
}

func (r *record) points() int { return r.wins*3 + r.draws }

func (r *record) winRate() float64 {
	if r.played == 0 {
		return 0
	}
	return 100 * float64(r.wins) / float64(r.played)
}

func toolGetTeamStats(s *Store, args map[string]any) (string, error) {
	teamName := argString(args, "team")
	if teamName == "" {
		return "", fmt.Errorf("'team' is required")
	}
	f, err := buildMatchFilter(s, args)
	if err != nil {
		return "", err
	}
	venue := strings.ToLower(argString(args, "venue"))
	if venue != "" && venue != "home" && venue != "away" && venue != "all" {
		return "", fmt.Errorf("'venue' must be home, away or all")
	}
	matches := s.filterMatches(f)
	if len(matches) == 0 {
		return fmt.Sprintf("No matches found for %q with the given criteria.", teamName), nil
	}
	total := &record{}
	perComp := map[string]*record{}
	for _, m := range matches {
		home := f.team.matches(m.HomeKey)
		if venue == "home" && !home || venue == "away" && home {
			continue
		}
		gf, ga := m.HomeGoals, m.AwayGoals
		if !home {
			gf, ga = ga, gf
		}
		total.addMatch(gf, ga)
		if perComp[m.Competition] == nil {
			perComp[m.Competition] = &record{}
		}
		perComp[m.Competition].addMatch(gf, ga)
	}
	if total.played == 0 {
		return fmt.Sprintf("No %s matches found for %q with the given criteria.", venue, teamName), nil
	}
	name := displayName(matches, f.team, teamName)
	var scope []string
	if venue == "home" || venue == "away" {
		scope = append(scope, venue)
	}
	if f.season != 0 {
		scope = append(scope, fmt.Sprintf("season %d", f.season))
	}
	if f.competition != "" {
		scope = append(scope, f.competition)
	}
	title := name + " record"
	if len(scope) > 0 {
		title += " (" + strings.Join(scope, ", ") + ")"
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s:\n", title)
	fmt.Fprintf(&b, "- Matches: %d\n", total.played)
	fmt.Fprintf(&b, "- Wins: %d, Draws: %d, Losses: %d\n", total.wins, total.draws, total.losses)
	fmt.Fprintf(&b, "- Goals For: %d, Goals Against: %d (diff %+d)\n",
		total.goalsFor, total.goalsAgainst, total.goalsFor-total.goalsAgainst)
	fmt.Fprintf(&b, "- Win rate: %.1f%%\n", total.winRate())
	if len(perComp) > 1 {
		b.WriteString("\nBy competition:\n")
		comps := make([]string, 0, len(perComp))
		for c := range perComp {
			comps = append(comps, c)
		}
		sort.Slice(comps, func(i, j int) bool { return perComp[comps[i]].played > perComp[comps[j]].played })
		for _, c := range comps {
			r := perComp[c]
			fmt.Fprintf(&b, "- %s: %dM %dW %dD %dL, GF %d GA %d\n",
				c, r.played, r.wins, r.draws, r.losses, r.goalsFor, r.goalsAgainst)
		}
	}
	return strings.TrimRight(b.String(), "\n"), nil
}

// ---------------------------------------------------------------------------
// Tool: head_to_head
// ---------------------------------------------------------------------------

func headToHeadSummary(matches []*Match, t1, t2 *teamMatcher, name1, name2 string) string {
	var w1, w2, draws, g1, g2 int
	for _, m := range matches {
		var gf, ga int
		switch {
		case t1.matches(m.HomeKey) && t2.matches(m.AwayKey):
			gf, ga = m.HomeGoals, m.AwayGoals
		case t2.matches(m.HomeKey) && t1.matches(m.AwayKey):
			gf, ga = m.AwayGoals, m.HomeGoals
		default:
			continue
		}
		g1 += gf
		g2 += ga
		switch {
		case gf > ga:
			w1++
		case ga > gf:
			w2++
		default:
			draws++
		}
	}
	return fmt.Sprintf("Head-to-head: %s %d wins, %s %d wins, %d draws (goals %d-%d)",
		name1, w1, name2, w2, draws, g1, g2)
}

func toolHeadToHead(s *Store, args map[string]any) (string, error) {
	t1Name := argString(args, "team1")
	t2Name := argString(args, "team2")
	if t1Name == "" || t2Name == "" {
		return "", fmt.Errorf("'team1' and 'team2' are required")
	}
	f, err := buildMatchFilter(s, args)
	if err != nil {
		return "", err
	}
	f.team = s.newTeamMatcher(t1Name)
	f.opponent = s.newTeamMatcher(t2Name)
	matches := s.filterMatches(f)
	if len(matches) == 0 {
		return fmt.Sprintf("No matches found between %q and %q.", t1Name, t2Name), nil
	}
	name1 := displayName(matches, f.team, t1Name)
	name2 := displayName(matches, f.opponent, t2Name)
	var b strings.Builder
	fmt.Fprintf(&b, "%s vs %s — %d matches in dataset\n", name1, name2, len(matches))
	b.WriteString(headToHeadSummary(matches, f.team, f.opponent, name1, name2) + "\n")
	b.WriteString("\nMost recent meetings:\n")
	for i, m := range matches {
		if i >= 10 {
			fmt.Fprintf(&b, "... (%d more matches in dataset)\n", len(matches)-10)
			break
		}
		b.WriteString("- " + formatMatch(m, false) + "\n")
	}
	return strings.TrimRight(b.String(), "\n"), nil
}

// ---------------------------------------------------------------------------
// Tool: search_players
// ---------------------------------------------------------------------------

var positionGroups = map[string][]string{
	"forward":    {"ST", "CF", "LS", "RS", "LF", "RF", "LW", "RW"},
	"striker":    {"ST", "CF", "LS", "RS"},
	"attacker":   {"ST", "CF", "LS", "RS", "LF", "RF", "LW", "RW"},
	"winger":     {"LW", "RW", "LM", "RM"},
	"midfielder": {"CM", "CDM", "CAM", "LM", "RM", "LCM", "RCM", "LDM", "RDM", "LAM", "RAM"},
	"defender":   {"CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"},
	"goalkeeper": {"GK"},
	"keeper":     {"GK"},
}

func positionMatches(query, position string) bool {
	if query == "" {
		return true
	}
	q := strings.ToLower(strings.TrimSpace(query))
	q = strings.TrimSuffix(q, "s") // "forwards" -> "forward"
	if group, ok := positionGroups[q]; ok {
		for _, p := range group {
			if strings.EqualFold(p, position) {
				return true
			}
		}
		return false
	}
	return strings.EqualFold(query, position)
}

func toolSearchPlayers(s *Store, args map[string]any) (string, error) {
	nameQ := normalizeText(argString(args, "name"))
	natQ := normalizeText(argString(args, "nationality"))
	clubQ := argString(args, "club")
	posQ := argString(args, "position")
	minOverall, _ := argInt(args, "min_overall")
	limit := 10
	if n, ok := argInt(args, "limit"); ok && n > 0 {
		if n > 100 {
			n = 100
		}
		limit = n
	}
	var clubMatcher *teamMatcher
	if clubQ != "" {
		clubMatcher = s.newTeamMatcher(clubQ)
	}
	var found []*Player
	for _, p := range s.Players {
		if nameQ != "" && !strings.Contains(p.NameKey, nameQ) {
			continue
		}
		if natQ != "" && normalizeText(p.Nationality) != natQ {
			continue
		}
		if clubMatcher != nil && !clubMatcher.matches(p.ClubKey) {
			continue
		}
		if !positionMatches(posQ, p.Position) {
			continue
		}
		if minOverall > 0 && p.Overall < minOverall {
			continue
		}
		found = append(found, p)
	}
	if len(found) == 0 {
		return "No players found for the given criteria.", nil
	}
	sortBy := strings.ToLower(argString(args, "sort_by"))
	switch sortBy {
	case "potential":
		sort.Slice(found, func(i, j int) bool { return found[i].Potential > found[j].Potential })
	case "age":
		sort.Slice(found, func(i, j int) bool { return found[i].Age < found[j].Age })
	case "name":
		sort.Slice(found, func(i, j int) bool { return found[i].Name < found[j].Name })
	default: // overall
		sort.Slice(found, func(i, j int) bool { return found[i].Overall > found[j].Overall })
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Found %d players", len(found))
	if len(found) > limit {
		fmt.Fprintf(&b, " (showing top %d)", limit)
	}
	b.WriteString(":\n")
	for i, p := range found {
		if i >= limit {
			break
		}
		club := p.Club
		if club == "" {
			club = "no club"
		}
		pos := p.Position
		if pos == "" {
			pos = "?"
		}
		fmt.Fprintf(&b, "%d. %s — Overall: %d, Potential: %d, Position: %s, Age: %d, Club: %s, Nationality: %s\n",
			i+1, p.Name, p.Overall, p.Potential, pos, p.Age, club, p.Nationality)
	}
	return strings.TrimRight(b.String(), "\n"), nil
}

// ---------------------------------------------------------------------------
// Tool: get_player_details
// ---------------------------------------------------------------------------

func toolGetPlayerDetails(s *Store, args map[string]any) (string, error) {
	nameQ := normalizeText(argString(args, "name"))
	if nameQ == "" {
		return "", fmt.Errorf("'name' is required")
	}
	var found []*Player
	for _, p := range s.Players {
		if strings.Contains(p.NameKey, nameQ) {
			found = append(found, p)
		}
	}
	if len(found) == 0 {
		return fmt.Sprintf("No player matching %q found.", argString(args, "name")), nil
	}
	sort.Slice(found, func(i, j int) bool { return found[i].Overall > found[j].Overall })
	var b strings.Builder
	if len(found) > 1 {
		fmt.Fprintf(&b, "%d players match (showing up to 3 by rating):\n\n", len(found))
	}
	for i, p := range found {
		if i >= 3 {
			break
		}
		fmt.Fprintf(&b, "%s\n", p.Name)
		fmt.Fprintf(&b, "- Age: %d | Nationality: %s\n", p.Age, p.Nationality)
		fmt.Fprintf(&b, "- Club: %s | Position: %s | Jersey: %s\n", p.Club, p.Position, p.JerseyNumber)
		fmt.Fprintf(&b, "- Overall: %d | Potential: %d | Preferred foot: %s\n", p.Overall, p.Potential, p.PreferredFoot)
		fmt.Fprintf(&b, "- Height: %s | Weight: %s | Value: %s | Wage: %s\n\n", p.Height, p.Weight, p.Value, p.Wage)
	}
	return strings.TrimRight(b.String(), "\n"), nil
}

// ---------------------------------------------------------------------------
// Tool: get_standings
// ---------------------------------------------------------------------------

func toolGetStandings(s *Store, args map[string]any) (string, error) {
	season, ok := argInt(args, "season")
	if !ok {
		return "", fmt.Errorf("'season' is required (e.g. 2019)")
	}
	comp := CompSerieA
	if c := argString(args, "competition"); c != "" {
		comp = canonicalCompetition(c)
		switch comp {
		case CompSerieA, CompSerieB, CompSerieC:
		case "":
			return "", fmt.Errorf("unknown competition %q", c)
		default:
			return "", fmt.Errorf("standings are only available for league competitions (Série A/B/C), not %s", comp)
		}
	}
	type row struct {
		name string
		rec  record
	}
	table := map[string]*row{}
	get := func(key, name string) *row {
		if table[key] == nil {
			table[key] = &row{name: name}
		}
		return table[key]
	}
	n := 0
	for _, m := range s.Matches {
		if m.Competition != comp || m.Season != season {
			continue
		}
		n++
		get(m.HomeKey, m.HomeTeam).rec.addMatch(m.HomeGoals, m.AwayGoals)
		get(m.AwayKey, m.AwayTeam).rec.addMatch(m.AwayGoals, m.HomeGoals)
	}
	if n == 0 {
		return fmt.Sprintf("No %s matches found for season %d.", comp, season), nil
	}
	rows := make([]*row, 0, len(table))
	for _, r := range table {
		rows = append(rows, r)
	}
	// Brasileirão tie-breakers: points, wins, goal difference, goals scored.
	sort.Slice(rows, func(i, j int) bool {
		a, b := rows[i].rec, rows[j].rec
		if a.points() != b.points() {
			return a.points() > b.points()
		}
		if a.wins != b.wins {
			return a.wins > b.wins
		}
		if d1, d2 := a.goalsFor-a.goalsAgainst, b.goalsFor-b.goalsAgainst; d1 != d2 {
			return d1 > d2
		}
		if a.goalsFor != b.goalsFor {
			return a.goalsFor > b.goalsFor
		}
		return rows[i].name < rows[j].name
	})
	var b strings.Builder
	fmt.Fprintf(&b, "%d %s standings (calculated from %d matches in dataset):\n", season, comp, n)
	for i, r := range rows {
		tag := ""
		if i == 0 {
			tag = " — Champion"
		} else if comp == CompSerieA && i >= len(rows)-4 {
			tag = " — Relegation zone"
		}
		fmt.Fprintf(&b, "%2d. %s — %d pts (%dW %dD %dL, GF %d GA %d, GD %+d)%s\n",
			i+1, r.name, r.rec.points(), r.rec.wins, r.rec.draws, r.rec.losses,
			r.rec.goalsFor, r.rec.goalsAgainst, r.rec.goalsFor-r.rec.goalsAgainst, tag)
	}
	return strings.TrimRight(b.String(), "\n"), nil
}

// ---------------------------------------------------------------------------
// Tool: get_competition_stats
// ---------------------------------------------------------------------------

func toolGetCompetitionStats(s *Store, args map[string]any) (string, error) {
	f, err := buildMatchFilter(s, args)
	if err != nil {
		return "", err
	}
	matches := s.filterMatches(f)
	if len(matches) == 0 {
		return "No matches found for the given criteria.", nil
	}
	var goals, homeWins, awayWins, draws int
	for _, m := range matches {
		goals += m.HomeGoals + m.AwayGoals
		switch {
		case m.HomeGoals > m.AwayGoals:
			homeWins++
		case m.HomeGoals < m.AwayGoals:
			awayWins++
		default:
			draws++
		}
	}
	biggest := make([]*Match, len(matches))
	copy(biggest, matches)
	sort.SliceStable(biggest, func(i, j int) bool {
		d1 := biggest[i].HomeGoals - biggest[i].AwayGoals
		if d1 < 0 {
			d1 = -d1
		}
		d2 := biggest[j].HomeGoals - biggest[j].AwayGoals
		if d2 < 0 {
			d2 = -d2
		}
		if d1 != d2 {
			return d1 > d2
		}
		return biggest[i].HomeGoals+biggest[i].AwayGoals > biggest[j].HomeGoals+biggest[j].AwayGoals
	})
	scope := "all competitions"
	if f.competition != "" {
		scope = f.competition
	}
	if f.season != 0 {
		scope += fmt.Sprintf(", season %d", f.season)
	}
	total := float64(len(matches))
	var b strings.Builder
	fmt.Fprintf(&b, "Statistics for %s (%d matches in dataset):\n", scope, len(matches))
	fmt.Fprintf(&b, "- Average goals per match: %.2f\n", float64(goals)/total)
	fmt.Fprintf(&b, "- Home wins: %d (%.1f%%), Draws: %d (%.1f%%), Away wins: %d (%.1f%%)\n",
		homeWins, 100*float64(homeWins)/total,
		draws, 100*float64(draws)/total,
		awayWins, 100*float64(awayWins)/total)
	b.WriteString("\nBiggest victories:\n")
	for i, m := range biggest {
		if i >= 5 {
			break
		}
		b.WriteString("- " + formatMatch(m, false) + "\n")
	}
	return strings.TrimRight(b.String(), "\n"), nil
}

// ---------------------------------------------------------------------------
// Tool: list_competitions
// ---------------------------------------------------------------------------

func toolListCompetitions(s *Store, _ map[string]any) (string, error) {
	type info struct {
		count                int
		minSeason, maxSeason int
		teams                map[string]bool
	}
	comps := map[string]*info{}
	for _, m := range s.Matches {
		c := comps[m.Competition]
		if c == nil {
			c = &info{minSeason: m.Season, maxSeason: m.Season, teams: map[string]bool{}}
			comps[m.Competition] = c
		}
		c.count++
		if m.Season < c.minSeason {
			c.minSeason = m.Season
		}
		if m.Season > c.maxSeason {
			c.maxSeason = m.Season
		}
		c.teams[m.HomeKey] = true
		c.teams[m.AwayKey] = true
	}
	names := make([]string, 0, len(comps))
	for n := range comps {
		names = append(names, n)
	}
	sort.Slice(names, func(i, j int) bool { return comps[names[i]].count > comps[names[j]].count })
	var b strings.Builder
	fmt.Fprintf(&b, "Competitions in dataset (%d matches total, deduplicated):\n", len(s.Matches))
	for _, n := range names {
		c := comps[n]
		fmt.Fprintf(&b, "- %s: %d matches, seasons %d-%d, %d teams\n",
			n, c.count, c.minSeason, c.maxSeason, len(c.teams))
	}
	fmt.Fprintf(&b, "\nPlayer database: %d players (FIFA ratings).", len(s.Players))
	return b.String(), nil
}

// ---------------------------------------------------------------------------
// Tool registry
// ---------------------------------------------------------------------------

var commonMatchProps = map[string]any{
	"competition": prop("string", "Competition filter: 'Brasileirão'/'Série A', 'Série B', 'Série C', 'Copa do Brasil', or 'Libertadores'."),
	"season":      prop("integer", "Season year, e.g. 2019."),
	"date_from":   prop("string", "Earliest match date, YYYY-MM-DD."),
	"date_to":     prop("string", "Latest match date, YYYY-MM-DD."),
}

func withCommonProps(extra map[string]any) map[string]any {
	out := map[string]any{}
	for k, v := range commonMatchProps {
		out[k] = v
	}
	for k, v := range extra {
		out[k] = v
	}
	return out
}

// AllTools returns the full tool registry.
func AllTools() []Tool {
	return []Tool{
		{
			Name: "search_matches",
			Description: "Search Brazilian soccer matches (Brasileirão Série A/B/C 2003-2023, Copa do Brasil, Copa Libertadores) " +
				"by team, opponent, competition, season, stage/round, or date range. Team names are normalized, so " +
				"'Flamengo', 'Flamengo-RJ' and 'flamengo' all work. Returns dates, scores and competition for each match, " +
				"newest first, plus a head-to-head summary when both team and opponent are given.",
			InputSchema: schema(nil, withCommonProps(map[string]any{
				"team":          prop("string", "Team name (matches home or away)."),
				"opponent":      prop("string", "Opposing team name; combine with 'team' for head-to-head fixtures."),
				"stage":         prop("string", "Round or stage filter, e.g. 'Final', 'semifinals', 'group stage', 'Round 22'."),
				"limit":         prop("integer", "Maximum matches to list (default 20, max 200)."),
				"include_stats": prop("boolean", "Include extended stats (shots, corners, attacks) when available."),
			})),
			Handler: toolSearchMatches,
		},
		{
			Name: "get_team_stats",
			Description: "Get a team's aggregated record: matches played, wins/draws/losses, goals for/against, win rate, " +
				"with a per-competition breakdown. Filter by season, competition, and venue (home/away/all).",
			InputSchema: schema([]string{"team"}, withCommonProps(map[string]any{
				"team":  prop("string", "Team name, e.g. 'Corinthians'."),
				"venue": prop("string", "'home', 'away', or 'all' (default all)."),
			})),
			Handler: toolGetTeamStats,
		},
		{
			Name: "head_to_head",
			Description: "Compare two teams head-to-head: wins for each side, draws, aggregate goals, and the most recent " +
				"meetings. Optionally filter by competition or season.",
			InputSchema: schema([]string{"team1", "team2"}, withCommonProps(map[string]any{
				"team1": prop("string", "First team name."),
				"team2": prop("string", "Second team name."),
			})),
			Handler: toolHeadToHead,
		},
		{
			Name: "search_players",
			Description: "Search the FIFA player database (18,000+ players) by name, nationality (e.g. 'Brazil'), club, " +
				"position ('forward', 'midfielder', 'defender', 'goalkeeper', or exact codes like ST/CAM/GK), and minimum " +
				"overall rating. Sorted by overall rating by default.",
			InputSchema: schema(nil, map[string]any{
				"name":        prop("string", "Full or partial player name."),
				"nationality": prop("string", "Player nationality, e.g. 'Brazil'."),
				"club":        prop("string", "Club name, e.g. 'Flamengo'."),
				"position":    prop("string", "Position group (forward/midfielder/defender/goalkeeper) or exact code (ST, CAM, GK...)."),
				"min_overall": prop("integer", "Minimum FIFA overall rating."),
				"sort_by":     prop("string", "'overall' (default), 'potential', 'age', or 'name'."),
				"limit":       prop("integer", "Maximum players to list (default 10, max 100)."),
			}),
			Handler: toolSearchPlayers,
		},
		{
			Name: "get_player_details",
			Description: "Get the full FIFA profile for a player by name: age, nationality, club, position, jersey number, " +
				"ratings, physique, market value and wage.",
			InputSchema: schema([]string{"name"}, map[string]any{
				"name": prop("string", "Full or partial player name, e.g. 'Gabriel Barbosa'."),
			}),
			Handler: toolGetPlayerDetails,
		},
		{
			Name: "get_standings",
			Description: "Calculate a league table from match results for a Brasileirão season (Série A 2003-2023; also " +
				"Série B/C where data exists). Shows points, W/D/L, goals, champion and relegation zone.",
			InputSchema: schema([]string{"season"}, map[string]any{
				"season":      prop("integer", "Season year, e.g. 2019."),
				"competition": prop("string", "League: 'Série A' (default), 'Série B', or 'Série C'."),
			}),
			Handler: toolGetStandings,
		},
		{
			Name: "get_competition_stats",
			Description: "Aggregate statistics across matches: average goals per match, home-win/draw/away-win rates, and the " +
				"biggest victories. Filter by competition, season, team, or date range.",
			InputSchema: schema(nil, withCommonProps(map[string]any{
				"team": prop("string", "Optional team filter."),
			})),
			Handler: toolGetCompetitionStats,
		},
		{
			Name:        "list_competitions",
			Description: "List the competitions, seasons, match counts and team counts available in the loaded datasets.",
			InputSchema: schema(nil, map[string]any{}),
			Handler:     toolListCompetitions,
		},
	}
}
