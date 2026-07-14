package soccer

import (
	"sort"
	"strings"
)

// MatchFilter holds search criteria for finding matches.
type MatchFilter struct {
	Team        string // either home or away (normalized match)
	Team1       string // must appear as either team
	Team2       string // must appear as either team (used with Team1)
	HomeTeam    string
	AwayTeam    string
	Season      int    // 0 = all seasons
	Competition string // "" = all competitions
	Limit       int    // 0 = default 20
}

// FindMatches returns matches matching the filter.
func (s *Store) FindMatches(f MatchFilter) []Match {
	limit := f.Limit
	if limit <= 0 {
		limit = 20
	}

	var results []Match
	for _, m := range s.Matches {
		if !matchPassesFilter(m, f) {
			continue
		}
		results = append(results, m)
		if len(results) >= limit {
			break
		}
	}
	return results
}

func matchPassesFilter(m Match, f MatchFilter) bool {
	// Competition filter
	if f.Competition != "" {
		if !strings.EqualFold(m.Competition, f.Competition) {
			return false
		}
	}
	// Season filter
	if f.Season != 0 && m.Season != f.Season {
		return false
	}
	// HomeTeam filter (exact normalized)
	if f.HomeTeam != "" && !TeamsMatch(m.HomeTeam, f.HomeTeam) {
		return false
	}
	// AwayTeam filter (exact normalized)
	if f.AwayTeam != "" && !TeamsMatch(m.AwayTeam, f.AwayTeam) {
		return false
	}
	// Team1 + Team2: both must appear in the match
	if f.Team1 != "" && f.Team2 != "" {
		home1 := TeamsMatch(m.HomeTeam, f.Team1)
		away1 := TeamsMatch(m.AwayTeam, f.Team1)
		home2 := TeamsMatch(m.HomeTeam, f.Team2)
		away2 := TeamsMatch(m.AwayTeam, f.Team2)
		team1Present := home1 || away1
		team2Present := home2 || away2
		if !team1Present || !team2Present {
			return false
		}
		// Make sure they're different teams in the match
		if (home1 && home2) || (away1 && away2) {
			return false
		}
		return true
	}
	// Single team filter: team appears anywhere
	if f.Team != "" {
		if !TeamMatchesSearch(m.HomeTeam, f.Team) && !TeamMatchesSearch(m.AwayTeam, f.Team) {
			return false
		}
	}
	return true
}

// GetTeamStats returns aggregated stats for a team.
func (s *Store) GetTeamStats(team, competition string, season int) TeamStats {
	stats := TeamStats{
		Team:        team,
		Competition: competition,
		Season:      season,
	}
	for _, m := range s.Matches {
		if competition != "" && !strings.EqualFold(m.Competition, competition) {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}
		isHome := TeamMatchesSearch(m.HomeTeam, team)
		isAway := TeamMatchesSearch(m.AwayTeam, team)
		if !isHome && !isAway {
			continue
		}
		stats.Matches++
		var gf, ga int
		if isHome {
			gf, ga = m.HomeGoals, m.AwayGoals
		} else {
			gf, ga = m.AwayGoals, m.HomeGoals
		}
		stats.GoalsFor += gf
		stats.GoalsAgainst += ga
		switch {
		case gf > ga:
			stats.Wins++
		case gf == ga:
			stats.Draws++
		default:
			stats.Losses++
		}
	}
	return stats
}

// GetStandings returns a sorted league table for a given season and competition.
func (s *Store) GetStandings(season int, competition string) []StandingEntry {
	if competition == "" {
		competition = "brasileirao"
	}
	// Use a map keyed by normalized team name
	type row struct {
		displayName  string
		played       int
		won          int
		drawn        int
		lost         int
		goalsFor     int
		goalsAgainst int
	}
	table := make(map[string]*row)

	ensureRow := func(normalName, displayName string) {
		if _, ok := table[normalName]; !ok {
			table[normalName] = &row{displayName: displayName}
		}
	}

	for _, m := range s.Matches {
		if !strings.EqualFold(m.Competition, competition) {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}
		hn := NormalizeTeamName(m.HomeTeam)
		an := NormalizeTeamName(m.AwayTeam)
		ensureRow(hn, m.HomeTeam)
		ensureRow(an, m.AwayTeam)

		hr := table[hn]
		ar := table[an]
		hr.played++
		ar.played++
		hr.goalsFor += m.HomeGoals
		hr.goalsAgainst += m.AwayGoals
		ar.goalsFor += m.AwayGoals
		ar.goalsAgainst += m.HomeGoals

		switch {
		case m.HomeGoals > m.AwayGoals:
			hr.won++
			ar.lost++
		case m.HomeGoals == m.AwayGoals:
			hr.drawn++
			ar.drawn++
		default:
			hr.lost++
			ar.won++
		}
	}

	entries := make([]StandingEntry, 0, len(table))
	for _, r := range table {
		gd := r.goalsFor - r.goalsAgainst
		pts := r.won*3 + r.drawn
		// Prefer cleanest display name (shortest / without state suffix)
		dn := cleanDisplayName(r.displayName)
		entries = append(entries, StandingEntry{
			Team:         dn,
			Played:       r.played,
			Won:          r.won,
			Drawn:        r.drawn,
			Lost:         r.lost,
			GoalsFor:     r.goalsFor,
			GoalsAgainst: r.goalsAgainst,
			GoalDiff:     gd,
			Points:       pts,
		})
	}

	sort.Slice(entries, func(i, j int) bool {
		if entries[i].Points != entries[j].Points {
			return entries[i].Points > entries[j].Points
		}
		if entries[i].GoalDiff != entries[j].GoalDiff {
			return entries[i].GoalDiff > entries[j].GoalDiff
		}
		if entries[i].GoalsFor != entries[j].GoalsFor {
			return entries[i].GoalsFor > entries[j].GoalsFor
		}
		return entries[i].Team < entries[j].Team
	})

	for i := range entries {
		entries[i].Position = i + 1
	}
	return entries
}

