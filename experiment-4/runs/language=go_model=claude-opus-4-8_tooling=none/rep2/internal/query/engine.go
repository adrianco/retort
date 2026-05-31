// Package query implements the analytical engine over the loaded soccer
// Database. It is deliberately independent of the MCP transport so that the same
// logic can be exercised directly from BDD tests.
//
// Context:
//   - Project: Brazilian Soccer MCP Server (see TASK.md).
//   - Role of this file: the Engine type and all query operations required by
//     the spec: match search, head-to-head, team statistics, computed league
//     standings, competition-wide statistics, and player search.
//   - Matching: team filters compare on the normalized key from package data so
//     that "Flamengo" matches "Flamengo-RJ", "São Paulo" matches "Sao Paulo",
//     etc.
package query

import (
	"sort"
	"strings"
	"time"

	"brazilian-soccer-mcp/internal/data"
)

// Engine answers queries against an immutable Database.
type Engine struct {
	db *data.Database
}

// New returns an Engine bound to db.
func New(db *data.Database) *Engine { return &Engine{db: db} }

// DB exposes the underlying database (read-only use).
func (e *Engine) DB() *data.Database { return e.db }

// MatchFilter describes the criteria for SearchMatches. Empty fields are
// ignored. Team matches either home or away; Opponent (when set together with
// Team) restricts to games between the two clubs.
type MatchFilter struct {
	Team        string
	Opponent    string
	Venue       string // "home", "away", or "" / "all"
	Competition string
	Season      int
	StartDate   time.Time
	EndDate     time.Time
	Limit       int // 0 = no limit
}

func compMatches(want, got string) bool {
	if want == "" {
		return true
	}
	w := strings.ToLower(strings.TrimSpace(want))
	g := strings.ToLower(got)
	// Friendly aliases for common shorthands.
	switch w {
	case "brasileirao", "brasileirão", "serie a", "série a", "brasileirao serie a":
		return strings.Contains(g, "série a") || strings.Contains(g, "serie a")
	case "serie b", "série b":
		return strings.Contains(g, "série b") || strings.Contains(g, "serie b")
	case "serie c", "série c":
		return strings.Contains(g, "série c") || strings.Contains(g, "serie c")
	case "copa do brasil", "cup", "brazilian cup":
		return strings.Contains(g, "copa do brasil")
	case "libertadores", "copa libertadores":
		return strings.Contains(g, "libertadores")
	}
	return strings.Contains(g, w)
}

// SearchMatches returns matches satisfying the filter, most recent first.
func (e *Engine) SearchMatches(f MatchFilter) []data.Match {
	venue := strings.ToLower(strings.TrimSpace(f.Venue))

	var out []data.Match
	for _, m := range e.db.Matches {
		if !compMatches(f.Competition, m.Competition) {
			continue
		}
		if f.Season != 0 && m.Season != f.Season {
			continue
		}
		if !f.StartDate.IsZero() && (!m.HasDate || m.Date.Before(f.StartDate)) {
			continue
		}
		if !f.EndDate.IsZero() && (!m.HasDate || m.Date.After(f.EndDate)) {
			continue
		}

		if f.Team != "" {
			isHome := data.TeamMatches(f.Team, m.HomeRaw)
			isAway := data.TeamMatches(f.Team, m.AwayRaw)
			switch venue {
			case "home":
				if !isHome {
					continue
				}
			case "away":
				if !isAway {
					continue
				}
			default:
				if !isHome && !isAway {
					continue
				}
			}
			if f.Opponent != "" {
				oppHome := data.TeamMatches(f.Opponent, m.HomeRaw)
				oppAway := data.TeamMatches(f.Opponent, m.AwayRaw)
				if !((isHome && oppAway) || (isAway && oppHome)) {
					continue
				}
			}
		}
		out = append(out, m)
	}

	sortMatchesRecent(out)
	if f.Limit > 0 && len(out) > f.Limit {
		out = out[:f.Limit]
	}
	return out
}

