// stats.go - derived statistics.
//
// Context
//
//	Nothing in the datasets is aggregated: there are no league tables, no
//	points, no head-to-head summaries. Everything in this file is computed from
//	the de-duplicated match edges at query time, which is fast enough (the
//	whole graph is ~13k matches) and means every number is reproducible from the
//	source rows.
//
//	Conventions used throughout:
//	  - three points for a win, one for a draw, as in every Brasileirão season
//	    covered by the data (2003 onwards)
//	  - only matches with a recorded score count towards records; ~100 rows
//	    across the datasets have "NA" scores and are reported separately
//	  - standings order by points, then wins, then goal difference, then goals
//	    scored, then name - the Brasileirão criteria
package soccer

import (
	"fmt"
	"sort"
	"strings"
)

// Record is a win/draw/loss summary for one club over a set of matches.
type Record struct {
	ClubID       string  `json:"club_id"`
	Club         string  `json:"club"`
	Played       int     `json:"played"`
	Wins         int     `json:"wins"`
	Draws        int     `json:"draws"`
	Losses       int     `json:"losses"`
	GoalsFor     int     `json:"goals_for"`
	GoalsAgainst int     `json:"goals_against"`
	GoalDiff     int     `json:"goal_difference"`
	Points       int     `json:"points"`
	WinRate      float64 `json:"win_rate_pct"`
	PointsPct    float64 `json:"points_pct"`
	Unscored     int     `json:"matches_without_score,omitempty"`
}

func (r *Record) add(m *Match, clubID string) {
	if !m.HasScore {
		r.Unscored++
		return
	}
	gf, ga := m.HomeGoals, m.AwayGoals
	if m.AwayClubID == clubID {
		gf, ga = ga, gf
	}
	r.Played++
	r.GoalsFor += gf
	r.GoalsAgainst += ga
	switch {
	case gf > ga:
		r.Wins++
	case gf == ga:
		r.Draws++
	default:
		r.Losses++
	}
}

func (r *Record) finish() {
	r.GoalDiff = r.GoalsFor - r.GoalsAgainst
	r.Points = r.Wins*3 + r.Draws
	if r.Played > 0 {
		r.WinRate = round1(float64(r.Wins) * 100 / float64(r.Played))
		r.PointsPct = round1(float64(r.Points) * 100 / float64(r.Played*3))
	}
}

// Summary renders a record as a compact string.
func (r *Record) Summary() string {
	return fmt.Sprintf("%d matches, %dW %dD %dL, %d-%d goals (GD %+d), %d pts, %.1f%% win rate",
		r.Played, r.Wins, r.Draws, r.Losses, r.GoalsFor, r.GoalsAgainst, r.GoalDiff, r.Points, r.WinRate)
}

// BuildRecord computes a club's record over the supplied matches.
func BuildRecord(club *Club, matches []*Match) Record {
	r := Record{ClubID: club.ID, Club: club.Name}
	for _, m := range matches {
		r.add(m, club.ID)
	}
	r.finish()
	return r
}

// TeamStats is the answer to "how did this team do?".
type TeamStats struct {
	Club          *Club               `json:"club"`
	Competition   Competition         `json:"competition,omitempty"`
	Season        int                 `json:"season,omitempty"`
	Venue         Venue               `json:"venue"`
	Overall       Record              `json:"overall"`
	Home          Record              `json:"home"`
	Away          Record              `json:"away"`
	BiggestWin    *Match              `json:"biggest_win,omitempty"`
	BiggestLoss   *Match              `json:"biggest_loss,omitempty"`
	FirstMatch    *Match              `json:"first_match,omitempty"`
	LastMatch     *Match              `json:"last_match,omitempty"`
	ByCompetition []CompetitionRecord `json:"by_competition,omitempty"`
}

// CompetitionRecord is a club's record within one competition.
type CompetitionRecord struct {
	Competition Competition `json:"competition"`
	Seasons     []int       `json:"seasons"`
	Record      Record      `json:"record"`
}

