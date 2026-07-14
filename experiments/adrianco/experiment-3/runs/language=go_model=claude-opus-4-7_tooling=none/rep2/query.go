// query.go contains the pure query/aggregation logic over the DataStore:
// match search, team records, head-to-head, player search, standings and
// competition-wide statistics. None of this code touches the MCP transport,
// which keeps it straightforward to unit test.
package main

import (
	"sort"
	"strings"
	"time"
)

// MatchFilter describes the criteria for FindMatches.
type MatchFilter struct {
	Team        string // matches the home or away team (see Venue)
	Opponent    string // restricts the other side of the fixture
	Competition string
	Season      int
	Venue       string // "home", "away" or "" / "any"
	DateFrom    time.Time
	DateTo      time.Time
	HasDateFrom bool
	HasDateTo   bool
}

// canonicalCompetition maps a free-text competition query onto one of the
// known competition names. The second return value reports whether the query
// was recognised; an unrecognised query falls back to loose substring matching.
func canonicalCompetition(query string) (string, bool) {
	n := normalizeText(query)
	switch {
	case n == "":
		return "", false
	case strings.Contains(n, "serie b"), strings.Contains(n, "segunda"):
		return "Brasileirão Série B", true
	case strings.Contains(n, "serie c"), strings.Contains(n, "terceira"):
		return "Brasileirão Série C", true
	case strings.Contains(n, "libertadores"):
		return "Copa Libertadores", true
	case strings.Contains(n, "copa do brasil"), strings.Contains(n, "brazilian cup"), n == "cup":
		return "Copa do Brasil", true
	case strings.Contains(n, "brasileir"), strings.Contains(n, "serie a"),
		strings.Contains(n, "campeonato brasileiro"):
		return "Brasileirão Série A", true
	}
	return query, false
}

// competitionMatches reports whether a match's competition satisfies the query.
// A recognised competition name must match exactly so that, for example,
// "Brasileirão" does not also pull in Série B and Série C results.
func competitionMatches(matchComp, query string) bool {
	if strings.TrimSpace(query) == "" {
		return true
	}
	if canon, ok := canonicalCompetition(query); ok {
		return matchComp == canon
	}
	return strings.Contains(normalizeText(matchComp), normalizeText(query))
}

// teamSideMatches reports whether team key tk satisfies the requested key/venue.
func (f MatchFilter) teamSideMatches(m Match) bool {
	if f.Team == "" {
		return true
	}
	want := normalizeTeamKey(f.Team)
	switch f.Venue {
	case "home":
		return strings.Contains(m.HomeKey, want)
	case "away":
		return strings.Contains(m.AwayKey, want)
	default:
		return strings.Contains(m.HomeKey, want) || strings.Contains(m.AwayKey, want)
	}
}

// opponentMatches reports whether the opponent filter is satisfied.
func (f MatchFilter) opponentMatches(m Match) bool {
	if f.Opponent == "" {
		return true
	}
	want := normalizeTeamKey(f.Opponent)
	return strings.Contains(m.HomeKey, want) || strings.Contains(m.AwayKey, want)
}

// FindMatches returns every match satisfying the filter, newest first.
func FindMatches(store *DataStore, f MatchFilter) []Match {
	var out []Match
	for _, m := range store.Matches {
		if !f.teamSideMatches(m) || !f.opponentMatches(m) {
			continue
		}
		if !competitionMatches(m.Competition, f.Competition) {
			continue
		}
		if f.Season != 0 && m.Season != f.Season {
			continue
		}
		if f.HasDateFrom && (!m.HasDate || m.Date.Before(f.DateFrom)) {
			continue
		}
		if f.HasDateTo && (!m.HasDate || m.Date.After(f.DateTo)) {
			continue
		}
		out = append(out, m)
	}
	sortMatchesByDateDesc(out)
	return out
}

// sortMatchesByDateDesc orders matches newest-first, dated before undated.
func sortMatchesByDateDesc(ms []Match) {
	sort.SliceStable(ms, func(i, j int) bool {
		a, b := ms[i], ms[j]
		if a.HasDate != b.HasDate {
			return a.HasDate
		}
		if a.HasDate && !a.Date.Equal(b.Date) {
			return a.Date.After(b.Date)
		}
		return a.Season > b.Season
	})
}

// TeamRecord is an aggregate win/draw/loss and goal summary for one team.
type TeamRecord struct {
	Team         string
	Played       int
	Wins         int
	Draws        int
	Losses       int
	GoalsFor     int
	GoalsAgainst int
}

