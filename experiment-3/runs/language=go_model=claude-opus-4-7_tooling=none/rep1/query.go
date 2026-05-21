// Query layer: all soccer questions (matches, head-to-head, team stats,
// standings, aggregate statistics, player search) are answered here over the
// canonical match set and the player list.
package main

import (
	"sort"
	"strings"
	"time"
)

// competitionMatches reports whether a competition name satisfies a free text
// query, accent- and case-insensitively.
func competitionMatches(competition, query string) bool {
	q := strings.TrimSpace(query)
	if q == "" {
		return true
	}
	return strings.Contains(stripAccents(strings.ToLower(competition)),
		stripAccents(strings.ToLower(q)))
}

// sortMatchesByDateDesc orders matches newest first; undated matches sink to
// the bottom.
func sortMatchesByDateDesc(matches []Match) {
	sort.SliceStable(matches, func(i, j int) bool {
		a, b := matches[i], matches[j]
		if a.HasDate != b.HasDate {
			return a.HasDate
		}
		if a.HasDate && !a.Date.Equal(b.Date) {
			return a.Date.After(b.Date)
		}
		return false
	})
}

// MatchFilter describes the criteria for FindMatches.
type MatchFilter struct {
	Team        string
	Opponent    string
	Competition string
	Season      int
	HasSeason   bool
	Venue       string // "home", "away" or "" / "any"
	DateFrom    time.Time
	DateTo      time.Time
}

// FindMatches returns the canonical matches satisfying the filter, newest
// first.
func (db *DB) FindMatches(f MatchFilter) []Match {
	venue := strings.ToLower(strings.TrimSpace(f.Venue))
	out := make([]Match, 0, 64)
	for _, m := range db.Matches {
		if f.HasSeason && m.Season != f.Season {
			continue
		}
		if !competitionMatches(m.Competition, f.Competition) {
			continue
		}
		if !f.DateFrom.IsZero() && (!m.HasDate || m.Date.Before(f.DateFrom)) {
			continue
		}
		if !f.DateTo.IsZero() && (!m.HasDate || m.Date.After(f.DateTo)) {
			continue
		}
		if !matchHasTeams(m, f.Team, f.Opponent, venue) {
			continue
		}
		out = append(out, m)
	}
	sortMatchesByDateDesc(out)
	return out
}

// matchHasTeams applies the team/opponent/venue part of a match filter.
func matchHasTeams(m Match, team, opponent, venue string) bool {
	homeTeam := identityMatches(m.HomeID, team)
	awayTeam := identityMatches(m.AwayID, team)
	if team != "" && !homeTeam && !awayTeam {
		return false
	}
	switch venue {
	case "home":
		if team != "" && !homeTeam {
			return false
		}
		awayTeam = false
	case "away":
		if team != "" && !awayTeam {
			return false
		}
		homeTeam = false
	}
	if opponent == "" {
		return true
	}
	homeOpp := identityMatches(m.HomeID, opponent)
	awayOpp := identityMatches(m.AwayID, opponent)
	// team at home requires opponent away, and vice versa.
	return (homeTeam && awayOpp) || (awayTeam && homeOpp)
}

// H2H holds a head-to-head record between two teams.
type H2H struct {
	TeamA, TeamB string
	AWins        int
	BWins        int
	Draws        int
	AGoals       int
	BGoals       int
	Matches      []Match
}

// HeadToHead computes the record of teamA against teamB, optionally restricted
// to a competition and/or season.
func (db *DB) HeadToHead(teamA, teamB, competition string, season int, hasSeason bool) H2H {
	h := H2H{
		TeamA: db.DisplayName(parseTeamIdentity(teamA).groupKey(), cleanTeamName(teamA)),
		TeamB: db.DisplayName(parseTeamIdentity(teamB).groupKey(), cleanTeamName(teamB)),
	}
	for _, m := range db.Matches {
		if hasSeason && m.Season != season {
			continue
		}
		if !competitionMatches(m.Competition, competition) {
			continue
		}
		aHome := identityMatches(m.HomeID, teamA)
		aAway := identityMatches(m.AwayID, teamA)
		bHome := identityMatches(m.HomeID, teamB)
		bAway := identityMatches(m.AwayID, teamB)
		if !((aHome && bAway) || (bHome && aAway)) {
			continue
		}
		h.Matches = append(h.Matches, m)
		if !m.HasScore {
			continue
		}
		var aGoals, bGoals int
		if aHome {
			aGoals, bGoals = m.HomeGoal, m.AwayGoal
		} else {
			aGoals, bGoals = m.AwayGoal, m.HomeGoal
		}
		h.AGoals += aGoals
		h.BGoals += bGoals
		switch {
		case aGoals > bGoals:
			h.AWins++
		case bGoals > aGoals:
			h.BWins++
		default:
			h.Draws++
		}
	}
	sortMatchesByDateDesc(h.Matches)
	return h
}

