package soccer

import (
	"sort"
	"strings"
	"time"
)

// This file holds the typed query engine. Each exported method answers one
// category of question from the specification (match, team, player,
// competition, statistics). Results are plain value types so the MCP layer can
// serialise them directly.

// MatchFilter describes the criteria for FindMatches. Zero-valued fields are
// ignored, so an empty filter matches every match.
type MatchFilter struct {
	Team        string // matches home OR away
	HomeTeam    string
	AwayTeam    string
	Opponent    string // combined with Team, restricts to head-to-head
	Competition string
	Season      int
	From        time.Time
	To          time.Time
	Limit       int // 0 = no limit
}

// FindMatches returns matches satisfying the filter, most recent first.
func (s *Store) FindMatches(f MatchFilter) []Match {
	teamKey := NormalizeTeam(f.Team)
	homeKey := NormalizeTeam(f.HomeTeam)
	awayKey := NormalizeTeam(f.AwayTeam)
	oppKey := NormalizeTeam(f.Opponent)
	compKey := NormalizeName(f.Competition)

	var out []Match
	for _, m := range s.Matches {
		if teamKey != "" && m.HomeKey != teamKey && m.AwayKey != teamKey {
			continue
		}
		if homeKey != "" && m.HomeKey != homeKey {
			continue
		}
		if awayKey != "" && m.AwayKey != awayKey {
			continue
		}
		if oppKey != "" && m.HomeKey != oppKey && m.AwayKey != oppKey {
			continue
		}
		if compKey != "" && !strings.Contains(NormalizeName(m.Competition), compKey) {
			continue
		}
		if f.Season != 0 && m.Season != f.Season {
			continue
		}
		if !f.From.IsZero() && (m.Date.IsZero() || m.Date.Before(f.From)) {
			continue
		}
		if !f.To.IsZero() && (m.Date.IsZero() || m.Date.After(f.To)) {
			continue
		}
		out = append(out, m)
	}

	sort.SliceStable(out, func(i, j int) bool {
		return out[i].Date.After(out[j].Date)
	})
	if f.Limit > 0 && len(out) > f.Limit {
		out = out[:f.Limit]
	}
	return out
}

// HeadToHead summarises the all-time record between two teams.
type HeadToHead struct {
	TeamA       string
	TeamB       string
	Matches     int
	WinsA       int
	WinsB       int
	Draws       int
	GoalsA      int
	GoalsB      int
	LastMeeting *Match
}

// HeadToHead computes the record between teamA and teamB across all data.
func (s *Store) HeadToHead(teamA, teamB string) HeadToHead {
	keyA := NormalizeTeam(teamA)
	keyB := NormalizeTeam(teamB)
	h := HeadToHead{TeamA: s.DisplayName(keyA), TeamB: s.DisplayName(keyB)}
	if keyA == "" || keyB == "" || keyA == keyB {
		return h
	}
	for i := range s.Matches {
		m := s.Matches[i]
		if !m.Decided() {
			continue
		}
		involvesBoth := (m.HomeKey == keyA && m.AwayKey == keyB) ||
			(m.HomeKey == keyB && m.AwayKey == keyA)
		if !involvesBoth {
			continue
		}
		h.Matches++
		// Goals from each team's perspective.
		if m.HomeKey == keyA {
			h.GoalsA += m.HomeGoals
			h.GoalsB += m.AwayGoals
		} else {
			h.GoalsA += m.AwayGoals
			h.GoalsB += m.HomeGoals
		}
		if r, ok := m.ResultFor(keyA); ok {
			switch r {
			case ResultWin:
				h.WinsA++
			case ResultLoss:
				h.WinsB++
			case ResultDraw:
				h.Draws++
			}
		}
		if h.LastMeeting == nil || m.Date.After(h.LastMeeting.Date) {
			mm := m
			h.LastMeeting = &mm
		}
	}
	return h
}

// TeamRecord aggregates a team's results, optionally scoped to a competition,
// season and/or venue.
type TeamRecord struct {
	Team         string
	Competition  string
	Season       int
	Venue        string // "home", "away" or "all"
	Played       int
	Wins         int
	Draws        int
	Losses       int
	GoalsFor     int
	GoalsAgainst int
	Points       int // 3 for a win, 1 for a draw (league convention)
}

// WinRate returns wins as a fraction of games played (0 when none played).
func (r TeamRecord) WinRate() float64 {
	if r.Played == 0 {
		return 0
	}
	return float64(r.Wins) / float64(r.Played)
}

// TeamRecordOptions scopes a TeamRecord query.
type TeamRecordOptions struct {
	Competition string
	Season      int
	Venue       string // "home", "away", or "" / "all"
}

// TeamRecord computes a team's aggregate record under the given options.
func (s *Store) TeamRecord(team string, opts TeamRecordOptions) TeamRecord {
	key := NormalizeTeam(team)
	compKey := NormalizeName(opts.Competition)
	venue := strings.ToLower(strings.TrimSpace(opts.Venue))
	rec := TeamRecord{
		Team:        s.DisplayName(key),
		Competition: opts.Competition,
		Season:      opts.Season,
		Venue:       venue,
	}
	if key == "" {
		return rec
	}
	for i := range s.Matches {
		m := s.Matches[i]
		if !m.Decided() {
			continue
		}
		isHome := m.HomeKey == key
		isAway := m.AwayKey == key
		if !isHome && !isAway {
			continue
		}
		if venue == "home" && !isHome {
			continue
		}
		if venue == "away" && !isAway {
			continue
		}
		if compKey != "" && !strings.Contains(NormalizeName(m.Competition), compKey) {
			continue
		}
		if opts.Season != 0 && m.Season != opts.Season {
			continue
		}
		rec.Played++
		if isHome {
			rec.GoalsFor += m.HomeGoals
			rec.GoalsAgainst += m.AwayGoals
		} else {
			rec.GoalsFor += m.AwayGoals
			rec.GoalsAgainst += m.HomeGoals
		}
		r, _ := m.ResultFor(key)
		switch r {
		case ResultWin:
			rec.Wins++
			rec.Points += 3
		case ResultDraw:
			rec.Draws++
			rec.Points++
		case ResultLoss:
			rec.Losses++
		}
	}
	return rec
}

