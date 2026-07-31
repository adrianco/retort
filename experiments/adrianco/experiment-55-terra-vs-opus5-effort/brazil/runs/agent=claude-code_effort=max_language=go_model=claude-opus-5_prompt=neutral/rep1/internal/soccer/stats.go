// stats.go computes everything that is not stored in the CSVs: win/draw/loss
// records, league tables (with champion and relegation zone), head-to-head
// summaries, per-competition aggregates and the various "best/biggest" lists.
package soccer

import (
	"fmt"
	"sort"
	"strings"
	"sync"
	"time"
)

// Record is a win/draw/loss and goals record for one club.
type Record struct {
	TeamID       string `json:"team_id,omitempty"`
	TeamName     string `json:"team,omitempty"`
	Matches      int    `json:"matches"`
	Wins         int    `json:"wins"`
	Draws        int    `json:"draws"`
	Losses       int    `json:"losses"`
	GoalsFor     int    `json:"goals_for"`
	GoalsAgainst int    `json:"goals_against"`
}

// Add folds one match into the record from teamID's point of view.
func (r *Record) Add(m *Match, teamID string) {
	r.Matches++
	gf, ga := m.GoalsFor(teamID), m.GoalsAgainst(teamID)
	r.GoalsFor += gf
	r.GoalsAgainst += ga
	switch {
	case gf > ga:
		r.Wins++
	case gf < ga:
		r.Losses++
	default:
		r.Draws++
	}
}

// Points uses the modern three-points-for-a-win system.
func (r Record) Points() int { return r.Wins*3 + r.Draws }

// GoalDiff is goals for minus goals against.
func (r Record) GoalDiff() int { return r.GoalsFor - r.GoalsAgainst }

// WinRate is the share of matches won, in percent.
func (r Record) WinRate() float64 {
	if r.Matches == 0 {
		return 0
	}
	return round1(float64(r.Wins) * 100 / float64(r.Matches))
}

// PointsPerMatch is the average points per match.
func (r Record) PointsPerMatch() float64 {
	if r.Matches == 0 {
		return 0
	}
	return round2(float64(r.Points()) / float64(r.Matches))
}

// GoalsPerMatch is the average goals scored per match.
func (r Record) GoalsPerMatch() float64 {
	if r.Matches == 0 {
		return 0
	}
	return round2(float64(r.GoalsFor) / float64(r.Matches))
}

func round2(f float64) float64 { return float64(int(f*100+0.5)) / 100 }

// TeamRecord aggregates a club's results under an arbitrary filter.
func (s *Store) TeamRecord(teamID string, f MatchFilter) Record {
	f.TeamID = teamID
	f.Limit, f.Offset = 0, 0
	rec := Record{TeamID: teamID}
	if t := s.Teams.Team(teamID); t != nil {
		rec.TeamName = t.Name
	}
	for _, m := range s.FindMatches(f).Matches {
		rec.Add(m, teamID)
	}
	return rec
}

// ---------------------------------------------------------------------------
// League tables
// ---------------------------------------------------------------------------

// StandingsOptions tunes a computed league table.
type StandingsOptions struct {
	ThroughRound int   // only count matches up to this round (0 = all)
	Venue        Venue // home-only or away-only table
	Through      time.Time
}

func (o StandingsOptions) isZero() bool {
	return o.ThroughRound == 0 && (o.Venue == "" || o.Venue == VenueAny) && o.Through.IsZero()
}

// StandingsRow is one line of a league table. The club's Record is embedded,
// so row.Wins, row.GoalsFor and friends read naturally.
type StandingsRow struct {
	Position int `json:"position"`
	Record
	Points   int      `json:"points"`
	GoalDiff int      `json:"goal_difference"`
	Form     []string `json:"form,omitempty"`
	Note     string   `json:"note,omitempty"`
}