// TeamStats summarizes a team's record for a scope of matches.
type TeamStats struct {
	Team        string
	Competition string
	Season      int
	HasSeason   bool
	Venue       string
	Played      int
	Wins        int
	Draws       int
	Losses      int
	GoalsFor    int
	GoalsAgst   int
}

// Points returns league points (3 per win, 1 per draw).
func (s TeamStats) Points() int { return s.Wins*3 + s.Draws }

// WinRate returns the fraction of matches won, as a percentage.
func (s TeamStats) WinRate() float64 {
	if s.Played == 0 {
		return 0
	}
	return 100 * float64(s.Wins) / float64(s.Played)
}

// ComputeTeamStats aggregates a team's results, optionally filtered by
// competition, season and venue.
func (db *DB) ComputeTeamStats(team, competition string, season int, hasSeason bool, venue string) TeamStats {
	venue = strings.ToLower(strings.TrimSpace(venue))
	key := parseTeamIdentity(team).groupKey()
	s := TeamStats{
		Team:        db.DisplayName(key, cleanTeamName(team)),
		Competition: competition,
		Season:      season,
		HasSeason:   hasSeason,
		Venue:       venue,
	}
	for _, m := range db.Matches {
		if hasSeason && m.Season != season {
			continue
		}
		if !competitionMatches(m.Competition, competition) {
			continue
		}
		isHome := identityMatches(m.HomeID, team)
		isAway := identityMatches(m.AwayID, team)
		if !isHome && !isAway {
			continue
		}
		if venue == "home" && !isHome {
			continue
		}
		if venue == "away" && !isAway {
			continue
		}
		if !m.HasScore {
			continue
		}
		var gf, ga int
		if isHome {
			gf, ga = m.HomeGoal, m.AwayGoal
		} else {
			gf, ga = m.AwayGoal, m.HomeGoal
		}
		s.Played++
		s.GoalsFor += gf
		s.GoalsAgst += ga
		switch {
		case gf > ga:
			s.Wins++
		case ga > gf:
			s.Losses++
		default:
			s.Draws++
		}
	}
	return s
}

// TableRow is one line of a calculated league table.
type TableRow struct {
	Team      string
	Played    int
	Wins      int
	Draws     int
	Losses    int
	GoalsFor  int
	GoalsAgst int
}

// Points returns league points for the row.
func (r TableRow) Points() int { return r.Wins*3 + r.Draws }

// GoalDiff returns the goal difference for the row.
func (r TableRow) GoalDiff() int { return r.GoalsFor - r.GoalsAgst }

// Standings calculates a full league table for a single competition and season
// from match results. competition must be an exact canonical competition name
// (see resolveCompetition) so that, e.g., Série A and Série B are not mixed.
func (db *DB) Standings(competition string, season int) []TableRow {
	rows := map[string]*TableRow{}
	get := func(key, display string) *TableRow {
		if r, ok := rows[key]; ok {
			return r
		}
		r := &TableRow{Team: db.DisplayName(key, display)}
		rows[key] = r
		return r
	}
	for _, m := range db.Matches {
		if m.Season != season || m.Competition != competition {
			continue
		}
		if !m.HasScore {
			continue
		}
		home := get(m.HomeID.groupKey(), m.HomeTeam)
		away := get(m.AwayID.groupKey(), m.AwayTeam)
		home.Played++
		away.Played++
		home.GoalsFor += m.HomeGoal
		home.GoalsAgst += m.AwayGoal
		away.GoalsFor += m.AwayGoal
		away.GoalsAgst += m.HomeGoal
		switch {
		case m.HomeGoal > m.AwayGoal:
			home.Wins++
			away.Losses++
		case m.AwayGoal > m.HomeGoal:
			away.Wins++
			home.Losses++
		default:
			home.Draws++
			away.Draws++
		}
	}
	table := make([]TableRow, 0, len(rows))
	for _, r := range rows {
		table = append(table, *r)
	}
	sort.SliceStable(table, func(i, j int) bool {
		a, b := table[i], table[j]
		if a.Points() != b.Points() {
			return a.Points() > b.Points()
		}
		if a.Wins != b.Wins {
			return a.Wins > b.Wins
		}
		if a.GoalDiff() != b.GoalDiff() {
			return a.GoalDiff() > b.GoalDiff()
		}
		if a.GoalsFor != b.GoalsFor {
			return a.GoalsFor > b.GoalsFor
		}
		return a.Team < b.Team
	})
	return table
}

// AggStats holds aggregate statistics over a set of matches.
type AggStats struct {
	Competition string
	Season      int
	HasSeason   bool
	Matches     int
	Scored      int // matches with a recorded score
	TotalGoals  int
	HomeWins    int
	AwayWins    int
	Draws       int
	BiggestWins []Match
}

// AvgGoals returns the mean goals per scored match.
func (a AggStats) AvgGoals() float64 {
	if a.Scored == 0 {
		return 0
	}
	return float64(a.TotalGoals) / float64(a.Scored)
}