// TeamStats computes a club's record, optionally scoped to a competition,
// season and venue.
func (g *Graph) TeamStats(club *Club, comp Competition, season int, venue Venue) TeamStats {
	base := MatchFilter{ClubID: club.ID, Competition: comp, Season: season, Venue: venue}
	matches := g.FindMatches(base)

	ts := TeamStats{Club: club, Competition: comp, Season: season, Venue: venue}
	ts.Overall = BuildRecord(club, matches)

	homeOnly, awayOnly := make([]*Match, 0, len(matches)), make([]*Match, 0, len(matches))
	for _, m := range matches {
		if m.HomeClubID == club.ID {
			homeOnly = append(homeOnly, m)
		} else {
			awayOnly = append(awayOnly, m)
		}
	}
	ts.Home = BuildRecord(club, homeOnly)
	ts.Away = BuildRecord(club, awayOnly)

	bestMargin, worstMargin := 0, 0
	for _, m := range matches {
		if !m.HasScore {
			continue
		}
		gf, ga := m.HomeGoals, m.AwayGoals
		if m.AwayClubID == club.ID {
			gf, ga = ga, gf
		}
		if gf-ga > bestMargin {
			bestMargin, ts.BiggestWin = gf-ga, m
		}
		if ga-gf > worstMargin {
			worstMargin, ts.BiggestLoss = ga-gf, m
		}
	}
	for _, m := range matches {
		if m.HasDate {
			if ts.FirstMatch == nil {
				ts.FirstMatch = m
			}
			ts.LastMatch = m
		}
	}

	// Only break down by competition when the caller has not already pinned one.
	if comp == "" {
		byComp := map[Competition][]*Match{}
		seasons := map[Competition]map[int]bool{}
		for _, m := range matches {
			byComp[m.Competition] = append(byComp[m.Competition], m)
			if seasons[m.Competition] == nil {
				seasons[m.Competition] = map[int]bool{}
			}
			seasons[m.Competition][m.Season] = true
		}
		for _, c := range AllCompetitions {
			list, ok := byComp[c]
			if !ok {
				continue
			}
			years := make([]int, 0, len(seasons[c]))
			for y := range seasons[c] {
				years = append(years, y)
			}
			sort.Ints(years)
			ts.ByCompetition = append(ts.ByCompetition, CompetitionRecord{
				Competition: c, Seasons: years, Record: BuildRecord(club, list),
			})
		}
	}
	return ts
}

// HeadToHead summarises the rivalry between two clubs.
type HeadToHead struct {
	ClubA         *Club          `json:"club_a"`
	ClubB         *Club          `json:"club_b"`
	Nickname      string         `json:"nickname,omitempty"`
	Competition   Competition    `json:"competition,omitempty"`
	Season        int            `json:"season,omitempty"`
	Played        int            `json:"played"`
	AWins         int            `json:"club_a_wins"`
	BWins         int            `json:"club_b_wins"`
	Draws         int            `json:"draws"`
	AGoals        int            `json:"club_a_goals"`
	BGoals        int            `json:"club_b_goals"`
	ByCompetition map[string]int `json:"matches_by_competition,omitempty"`
	Matches       []*Match       `json:"matches"`
	Total         int            `json:"total_matches"`
}

// HeadToHead computes the record between two clubs, newest match first.
func (g *Graph) HeadToHead(a, b *Club, comp Competition, season, limit int) HeadToHead {
	all := g.FindMatches(MatchFilter{
		ClubID: a.ID, OpponentID: b.ID, Competition: comp, Season: season, Newest: true,
	})
	h := HeadToHead{
		ClubA: a, ClubB: b, Competition: comp, Season: season,
		Total: len(all), ByCompetition: map[string]int{},
	}
	h.Nickname = RivalryName(a.ID, b.ID)
	for _, m := range all {
		h.ByCompetition[string(m.Competition)]++
		if !m.HasScore {
			continue
		}
		h.Played++
		ag, bg := m.HomeGoals, m.AwayGoals
		if m.HomeClubID == b.ID {
			ag, bg = bg, ag
		}
		h.AGoals += ag
		h.BGoals += bg
		switch {
		case ag > bg:
			h.AWins++
		case bg > ag:
			h.BWins++
		default:
			h.Draws++
		}
	}
	if limit > 0 && len(all) > limit {
		all = all[:limit]
	}
	h.Matches = all
	return h
}