// Standings is a computed league table.
type Standings struct {
	CompetitionID string         `json:"competition"`
	Season        int            `json:"season"`
	Rows          []StandingsRow `json:"rows"`
	Matches       int            `json:"matches"`
	Complete      bool           `json:"complete"`
	Champion      string         `json:"champion,omitempty"`
	Leader        string         `json:"leader,omitempty"`
	Relegated     []string       `json:"relegated,omitempty"`
	Note          string         `json:"note,omitempty"`
}

// relegationSlots is the number of clubs relegated from Série A / B each year.
const relegationSlots = 4

// Standings computes a league table from match results.
//
// Ordering follows the Brazilian criteria that can be derived from results
// alone: points, then wins, then goal difference, then goals scored, then name.
func (s *Store) Standings(comp string, season int, opts StandingsOptions) *Standings {
	if opts.isZero() {
		s.standingsOnce.Do(func() { s.standingsCache = map[compSeason]*Standings{} })
		s.standingsMu.Lock()
		if t, ok := s.standingsCache[compSeason{comp, season}]; ok {
			s.standingsMu.Unlock()
			return t
		}
		s.standingsMu.Unlock()
		t := s.computeStandings(comp, season, opts)
		s.standingsMu.Lock()
		s.standingsCache[compSeason{comp, season}] = t
		s.standingsMu.Unlock()
		return t
	}
	return s.computeStandings(comp, season, opts)
}

func (s *Store) computeStandings(comp string, season int, opts StandingsOptions) *Standings {
	table := &Standings{CompetitionID: comp, Season: season}
	recs := map[string]*StandingsRow{}
	form := map[string][]*Match{}
	matches := s.SeasonMatches(comp, season)
	for _, m := range matches {
		if opts.ThroughRound > 0 && (m.Round == 0 || m.Round > opts.ThroughRound) {
			continue
		}
		if !opts.Through.IsZero() && m.Date.After(opts.Through) {
			continue
		}
		table.Matches++
		for _, id := range []string{m.HomeTeamID, m.AwayTeamID} {
			if opts.Venue == VenueHome && id != m.HomeTeamID {
				continue
			}
			if opts.Venue == VenueAway && id != m.AwayTeamID {
				continue
			}
			row := recs[id]
			if row == nil {
				name := id
				if t := s.Teams.Team(id); t != nil {
					name = t.Name
				}
				row = &StandingsRow{Record: Record{TeamID: id, TeamName: name}}
				recs[id] = row
			}
			row.Record.Add(m, id)
			form[id] = append(form[id], m)
		}
	}
	for id, row := range recs {
		row.Points = row.Record.Points()
		row.GoalDiff = row.Record.GoalDiff()
		fm := form[id]
		sortSlice(fm, func(a, b *Match) bool { return a.Date.After(b.Date) })
		for i, m := range fm {
			if i == 5 {
				break
			}
			row.Form = append(row.Form, m.ResultFor(id))
		}
		table.Rows = append(table.Rows, *row)
	}
	sortSlice(table.Rows, func(a, b StandingsRow) bool {
		switch {
		case a.Points != b.Points:
			return a.Points > b.Points
		case a.Record.Wins != b.Record.Wins:
			return a.Record.Wins > b.Record.Wins
		case a.GoalDiff != b.GoalDiff:
			return a.GoalDiff > b.GoalDiff
		case a.Record.GoalsFor != b.Record.GoalsFor:
			return a.Record.GoalsFor > b.Record.GoalsFor
		default:
			return Fold(a.TeamName) < Fold(b.TeamName)
		}
	})
	for i := range table.Rows {
		table.Rows[i].Position = i + 1
	}

	// Only a double round-robin turns into a single table with a champion.
	n := len(table.Rows)
	c, known := CompetitionByID(comp)
	switch {
	case !opts.isZero() || n < 2:
		// Partial tables (through_round, home-only) are never "complete".
	case known && c.Format == FormatDoubleRoundRobin:
		expected := n * (n - 1)
		table.Complete = table.Matches >= expected
		if table.Matches < expected {
			table.Note = fmt.Sprintf("%d of the %d fixtures of this season are in the data", table.Matches, expected)
		}
		table.decide(n)
	case known && c.Format == FormatGroupKnockout:
		table.Note = "this competition is played in groups followed by knockout rounds, so a single table is only a summary of results"
	}
	return table
}

