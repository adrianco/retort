package soccer

import (
	"sort"
	"time"
)

// Store holds all match and player data loaded from the source datasets and
// answers queries over it.
type Store struct {
	Matches []Match
	Players []Player
}

// NewStore builds a Store from already-loaded matches and players.
func NewStore(matches []Match, players []Player) *Store {
	return &Store{Matches: matches, Players: players}
}

// MatchFilter selects matches by team, opponent, competition, season and/or
// date range. Zero values mean "no constraint" on that field.
type MatchFilter struct {
	Team        string
	Opponent    string
	Competition string
	Season      int
	From        time.Time
	To          time.Time
	Limit       int
}

// matches reports whether m satisfies the filter, ignoring Limit.
func (f MatchFilter) matches(m Match) bool {
	if f.Team != "" {
		key := NormalizeTeamKey(f.Team)
		if m.HomeKey != key && m.AwayKey != key {
			return false
		}
	}
	if f.Opponent != "" {
		key := NormalizeTeamKey(f.Opponent)
		if m.HomeKey != key && m.AwayKey != key {
			return false
		}
	}
	if f.Competition != "" && m.Competition != f.Competition {
		return false
	}
	if f.Season != 0 && m.Season != f.Season {
		return false
	}
	if !f.From.IsZero() && m.Date.Before(f.From) {
		return false
	}
	if !f.To.IsZero() && m.Date.After(f.To) {
		return false
	}
	return true
}

// HeadToHeadResult summarizes all matches found between two teams.
type HeadToHeadResult struct {
	TeamA     string
	TeamB     string
	Matches   []Match
	TeamAWins int
	TeamBWins int
	Draws     int
}

// HeadToHead returns every match between teamA and teamB (in either
// home/away arrangement, across all competitions), most recent first, along
// with the aggregate win/draw record.
func (s *Store) HeadToHead(teamA, teamB string) HeadToHeadResult {
	keyA := NormalizeTeamKey(teamA)
	keyB := NormalizeTeamKey(teamB)
	result := HeadToHeadResult{TeamA: teamA, TeamB: teamB}
	for _, m := range s.Matches {
		var aIsHome bool
		switch {
		case m.HomeKey == keyA && m.AwayKey == keyB:
			aIsHome = true
		case m.HomeKey == keyB && m.AwayKey == keyA:
			aIsHome = false
		default:
			continue
		}
		result.Matches = append(result.Matches, m)
		switch m.Outcome() {
		case "draw":
			result.Draws++
		case "home":
			if aIsHome {
				result.TeamAWins++
			} else {
				result.TeamBWins++
			}
		case "away":
			if aIsHome {
				result.TeamBWins++
			} else {
				result.TeamAWins++
			}
		}
	}
	sort.Slice(result.Matches, func(i, j int) bool { return result.Matches[i].Date.After(result.Matches[j].Date) })
	return result
}

// TeamRecordFilter scopes a team's win/loss/draw record. Venue is "home",
// "away", or "" for both.
type TeamRecordFilter struct {
	Team        string
	Season      int
	Competition string
	Venue       string
}

// TeamRecord summarizes a team's results over a set of matches.
type TeamRecord struct {
	Team         string
	Matches      int
	Wins         int
	Draws        int
	Losses       int
	GoalsFor     int
	GoalsAgainst int
	WinRate      float64
}

// TeamRecord computes a team's win/loss/draw record, optionally scoped to a
// season, competition, and/or venue (home/away).
func (s *Store) TeamRecord(f TeamRecordFilter) TeamRecord {
	key := NormalizeTeamKey(f.Team)
	rec := TeamRecord{Team: f.Team}
	for _, m := range s.Matches {
		isHome := m.HomeKey == key
		isAway := m.AwayKey == key
		if !isHome && !isAway {
			continue
		}
		if f.Venue == "home" && !isHome {
			continue
		}
		if f.Venue == "away" && !isAway {
			continue
		}
		if f.Season != 0 && m.Season != f.Season {
			continue
		}
		if f.Competition != "" && m.Competition != f.Competition {
			continue
		}
		rec.Matches++
		var goalsFor, goalsAgainst int
		if isHome {
			goalsFor, goalsAgainst = m.HomeGoals, m.AwayGoals
		} else {
			goalsFor, goalsAgainst = m.AwayGoals, m.HomeGoals
		}
		rec.GoalsFor += goalsFor
		rec.GoalsAgainst += goalsAgainst
		switch {
		case goalsFor > goalsAgainst:
			rec.Wins++
		case goalsFor < goalsAgainst:
			rec.Losses++
		default:
			rec.Draws++
		}
	}
	if rec.Matches > 0 {
		rec.WinRate = float64(rec.Wins) / float64(rec.Matches) * 100
	}
	return rec
}

