package soccer

import (
	"fmt"
	"sort"
	"strings"
)

type TeamStats struct {
	Team       string
	Matches    int
	Wins       int
	Draws      int
	Losses     int
	GoalsFor   int
	GoalsAgainst int
	Points     int
}

func (t TeamStats) WinRate() float64 {
	if t.Matches == 0 {
		return 0
	}
	return float64(t.Wins) / float64(t.Matches) * 100
}

type HeadToHead struct {
	TeamA   string
	TeamB   string
	AWins   int
	BWins   int
	Draws   int
	Matches []Match
}

// MatchesByTeam returns all matches for team (home or away).
func (db *DB) MatchesByTeam(team string) []Match {
	var out []Match
	for _, m := range db.Matches {
		if TeamMatches(team, m.HomeTeam) || TeamMatches(team, m.AwayTeam) {
			out = append(out, m)
		}
	}
	return out
}

// MatchesBetween returns matches involving both teams (either side).
func (db *DB) MatchesBetween(a, b string) []Match {
	var out []Match
	for _, m := range db.Matches {
		ha := TeamMatches(a, m.HomeTeam)
		aa := TeamMatches(a, m.AwayTeam)
		hb := TeamMatches(b, m.HomeTeam)
		ab := TeamMatches(b, m.AwayTeam)
		if (ha && ab) || (hb && aa) {
			out = append(out, m)
		}
	}
	return out
}

// H2H summarises head-to-head between two teams.
func (db *DB) H2H(a, b string) HeadToHead {
	ms := db.MatchesBetween(a, b)
	h := HeadToHead{TeamA: a, TeamB: b, Matches: ms}
	for _, m := range ms {
		if m.HomeGoal == m.AwayGoal {
			h.Draws++
			continue
		}
		homeWon := m.HomeGoal > m.AwayGoal
		aIsHome := TeamMatches(a, m.HomeTeam)
		if (aIsHome && homeWon) || (!aIsHome && !homeWon) {
			h.AWins++
		} else {
			h.BWins++
		}
	}
	return h
}

// MatchesBySeason filters matches by season (year).
func (db *DB) MatchesBySeason(season int) []Match {
	var out []Match
	for _, m := range db.Matches {
		if m.Season == season {
			out = append(out, m)
		}
	}
	return out
}

// MatchesByCompetition filters matches by competition (substring, case-insensitive).
func (db *DB) MatchesByCompetition(comp string) []Match {
	c := strings.ToLower(comp)
	var out []Match
	for _, m := range db.Matches {
		if strings.Contains(strings.ToLower(m.Competition), c) {
			out = append(out, m)
		}
	}
	return out
}

// TeamSeasonStats computes team stats restricted to season and optional competition.
// If season <= 0, all seasons. If comp == "", all competitions. If homeOnly/awayOnly, restrict side.
type StatsFilter struct {
	Season      int
	Competition string
	HomeOnly    bool
	AwayOnly    bool
}

func (db *DB) TeamStats(team string, f StatsFilter) TeamStats {
	ts := TeamStats{Team: team}
	compLower := strings.ToLower(f.Competition)
	for _, m := range db.Matches {
		if f.Season > 0 && m.Season != f.Season {
			continue
		}
		if f.Competition != "" && !strings.Contains(strings.ToLower(m.Competition), compLower) {
			continue
		}
		home := TeamMatches(team, m.HomeTeam)
		away := TeamMatches(team, m.AwayTeam)
		if !home && !away {
			continue
		}
		if f.HomeOnly && !home {
			continue
		}
		if f.AwayOnly && !away {
			continue
		}
		ts.Matches++
		var gf, ga int
		if home {
			gf, ga = m.HomeGoal, m.AwayGoal
		} else {
			gf, ga = m.AwayGoal, m.HomeGoal
		}
		ts.GoalsFor += gf
		ts.GoalsAgainst += ga
		switch {
		case gf > ga:
			ts.Wins++
			ts.Points += 3
		case gf == ga:
			ts.Draws++
			ts.Points++
		default:
			ts.Losses++
		}
	}
	return ts
}