// decide labels the champion and the relegation zone, but only where the
// missing fixtures cannot change the outcome.
//
// The 2023 Série A is the reason this is not simply "top of the table wins":
// three fixtures are missing from the sources, Grêmio leads the partial table
// and Palmeiras - who actually won the title - still has an unplayed match in
// hand, so no champion can be declared from this data alone.
func (t *Standings) decide(teams int) {
	if teams < 2 {
		return
	}
	t.Leader = t.Rows[0].TeamName
	if t.Complete {
		// With every fixture present the table order is the final one: it uses
		// the Brazilian criteria (points, wins, goal difference, goals scored),
		// which is what separates clubs level on points.
		t.Rows[0].Note = "Champion"
		t.Champion = t.Rows[0].TeamName
		for i := teams - relegationSlots; i < teams; i++ {
			if i > 0 {
				t.Rows[i].Note = "Relegated"
				t.Relegated = append(t.Relegated, t.Rows[i].TeamName)
			}
		}
		return
	}
	perTeam := 2 * (teams - 1)
	potential := make([]int, len(t.Rows))
	for i, row := range t.Rows {
		remaining := perTeam - row.Matches
		if remaining < 0 {
			remaining = 0
		}
		potential[i] = row.Points + 3*remaining
	}

	leader := t.Rows[0]
	certain := true
	for i := 1; i < len(t.Rows); i++ {
		if potential[i] >= leader.Points {
			certain = false
			break
		}
	}
	if certain {
		t.Rows[0].Note = "Champion"
		t.Champion = leader.TeamName
	} else if !t.Complete {
		t.Note = strings.TrimSuffix(t.Note, ".") +
			"; the leader could still be caught by a club with fixtures missing, so no champion is declared"
	}

	// A club is relegated when enough clubs are certain to finish above it.
	for i := range t.Rows {
		above := 0
		for j := range t.Rows {
			if j != i && t.Rows[j].Points > potential[i] {
				above++
			}
		}
		if above >= teams-relegationSlots {
			t.Rows[i].Note = "Relegated"
			t.Relegated = append(t.Relegated, t.Rows[i].TeamName)
		}
	}
}

// ---------------------------------------------------------------------------
// Head to head
// ---------------------------------------------------------------------------

// HeadToHead summarises every meeting between two clubs.
type HeadToHead struct {
	TeamA        *Team        `json:"team_a"`
	TeamB        *Team        `json:"team_b"`
	Matches      []*Match     `json:"matches"`
	Total        int          `json:"total_matches"`
	AWins        int          `json:"team_a_wins"`
	BWins        int          `json:"team_b_wins"`
	Draws        int          `json:"draws"`
	AGoals       int          `json:"team_a_goals"`
	BGoals       int          `json:"team_b_goals"`
	Rivalry      string       `json:"rivalry,omitempty"`
	ByComp       []CompRecord `json:"by_competition,omitempty"`
	FirstMeeting *Match       `json:"first_meeting,omitempty"`
	LastMeeting  *Match       `json:"last_meeting,omitempty"`
	BiggestA     *Match       `json:"biggest_team_a_win,omitempty"`
	BiggestB     *Match       `json:"biggest_team_b_win,omitempty"`
}