// StandingEntry is one row of a computed competition table.
type StandingEntry struct {
	Team         string
	Played       int
	Wins         int
	Draws        int
	Losses       int
	GoalsFor     int
	GoalsAgainst int
	GoalDiff     int
	Points       int
}

// Standings computes a competition table for the given season from match
// results, awarding 3 points for a win and 1 for a draw. Teams are ordered
// by points, then goal difference, then goals scored, all descending.
func (s *Store) Standings(competition string, season int) []StandingEntry {
	entries := make(map[string]*StandingEntry)
	order := func(key, display string) *StandingEntry {
		e, ok := entries[key]
		if !ok {
			e = &StandingEntry{Team: display}
			entries[key] = e
		}
		return e
	}
	for _, m := range s.Matches {
		if m.Competition != competition || m.Season != season {
			continue
		}
		home := order(m.HomeKey, m.HomeTeam)
		away := order(m.AwayKey, m.AwayTeam)
		home.Played++
		away.Played++
		home.GoalsFor += m.HomeGoals
		home.GoalsAgainst += m.AwayGoals
		away.GoalsFor += m.AwayGoals
		away.GoalsAgainst += m.HomeGoals
		switch m.Outcome() {
		case "home":
			home.Wins++
			home.Points += 3
			away.Losses++
		case "away":
			away.Wins++
			away.Points += 3
			home.Losses++
		default:
			home.Draws++
			away.Draws++
			home.Points++
			away.Points++
		}
	}

	table := make([]StandingEntry, 0, len(entries))
	for _, e := range entries {
		e.GoalDiff = e.GoalsFor - e.GoalsAgainst
		table = append(table, *e)
	}
	sort.Slice(table, func(i, j int) bool {
		if table[i].Points != table[j].Points {
			return table[i].Points > table[j].Points
		}
		if table[i].GoalDiff != table[j].GoalDiff {
			return table[i].GoalDiff > table[j].GoalDiff
		}
		return table[i].GoalsFor > table[j].GoalsFor
	})
	return table
}

// BiggestWinsFilter scopes a search for the most lopsided results.
type BiggestWinsFilter struct {
	Competition string
	Season      int
	Limit       int
}

// BiggestWins returns decisive matches (excluding draws) ordered by goal
// difference, largest first.
func (s *Store) BiggestWins(f BiggestWinsFilter) []Match {
	var out []Match
	for _, m := range s.Matches {
		if f.Competition != "" && m.Competition != f.Competition {
			continue
		}
		if f.Season != 0 && m.Season != f.Season {
			continue
		}
		if m.Outcome() == "draw" {
			continue
		}
		out = append(out, m)
	}
	sort.Slice(out, func(i, j int) bool {
		diffI := absInt(out[i].HomeGoals - out[i].AwayGoals)
		diffJ := absInt(out[j].HomeGoals - out[j].AwayGoals)
		if diffI != diffJ {
			return diffI > diffJ
		}
		return out[i].Date.After(out[j].Date)
	})
	if f.Limit > 0 && len(out) > f.Limit {
		out = out[:f.Limit]
	}
	return out
}

func absInt(n int) int {
	if n < 0 {
		return -n
	}
	return n
}

// Summary holds aggregate statistics over a set of matches.
type Summary struct {
	TotalMatches     int
	AvgGoalsPerMatch float64
	HomeWinRate      float64
	AwayWinRate      float64
	DrawRate         float64
}

// StatsSummary computes aggregate goal and outcome statistics over all
// matches satisfying the filter (Limit is ignored).
func (s *Store) StatsSummary(f MatchFilter) Summary {
	var totalGoals, homeWins, awayWins, draws, total int
	for _, m := range s.Matches {
		if !f.matches(m) {
			continue
		}
		total++
		totalGoals += m.HomeGoals + m.AwayGoals
		switch m.Outcome() {
		case "home":
			homeWins++
		case "away":
			awayWins++
		default:
			draws++
		}
	}
	if total == 0 {
		return Summary{}
	}
	return Summary{
		TotalMatches:     total,
		AvgGoalsPerMatch: float64(totalGoals) / float64(total),
		HomeWinRate:      float64(homeWins) / float64(total) * 100,
		AwayWinRate:      float64(awayWins) / float64(total) * 100,
		DrawRate:         float64(draws) / float64(total) * 100,
	}
}

// FindMatches returns matches satisfying the filter, most recent first.
func (s *Store) FindMatches(f MatchFilter) []Match {
	var out []Match
	for _, m := range s.Matches {
		if f.matches(m) {
			out = append(out, m)
		}
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Date.After(out[j].Date) })
	if f.Limit > 0 && len(out) > f.Limit {
		out = out[:f.Limit]
	}
	return out
}