// RivalryName returns the popular name of a fixture, if it is a classic.
func RivalryName(a, b string) string {
	for _, r := range classicRivalries {
		if (r.A == a && r.B == b) || (r.A == b && r.B == a) {
			return r.Name
		}
	}
	return ""
}

// StandingRow is one line of a calculated league table.
type StandingRow struct {
	Position int    `json:"position"`
	Record   Record `json:"record"`
	Status   string `json:"status,omitempty"`
}

// Standings is a calculated league table for one competition season.
type Standings struct {
	Competition   Competition   `json:"competition"`
	Season        int           `json:"season"`
	Rows          []StandingRow `json:"rows"`
	MatchesPlayed int           `json:"matches_played"`
	MatchesTotal  int           `json:"matches_total"`
	Complete      bool          `json:"complete"`
	Note          string        `json:"note,omitempty"`
}

// Standings calculates the table for a competition season from match results.
func (g *Graph) Standings(comp Competition, season int) (Standings, error) {
	matches := g.CompetitionMatches(comp, season)
	if len(matches) == 0 {
		return Standings{}, fmt.Errorf("no %s matches for season %d (available: %s)",
			comp, season, formatSeasons(g.Seasons(comp)))
	}
	s := Standings{Competition: comp, Season: season, MatchesTotal: len(matches)}

	records := map[string]*Record{}
	get := func(clubID string) *Record {
		r, ok := records[clubID]
		if !ok {
			club := g.clubs[clubID]
			name := clubID
			if club != nil {
				name = club.Name
			}
			r = &Record{ClubID: clubID, Club: name}
			records[clubID] = r
		}
		return r
	}
	for _, m := range matches {
		hr, ar := get(m.HomeClubID), get(m.AwayClubID)
		if !m.HasScore {
			hr.Unscored++
			ar.Unscored++
			continue
		}
		s.MatchesPlayed++
		hr.add(m, m.HomeClubID)
		ar.add(m, m.AwayClubID)
	}
	rows := make([]StandingRow, 0, len(records))
	for _, r := range records {
		r.finish()
		rows = append(rows, StandingRow{Record: *r})
	}
	sort.Slice(rows, func(i, j int) bool { return lessStanding(rows[i].Record, rows[j].Record) })
	for i := range rows {
		rows[i].Position = i + 1
	}
	s.Rows = rows
	s.Complete = s.MatchesPlayed == s.MatchesTotal

	annotateStatus(&s)
	switch {
	case comp == CopaDoBrasil || comp == Libertadores:
		s.Note = "This is a knockout competition; the table ranks clubs by results only and is not an official standing. Use find_matches with stage=\"final\" for the decisive ties."
	case s.Complete && isSerieARelegationSeason(&s):
		s.Note = "Relegation places are inferred from the final positions. Brazilian football has occasionally overridden them off the field - notably in 2003 - so verify the outcome of a bottom-four finish before relying on it."
	}
	return s, nil
}

func lessStanding(a, b Record) bool {
	if a.Points != b.Points {
		return a.Points > b.Points
	}
	if a.Wins != b.Wins {
		return a.Wins > b.Wins
	}
	if a.GoalDiff != b.GoalDiff {
		return a.GoalDiff > b.GoalDiff
	}
	if a.GoalsFor != b.GoalsFor {
		return a.GoalsFor > b.GoalsFor
	}
	return a.Club < b.Club
}

// isSerieARelegationSeason reports whether relegation places were annotated.
func isSerieARelegationSeason(s *Standings) bool {
	for _, row := range s.Rows {
		if row.Status == "Relegated" {
			return true
		}
	}
	return false
}