// HomeWinRate returns the percentage of scored matches won by the home team.
func (a AggStats) HomeWinRate() float64 {
	if a.Scored == 0 {
		return 0
	}
	return 100 * float64(a.HomeWins) / float64(a.Scored)
}

// AwayWinRate returns the percentage of scored matches won by the away team.
func (a AggStats) AwayWinRate() float64 {
	if a.Scored == 0 {
		return 0
	}
	return 100 * float64(a.AwayWins) / float64(a.Scored)
}

// DrawRate returns the percentage of scored matches that were drawn.
func (a AggStats) DrawRate() float64 {
	if a.Scored == 0 {
		return 0
	}
	return 100 * float64(a.Draws) / float64(a.Scored)
}

// ComputeAggStats computes aggregate statistics, optionally scoped to a
// competition and season. topN controls how many biggest wins are kept.
func (db *DB) ComputeAggStats(competition string, season int, hasSeason bool, topN int) AggStats {
	if topN <= 0 {
		topN = 5
	}
	a := AggStats{Competition: competition, Season: season, HasSeason: hasSeason}
	scored := make([]Match, 0, 256)
	for _, m := range db.Matches {
		if hasSeason && m.Season != season {
			continue
		}
		if !competitionMatches(m.Competition, competition) {
			continue
		}
		a.Matches++
		if !m.HasScore {
			continue
		}
		a.Scored++
		a.TotalGoals += m.HomeGoal + m.AwayGoal
		switch {
		case m.HomeGoal > m.AwayGoal:
			a.HomeWins++
		case m.AwayGoal > m.HomeGoal:
			a.AwayWins++
		default:
			a.Draws++
		}
		scored = append(scored, m)
	}
	sort.SliceStable(scored, func(i, j int) bool {
		if scored[i].GoalMargin() != scored[j].GoalMargin() {
			return scored[i].GoalMargin() > scored[j].GoalMargin()
		}
		gi := scored[i].HomeGoal + scored[i].AwayGoal
		gj := scored[j].HomeGoal + scored[j].AwayGoal
		return gi > gj
	})
	if len(scored) > topN {
		scored = scored[:topN]
	}
	a.BiggestWins = scored
	return a
}

// PlayerFilter describes a player search.
type PlayerFilter struct {
	Name        string
	Nationality string
	Club        string
	Position    string
	MinOverall  int
	SortBy      string // overall, potential, age, name
	Limit       int
}

// SearchPlayers returns players matching the filter, sorted as requested.
func (db *DB) SearchPlayers(f PlayerFilter) []Player {
	contains := func(haystack, needle string) bool {
		if needle == "" {
			return true
		}
		return strings.Contains(stripAccents(strings.ToLower(haystack)),
			stripAccents(strings.ToLower(needle)))
	}
	out := make([]Player, 0, 64)
	for _, p := range db.Players {
		if !contains(p.Name, f.Name) {
			continue
		}
		if !contains(p.Nationality, f.Nationality) {
			continue
		}
		if !contains(p.Club, f.Club) {
			continue
		}
		if !contains(p.Position, f.Position) {
			continue
		}
		if p.Overall < f.MinOverall {
			continue
		}
		out = append(out, p)
	}
	sort.SliceStable(out, func(i, j int) bool {
		a, b := out[i], out[j]
		switch strings.ToLower(f.SortBy) {
		case "potential":
			if a.Potential != b.Potential {
				return a.Potential > b.Potential
			}
		case "age":
			if a.Age != b.Age {
				return a.Age < b.Age
			}
		case "name":
			return a.Name < b.Name
		default: // overall
			if a.Overall != b.Overall {
				return a.Overall > b.Overall
			}
		}
		return a.Name < b.Name
	})
	if f.Limit > 0 && len(out) > f.Limit {
		out = out[:f.Limit]
	}
	return out
}

// CompetitionInfo summarizes one competition in the dataset.
type CompetitionInfo struct {
	Name      string
	Matches   int
	MinSeason int
	MaxSeason int
	Seasons   []int
}

// Competitions lists every competition in the canonical match set.
func (db *DB) Competitions() []CompetitionInfo {
	byName := map[string][]Match{}
	for _, m := range db.Matches {
		byName[m.Competition] = append(byName[m.Competition], m)
	}
	out := make([]CompetitionInfo, 0, len(byName))
	for name, matches := range byName {
		seasons := seasonsOf(matches)
		info := CompetitionInfo{Name: name, Matches: len(matches), Seasons: seasons}
		if len(seasons) > 0 {
			info.MinSeason = seasons[0]
			info.MaxSeason = seasons[len(seasons)-1]
		}
		out = append(out, info)
	}
	sort.SliceStable(out, func(i, j int) bool {
		if out[i].Matches != out[j].Matches {
			return out[i].Matches > out[j].Matches
		}
		return out[i].Name < out[j].Name
	})
	return out
}