// HeadToHead computes the record between two clubs under a filter.
func (s *Store) HeadToHead(aID, bID string, f MatchFilter) *HeadToHead {
	a, b := s.Teams.Team(aID), s.Teams.Team(bID)
	if a == nil || b == nil {
		return nil
	}
	f.TeamID, f.OpponentID, f.Venue = aID, bID, VenueAny
	limit, offset := f.Limit, f.Offset
	f.Limit, f.Offset = 0, 0
	page := s.FindMatches(f)
	h := &HeadToHead{TeamA: a, TeamB: b, Total: page.Total}
	byComp := map[string]*Record{}
	for _, m := range page.Matches {
		ga, gb := m.GoalsFor(aID), m.GoalsFor(bID)
		h.AGoals += ga
		h.BGoals += gb
		switch {
		case ga > gb:
			h.AWins++
			if h.BiggestA == nil || ga-gb > h.BiggestA.GoalMargin() {
				h.BiggestA = m
			}
		case gb > ga:
			h.BWins++
			if h.BiggestB == nil || gb-ga > h.BiggestB.GoalMargin() {
				h.BiggestB = m
			}
		default:
			h.Draws++
		}
		r := byComp[m.CompetitionID]
		if r == nil {
			r = &Record{TeamID: aID, TeamName: a.Name}
			byComp[m.CompetitionID] = r
		}
		r.Add(m, aID)
		if h.FirstMeeting == nil || m.Date.Before(h.FirstMeeting.Date) {
			h.FirstMeeting = m
		}
		if h.LastMeeting == nil || m.Date.After(h.LastMeeting.Date) {
			h.LastMeeting = m
		}
	}
	for comp, r := range byComp {
		h.ByComp = append(h.ByComp, CompRecord{CompetitionID: comp, Record: *r})
	}
	sortSlice(h.ByComp, func(x, y CompRecord) bool {
		if x.Record.Matches != y.Record.Matches {
			return x.Record.Matches > y.Record.Matches
		}
		return x.CompetitionID < y.CompetitionID // ties must not depend on map order
	})
	if r, ok := RivalryFor(aID, bID); ok {
		h.Rivalry = r.Name
	}
	out := page.Matches
	if offset > 0 {
		if offset >= len(out) {
			out = nil
		} else {
			out = out[offset:]
		}
	}
	if limit > 0 && len(out) > limit {
		out = out[:limit]
	}
	h.Matches = out
	return h
}

// ---------------------------------------------------------------------------
// Aggregates
// ---------------------------------------------------------------------------

// Aggregate holds the summary statistics of a set of matches.
type Aggregate struct {
	Matches        int     `json:"matches"`
	Goals          int     `json:"goals"`
	HomeGoals      int     `json:"home_goals"`
	AwayGoals      int     `json:"away_goals"`
	HomeWins       int     `json:"home_wins"`
	AwayWins       int     `json:"away_wins"`
	Draws          int     `json:"draws"`
	AvgGoals       float64 `json:"avg_goals_per_match"`
	AvgHomeGoals   float64 `json:"avg_home_goals"`
	AvgAwayGoals   float64 `json:"avg_away_goals"`
	HomeWinRate    float64 `json:"home_win_rate"`
	AwayWinRate    float64 `json:"away_win_rate"`
	DrawRate       float64 `json:"draw_rate"`
	BothScoredRate float64 `json:"both_teams_scored_rate"`
	Over25Rate     float64 `json:"over_2_5_goals_rate"`
	CleanSheets    int     `json:"clean_sheets"`
	BiggestMargin  int     `json:"biggest_margin"`
	HighestScoring int     `json:"highest_scoring_match_goals"`
	FirstDate      string  `json:"first_match,omitempty"`
	LastDate       string  `json:"last_match,omitempty"`
}

