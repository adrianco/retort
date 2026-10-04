package soccer

import (
	"fmt"
	"sort"
	"strings"
	"time"
)

// Args are the named parameters of a question.
type Args map[string]any

func (a Args) Str(k string) string {
	if v, ok := a[k]; ok && v != nil {
		return strings.TrimSpace(fmt.Sprint(v))
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
		if n := num(v); n != 0 {
			return n
		}
	}
	return def
}

func (a Args) Bool(k string) bool {
	v, _ := a[k].(bool)
	return v || a.Str(k) == "true"
}

// CompetitionMatches reports whether a competition satisfies a user's description of it.
func CompetitionMatches(comp, query string) bool {
	q := Fold(query)
	switch q {
	case "":
		return true
	case "brasileirao", "serie a", "brasileirao serie a", "campeonato brasileiro":
		return comp == SerieA
	case "serie b":
		return comp == SerieB
	case "copa", "cup", "brazilian cup":
		return comp == CopaDoBrasil
	case "copa libertadores":
		return comp == Libertadores
	}
	return strings.Contains(Fold(comp), q)
}

// TeamMatches reports whether a team key satisfies a user's team name.
func TeamMatches(key, query string) bool {
	q := TeamKey(query)
	if key == q {
		return true
	}
	def, amb := ambiguous[q]
	return amb && def == "" && strings.HasPrefix(key, q+"-")
}

func (m *Match) Involves(team string) bool {
	return TeamMatches(m.HomeKey, team) || TeamMatches(m.AwayKey, team)
}

func (db *DB) Line(m *Match) string {
	ctx := m.Competition
	switch {
	case m.Stage != "":
		ctx += " " + m.Stage
	case m.Competition == SerieA || m.Competition == SerieB:
		if m.Round != "" {
			ctx += " Round " + m.Round
		}
	case m.Competition == CopaDoBrasil && m.Round != "":
		if num(m.Round) == db.cupFinalRound[m.Season] {
			ctx += " Final"
		} else {
			ctx += " Round " + m.Round
		}
	}
	s := fmt.Sprintf("- %s: %s %d-%d %s (%s)", m.Date.Format("2006-01-02"), db.Name(m.HomeKey), m.HomeGoals, m.AwayGoals, db.Name(m.AwayKey), ctx)
	return s
}

func (db *DB) filter(a Args) ([]*Match, error) {
	var from, to time.Time
	var err error
	if s := a.Str("date_from"); s != "" {
		if from, err = ParseDate(s); err != nil {
			return nil, err
		}
	}
	if s := a.Str("date_to"); s != "" {
		if to, err = ParseDate(s); err != nil {
			return nil, err
		}
	}
	team, opp, comp, season, venue := a.Str("team"), a.Str("opponent"), a.Str("competition"), a.Int("season", 0), a.Str("venue")
	stage := Fold(a.Str("stage"))
	var out []*Match
	for _, m := range db.Matches {
		if season != 0 && m.Season != season || !CompetitionMatches(m.Competition, comp) {
			continue
		}
		if !from.IsZero() && m.Date.Before(from) || !to.IsZero() && m.Date.After(to.Add(24*time.Hour-time.Second)) {
			continue
		}
		if stage != "" && Fold(m.Stage) != stage {
			continue
		}
		if a.Bool("finals_only") && !(m.Stage == "final" || m.Competition == CopaDoBrasil && m.Round != "" && num(m.Round) == db.cupFinalRound[m.Season]) {
			continue
		}
		if team != "" {
			home, away := TeamMatches(m.HomeKey, team), TeamMatches(m.AwayKey, team)
			if venue == "home" && !home || venue == "away" && !away || !home && !away {
				continue
			}
			if opp != "" && !(home && TeamMatches(m.AwayKey, opp) || away && TeamMatches(m.HomeKey, opp)) {
				continue
			}
		} else if opp != "" && !m.Involves(opp) {
			continue
		}
		out = append(out, m)
	}
	return out, nil
}