// Standings computes a table for the given season/competition.
func (db *DB) Standings(season int, competition string) []TeamStats {
	agg := map[string]*TeamStats{}
	compLower := strings.ToLower(competition)
	for _, m := range db.Matches {
		if season > 0 && m.Season != season {
			continue
		}
		if competition != "" && !strings.Contains(strings.ToLower(m.Competition), compLower) {
			continue
		}
		if m.HomeTeam == "" || m.AwayTeam == "" {
			continue
		}
		for _, side := range []struct {
			name string
			gf   int
			ga   int
		}{
			{m.HomeTeam, m.HomeGoal, m.AwayGoal},
			{m.AwayTeam, m.AwayGoal, m.HomeGoal},
		} {
			key := NormalizeTeam(side.name)
			if _, ok := agg[key]; !ok {
				agg[key] = &TeamStats{Team: canonicalTeamName(side.name)}
			}
			s := agg[key]
			s.Matches++
			s.GoalsFor += side.gf
			s.GoalsAgainst += side.ga
			switch {
			case side.gf > side.ga:
				s.Wins++
				s.Points += 3
			case side.gf == side.ga:
				s.Draws++
				s.Points++
			default:
				s.Losses++
			}
		}
	}
	out := make([]TeamStats, 0, len(agg))
	for _, v := range agg {
		out = append(out, *v)
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].Points != out[j].Points {
			return out[i].Points > out[j].Points
		}
		gdi := out[i].GoalsFor - out[i].GoalsAgainst
		gdj := out[j].GoalsFor - out[j].GoalsAgainst
		if gdi != gdj {
			return gdi > gdj
		}
		return out[i].GoalsFor > out[j].GoalsFor
	})
	return out
}

func canonicalTeamName(s string) string {
	s = strings.TrimSpace(s)
	if i := strings.LastIndex(s, "-"); i >= 0 {
		suf := strings.TrimSpace(s[i+1:])
		if len(suf) == 2 {
			return strings.TrimSpace(s[:i])
		}
	}
	return s
}

// BiggestWins returns matches sorted by largest goal difference, up to limit.
func (db *DB) BiggestWins(limit int) []Match {
	out := make([]Match, len(db.Matches))
	copy(out, db.Matches)
	sort.Slice(out, func(i, j int) bool {
		di := abs(out[i].HomeGoal - out[i].AwayGoal)
		dj := abs(out[j].HomeGoal - out[j].AwayGoal)
		return di > dj
	})
	if limit > 0 && len(out) > limit {
		out = out[:limit]
	}
	return out
}

func abs(x int) int {
	if x < 0 {
		return -x
	}
	return x
}

// AverageGoalsPerMatch across a competition/season filter.
func (db *DB) AverageGoalsPerMatch(season int, competition string) float64 {
	var total, count int
	compLower := strings.ToLower(competition)
	for _, m := range db.Matches {
		if season > 0 && m.Season != season {
			continue
		}
		if competition != "" && !strings.Contains(strings.ToLower(m.Competition), compLower) {
			continue
		}
		total += m.HomeGoal + m.AwayGoal
		count++
	}
	if count == 0 {
		return 0
	}
	return float64(total) / float64(count)
}

// PlayersByName returns players whose name contains substring (case-insensitive).
func (db *DB) PlayersByName(name string) []Player {
	n := strings.ToLower(name)
	var out []Player
	for _, p := range db.Players {
		if strings.Contains(strings.ToLower(p.Name), n) {
			out = append(out, p)
		}
	}
	return out
}

// PlayersByNationality returns players whose nationality matches exactly (case-insensitive).
func (db *DB) PlayersByNationality(nation string) []Player {
	n := strings.ToLower(nation)
	var out []Player
	for _, p := range db.Players {
		if strings.ToLower(p.Nationality) == n {
			out = append(out, p)
		}
	}
	return out
}

// PlayersByClub returns players where the club contains the substring.
func (db *DB) PlayersByClub(club string) []Player {
	c := strings.ToLower(club)
	var out []Player
	for _, p := range db.Players {
		if strings.Contains(strings.ToLower(p.Club), c) {
			out = append(out, p)
		}
	}
	return out
}

// TopPlayers returns up to limit players sorted by Overall (desc), optionally filtered.
func (db *DB) TopPlayers(limit int, nationality, club, position string) []Player {
	var pool []Player
	for _, p := range db.Players {
		if nationality != "" && !strings.EqualFold(p.Nationality, nationality) {
			continue
		}
		if club != "" && !strings.Contains(strings.ToLower(p.Club), strings.ToLower(club)) {
			continue
		}
		if position != "" && !strings.EqualFold(p.Position, position) {
			continue
		}
		pool = append(pool, p)
	}
	sort.Slice(pool, func(i, j int) bool { return pool[i].Overall > pool[j].Overall })
	if limit > 0 && len(pool) > limit {
		pool = pool[:limit]
	}
	return pool
}

// FormatMatches is a helper that renders matches as lines.
func FormatMatches(ms []Match) string {
	var b strings.Builder
	for _, m := range ms {
		date := "unknown"
		if !m.Date.IsZero() {
			date = m.Date.Format("2006-01-02")
		}
		extra := m.Competition
		if m.Round != "" {
			extra += " Round " + m.Round
		}
		if m.Stage != "" {
			extra += " " + m.Stage
		}
		fmt.Fprintf(&b, "%s: %s %d-%d %s (%s)\n",
			date, m.HomeTeam, m.HomeGoal, m.AwayGoal, m.AwayTeam, strings.TrimSpace(extra))
	}
	return b.String()
}