// Aggregate summarises the matches selected by a filter.
func (s *Store) Aggregate(f MatchFilter) Aggregate {
	f.Limit, f.Offset = 0, 0
	ms := s.FindMatches(f).Matches
	var a Aggregate
	a.Matches = len(ms)
	for _, m := range ms {
		a.Goals += m.TotalGoals()
		a.HomeGoals += m.HomeGoals
		a.AwayGoals += m.AwayGoals
		switch m.Outcome() {
		case HomeWin:
			a.HomeWins++
		case AwayWin:
			a.AwayWins++
		default:
			a.Draws++
		}
		if m.HomeGoals > 0 && m.AwayGoals > 0 {
			a.BothScoredRate++
		}
		if m.TotalGoals() > 2 {
			a.Over25Rate++
		}
		// A goalless draw is two clean sheets, one for each defence.
		if m.AwayGoals == 0 {
			a.CleanSheets++
		}
		if m.HomeGoals == 0 {
			a.CleanSheets++
		}
		if m.GoalMargin() > a.BiggestMargin {
			a.BiggestMargin = m.GoalMargin()
		}
		if m.TotalGoals() > a.HighestScoring {
			a.HighestScoring = m.TotalGoals()
		}
		if a.FirstDate == "" || m.DateString() < a.FirstDate {
			a.FirstDate = m.DateString()
		}
		if m.DateString() > a.LastDate {
			a.LastDate = m.DateString()
		}
	}
	if a.Matches > 0 {
		n := float64(a.Matches)
		a.AvgGoals = round2(float64(a.Goals) / n)
		a.AvgHomeGoals = round2(float64(a.HomeGoals) / n)
		a.AvgAwayGoals = round2(float64(a.AwayGoals) / n)
		a.HomeWinRate = round1(float64(a.HomeWins) * 100 / n)
		a.AwayWinRate = round1(float64(a.AwayWins) * 100 / n)
		a.DrawRate = round1(float64(a.Draws) * 100 / n)
		a.BothScoredRate = round1(a.BothScoredRate * 100 / n)
		a.Over25Rate = round1(a.Over25Rate * 100 / n)
	}
	return a
}

// TeamRecords builds a record for every club matching a filter, ranked by the
// requested metric.
//
// metric: points | win_rate | wins | goals_for | goals_against | goal_diff
func (s *Store) TeamRecords(f MatchFilter, metric string, minMatches, limit int) []Record {
	f.Limit, f.Offset = 0, 0
	teamID := f.TeamID
	f.TeamID = ""
	ms := s.FindMatches(f).Matches
	byTeam := map[string]*Record{}
	touch := func(id string) *Record {
		r := byTeam[id]
		if r == nil {
			name := id
			if t := s.Teams.Team(id); t != nil {
				name = t.Name
			}
			r = &Record{TeamID: id, TeamName: name}
			byTeam[id] = r
		}
		return r
	}
	for _, m := range ms {
		if teamID != "" && !m.Involves(teamID) {
			continue
		}
		switch f.Venue {
		case VenueHome:
			touch(m.HomeTeamID).Add(m, m.HomeTeamID)
		case VenueAway:
			touch(m.AwayTeamID).Add(m, m.AwayTeamID)
		default:
			touch(m.HomeTeamID).Add(m, m.HomeTeamID)
			touch(m.AwayTeamID).Add(m, m.AwayTeamID)
		}
	}
	out := make([]Record, 0, len(byTeam))
	for _, r := range byTeam {
		if r.Matches >= minMatches {
			out = append(out, *r)
		}
	}
	less := func(a, b Record) bool {
		switch metric {
		case "win_rate":
			if a.WinRate() != b.WinRate() {
				return a.WinRate() > b.WinRate()
			}
			return a.Wins > b.Wins
		case "wins":
			return a.Wins > b.Wins
		case "goals_for":
			return a.GoalsFor > b.GoalsFor
		case "goals_against":
			return a.GoalsAgainst < b.GoalsAgainst
		case "goal_diff":
			return a.GoalDiff() > b.GoalDiff()
		case "points_per_match":
			return a.PointsPerMatch() > b.PointsPerMatch()
		default: // points
			if a.Points() != b.Points() {
				return a.Points() > b.Points()
			}
			return a.GoalDiff() > b.GoalDiff()
		}
	}
	sortSlice(out, func(a, b Record) bool {
		if less(a, b) != less(b, a) {
			return less(a, b)
		}
		return Fold(a.TeamName) < Fold(b.TeamName)
	})
	if limit > 0 && len(out) > limit {
		out = out[:limit]
	}
	return out
}