// annotateStatus marks the champion and the relegation places of a completed
// league season.
func annotateStatus(s *Standings) {
	if s.Competition != SerieA && s.Competition != SerieB && s.Competition != SerieC {
		return
	}
	n := len(s.Rows)
	if n == 0 {
		return
	}
	label := "Champion"
	if !s.Complete {
		label = "Leader (season incomplete in dataset)"
	}
	s.Rows[0].Status = label
	// The bottom four are relegated in every Série A season the data covers
	// (2003 onwards). Continental qualification is deliberately not annotated:
	// the number of Libertadores berths changed repeatedly over this period and
	// the match results alone do not determine it.
	if s.Competition == SerieA && n >= 20 && s.Complete {
		for i := n - 4; i < n; i++ {
			if i > 0 {
				s.Rows[i].Status = "Relegated"
			}
		}
	}
}

// Champion returns the club that topped a completed league season.
func (g *Graph) Champion(comp Competition, season int) (*Club, Standings, error) {
	s, err := g.Standings(comp, season)
	if err != nil {
		return nil, Standings{}, err
	}
	if len(s.Rows) == 0 {
		return nil, s, fmt.Errorf("no results for %s %d", comp, season)
	}
	return g.clubs[s.Rows[0].Record.ClubID], s, nil
}

// Aggregate is a competition-wide statistical summary.
type Aggregate struct {
	Competition    Competition `json:"competition,omitempty"`
	Season         int         `json:"season,omitempty"`
	Matches        int         `json:"matches"`
	Played         int         `json:"matches_with_scores"`
	TotalGoals     int         `json:"total_goals"`
	GoalsPerMatch  float64     `json:"goals_per_match"`
	HomeWins       int         `json:"home_wins"`
	AwayWins       int         `json:"away_wins"`
	Draws          int         `json:"draws"`
	HomeWinPct     float64     `json:"home_win_pct"`
	AwayWinPct     float64     `json:"away_win_pct"`
	DrawPct        float64     `json:"draw_pct"`
	HomeGoals      int         `json:"home_goals"`
	AwayGoals      int         `json:"away_goals"`
	CleanSheets    int         `json:"clean_sheets"`
	GoallessDraws  int         `json:"goalless_draws"`
	BiggestWin     *Match      `json:"biggest_win,omitempty"`
	HighestScoring *Match      `json:"highest_scoring_match,omitempty"`
}

// computeAggregate calculates league-wide statistics over a set of matches.
func computeAggregate(comp Competition, season int, matches []*Match) Aggregate {
	a := Aggregate{Competition: comp, Season: season, Matches: len(matches)}
	bestMargin, bestTotal := -1, -1
	for _, m := range matches {
		if !m.HasScore {
			continue
		}
		a.Played++
		a.TotalGoals += m.TotalGoals()
		a.HomeGoals += m.HomeGoals
		a.AwayGoals += m.AwayGoals
		switch m.Outcome() {
		case "home":
			a.HomeWins++
		case "away":
			a.AwayWins++
		default:
			a.Draws++
			if m.TotalGoals() == 0 {
				a.GoallessDraws++
			}
		}
		if m.HomeGoals == 0 || m.AwayGoals == 0 {
			a.CleanSheets++
		}
		if m.GoalDifference() > bestMargin {
			bestMargin, a.BiggestWin = m.GoalDifference(), m
		}
		if m.TotalGoals() > bestTotal {
			bestTotal, a.HighestScoring = m.TotalGoals(), m
		}
	}
	if a.Played > 0 {
		p := float64(a.Played)
		a.GoalsPerMatch = round2(float64(a.TotalGoals) / p)
		a.HomeWinPct = round1(float64(a.HomeWins) * 100 / p)
		a.AwayWinPct = round1(float64(a.AwayWins) * 100 / p)
		a.DrawPct = round1(float64(a.Draws) * 100 / p)
	}
	return a
}

// AggregateStats computes competition-wide statistics with the usual filters.
func (g *Graph) AggregateStats(comp Competition, season int) Aggregate {
	f := MatchFilter{Competition: comp, Season: season}
	return computeAggregate(comp, season, g.FindMatches(f))
}

