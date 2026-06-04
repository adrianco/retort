// query.go - the query layer over the loaded DB.
//
// Context
// -------
// These functions implement the five capability areas from the specification:
// match queries, team queries, player queries, competition queries and
// statistical analysis. They operate purely on the in-memory slices in *DB and
// return structured results; all human-readable formatting lives in the command
// layer (format.go / the MCP tool handlers) so the same query results can be
// reused by tests.
//
// Team-name matching is delegated to NameMatches (normalize.go) so that user
// queries such as "Flamengo" line up with stored names like "Flamengo-RJ".
package soccer

import (
	"sort"
	"strings"
	"time"
)

// MatchFilter expresses the criteria for a match search. All fields are
// optional; zero values mean "no constraint".
type MatchFilter struct {
	Team        string    // matches home or away
	Opponent    string    // when set with Team, both must appear (in any order)
	Home        string    // restrict to this team playing at home
	Away        string    // restrict to this team playing away
	Competition string    // canonical competition key
	Season      int       // exact season/year
	Start       time.Time // inclusive lower date bound
	End         time.Time // inclusive upper date bound
	OnlyScored  bool      // exclude matches without a usable score
}

// FindMatches returns every match satisfying the filter, sorted by date
// (most recent first; undated matches sort last).
func (db *DB) FindMatches(f MatchFilter) []*Match {
	var out []*Match
	for _, m := range db.Matches {
		if !matchPasses(m, f) {
			continue
		}
		out = append(out, m)
	}
	sortMatchesDesc(out)
	return out
}

func matchPasses(m *Match, f MatchFilter) bool {
	if f.OnlyScored && !m.HasScore {
		return false
	}
	if f.Competition != "" && m.Competition != f.Competition {
		return false
	}
	if f.Season != 0 && m.Season != f.Season {
		return false
	}
	if !f.Start.IsZero() && (!m.HasDate || m.Date.Before(f.Start)) {
		return false
	}
	if !f.End.IsZero() && (!m.HasDate || m.Date.After(f.End)) {
		return false
	}
	if f.Home != "" && !NameMatches(f.Home, m.HomeTeam) {
		return false
	}
	if f.Away != "" && !NameMatches(f.Away, m.AwayTeam) {
		return false
	}
	if f.Team != "" {
		if !NameMatches(f.Team, m.HomeTeam) && !NameMatches(f.Team, m.AwayTeam) {
			return false
		}
	}
	if f.Opponent != "" {
		if !NameMatches(f.Opponent, m.HomeTeam) && !NameMatches(f.Opponent, m.AwayTeam) {
			return false
		}
	}
	return true
}