// Standing is a single row of a league table.
type Standing struct {
	Position     int
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

// Standings computes a league table for a competition and season from match
// results. Ordering follows the usual tie-breakers: points, then goal
// difference, then goals for, then name.
func (s *Store) Standings(competition string, season int) []Standing {
	compKey := NormalizeName(competition)
	agg := map[string]*Standing{}
	get := func(key string) *Standing {
		st := agg[key]
		if st == nil {
			st = &Standing{Team: s.DisplayName(key)}
			agg[key] = st
		}
		return st
	}
	for i := range s.Matches {
		m := s.Matches[i]
		if !m.Decided() {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}
		if compKey != "" && !strings.Contains(NormalizeName(m.Competition), compKey) {
			continue
		}
		home := get(m.HomeKey)
		away := get(m.AwayKey)
		home.Played++
		away.Played++
		home.GoalsFor += m.HomeGoals
		home.GoalsAgainst += m.AwayGoals
		away.GoalsFor += m.AwayGoals
		away.GoalsAgainst += m.HomeGoals
		switch {
		case m.HomeGoals > m.AwayGoals:
			home.Wins++
			home.Points += 3
			away.Losses++
		case m.HomeGoals < m.AwayGoals:
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

	table := make([]Standing, 0, len(agg))
	for _, st := range agg {
		st.GoalDiff = st.GoalsFor - st.GoalsAgainst
		table = append(table, *st)
	}
	sort.SliceStable(table, func(i, j int) bool {
		a, b := table[i], table[j]
		if a.Points != b.Points {
			return a.Points > b.Points
		}
		if a.GoalDiff != b.GoalDiff {
			return a.GoalDiff > b.GoalDiff
		}
		if a.GoalsFor != b.GoalsFor {
			return a.GoalsFor > b.GoalsFor
		}
		return a.Team < b.Team
	})
	for i := range table {
		table[i].Position = i + 1
	}
	return table
}

// PlayerFilter scopes a player search.
type PlayerFilter struct {
	Name        string
	Nationality string
	Club        string
	Position    string
	MinOverall  int
	Limit       int
}

// FindPlayers returns players matching the filter, sorted by Overall rating
// (highest first).
func (s *Store) FindPlayers(f PlayerFilter) []Player {
	nameKey := NormalizeName(f.Name)
	natKey := NormalizeName(f.Nationality)
	clubKey := NormalizeTeam(f.Club)
	posKey := strings.ToUpper(strings.TrimSpace(f.Position))

	var out []Player
	for _, p := range s.Players {
		if nameKey != "" && !strings.Contains(p.NameKey, nameKey) {
			continue
		}
		if natKey != "" && NormalizeName(p.Nationality) != natKey {
			continue
		}
		if clubKey != "" && !strings.Contains(p.ClubKey, clubKey) {
			continue
		}
		if posKey != "" && strings.ToUpper(p.Position) != posKey {
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
	if f.Limit > 0 && len(out) > f.Limit {
		out = out[:f.Limit]
	}
	return out
}

// Statistics summarises a set of matches (typically the result of a filter).
type Statistics struct {
	Matches         int
	TotalGoals      int
	HomeGoals       int
	AwayGoals       int
	HomeWins        int
	AwayWins        int
	Draws           int
	AvgGoalsPerGame float64
	HomeWinRate     float64
	BiggestWins     []Match // largest goal margins, most lopsided first
}

// Stats computes aggregate statistics for the matches matching the filter.
// biggestN controls how many top-margin matches to include (default 5 when 0).
func (s *Store) Stats(f MatchFilter, biggestN int) Statistics {
	if biggestN <= 0 {
		biggestN = 5
	}
	matches := s.FindMatches(f)
	var st Statistics
	decided := make([]Match, 0, len(matches))
	for _, m := range matches {
		if !m.Decided() {
			continue
		}
		decided = append(decided, m)
		st.Matches++
		st.TotalGoals += m.TotalGoals()
		st.HomeGoals += m.HomeGoals
		st.AwayGoals += m.AwayGoals
		switch {
		case m.HomeGoals > m.AwayGoals:
			st.HomeWins++
		case m.HomeGoals < m.AwayGoals:
			st.AwayWins++
		default:
			st.Draws++
		}
	}
	if st.Matches > 0 {
		st.AvgGoalsPerGame = float64(st.TotalGoals) / float64(st.Matches)
		st.HomeWinRate = float64(st.HomeWins) / float64(st.Matches)
	}
	sort.SliceStable(decided, func(i, j int) bool {
		mi := abs(decided[i].HomeGoals - decided[i].AwayGoals)
		mj := abs(decided[j].HomeGoals - decided[j].AwayGoals)
		if mi != mj {
			return mi > mj
		}
		return decided[i].TotalGoals() > decided[j].TotalGoals()
	})
	if len(decided) > biggestN {
		decided = decided[:biggestN]
	}
	st.BiggestWins = decided
	return st
}

func abs(n int) int {
	if n < 0 {
		return -n
	}
	return n
}