// Leaderboard ranks clubs by a chosen metric.
type Leaderboard struct {
	Metric      string      `json:"metric"`
	Competition Competition `json:"competition,omitempty"`
	Season      int         `json:"season,omitempty"`
	Venue       Venue       `json:"venue"`
	MinMatches  int         `json:"min_matches"`
	Rows        []Record    `json:"rows"`
}

// LeaderboardMetrics are the ranking modes exposed by the MCP tool.
var LeaderboardMetrics = []string{
	"points", "wins", "win_rate", "goals_for", "goals_against", "goal_difference",
}

// Leaderboard ranks every club that played in the given scope.
func (g *Graph) Leaderboard(metric string, comp Competition, season int, venue Venue, minMatches, limit int) (Leaderboard, error) {
	metric = strings.ToLower(strings.TrimSpace(metric))
	if metric == "" {
		metric = "points"
	}
	valid := false
	for _, m := range LeaderboardMetrics {
		if m == metric {
			valid = true
			break
		}
	}
	if !valid {
		return Leaderboard{}, fmt.Errorf("unknown metric %q; supported: %s", metric, strings.Join(LeaderboardMetrics, ", "))
	}

	matches := g.FindMatches(MatchFilter{Competition: comp, Season: season})
	records := map[string]*Record{}
	get := func(clubID string) *Record {
		r, ok := records[clubID]
		if !ok {
			name := clubID
			if c := g.clubs[clubID]; c != nil {
				name = c.Name
			}
			r = &Record{ClubID: clubID, Club: name}
			records[clubID] = r
		}
		return r
	}
	for _, m := range matches {
		if venue != VenueAway {
			get(m.HomeClubID).add(m, m.HomeClubID)
		}
		if venue != VenueHome {
			get(m.AwayClubID).add(m, m.AwayClubID)
		}
	}

	rows := make([]Record, 0, len(records))
	for _, r := range records {
		r.finish()
		if r.Played < minMatches {
			continue
		}
		rows = append(rows, *r)
	}
	sort.Slice(rows, func(i, j int) bool {
		a, b := rows[i], rows[j]
		switch metric {
		case "wins":
			if a.Wins != b.Wins {
				return a.Wins > b.Wins
			}
		case "win_rate":
			if a.WinRate != b.WinRate {
				return a.WinRate > b.WinRate
			}
		case "goals_for":
			if a.GoalsFor != b.GoalsFor {
				return a.GoalsFor > b.GoalsFor
			}
		case "goals_against":
			if a.GoalsAgainst != b.GoalsAgainst {
				return a.GoalsAgainst < b.GoalsAgainst
			}
		case "goal_difference":
			if a.GoalDiff != b.GoalDiff {
				return a.GoalDiff > b.GoalDiff
			}
		}
		return lessStanding(a, b)
	})
	if limit > 0 && len(rows) > limit {
		rows = rows[:limit]
	}
	return Leaderboard{
		Metric: metric, Competition: comp, Season: season, Venue: venue,
		MinMatches: minMatches, Rows: rows,
	}, nil
}

// BiggestWins returns the largest margins of victory in a scope.
func (g *Graph) BiggestWins(comp Competition, season, limit int) []*Match {
	matches := g.FindMatches(MatchFilter{Competition: comp, Season: season, OnlyPlayed: true})
	out := append([]*Match(nil), matches...)
	sort.SliceStable(out, func(i, j int) bool {
		if out[i].GoalDifference() != out[j].GoalDifference() {
			return out[i].GoalDifference() > out[j].GoalDifference()
		}
		return out[i].TotalGoals() > out[j].TotalGoals()
	})
	if limit > 0 && len(out) > limit {
		out = out[:limit]
	}
	return out
}

