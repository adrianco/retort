// Brazilian Soccer MCP Server
//
// File: store.go
// Responsibility: In-memory data store and query engine. Holds all loaded
// matches and players and answers the analytical questions the MCP tools expose:
// match lookups, team records, head-to-head comparisons, computed league
// standings, competition-wide statistics and player search. All matching is
// done on the canonical keys produced in normalize.go so callers can pass a
// loosely-typed team name like "flamengo" and still hit "Flamengo-RJ".
package main

import (
	"sort"
	"strings"
	"time"
)

// Store is the queryable collection of all loaded data.
type Store struct {
	Matches []Match
	Players []Player

	// teamNames maps a full canonical key (with state suffix) to the most
	// frequently seen display name; baseNames does the same for suffix-stripped
	// base keys. Both keep output spelling consistent.
	teamNames map[string]string
	baseNames map[string]string
}

// NewStore returns an empty store ready to be filled by the loader.
func NewStore() *Store {
	return &Store{teamNames: map[string]string{}, baseNames: map[string]string{}}
}

// Index builds derived lookup structures after loading. It is safe to call once
// all matches/players are appended.
func (s *Store) Index() {
	full := map[string]map[string]int{}
	base := map[string]map[string]int{}
	note := func(m map[string]map[string]int, key, display string) {
		if key == "" {
			return
		}
		if m[key] == nil {
			m[key] = map[string]int{}
		}
		m[key][display]++
	}
	for _, mt := range s.Matches {
		note(full, mt.HomeKey, mt.HomeTeam)
		note(full, mt.AwayKey, mt.AwayTeam)
		note(base, mt.HomeBase, mt.HomeTeam)
		note(base, mt.AwayBase, mt.AwayTeam)
	}
	pickBest := func(src map[string]map[string]int, dst map[string]string) {
		for key, names := range src {
			best, bestN := "", -1
			for name, n := range names {
				if n > bestN || (n == bestN && name < best) {
					best, bestN = name, n
				}
			}
			dst[key] = best
		}
	}
	pickBest(full, s.teamNames)
	pickBest(base, s.baseNames)
}

// DisplayName returns the canonical display spelling for a full team key,
// falling back to the key itself if unknown.
func (s *Store) DisplayName(key string) string {
	if name, ok := s.teamNames[key]; ok {
		return name
	}
	return key
}

// DisplayForTeam resolves a user-supplied team query to a canonical display
// name, honoring an explicit state suffix if the query carries one.
func (s *Store) DisplayForTeam(query string) string {
	b, st := baseAndState(query)
	if st != "" {
		if name, ok := s.teamNames[b+"-"+strings.ToLower(st)]; ok {
			return name
		}
	}
	if name, ok := s.baseNames[b]; ok {
		return name
	}
	return cleanTeamName(query)
}

// sideMatchesQuery reports whether a match team (identified by its full and base
// keys) satisfies a user query term. A query carrying an explicit state suffix
// matches only that exact club; a bare query matches any club sharing the base
// name (so "Flamengo" matches "Flamengo-RJ").
func sideMatchesQuery(query, fullKey, baseKey string) bool {
	b, st := baseAndState(query)
	if b == "" {
		return false
	}
	if st != "" {
		return fullKey == b+"-"+strings.ToLower(st)
	}
	return baseKey == b
}

// MatchFilter describes the criteria accepted by FindMatches. Zero-valued
// fields are ignored.
type MatchFilter struct {
	Team        string // matches home OR away
	Opponent    string // when set with Team, restricts to games between them
	Competition string
	Season      int
	StartDate   time.Time
	EndDate     time.Time
	HomeAway    string // "home", "away" or "" for either (relative to Team)
	Dedup       bool   // collapse the same match appearing in multiple datasets
}