// Points returns league points (3 per win, 1 per draw).
func (r TeamRecord) Points() int { return r.Wins*3 + r.Draws }

// GoalDifference returns goals for minus goals against.
func (r TeamRecord) GoalDifference() int { return r.GoalsFor - r.GoalsAgainst }

// WinRate returns the win percentage (0-100).
func (r TeamRecord) WinRate() float64 {
	if r.Played == 0 {
		return 0
	}
	return float64(r.Wins) * 100 / float64(r.Played)
}

// add folds one match into the record from the perspective of the given side.
func (r *TeamRecord) add(m Match, side string) {
	if !m.HasScore {
		return
	}
	r.Played++
	var gf, ga int
	if side == "home" {
		gf, ga = m.HomeGoal, m.AwayGoal
	} else {
		gf, ga = m.AwayGoal, m.HomeGoal
	}
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

// resolveTeamName returns the most frequent display name for a normalized key
// across the supplied matches, so output uses real-world spelling.
func resolveTeamName(matches []Match, key string) string {
	counts := map[string]int{}
	for _, m := range matches {
		if strings.Contains(m.HomeKey, key) {
			counts[m.HomeTeam]++
		}
		if strings.Contains(m.AwayKey, key) {
			counts[m.AwayTeam]++
		}
	}
	best, bestN := "", 0
	for name, n := range counts {
		if n > bestN {
			best, bestN = name, n
		}
	}
	return best
}

// ComputeTeamRecord aggregates a team's matches subject to filter + venue.
func ComputeTeamRecord(store *DataStore, f MatchFilter) TeamRecord {
	key := normalizeTeamKey(f.Team)
	matches := FindMatches(store, f)
	rec := TeamRecord{Team: resolveTeamName(matches, key)}
	if rec.Team == "" {
		rec.Team = f.Team
	}
	for _, m := range matches {
		isHome := strings.Contains(m.HomeKey, key)
		isAway := strings.Contains(m.AwayKey, key)
		switch f.Venue {
		case "home":
			if isHome {
				rec.add(m, "home")
			}
		case "away":
			if isAway {
				rec.add(m, "away")
			}
		default:
			if isHome {
				rec.add(m, "home")
			} else if isAway {
				rec.add(m, "away")
			}
		}
	}
	return rec
}

// H2HResult captures a head-to-head summary between two teams.
type H2HResult struct {
	Team1, Team2 string
	Team1Wins    int
	Team2Wins    int
	Draws        int
	Team1Goals   int
	Team2Goals   int
	Matches      []Match
}

// HeadToHead computes the all-time record between two teams.
func HeadToHead(store *DataStore, team1, team2, competition string) H2HResult {
	k1 := normalizeTeamKey(team1)
	k2 := normalizeTeamKey(team2)
	res := H2HResult{}
	matches := FindMatches(store, MatchFilter{Team: team1, Opponent: team2, Competition: competition})
	for _, m := range matches {
		// Determine which side is team1.
		var t1Home bool
		switch {
		case strings.Contains(m.HomeKey, k1) && strings.Contains(m.AwayKey, k2):
			t1Home = true
		case strings.Contains(m.AwayKey, k1) && strings.Contains(m.HomeKey, k2):
			t1Home = false
		default:
			continue
		}
		res.Matches = append(res.Matches, m)
		if !m.HasScore {
			continue
		}
		var g1, g2 int
		if t1Home {
			g1, g2 = m.HomeGoal, m.AwayGoal
		} else {
			g1, g2 = m.AwayGoal, m.HomeGoal
		}
		res.Team1Goals += g1
		res.Team2Goals += g2
		switch {
		case g1 > g2:
			res.Team1Wins++
		case g2 > g1:
			res.Team2Wins++
		default:
			res.Draws++
		}
	}
	res.Team1 = resolveTeamName(res.Matches, k1)
	res.Team2 = resolveTeamName(res.Matches, k2)
	if res.Team1 == "" {
		res.Team1 = team1
	}
	if res.Team2 == "" {
		res.Team2 = team2
	}
	return res
}

// PlayerFilter describes the criteria for SearchPlayers.
type PlayerFilter struct {
	Name        string
	Nationality string
	Club        string
	Position    string
	MinOverall  int
}

// SearchPlayers returns players matching the filter, sorted by overall rating.
func SearchPlayers(store *DataStore, f PlayerFilter) []Player {
	name := normalizeText(f.Name)
	nat := normalizeText(f.Nationality)
	pos := normalizeText(f.Position)
	clubKey := normalizeTeamKey(f.Club)

	var out []Player
	for _, p := range store.Players {
		if name != "" && !strings.Contains(normalizeText(p.Name), name) {
			continue
		}
		if nat != "" && !strings.Contains(normalizeText(p.Nationality), nat) {
			continue
		}
		if pos != "" && !strings.EqualFold(normalizeText(p.Position), pos) {
			continue
		}
		if clubKey != "" && !strings.Contains(p.ClubKey, clubKey) {
			continue
		}
		if f.MinOverall != 0 && p.Overall < f.MinOverall {
			continue
		}
		out = append(out, p)
	}
	sort.SliceStable(out, func(i, j int) bool {
		if out[i].Overall != out[j].Overall {
			return out[i].Overall > out[j].Overall
		}
		return out[i].Name < out[j].Name
	})
	return out
}

// StandingRow is one ranked line of a calculated league table.
type StandingRow struct {
	Rank int
	TeamRecord
}

// Standings calculates a league table for a competition/season from match
// results (fixtures are de-duplicated across datasets at load time).
func Standings(store *DataStore, competition string, season int) []StandingRow {
	var chosen []Match
	for _, m := range store.Matches {
		if !competitionMatches(m.Competition, competition) {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}
		if !m.HasScore {
			continue
		}
		chosen = append(chosen, m)
	}

	records := map[string]*TeamRecord{}
	get := func(key, name string) *TeamRecord {
		r := records[key]
		if r == nil {
			r = &TeamRecord{Team: name}
			records[key] = r
		}
		return r
	}
	for _, m := range chosen {
		get(m.HomeKey, m.HomeTeam).add(m, "home")
		get(m.AwayKey, m.AwayTeam).add(m, "away")
	}

	rows := make([]StandingRow, 0, len(records))
	for _, r := range records {
		rows = append(rows, StandingRow{TeamRecord: *r})
	}
	sort.SliceStable(rows, func(i, j int) bool {
		a, b := rows[i], rows[j]
		if a.Points() != b.Points() {
			return a.Points() > b.Points()
		}
		if a.Wins != b.Wins {
			return a.Wins > b.Wins
		}
		if a.GoalDifference() != b.GoalDifference() {
			return a.GoalDifference() > b.GoalDifference()
		}
		if a.GoalsFor != b.GoalsFor {
			return a.GoalsFor > b.GoalsFor
		}
		return a.Team < b.Team
	})
	for i := range rows {
		rows[i].Rank = i + 1
	}
	return rows
}

// CompetitionStats summarises aggregate numbers for a set of matches.
type CompetitionStats struct {
	Matches     int
	TotalGoals  int
	HomeWins    int
	AwayWins    int
	Draws       int
	BiggestWins []Match
	SeasonLow   int
	SeasonHigh  int
}

// AvgGoals returns mean goals per match.
func (c CompetitionStats) AvgGoals() float64 {
	if c.Matches == 0 {
		return 0
	}
	return float64(c.TotalGoals) / float64(c.Matches)
}

// HomeWinRate returns the home-win percentage (0-100).
func (c CompetitionStats) HomeWinRate() float64 {
	if c.Matches == 0 {
		return 0
	}
	return float64(c.HomeWins) * 100 / float64(c.Matches)
}

// ComputeCompetitionStats aggregates stats over matches passing the filter.
func ComputeCompetitionStats(store *DataStore, f MatchFilter) CompetitionStats {
	matches := FindMatches(store, f)
	stats := CompetitionStats{}
	for _, m := range matches {
		if !m.HasScore {
			continue
		}
		stats.Matches++
		stats.TotalGoals += m.HomeGoal + m.AwayGoal
		switch m.Outcome() {
		case "home":
			stats.HomeWins++
		case "away":
			stats.AwayWins++
		default:
			stats.Draws++
		}
		if m.Season > 0 {
			if stats.SeasonLow == 0 || m.Season < stats.SeasonLow {
				stats.SeasonLow = m.Season
			}
			if m.Season > stats.SeasonHigh {
				stats.SeasonHigh = m.Season
			}
		}
	}
	scored := make([]Match, 0, len(matches))
	for _, m := range matches {
		if m.HasScore {
			scored = append(scored, m)
		}
	}
	sort.SliceStable(scored, func(i, j int) bool {
		return scored[i].GoalMargin() > scored[j].GoalMargin()
	})
	if len(scored) > 5 {
		scored = scored[:5]
	}
	stats.BiggestWins = scored
	return stats
}