func sortMatchesRecent(ms []data.Match) {
	sort.SliceStable(ms, func(i, j int) bool {
		a, b := ms[i], ms[j]
		if a.HasDate != b.HasDate {
			return a.HasDate // dated before undated
		}
		if a.HasDate && b.HasDate && !a.Date.Equal(b.Date) {
			return a.Date.After(b.Date)
		}
		return a.Season > b.Season
	})
}

// HeadToHead summarizes the all-time record between two clubs.
type HeadToHead struct {
	TeamA   string
	TeamB   string
	Matches []data.Match
	AWins   int
	BWins   int
	Draws   int
	AGoals  int
	BGoals  int
}

// HeadToHead computes the record between teamA and teamB across all
// competitions.
func (e *Engine) HeadToHead(teamA, teamB string) HeadToHead {
	matches := e.SearchMatches(MatchFilter{Team: teamA, Opponent: teamB})

	h := HeadToHead{
		TeamA:   data.DisplayTeam(teamA),
		TeamB:   data.DisplayTeam(teamB),
		Matches: matches,
	}
	for _, m := range matches {
		homeIsA := data.TeamMatches(teamA, m.HomeRaw)
		var aGoals, bGoals int
		if homeIsA {
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
	return h
}

// TeamStats is an aggregate performance record for a single team.
type TeamStats struct {
	Team         string
	State        string
	Season       int
	Competition  string
	Venue        string
	Played       int
	Wins         int
	Draws        int
	Losses       int
	GoalsFor     int
	GoalsAgainst int
}

// Points returns league points (3 per win, 1 per draw).
func (s TeamStats) Points() int { return s.Wins*3 + s.Draws }

// GoalDiff returns goals for minus goals against.
func (s TeamStats) GoalDiff() int { return s.GoalsFor - s.GoalsAgainst }

// WinRate returns the fraction of matches won (0..1).
func (s TeamStats) WinRate() float64 {
	if s.Played == 0 {
		return 0
	}
	return float64(s.Wins) / float64(s.Played)
}

// TeamStats aggregates a team's results under the given filter. Venue may be
// "home", "away", or "" for all matches.
func (e *Engine) TeamStats(team string, season int, competition, venue string) TeamStats {
	matches := e.SearchMatches(MatchFilter{
		Team:        team,
		Competition: competition,
		Season:      season,
		Venue:       venue,
	})
	st := TeamStats{
		Team:        data.DisplayTeam(team),
		Season:      season,
		Competition: competition,
		Venue:       venue,
	}
	for _, m := range matches {
		homeIsTeam := data.TeamMatches(team, m.HomeRaw)
		var gf, ga int
		if homeIsTeam {
			gf, ga = m.HomeGoal, m.AwayGoal
		} else {
			gf, ga = m.AwayGoal, m.HomeGoal
		}
		st.Played++
		st.GoalsFor += gf
		st.GoalsAgainst += ga
		switch {
		case gf > ga:
			st.Wins++
		case ga > gf:
			st.Losses++
		default:
			st.Draws++
		}
	}
	return st
}

// Standings computes the league table for a competition/season from match
// results, ordered by points, then goal difference, then goals for.
func (e *Engine) Standings(competition string, season int) []TeamStats {
	matches := e.SearchMatches(MatchFilter{Competition: competition, Season: season})
	byTeam := map[string]*TeamStats{}

	record := func(rawName string, gf, ga int) {
		key := data.TeamKey(rawName)
		s := byTeam[key]
		if s == nil {
			s = &TeamStats{
				Team:        data.DisplayTeam(rawName),
				State:       data.TeamState(rawName),
				Season:      season,
				Competition: competition,
			}
			byTeam[key] = s
		}
		s.Played++
		s.GoalsFor += gf
		s.GoalsAgainst += ga
		switch {
		case gf > ga:
			s.Wins++
		case ga > gf:
			s.Losses++
		default:
			s.Draws++
		}
	}

	for _, m := range matches {
		record(m.HomeRaw, m.HomeGoal, m.AwayGoal)
		record(m.AwayRaw, m.AwayGoal, m.HomeGoal)
	}

	out := make([]TeamStats, 0, len(byTeam))
	for _, s := range byTeam {
		out = append(out, *s)
	}
	sort.SliceStable(out, func(i, j int) bool {
		a, b := out[i], out[j]
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
	return out
}

// CompetitionStats summarizes a competition (optionally a single season).
type CompetitionStats struct {
	Competition     string
	Season          int
	Matches         int
	TotalGoals      int
	HomeWins        int
	AwayWins        int
	Draws           int
	BiggestWins     []data.Match
	AvgGoalsPerGame float64
	HomeWinRate     float64
	AwayWinRate     float64
	DrawRate        float64
}

// CompetitionStats aggregates statistics for a competition. competition may be
// empty to span all data; season 0 spans all seasons.
func (e *Engine) CompetitionStats(competition string, season int, topWins int) CompetitionStats {
	matches := e.SearchMatches(MatchFilter{Competition: competition, Season: season})
	cs := CompetitionStats{Competition: competition, Season: season, Matches: len(matches)}
	for _, m := range matches {
		cs.TotalGoals += m.TotalGoals()
		switch {
		case m.HomeGoal > m.AwayGoal:
			cs.HomeWins++
		case m.AwayGoal > m.HomeGoal:
			cs.AwayWins++
		default:
			cs.Draws++
		}
	}
	if cs.Matches > 0 {
		cs.AvgGoalsPerGame = float64(cs.TotalGoals) / float64(cs.Matches)
		cs.HomeWinRate = float64(cs.HomeWins) / float64(cs.Matches)
		cs.AwayWinRate = float64(cs.AwayWins) / float64(cs.Matches)
		cs.DrawRate = float64(cs.Draws) / float64(cs.Matches)
	}

	if topWins <= 0 {
		topWins = 5
	}
	sorted := make([]data.Match, len(matches))
	copy(sorted, matches)
	sort.SliceStable(sorted, func(i, j int) bool {
		return sorted[i].GoalDiff() > sorted[j].GoalDiff()
	})
	if len(sorted) > topWins {
		sorted = sorted[:topWins]
	}
	cs.BiggestWins = sorted
	return cs
}

// PlayerFilter describes criteria for SearchPlayers. Empty fields are ignored.
type PlayerFilter struct {
	Name        string
	Nationality string
	Club        string
	Position    string
	MinOverall  int
	Limit       int // 0 -> default applied by caller
}

// SearchPlayers returns players matching the filter sorted by Overall (desc).
func (e *Engine) SearchPlayers(f PlayerFilter) []data.Player {
	name := strings.ToLower(strings.TrimSpace(f.Name))
	nat := strings.ToLower(strings.TrimSpace(f.Nationality))
	club := strings.ToLower(strings.TrimSpace(f.Club))
	pos := strings.ToUpper(strings.TrimSpace(f.Position))

	var out []data.Player
	for _, p := range e.db.Players {
		if name != "" && !strings.Contains(strings.ToLower(p.Name), name) {
			continue
		}
		if nat != "" && !strings.Contains(strings.ToLower(p.Nationality), nat) {
			continue
		}
		if club != "" && !strings.Contains(strings.ToLower(p.Club), club) {
			continue
		}
		if pos != "" && !strings.EqualFold(p.Position, pos) {
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

// Competitions returns the distinct competition labels present in the data,
// sorted alphabetically.
func (e *Engine) Competitions() []string {
	set := map[string]bool{}
	for _, m := range e.db.Matches {
		set[m.Competition] = true
	}
	out := make([]string, 0, len(set))
	for c := range set {
		out = append(out, c)
	}
	sort.Strings(out)
	return out
}