// BiggestWins returns the largest margins matching a filter.
func (s *Store) BiggestWins(f MatchFilter, limit int) []*Match {
	f.Limit, f.Offset = 0, 0
	f.Sort = "margin_desc"
	ms := s.FindMatches(f).Matches
	if limit > 0 && len(ms) > limit {
		ms = ms[:limit]
	}
	return ms
}

// HighestScoring returns the matches with the most goals.
func (s *Store) HighestScoring(f MatchFilter, limit int) []*Match {
	f.Limit, f.Offset = 0, 0
	f.Sort = "goals_desc"
	ms := s.FindMatches(f).Matches
	if limit > 0 && len(ms) > limit {
		ms = ms[:limit]
	}
	return ms
}

// SeasonComparison compares aggregates across seasons.
type SeasonComparison struct {
	CompetitionID string             `json:"competition"`
	Seasons       []int              `json:"seasons"`
	Aggregates    map[int]Aggregate  `json:"aggregates"`
	Champions     map[int]string     `json:"champions,omitempty"`
	TopScorers    map[int]Record     `json:"top_scoring_team,omitempty"`
	Standings     map[int]*Standings `json:"-"`
}

// CompareSeasons builds a side-by-side comparison of several seasons.
func (s *Store) CompareSeasons(comp string, seasons []int) *SeasonComparison {
	c := &SeasonComparison{
		CompetitionID: comp,
		Aggregates:    map[int]Aggregate{},
		Champions:     map[int]string{},
		TopScorers:    map[int]Record{},
		Standings:     map[int]*Standings{},
	}
	seen := map[int]bool{}
	for _, season := range seasons {
		if seen[season] || len(s.SeasonMatches(comp, season)) == 0 {
			continue
		}
		seen[season] = true
		c.Seasons = append(c.Seasons, season)
		c.Aggregates[season] = s.Aggregate(MatchFilter{CompetitionID: comp, Season: season})
		table := s.Standings(comp, season, StandingsOptions{})
		c.Standings[season] = table
		if table.Champion != "" {
			c.Champions[season] = table.Champion
		}
		if best := s.TeamRecords(MatchFilter{CompetitionID: comp, Season: season}, "goals_for", 0, 1); len(best) > 0 {
			c.TopScorers[season] = best[0]
		}
	}
	sort.Ints(c.Seasons)
	return c
}

// DerbyMatch pairs a match with the derby it belongs to.
type DerbyMatch struct {
	Match   *Match  `json:"match"`
	Rivalry Rivalry `json:"rivalry"`
}

// Derbies returns matches between traditional rivals.
func (s *Store) Derbies(f MatchFilter, rivalryName string, limit int) []DerbyMatch {
	f.Limit, f.Offset = 0, 0
	ms := s.FindMatches(f).Matches
	var out []DerbyMatch
	for _, m := range ms {
		r, ok := RivalryFor(m.HomeTeamID, m.AwayTeamID)
		if !ok {
			continue
		}
		if rivalryName != "" && Fold(r.Name) != Fold(rivalryName) {
			continue
		}
		out = append(out, DerbyMatch{Match: m, Rivalry: r})
	}
	if limit > 0 && len(out) > limit {
		out = out[:limit]
	}
	return out
}

// standings cache guards, kept out of Store's literal for clarity.
type standingsCacheFields struct {
	standingsMu    sync.Mutex
	standingsOnce  sync.Once
	standingsCache map[compSeason]*Standings
}