// sortMatchesDesc orders matches by date descending, undated matches last,
// breaking ties stably by season.
func sortMatchesDesc(ms []*Match) {
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

// H2HResult captures a head-to-head comparison between two teams.
type H2HResult struct {
	TeamA   string
	TeamB   string
	AWins   int
	BWins   int
	Draws   int
	AGoals  int // goals scored by team A across the fixtures
	BGoals  int
	Matches []*Match // all qualifying matches, most recent first
	Total   int
}

// HeadToHead computes the record between teamA and teamB, optionally restricted
// to one competition.
func (db *DB) HeadToHead(teamA, teamB, competition string) H2HResult {
	res := H2HResult{}
	matches := db.FindMatches(MatchFilter{
		Team:        teamA,
		Opponent:    teamB,
		Competition: competition,
		OnlyScored:  true,
	})
	res.Matches = matches
	res.Total = len(matches)
	// Resolve canonical display names from the first match if possible.
	res.TeamA, res.TeamB = teamA, teamB
	for _, m := range matches {
		aHome := NameMatches(teamA, m.HomeTeam)
		// Identify A's and B's goals for this fixture.
		var aGoals, bGoals int
		if aHome {
			aGoals, bGoals = m.HomeGoals, m.AwayGoals
			res.TeamA, res.TeamB = m.HomeTeam, m.AwayTeam
		} else {
			aGoals, bGoals = m.AwayGoals, m.HomeGoals
			res.TeamA, res.TeamB = m.AwayTeam, m.HomeTeam
		}
		res.AGoals += aGoals
		res.BGoals += bGoals
		switch {
		case aGoals > bGoals:
			res.AWins++
		case bGoals > aGoals:
			res.BWins++
		default:
			res.Draws++
		}
	}
	return res
}

// TeamStats holds an aggregated record for a team.
type TeamStats struct {
	Team         string
	Season       int    // 0 means all seasons
	Competition  string // "" means all competitions
	Venue        string // "all", "home" or "away"
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

// WinRate returns the fraction of matches won (0 when none played).
func (s TeamStats) WinRate() float64 {
	if s.Played == 0 {
		return 0
	}
	return float64(s.Wins) / float64(s.Played)
}

// ComputeTeamStats aggregates a team's record. venue may be "home", "away" or
// anything else (treated as "all").
func (db *DB) ComputeTeamStats(team string, season int, competition, venue string) TeamStats {
	venue = strings.ToLower(strings.TrimSpace(venue))
	stats := TeamStats{Team: team, Season: season, Competition: competition, Venue: venue}
	if venue != "home" && venue != "away" {
		stats.Venue = "all"
	}
	for _, m := range db.Matches {
		if !m.HasScore {
			continue
		}
		if competition != "" && m.Competition != competition {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}
		isHome := NameMatches(team, m.HomeTeam)
		isAway := NameMatches(team, m.AwayTeam)
		if !isHome && !isAway {
			continue
		}
		// A neutral fixture cannot be both; if a team plays itself skip.
		if isHome && isAway {
			continue
		}
		if stats.Venue == "home" && !isHome {
			continue
		}
		if stats.Venue == "away" && !isAway {
			continue
		}
		var gf, ga int
		if isHome {
			gf, ga = m.HomeGoals, m.AwayGoals
		} else {
			gf, ga = m.AwayGoals, m.HomeGoals
		}
		stats.Played++
		stats.GoalsFor += gf
		stats.GoalsAgainst += ga
		switch {
		case gf > ga:
			stats.Wins++
		case ga > gf:
			stats.Losses++
		default:
			stats.Draws++
		}
		stats.Team = canonicalDisplay(team, m, isHome)
	}
	return stats
}

// canonicalDisplay picks the stored display name corresponding to the queried
// team for nicer output.
func canonicalDisplay(query string, m *Match, isHome bool) string {
	if isHome {
		return m.HomeTeam
	}
	return m.AwayTeam
}

// PlayerFilter expresses criteria for a player search.
type PlayerFilter struct {
	Name        string
	Nationality string
	Club        string
	Position    string
	MinOverall  int
	MaxOverall  int
}

// FindPlayers returns matching players sorted by Overall rating descending.
func (db *DB) FindPlayers(f PlayerFilter) []*Player {
	var out []*Player
	for _, p := range db.Players {
		if f.Name != "" && !matchesAllTokens(p.Name, f.Name) {
			continue
		}
		if f.Nationality != "" && !equalsFold(p.Nationality, f.Nationality) &&
			!containsFold(p.Nationality, f.Nationality) {
			continue
		}
		if f.Club != "" && !containsFold(p.Club, f.Club) {
			continue
		}
		if f.Position != "" && !equalsFold(p.Position, f.Position) {
			continue
		}
		if f.MinOverall != 0 && p.Overall < f.MinOverall {
			continue
		}
		if f.MaxOverall != 0 && p.Overall > f.MaxOverall {
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

// StandingRow is one line of a computed league table.
type StandingRow struct {
	Position int
	TeamStats
}

// Standings computes the final table for a competition/season from match
// results. Only scored matches count. Teams are ranked by points, then goal
// difference, then goals for, then name.
func (db *DB) Standings(competition string, season int) []StandingRow {
	agg := map[string]*TeamStats{}
	order := []string{}
	for _, m := range db.Matches {
		if !m.HasScore {
			continue
		}
		if competition != "" && m.Competition != competition {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}
		recordSide(agg, &order, m.HomeTeam, m.HomeGoals, m.AwayGoals)
		recordSide(agg, &order, m.AwayTeam, m.AwayGoals, m.HomeGoals)
	}

	rows := make([]StandingRow, 0, len(agg))
	for _, name := range order {
		rows = append(rows, StandingRow{TeamStats: *agg[name]})
	}
	sort.SliceStable(rows, func(i, j int) bool {
		a, b := rows[i].TeamStats, rows[j].TeamStats
		if a.Points() != b.Points() {
			return a.Points() > b.Points()
		}
		if a.GoalDiff() != b.GoalDiff() {
			return a.GoalDiff() > b.GoalDiff()
		}
		if a.GoalsFor != b.GoalsFor {
			return a.GoalsFor > b.GoalsFor
		}
		return a.Team < b.Team
	})
	for i := range rows {
		rows[i].Position = i + 1
	}
	return rows
}

// recordSide folds one team's result for a single match into the aggregate map,
// keyed by canonical match key so name variants merge.
func recordSide(agg map[string]*TeamStats, order *[]string, team string, gf, ga int) {
	key := MatchKey(team)
	s, ok := agg[key]
	if !ok {
		s = &TeamStats{Team: team}
		agg[key] = s
		*order = append(*order, key)
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

// equalsFold reports case-insensitive, accent-insensitive equality.
func equalsFold(a, b string) bool {
	return strings.EqualFold(FoldAccents(strings.TrimSpace(a)), FoldAccents(strings.TrimSpace(b)))
}

// matchesAllTokens reports whether every whitespace-separated token of the query
// appears (case- and accent-insensitively) in the text. This lets multi-word
// name queries like "Gabriel Jesus" match while staying precise.
func matchesAllTokens(text, query string) bool {
	h := strings.ToLower(FoldAccents(text))
	for _, tok := range strings.Fields(strings.ToLower(FoldAccents(query))) {
		if !strings.Contains(h, tok) {
			return false
		}
	}
	return true
}

// containsFold reports whether needle appears in haystack, ignoring case and
// accents.
func containsFold(haystack, needle string) bool {
	h := strings.ToLower(FoldAccents(haystack))
	n := strings.ToLower(FoldAccents(strings.TrimSpace(needle)))
	if n == "" {
		return true
	}
	return strings.Contains(h, n)
}