// HighestScoring returns the matches with the most combined goals.
func (g *Graph) HighestScoring(comp Competition, season, limit int) []*Match {
	matches := g.FindMatches(MatchFilter{Competition: comp, Season: season, OnlyPlayed: true})
	out := append([]*Match(nil), matches...)
	sort.SliceStable(out, func(i, j int) bool {
		if out[i].TotalGoals() != out[j].TotalGoals() {
			return out[i].TotalGoals() > out[j].TotalGoals()
		}
		return out[i].GoalDifference() > out[j].GoalDifference()
	})
	if limit > 0 && len(out) > limit {
		out = out[:limit]
	}
	return out
}

// SeasonComparison contrasts two seasons of the same competition.
type SeasonComparison struct {
	Competition Competition        `json:"competition"`
	A           Aggregate          `json:"season_a"`
	B           Aggregate          `json:"season_b"`
	ChampionA   string             `json:"champion_a,omitempty"`
	ChampionB   string             `json:"champion_b,omitempty"`
	Deltas      map[string]float64 `json:"deltas"`
}

// CompareSeasons computes the difference between two seasons.
func (g *Graph) CompareSeasons(comp Competition, a, b int) (SeasonComparison, error) {
	if len(g.CompetitionMatches(comp, a)) == 0 {
		return SeasonComparison{}, fmt.Errorf("no %s data for %d (available: %s)", comp, a, formatSeasons(g.Seasons(comp)))
	}
	if len(g.CompetitionMatches(comp, b)) == 0 {
		return SeasonComparison{}, fmt.Errorf("no %s data for %d (available: %s)", comp, b, formatSeasons(g.Seasons(comp)))
	}
	sc := SeasonComparison{
		Competition: comp,
		A:           g.AggregateStats(comp, a),
		B:           g.AggregateStats(comp, b),
	}
	if champ, _, err := g.Champion(comp, a); err == nil && champ != nil {
		sc.ChampionA = champ.Name
	}
	if champ, _, err := g.Champion(comp, b); err == nil && champ != nil {
		sc.ChampionB = champ.Name
	}
	sc.Deltas = map[string]float64{
		"goals_per_match": round2(sc.B.GoalsPerMatch - sc.A.GoalsPerMatch),
		"home_win_pct":    round1(sc.B.HomeWinPct - sc.A.HomeWinPct),
		"draw_pct":        round1(sc.B.DrawPct - sc.A.DrawPct),
		"total_goals":     float64(sc.B.TotalGoals - sc.A.TotalGoals),
		"matches":         float64(sc.B.Played - sc.A.Played),
	}
	return sc, nil
}

// Derby pairs a classic fixture with the matches found for it.
type Derby struct {
	Name    string   `json:"name"`
	ClubA   string   `json:"club_a"`
	ClubB   string   `json:"club_b"`
	Matches []*Match `json:"matches"`
}

// Derbies finds matches between traditional rivals in a scope.
func (g *Graph) Derbies(comp Competition, season int, clubID string, limit int) []Derby {
	var out []Derby
	for _, r := range classicRivalries {
		if clubID != "" && r.A != clubID && r.B != clubID {
			continue
		}
		a, b := g.clubs[r.A], g.clubs[r.B]
		if a == nil || b == nil {
			continue
		}
		matches := g.FindMatches(MatchFilter{
			ClubID: a.ID, OpponentID: b.ID, Competition: comp, Season: season, Newest: true, Limit: limit,
		})
		if len(matches) == 0 {
			continue
		}
		out = append(out, Derby{Name: r.Name, ClubA: a.Name, ClubB: b.Name, Matches: matches})
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Name < out[j].Name })
	return out
}

func formatSeasons(seasons []int) string {
	if len(seasons) == 0 {
		return "none"
	}
	parts := make([]string, 0, len(seasons))
	for _, s := range seasons {
		parts = append(parts, fmt.Sprint(s))
	}
	return strings.Join(parts, ", ")
}

func round1(f float64) float64 { return float64(int(f*10+sign(f)*0.5)) / 10 }
func round2(f float64) float64 { return float64(int(f*100+sign(f)*0.5)) / 100 }

func sign(f float64) float64 {
	if f < 0 {
		return -1
	}
	return 1
}