func (db *DB) SearchMatches(a Args) (string, error) {
	ms, err := db.filter(a)
	if err != nil {
		return "", err
	}
	if len(ms) == 0 {
		return "No matches found for those criteria.", nil
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Found %d matches (most recent first):\n", len(ms))
	limit := a.Int("limit", 50)
	for i, m := range ms {
		if i == limit {
			fmt.Fprintf(&b, "... (%d more matches in dataset)\n", len(ms)-limit)
			break
		}
		b.WriteString(db.Line(m) + "\n")
	}
	if a.Str("team") != "" && a.Str("opponent") != "" {
		b.WriteString("\n" + db.h2hLine(ms, a.Str("team"), a.Str("opponent")))
	}
	return b.String(), nil
}

func (db *DB) h2hLine(ms []*Match, a, b string) string {
	var wa, wb, d int
	for _, m := range ms {
		switch {
		case m.HomeGoals == m.AwayGoals:
			d++
		case (m.HomeGoals > m.AwayGoals) == TeamMatches(m.HomeKey, a):
			wa++
		default:
			wb++
		}
	}
	return fmt.Sprintf("Head-to-head in dataset (%d matches): %s %d wins, %s %d wins, %d draws\n", len(ms), db.Name(TeamKey(a)), wa, db.Name(TeamKey(b)), wb, d)
}

func (db *DB) LastMeeting(a Args) (string, error) {
	ms, _ := db.filter(Args{"team": a.Str("team_a"), "opponent": a.Str("team_b"), "competition": a.Str("competition")})
	if len(ms) == 0 {
		return "No meetings found between those teams.", nil
	}
	return "Most recent meeting:\n" + db.Line(ms[0]) + "\n", nil
}

func (db *DB) HeadToHead(a Args) (string, error) {
	ta, tb := a.Str("team_a"), a.Str("team_b")
	ms, _ := db.filter(Args{"team": ta, "opponent": tb, "competition": a.Str("competition"), "season": a.Int("season", 0)})
	if len(ms) == 0 {
		return "No meetings found between those teams.", nil
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%s vs %s:\n", db.Name(TeamKey(ta)), db.Name(TeamKey(tb)))
	for i, m := range ms {
		if i == 10 {
			fmt.Fprintf(&b, "- ... (%d more matches in dataset)\n", len(ms)-10)
			break
		}
		b.WriteString(db.Line(m) + "\n")
	}
	var ga, gb int
	for _, m := range ms {
		if TeamMatches(m.HomeKey, ta) {
			ga, gb = ga+m.HomeGoals, gb+m.AwayGoals
		} else {
			ga, gb = ga+m.AwayGoals, gb+m.HomeGoals
		}
	}
	b.WriteString("\n" + db.h2hLine(ms, ta, tb))
	fmt.Fprintf(&b, "Goals: %s %d, %s %d\n", db.Name(TeamKey(ta)), ga, db.Name(TeamKey(tb)), gb)
	return b.String(), nil
}

// Record is a team's aggregate results.
type Record struct {
	Team                                     string
	Played, Won, Drawn, Lost, GF, GA         int
	HomePlayed, HomeWon, AwayPlayed, AwayWon int
}

func (r *Record) Points() int { return 3*r.Won + r.Drawn }
func (r *Record) WinRate() float64 {
	if r.Played == 0 {
		return 0
	}
	return 100 * float64(r.Won) / float64(r.Played)
}

func (r *Record) add(gf, ga int, home bool) {
	r.Played++
	r.GF += gf
	r.GA += ga
	won := gf > ga
	switch {
	case won:
		r.Won++
	case gf == ga:
		r.Drawn++
	default:
		r.Lost++
	}
	if home {
		r.HomePlayed++
		if won {
			r.HomeWon++
		}
	} else {
		r.AwayPlayed++
		if won {
			r.AwayWon++
		}
	}
}

func (db *DB) records(ms []*Match, venue string) map[string]*Record {
	recs := map[string]*Record{}
	get := func(k string) *Record {
		if recs[k] == nil {
			recs[k] = &Record{Team: k}
		}
		return recs[k]
	}
	for _, m := range ms {
		if venue != "away" {
			get(m.HomeKey).add(m.HomeGoals, m.AwayGoals, true)
		}
		if venue != "home" {
			get(m.AwayKey).add(m.AwayGoals, m.HomeGoals, false)
		}
	}
	return recs
}

func describe(a Args) string {
	var parts []string
	if s := a.Int("season", 0); s != 0 {
		parts = append(parts, fmt.Sprint(s))
	}
	if c := a.Str("competition"); c != "" {
		parts = append(parts, c)
	}
	if len(parts) == 0 {
		return "all competitions in dataset"
	}
	return strings.Join(parts, " ")
}

func (db *DB) TeamRecord(a Args) (string, error) {
	team := a.Str("team")
	if team == "" {
		return "", fmt.Errorf("team is required")
	}
	venue := a.Str("venue")
	ms, err := db.filter(Args{"team": team, "season": a.Int("season", 0), "competition": a.Str("competition"), "venue": venue, "date_from": a.Str("date_from"), "date_to": a.Str("date_to")})
	if err != nil {
		return "", err
	}
	r := &Record{}
	for _, m := range ms {
		if TeamMatches(m.HomeKey, team) {
			r.add(m.HomeGoals, m.AwayGoals, true)
		} else {
			r.add(m.AwayGoals, m.HomeGoals, false)
		}
	}
	label := "overall"
	if venue == "home" || venue == "away" {
		label = venue
	}
	return fmt.Sprintf("%s %s record (%s):\n- Matches: %d\n- Wins: %d, Draws: %d, Losses: %d\n- Goals For: %d, Goals Against: %d\n- Points: %d\n- Win rate: %.1f%%\n",
		db.Name(TeamKey(team)), label, describe(a), r.Played, r.Won, r.Drawn, r.Lost, r.GF, r.GA, r.Points(), r.WinRate()), nil
}

func (db *DB) TeamCompetitions(a Args) (string, error) {
	team := a.Str("team")
	counts := map[string]int{}
	seasons := map[string][2]int{}
	for _, m := range db.Matches {
		if m.Involves(team) {
			counts[m.Competition]++
			s := seasons[m.Competition]
			if s[0] == 0 || m.Season < s[0] {
				s[0] = m.Season
			}
			if m.Season > s[1] {
				s[1] = m.Season
			}
			seasons[m.Competition] = s
		}
	}
	if len(counts) == 0 {
		return "No matches found for " + team + ".", nil
	}
	var comps []string
	for c := range counts {
		comps = append(comps, c)
	}
	sort.Strings(comps)
	var b strings.Builder
	fmt.Fprintf(&b, "Competitions %s has played in (dataset):\n", db.Name(TeamKey(team)))
	for _, c := range comps {
		fmt.Fprintf(&b, "- %s: %d matches (%d-%d)\n", c, counts[c], seasons[c][0], seasons[c][1])
	}
	return b.String(), nil
}

func sortedRecords(recs map[string]*Record, less func(a, b *Record) bool) []*Record {
	var rs []*Record
	for _, r := range recs {
		rs = append(rs, r)
	}
	sort.Slice(rs, func(i, j int) bool {
		if less(rs[i], rs[j]) != less(rs[j], rs[i]) {
			return less(rs[i], rs[j])
		}
		return rs[i].Team < rs[j].Team
	})
	return rs
}

func byTable(a, b *Record) bool {
	if a.Points() != b.Points() {
		return a.Points() > b.Points()
	}
	if a.Won != b.Won {
		return a.Won > b.Won
	}
	if a.GF-a.GA != b.GF-b.GA {
		return a.GF-a.GA > b.GF-b.GA
	}
	return a.GF > b.GF
}

func rate(n, d int) float64 {
	if d == 0 {
		return 0
	}
	return 100 * float64(n) / float64(d)
}

func (db *DB) TeamRanking(a Args) (string, error) {
	ms, err := db.filter(Args{"season": a.Int("season", 0), "competition": a.Str("competition")})
	if err != nil {
		return "", err
	}
	recs := db.records(ms, "")
	by := a.Str("by")
	minGames := 1
	if a.Int("season", 0) == 0 {
		minGames = 38
	}
	var less func(x, y *Record) bool
	switch by {
	case "goals_for":
		less = func(x, y *Record) bool { return x.GF > y.GF }
	case "goals_against":
		less = func(x, y *Record) bool { return x.GA < y.GA }
	case "win_rate":
		less = func(x, y *Record) bool { return x.WinRate() > y.WinRate() }
	case "home_win_rate":
		less = func(x, y *Record) bool { return rate(x.HomeWon, x.HomePlayed) > rate(y.HomeWon, y.HomePlayed) }
	case "away_win_rate":
		less = func(x, y *Record) bool { return rate(x.AwayWon, x.AwayPlayed) > rate(y.AwayWon, y.AwayPlayed) }
	default:
		by, less = "points", byTable
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Teams ranked by %s (%s):\n", by, describe(a))
	i := 0
	for _, r := range sortedRecords(recs, less) {
		if r.Played < minGames {
			continue
		}
		i++
		if i > a.Int("limit", 10) {
			break
		}
		fmt.Fprintf(&b, "%d. %s - %d pts, P%d W%d D%d L%d, GF %d, GA %d, Win rate: %.1f%%, Home win rate: %.1f%%, Away win rate: %.1f%%\n",
			i, db.Name(r.Team), r.Points(), r.Played, r.Won, r.Drawn, r.Lost, r.GF, r.GA, r.WinRate(), rate(r.HomeWon, r.HomePlayed), rate(r.AwayWon, r.AwayPlayed))
	}
	if i == 0 {
		return "No matches found for those criteria.", nil
	}
	return b.String(), nil
}

func (db *DB) Standings(a Args) (string, error) {
	season := a.Int("season", 0)
	comp := a.Str("competition")
	if comp == "" {
		comp = SerieA
	}
	if season == 0 {
		return "", fmt.Errorf("season is required")
	}
	ms, _ := db.filter(Args{"season": season, "competition": comp})
	if len(ms) == 0 {
		return fmt.Sprintf("No %s matches found for %d.", comp, season), nil
	}
	all := sortedRecords(db.records(ms, ""), byTable)
	most := 0
	for _, r := range all {
		most = max(most, r.Played)
	}
	// a few mislabelled rows in the extended dataset bring in clubs from
	// other tournaments; a real league member plays a full fixture list
	var rs []*Record
	for _, r := range all {
		if r.Played*2 >= most {
			rs = append(rs, r)
		}
	}
	var b strings.Builder
	fmt.Fprintf(&b, "%d %s Final Standings (calculated from %d matches):\n", season, comp, len(ms))
	for i, r := range rs {
		note := ""
		if i == 0 {
			note = " - Champion"
		} else if CompetitionMatches(SerieA, comp) && len(rs) >= 20 && i >= len(rs)-4 {
			note = " - Relegated"
		}
		fmt.Fprintf(&b, "%d. %s - %d pts (%dW, %dD, %dL, GF %d, GA %d)%s\n", i+1, db.Name(r.Team), r.Points(), r.Won, r.Drawn, r.Lost, r.GF, r.GA, note)
	}
	return b.String(), nil
}

func (db *DB) LibertadoresBracket(a Args) (string, error) {
	season := a.Int("season", 0)
	var b strings.Builder
	fmt.Fprintf(&b, "%d Copa Libertadores knockout bracket:\n", season)
	found := false
	for _, st := range []string{"round of 16", "quarterfinals", "semifinals", "final"} {
		ms, _ := db.filter(Args{"season": season, "competition": Libertadores, "stage": st})
		if len(ms) == 0 {
			continue
		}
		found = true
		fmt.Fprintf(&b, "\n%s:\n", st)
		for i := len(ms) - 1; i >= 0; i-- {
			b.WriteString(db.Line(ms[i]) + "\n")
		}
	}
	if !found {
		return fmt.Sprintf("No Libertadores knockout matches found for %d.", season), nil
	}
	return b.String(), nil
}

func (db *DB) StatsSummary(a Args) (string, error) {
	ms, err := db.filter(Args{"season": a.Int("season", 0), "competition": a.Str("competition"), "team": a.Str("team")})
	if err != nil {
		return "", err
	}
	if len(ms) == 0 {
		return "No matches found for those criteria.", nil
	}
	var goals, hw, aw, dr, corners, withStats int
	for _, m := range ms {
		goals += m.HomeGoals + m.AwayGoals
		switch {
		case m.HomeGoals > m.AwayGoals:
			hw++
		case m.HomeGoals < m.AwayGoals:
			aw++
		default:
			dr++
		}
		if m.HasStats {
			withStats++
			corners += m.HomeCorners + m.AwayCorners
		}
	}
	n := len(ms)
	var b strings.Builder
	fmt.Fprintf(&b, "Statistics (%s):\n- Matches: %d\n- Total goals: %d\n- Average goals per match: %.2f\n- Home win rate: %.1f%%\n- Draw rate: %.1f%%\n- Away win rate: %.1f%%\n",
		describe(a), n, goals, float64(goals)/float64(n), rate(hw, n), rate(dr, n), rate(aw, n))
	if withStats > 0 {
		fmt.Fprintf(&b, "- Average corners per match: %.2f (%d matches with extended stats)\n", float64(corners)/float64(withStats), withStats)
	}
	return b.String(), nil
}

func (db *DB) BiggestWins(a Args) (string, error) {
	ms, err := db.filter(Args{"season": a.Int("season", 0), "competition": a.Str("competition"), "team": a.Str("team")})
	if err != nil {
		return "", err
	}
	ms = append([]*Match(nil), ms...)
	margin := func(m *Match) int {
		d := m.HomeGoals - m.AwayGoals
		if d < 0 {
			return -d
		}
		return d
	}
	sort.SliceStable(ms, func(i, j int) bool {
		if margin(ms[i]) != margin(ms[j]) {
			return margin(ms[i]) > margin(ms[j])
		}
		return ms[i].HomeGoals+ms[i].AwayGoals > ms[j].HomeGoals+ms[j].AwayGoals
	})
	var b strings.Builder
	fmt.Fprintf(&b, "Biggest victories (%s):\n", describe(a))
	for i, m := range ms {
		if i == a.Int("limit", 10) {
			break
		}
		fmt.Fprintf(&b, "%d. %s\n", i+1, strings.TrimPrefix(db.Line(m), "- "))
	}
	return b.String(), nil
}

// Rivalries are traditional Brazilian derbies.
var Rivalries = [][3]string{
	{"Flamengo", "Fluminense", "Fla-Flu"}, {"Flamengo", "Vasco", "Clássico dos Milhões"}, {"Flamengo", "Botafogo", "Clássico da Rivalidade"},
	{"Fluminense", "Vasco", "Clássico dos Gigantes"}, {"Botafogo", "Vasco", "Clássico da Amizade"}, {"Botafogo", "Fluminense", "Clássico Vovô"},
	{"Corinthians", "Palmeiras", "Derby Paulista"}, {"Corinthians", "São Paulo", "Majestoso"}, {"Palmeiras", "São Paulo", "Choque-Rei"},
	{"Santos", "Corinthians", "Clássico Alvinegro"}, {"Palmeiras", "Santos", "Clássico da Saudade"}, {"São Paulo", "Santos", "San-São"},
	{"Grêmio", "Internacional", "Grenal"}, {"Cruzeiro", "Atlético-MG", "Clássico Mineiro"}, {"Athletico-PR", "Coritiba", "Atletiba"},
	{"Bahia", "Vitória", "Ba-Vi"}, {"Sport", "Náutico", "Clássico dos Clássicos"}, {"Ceará", "Fortaleza", "Clássico-Rei"},
}

func (db *DB) Derbies(a Args) (string, error) {
	var b strings.Builder
	total := 0
	for _, r := range Rivalries {
		ms, err := db.filter(Args{"team": r[0], "opponent": r[1], "season": a.Int("season", 0), "competition": a.Str("competition")})
		if err != nil {
			return "", err
		}
		if len(ms) == 0 {
			continue
		}
		total += len(ms)
		fmt.Fprintf(&b, "\n%s (%s vs %s):\n", r[2], r[0], r[1])
		for i, m := range ms {
			if i == 10 {
				fmt.Fprintf(&b, "- ... (%d more)\n", len(ms)-10)
				break
			}
			b.WriteString(db.Line(m) + "\n")
		}
	}
	if total == 0 {
		return "No derbies found for those criteria.", nil
	}
	return fmt.Sprintf("Found %d derby matches (%s):\n", total, describe(a)) + b.String(), nil
}

var positionGroups = map[string][]string{
	"forward":    {"ST", "CF", "LW", "RW", "LS", "RS", "LF", "RF"},
	"midfielder": {"CM", "CDM", "CAM", "LM", "RM", "LCM", "RCM", "LDM", "RDM", "LAM", "RAM"},
	"defender":   {"CB", "LB", "RB", "LCB", "RCB", "LWB", "RWB"},
	"goalkeeper": {"GK"},
}

func positionMatches(pos, q string) bool {
	q = strings.TrimSuffix(Fold(q), "s")
	if q == "" {
		return true
	}
	if g, ok := positionGroups[q]; ok {
		for _, p := range g {
			if p == pos {
				return true
			}
		}
		return false
	}
	return strings.EqualFold(pos, q)
}

func (db *DB) players(a Args) []*Player {
	name, nat, club, pos := Fold(a.Str("name")), Fold(a.Str("nationality")), Fold(a.Str("club")), a.Str("position")
	if nat == "brazilian" {
		nat = "brazil"
	}
	minOverall := a.Int("min_overall", 0)
	var out []*Player
	for _, p := range db.Players {
		if name != "" && !strings.Contains(Fold(p.Name), name) ||
			nat != "" && Fold(p.Nationality) != nat ||
			club != "" && !strings.Contains(Fold(p.Club), club) ||
			!positionMatches(p.Position, pos) || p.Overall < minOverall {
			continue
		}
		out = append(out, p)
	}
	return out
}

func (db *DB) SearchPlayers(a Args) (string, error) {
	ps := db.players(a)
	if len(ps) == 0 {
		return "No players found for those criteria.", nil
	}
	var b strings.Builder
	fmt.Fprintf(&b, "Found %d players (by overall rating):\n", len(ps))
	limit := a.Int("limit", 20)
	for i, p := range ps {
		if i == limit {
			fmt.Fprintf(&b, "... (%d more players)\n", len(ps)-limit)
			break
		}
		fmt.Fprintf(&b, "%d. %s - Overall: %d, Potential: %d, Position: %s, Club: %s, Nationality: %s, Age: %d\n",
			i+1, p.Name, p.Overall, p.Potential, p.Position, p.Club, p.Nationality, p.Age)
		if len(ps) <= 3 {
			fmt.Fprintf(&b, "   Jersey: %d, Height: %s, Weight: %s, Foot: %s, Value: %s, Skills: %v\n", p.Jersey, p.Height, p.Weight, p.Foot, p.Value, p.Skills)
		}
	}
	return b.String(), nil
}

// brazilianClubs are clubs whose squads in the FIFA data are mostly Brazilian.
func (db *DB) brazilianClubs() map[string]bool {
	total, br := map[string]int{}, map[string]int{}
	for _, p := range db.Players {
		total[p.Club]++
		if p.Nationality == "Brazil" {
			br[p.Club]++
		}
	}
	out := map[string]bool{}
	for c, n := range total {
		if c != "" && n >= 5 && br[c]*2 > n {
			out[c] = true
		}
	}
	return out
}

func (db *DB) ClubSummary(a Args) (string, error) {
	ps := db.players(a)
	clubs := db.brazilianClubs()
	type agg struct {
		club   string
		n, sum int
	}
	m := map[string]*agg{}
	for _, p := range ps {
		if !clubs[p.Club] && !a.Bool("all_clubs") || p.Club == "" {
			continue
		}
		if m[p.Club] == nil {
			m[p.Club] = &agg{club: p.Club}
		}
		m[p.Club].n++
		m[p.Club].sum += p.Overall
	}
	var as []*agg
	for _, x := range m {
		as = append(as, x)
	}
	sort.Slice(as, func(i, j int) bool {
		ai, aj := float64(as[i].sum)/float64(as[i].n), float64(as[j].sum)/float64(as[j].n)
		if ai != aj {
			return ai > aj
		}
		return as[i].club < as[j].club
	})
	if len(as) == 0 {
		return "No players found for those criteria.", nil
	}
	var b strings.Builder
	b.WriteString("Players by club (Brazilian clubs):\n")
	for _, x := range as {
		fmt.Fprintf(&b, "- %s: %d players (avg rating: %.0f)\n", x.club, x.n, float64(x.sum)/float64(x.n))
	}
	return b.String(), nil
}