// cleanDisplayName returns the team name without state suffix if present,
// otherwise the original.
func cleanDisplayName(name string) string {
	clean := strings.TrimSpace(stateSuffixRe.ReplaceAllString(name, ""))
	if clean == "" {
		return name
	}
	return clean
}

// GetHeadToHead returns head-to-head stats between two teams.
func (s *Store) GetHeadToHead(team1, team2, competition string) HeadToHead {
	h2h := HeadToHead{Team1: team1, Team2: team2}
	for _, m := range s.Matches {
		if competition != "" && !strings.EqualFold(m.Competition, competition) {
			continue
		}
		home1 := TeamsMatch(m.HomeTeam, team1)
		away1 := TeamsMatch(m.AwayTeam, team1)
		home2 := TeamsMatch(m.HomeTeam, team2)
		away2 := TeamsMatch(m.AwayTeam, team2)

		t1home := home1 && away2
		t1away := away1 && home2

		if !t1home && !t1away {
			continue
		}
		h2h.Matches = append(h2h.Matches, m)

		var t1g, t2g int
		if t1home {
			t1g, t2g = m.HomeGoals, m.AwayGoals
		} else {
			t1g, t2g = m.AwayGoals, m.HomeGoals
		}
		h2h.Team1Goals += t1g
		h2h.Team2Goals += t2g
		switch {
		case t1g > t2g:
			h2h.Team1Wins++
		case t1g == t2g:
			h2h.Draws++
		default:
			h2h.Team2Wins++
		}
	}
	return h2h
}

// PlayerFilter holds search criteria for finding players.
type PlayerFilter struct {
	Name        string
	Nationality string
	Club        string
	Position    string
	MinOverall  int
	Limit       int
}

// FindPlayers returns players matching the filter, sorted by Overall desc.
func (s *Store) FindPlayers(f PlayerFilter) []Player {
	limit := f.Limit
	if limit <= 0 {
		limit = 20
	}

	var candidates []Player
	for _, p := range s.Players {
		if f.Name != "" && !strings.Contains(strings.ToLower(p.Name), strings.ToLower(f.Name)) {
			continue
		}
		if f.Nationality != "" && !strings.EqualFold(p.Nationality, f.Nationality) {
			continue
		}
		if f.Club != "" && !strings.Contains(strings.ToLower(p.Club), strings.ToLower(f.Club)) {
			continue
		}
		if f.Position != "" && !strings.EqualFold(p.Position, f.Position) {
			continue
		}
		if f.MinOverall > 0 && p.Overall < f.MinOverall {
			continue
		}
		candidates = append(candidates, p)
	}

	sort.Slice(candidates, func(i, j int) bool {
		return candidates[i].Overall > candidates[j].Overall
	})

	if len(candidates) > limit {
		candidates = candidates[:limit]
	}
	return candidates
}

// BiggestWins returns the top N matches sorted by goal difference.
func (s *Store) BiggestWins(competition string, season int, limit int) []Match {
	if limit <= 0 {
		limit = 10
	}
	var matches []Match
	for _, m := range s.Matches {
		if competition != "" && !strings.EqualFold(m.Competition, competition) {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}
		matches = append(matches, m)
	}
	sort.Slice(matches, func(i, j int) bool {
		di := abs(matches[i].HomeGoals - matches[i].AwayGoals)
		dj := abs(matches[j].HomeGoals - matches[j].AwayGoals)
		if di != dj {
			return di > dj
		}
		// secondary: total goals
		ti := matches[i].HomeGoals + matches[i].AwayGoals
		tj := matches[j].HomeGoals + matches[j].AwayGoals
		return ti > tj
	})
	if len(matches) > limit {
		matches = matches[:limit]
	}
	return matches
}

// GoalsAverage returns the average goals per match across filtered matches.
func (s *Store) GoalsAverage(competition string, season int) (float64, int) {
	total := 0
	count := 0
	for _, m := range s.Matches {
		if competition != "" && !strings.EqualFold(m.Competition, competition) {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}
		total += m.HomeGoals + m.AwayGoals
		count++
	}
	if count == 0 {
		return 0, 0
	}
	return float64(total) / float64(count), count
}

// HomeAwayRecord computes overall home/away/draw breakdown.
func (s *Store) HomeAwayRecord(competition string, season int) (homeWins, awayWins, draws, total int) {
	for _, m := range s.Matches {
		if competition != "" && !strings.EqualFold(m.Competition, competition) {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}
		total++
		switch {
		case m.HomeGoals > m.AwayGoals:
			homeWins++
		case m.HomeGoals < m.AwayGoals:
			awayWins++
		default:
			draws++
		}
	}
	return
}

func abs(x int) int {
	if x < 0 {
		return -x
	}
	return x
}