// FindMatches returns the matches satisfying the filter, sorted most-recent
// first.
func (s *Store) FindMatches(f MatchFilter) []Match {
	compK := normKey(f.Competition)

	var out []Match
	seen := map[string]bool{}
	for _, m := range s.Matches {
		if f.Team != "" {
			homeHit := sideMatchesQuery(f.Team, m.HomeKey, m.HomeBase)
			awayHit := sideMatchesQuery(f.Team, m.AwayKey, m.AwayBase)
			switch f.HomeAway {
			case "home":
				if !homeHit {
					continue
				}
			case "away":
				if !awayHit {
					continue
				}
			default:
				if !homeHit && !awayHit {
					continue
				}
			}
		}
		if f.Opponent != "" {
			oppHome := sideMatchesQuery(f.Opponent, m.HomeKey, m.HomeBase)
			oppAway := sideMatchesQuery(f.Opponent, m.AwayKey, m.AwayBase)
			teamHome := sideMatchesQuery(f.Team, m.HomeKey, m.HomeBase)
			teamAway := sideMatchesQuery(f.Team, m.AwayKey, m.AwayBase)
			if !((teamHome && oppAway) || (oppHome && teamAway)) {
				continue
			}
		}
		if compK != "" && !strings.Contains(normKey(m.Competition), compK) {
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
		if f.Dedup {
			sig := m.signature()
			if seen[sig] {
				continue
			}
			seen[sig] = true
		}
		out = append(out, m)
	}
	sortMatchesDesc(out)
	return out
}

// sortMatchesDesc orders matches newest-first; undated matches sort last.
func sortMatchesDesc(ms []Match) {
	sort.SliceStable(ms, func(i, j int) bool {
		a, b := ms[i], ms[j]
		if a.HasDate != b.HasDate {
			return a.HasDate // dated before undated
		}
		if a.HasDate && !a.Date.Equal(b.Date) {
			return a.Date.After(b.Date)
		}
		return a.Season > b.Season
	})
}

// TeamRecord is an aggregate win/draw/loss and goal summary for a team.
type TeamRecord struct {
	Team         string
	Matches      int
	Wins         int
	Draws        int
	Losses       int
	GoalsFor     int
	GoalsAgainst int
}

// Points returns league points (3 per win, 1 per draw).
func (r TeamRecord) Points() int { return r.Wins*3 + r.Draws }

// GoalDiff returns goal difference.
func (r TeamRecord) GoalDiff() int { return r.GoalsFor - r.GoalsAgainst }

// WinRate returns the fraction of matches won (0..1).
func (r TeamRecord) WinRate() float64 {
	if r.Matches == 0 {
		return 0
	}
	return float64(r.Wins) / float64(r.Matches)
}

// TeamStats computes a team's aggregate record over the matches selected by the
// filter (the filter's Team field is set from team automatically).
func (s *Store) TeamStats(team string, f MatchFilter) TeamRecord {
	f.Team = team
	f.Dedup = true
	rec := TeamRecord{Team: s.DisplayForTeam(team)}
	for _, m := range s.FindMatches(f) {
		if !m.HasScore {
			continue
		}
		rec.Matches++
		if sideMatchesQuery(team, m.HomeKey, m.HomeBase) {
			rec.GoalsFor += m.HomeGoal
			rec.GoalsAgainst += m.AwayGoal
			switch {
			case m.HomeGoal > m.AwayGoal:
				rec.Wins++
			case m.HomeGoal < m.AwayGoal:
				rec.Losses++
			default:
				rec.Draws++
			}
		} else {
			rec.GoalsFor += m.AwayGoal
			rec.GoalsAgainst += m.HomeGoal
			switch {
			case m.AwayGoal > m.HomeGoal:
				rec.Wins++
			case m.AwayGoal < m.HomeGoal:
				rec.Losses++
			default:
				rec.Draws++
			}
		}
	}
	return rec
}

// HeadToHead summarizes the all-time record between two teams from team1's
// perspective, along with the underlying matches.
type HeadToHead struct {
	Team1      string
	Team2      string
	Team1Wins  int
	Team2Wins  int
	Draws      int
	Team1Goals int
	Team2Goals int
	Matches    []Match
}

// HeadToHead computes the record between team1 and team2 across all competitions.
func (s *Store) HeadToHead(team1, team2 string) HeadToHead {
	h := HeadToHead{Team1: s.DisplayForTeam(team1), Team2: s.DisplayForTeam(team2)}
	matches := s.FindMatches(MatchFilter{Team: team1, Opponent: team2, Dedup: true})
	for _, m := range matches {
		h.Matches = append(h.Matches, m)
		if !m.HasScore {
			continue
		}
		var t1Goals, t2Goals int
		if sideMatchesQuery(team1, m.HomeKey, m.HomeBase) {
			t1Goals, t2Goals = m.HomeGoal, m.AwayGoal
		} else {
			t1Goals, t2Goals = m.AwayGoal, m.HomeGoal
		}
		h.Team1Goals += t1Goals
		h.Team2Goals += t2Goals
		switch {
		case t1Goals > t2Goals:
			h.Team1Wins++
		case t2Goals > t1Goals:
			h.Team2Wins++
		default:
			h.Draws++
		}
	}
	return h
}

// standingsSourcePriority ranks the datasets for standings computation: lower
// is preferred. We compute a table from a single dataset (rather than the merged
// pool) so the overlapping Brasileirão sources can't double-count games, and we
// prefer sources that carry club-distinguishing state suffixes.
var standingsSourcePriority = map[string]int{
	"Brasileirao_Matches.csv":        1,
	"novo_campeonato_brasileiro.csv": 2,
	"Brazilian_Cup_Matches.csv":      3,
	"Libertadores_Matches.csv":       4,
	"BR-Football-Dataset.csv":        5,
}

// Standings computes a league table for a competition and season from match
// results, sorted by points, then wins, then goal difference, then goals for.
func (s *Store) Standings(competition string, season int) []TeamRecord {
	compK := normKey(competition)

	// Select the single highest-priority source that has scored matches for
	// this competition+season.
	bestSrc, bestPri := "", 1<<30
	for _, m := range s.Matches {
		if m.Season != season || !m.HasScore {
			continue
		}
		if compK != "" && !strings.Contains(normKey(m.Competition), compK) {
			continue
		}
		pri, ok := standingsSourcePriority[m.Source]
		if !ok {
			pri = 99
		}
		if pri < bestPri {
			bestPri, bestSrc = pri, m.Source
		}
	}

	var matches []Match
	for _, m := range s.Matches {
		if m.Source != bestSrc || m.Season != season || !m.HasScore {
			continue
		}
		if compK != "" && !strings.Contains(normKey(m.Competition), compK) {
			continue
		}
		matches = append(matches, m)
	}

	byTeam := map[string]*TeamRecord{}
	get := func(key string) *TeamRecord {
		if r, ok := byTeam[key]; ok {
			return r
		}
		r := &TeamRecord{Team: s.DisplayName(key)}
		byTeam[key] = r
		return r
	}
	for _, m := range matches {
		if !m.HasScore {
			continue
		}
		home, away := get(m.HomeKey), get(m.AwayKey)
		home.Matches++
		away.Matches++
		home.GoalsFor += m.HomeGoal
		home.GoalsAgainst += m.AwayGoal
		away.GoalsFor += m.AwayGoal
		away.GoalsAgainst += m.HomeGoal
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
	table := make([]TeamRecord, 0, len(byTeam))
	for _, r := range byTeam {
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

// CompetitionStats holds aggregate statistics for a slice of matches.
type CompetitionStats struct {
	Matches        int
	WithScore      int
	TotalGoals     int
	HomeWins       int
	AwayWins       int
	Draws          int
	BiggestWins    []Match // sorted by goal margin, descending
	HighestScoring []Match // sorted by total goals, descending
}

// AvgGoals returns the mean goals per scored match.
func (c CompetitionStats) AvgGoals() float64 {
	if c.WithScore == 0 {
		return 0
	}
	return float64(c.TotalGoals) / float64(c.WithScore)
}

// HomeWinRate returns the fraction of scored matches won by the home side.
func (c CompetitionStats) HomeWinRate() float64 {
	if c.WithScore == 0 {
		return 0
	}
	return float64(c.HomeWins) / float64(c.WithScore)
}

// Stats computes competition-wide aggregate statistics over the matches
// selected by the filter.
func (s *Store) Stats(f MatchFilter) CompetitionStats {
	f.Dedup = true
	matches := s.FindMatches(f)
	c := CompetitionStats{Matches: len(matches)}
	scored := make([]Match, 0, len(matches))
	for _, m := range matches {
		if !m.HasScore {
			continue
		}
		c.WithScore++
		c.TotalGoals += m.HomeGoal + m.AwayGoal
		switch m.Winner() {
		case "home":
			c.HomeWins++
		case "away":
			c.AwayWins++
		default:
			c.Draws++
		}
		scored = append(scored, m)
	}

	byMargin := append([]Match(nil), scored...)
	sort.SliceStable(byMargin, func(i, j int) bool {
		return absDiff(byMargin[i]) > absDiff(byMargin[j])
	})
	c.BiggestWins = head(byMargin, 10)

	byTotal := append([]Match(nil), scored...)
	sort.SliceStable(byTotal, func(i, j int) bool {
		return (byTotal[i].HomeGoal + byTotal[i].AwayGoal) >
			(byTotal[j].HomeGoal + byTotal[j].AwayGoal)
	})
	c.HighestScoring = head(byTotal, 10)
	return c
}

// Competitions returns the distinct competition labels present, sorted.
func (s *Store) Competitions() []string {
	set := map[string]bool{}
	for _, m := range s.Matches {
		set[m.Competition] = true
	}
	out := make([]string, 0, len(set))
	for c := range set {
		out = append(out, c)
	}
	sort.Strings(out)
	return out
}

// Seasons returns the distinct seasons available for a competition, sorted
// ascending. An empty competition returns seasons across all competitions.
func (s *Store) Seasons(competition string) []int {
	compK := normKey(competition)
	set := map[int]bool{}
	for _, m := range s.Matches {
		if m.Season == 0 {
			continue
		}
		if compK != "" && !strings.Contains(normKey(m.Competition), compK) {
			continue
		}
		set[m.Season] = true
	}
	out := make([]int, 0, len(set))
	for y := range set {
		out = append(out, y)
	}
	sort.Ints(out)
	return out
}

// PlayerFilter describes the criteria accepted by SearchPlayers.
type PlayerFilter struct {
	Name        string
	Nationality string
	Club        string
	Position    string
	MinOverall  int
	Limit       int
}

// SearchPlayers returns players matching the filter, sorted by Overall rating
// descending. Name/Nationality/Club use case- and accent-insensitive substring
// matching; Position matches exactly (case-insensitive).
func (s *Store) SearchPlayers(f PlayerFilter) []Player {
	nameK := normKey(f.Name)
	natK := normKey(f.Nationality)
	clubK := teamKey(f.Club)
	posK := normKey(f.Position)

	var out []Player
	for _, p := range s.Players {
		if nameK != "" && !strings.Contains(p.NameKey, nameK) {
			continue
		}
		if natK != "" && !strings.Contains(normKey(p.Nationality), natK) {
			continue
		}
		if clubK != "" && !strings.Contains(p.ClubKey, clubK) {
			continue
		}
		if posK != "" && normKey(p.Position) != posK {
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

// absDiff returns the absolute goal margin of a match.
func absDiff(m Match) int {
	d := m.HomeGoal - m.AwayGoal
	if d < 0 {
		return -d
	}
	return d
}

// head returns the first n elements of ms (or all of them if fewer).
func head(ms []Match, n int) []Match {
	if len(ms) > n {
		return ms[:n]
	}
	return ms
}
