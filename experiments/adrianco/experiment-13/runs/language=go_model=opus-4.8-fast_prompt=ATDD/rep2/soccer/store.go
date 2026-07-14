// The in-memory Store and the domain queries that back the MCP tools:
// match finding, team statistics, head-to-head comparison, player search,
// standings calculation, and league-wide statistical aggregation. All matching
// is expressed in domain terms and is name-variation tolerant.
package soccer

import (
	"sort"
	"strconv"
	"strings"
	"time"
)

// Store holds all loaded matches and players and answers domain queries.
type Store struct {
	matches []Match
	players []Player
}

func NewStore() *Store { return &Store{} }

func (s *Store) AddMatch(m Match)   { s.matches = append(s.matches, m) }
func (s *Store) AddPlayer(p Player) { s.players = append(s.players, p) }

// dedupMatches removes the same fixture appearing in more than one source file.
// Within a single competition and season a given ordered (home, away) pairing
// occurs at most once (a double round-robin has A-vs-B and B-vs-A as distinct
// pairings, two-legged cup ties swap venues), so that tuple identifies a
// fixture even when the two sources disagree on its exact date or recorded
// score. Dedup is scoped to one competition label, so the same game listed
// under a different competition name (e.g. "Serie A" vs "Brasileirão") is kept.
// Records with neither a season nor a date are never collapsed (the key is too
// weak to trust).
func (s *Store) dedupMatches() {
	seen := make(map[string]struct{}, len(s.matches))
	out := s.matches[:0]
	for _, m := range s.matches {
		if m.Season == 0 && !m.HasDate {
			out = append(out, m)
			continue
		}
		key := strings.Join([]string{
			strings.ToLower(m.Competition),
			itoa(m.Season),
			IdentityKey(m.HomeTeam),
			IdentityKey(m.AwayTeam),
		}, "|")
		if _, dup := seen[key]; dup {
			continue
		}
		seen[key] = struct{}{}
		out = append(out, m)
	}
	s.matches = out
}

func itoa(n int) string { return strconv.Itoa(n) }

func (s *Store) MatchCount() int  { return len(s.matches) }
func (s *Store) PlayerCount() int { return len(s.players) }

// Competitions returns the distinct competition names present, sorted.
func (s *Store) Competitions() []string {
	seen := map[string]bool{}
	for _, m := range s.matches {
		seen[m.Competition] = true
	}
	out := make([]string, 0, len(seen))
	for c := range seen {
		out = append(out, c)
	}
	sort.Strings(out)
	return out
}

// MatchQuery describes the criteria for FindMatches. Zero-valued fields are
// treated as "no constraint".
type MatchQuery struct {
	Team        string // matches either side
	Opponent    string // when set with Team, restricts to games between them
	HomeTeam    string
	AwayTeam    string
	Competition string
	Season      int
	Start       time.Time
	End         time.Time
	HasStart    bool
	HasEnd      bool
	Limit       int
}

// FindMatches returns matches satisfying the query, most recent first.
func (s *Store) FindMatches(q MatchQuery) []Match {
	var out []Match
	for _, m := range s.matches {
		if q.Competition != "" && !containsFold(m.Competition, q.Competition) {
			continue
		}
		if q.Season != 0 && m.Season != q.Season {
			continue
		}
		if q.HomeTeam != "" && !teamMatches(m.HomeTeam, q.HomeTeam) {
			continue
		}
		if q.AwayTeam != "" && !teamMatches(m.AwayTeam, q.AwayTeam) {
			continue
		}
		if q.Team != "" {
			if !(teamMatches(m.HomeTeam, q.Team) || teamMatches(m.AwayTeam, q.Team)) {
				continue
			}
		}
		if q.Opponent != "" {
			if !(teamMatches(m.HomeTeam, q.Opponent) || teamMatches(m.AwayTeam, q.Opponent)) {
				continue
			}
		}
		// When both Team and Opponent are given, ensure the two are on
		// opposite sides of the same match.
		if q.Team != "" && q.Opponent != "" {
			direct := (teamMatches(m.HomeTeam, q.Team) && teamMatches(m.AwayTeam, q.Opponent)) ||
				(teamMatches(m.HomeTeam, q.Opponent) && teamMatches(m.AwayTeam, q.Team))
			if !direct {
				continue
			}
		}
		if q.HasStart || q.HasEnd {
			if !m.HasDate {
				continue
			}
			if q.HasStart && m.Date.Before(q.Start) {
				continue
			}
			if q.HasEnd && m.Date.After(endOfDay(q.End)) {
				continue
			}
		}
		out = append(out, m)
	}
	sortMatchesRecent(out)
	if q.Limit > 0 && len(out) > q.Limit {
		out = out[:q.Limit]
	}
	return out
}

func endOfDay(t time.Time) time.Time {
	return t.Add(24*time.Hour - time.Nanosecond)
}

// sortMatchesRecent orders matches newest-first; undated matches go last.
func sortMatchesRecent(ms []Match) {
	sort.SliceStable(ms, func(i, j int) bool {
		a, b := ms[i], ms[j]
		if a.HasDate != b.HasDate {
			return a.HasDate // dated before undated
		}
		if a.HasDate && b.HasDate {
			return a.Date.After(b.Date)
		}
		return false
	})
}

// TeamRecord summarises a team's results over a set of matches.
type TeamRecord struct {
	Team         string
	Played       int
	Wins         int
	Draws        int
	Losses       int
	GoalsFor     int
	GoalsAgainst int
}

func (r TeamRecord) WinRate() float64 {
	if r.Played == 0 {
		return 0
	}
	return 100 * float64(r.Wins) / float64(r.Played)
}

// Venue narrows team stats to home or away games.
type Venue int

const (
	VenueAll Venue = iota
	VenueHome
	VenueAway
)

// TeamStats computes a team's record, optionally filtered by competition,
// season, and venue.
func (s *Store) TeamStats(team, competition string, season int, venue Venue) TeamRecord {
	rec := TeamRecord{Team: CleanTeamName(team)}
	for _, m := range s.matches {
		if competition != "" && !containsFold(m.Competition, competition) {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}
		isHome := teamMatches(m.HomeTeam, team)
		isAway := teamMatches(m.AwayTeam, team)
		if !isHome && !isAway {
			continue
		}
		if venue == VenueHome && !isHome {
			continue
		}
		if venue == VenueAway && !isAway {
			continue
		}
		// If a team appears on both sides (name collision), treat as home.
		gf, ga := m.HomeGoals, m.AwayGoals
		if isAway && !isHome {
			gf, ga = m.AwayGoals, m.HomeGoals
		}
		rec.Played++
		rec.GoalsFor += gf
		rec.GoalsAgainst += ga
		switch {
		case gf > ga:
			rec.Wins++
		case gf < ga:
			rec.Losses++
		default:
			rec.Draws++
		}
	}
	if rec.Team == "" {
		rec.Team = team
	}
	return rec
}

// HeadToHead summarises results between two specific teams.
type HeadToHead struct {
	Team1     string
	Team2     string
	Team1Wins int
	Team2Wins int
	Draws     int
	Matches   []Match
}

func (s *Store) HeadToHead(team1, team2 string) HeadToHead {
	h := HeadToHead{Team1: CleanTeamName(team1), Team2: CleanTeamName(team2)}
	matches := s.FindMatches(MatchQuery{Team: team1, Opponent: team2})
	h.Matches = matches
	for _, m := range matches {
		t1Home := teamMatches(m.HomeTeam, team1)
		var t1Goals, t2Goals int
		if t1Home {
			t1Goals, t2Goals = m.HomeGoals, m.AwayGoals
		} else {
			t1Goals, t2Goals = m.AwayGoals, m.HomeGoals
		}
		switch {
		case t1Goals > t2Goals:
			h.Team1Wins++
		case t1Goals < t2Goals:
			h.Team2Wins++
		default:
			h.Draws++
		}
	}
	return h
}

// PlayerQuery describes a player search. Zero-valued fields are ignored.
type PlayerQuery struct {
	Name        string
	Nationality string
	Club        string
	Position    string
	MinOverall  int
	Limit       int
}

// SearchPlayers returns matching players sorted by overall rating (desc).
func (s *Store) SearchPlayers(q PlayerQuery) []Player {
	var out []Player
	for _, p := range s.players {
		if q.Name != "" && !containsFold(p.Name, q.Name) {
			continue
		}
		if q.Nationality != "" && !containsFold(p.Nationality, q.Nationality) {
			continue
		}
		if q.Club != "" && !containsFold(p.Club, q.Club) {
			continue
		}
		if q.Position != "" && !strings.EqualFold(strings.TrimSpace(p.Position), strings.TrimSpace(q.Position)) {
			continue
		}
		if q.MinOverall != 0 && p.Overall < q.MinOverall {
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
	if q.Limit > 0 && len(out) > q.Limit {
		out = out[:q.Limit]
	}
	return out
}

// StandingRow is one line of a calculated league table.
type StandingRow struct {
	Team         string
	Played       int
	Wins         int
	Draws        int
	Losses       int
	GoalsFor     int
	GoalsAgainst int
	Points       int
}

func (r StandingRow) GoalDiff() int { return r.GoalsFor - r.GoalsAgainst }

// Standings computes a points table for a competition+season from match
// results (3 points for a win, 1 for a draw), sorted by points, then goal
// difference, then goals scored, then name.
func (s *Store) Standings(competition string, season int) []StandingRow {
	rows := map[string]*StandingRow{}
	record := func(team string, gf, ga int) {
		k := IdentityKey(team)
		r := rows[k]
		if r == nil {
			r = &StandingRow{Team: team}
			rows[k] = r
		}
		r.Played++
		r.GoalsFor += gf
		r.GoalsAgainst += ga
		switch {
		case gf > ga:
			r.Wins++
			r.Points += 3
		case gf < ga:
			r.Losses++
		default:
			r.Draws++
			r.Points++
		}
	}
	for _, m := range s.matches {
		if competition != "" && !containsFold(m.Competition, competition) {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}
		record(m.HomeTeam, m.HomeGoals, m.AwayGoals)
		record(m.AwayTeam, m.AwayGoals, m.HomeGoals)
	}
	out := make([]StandingRow, 0, len(rows))
	for _, r := range rows {
		out = append(out, *r)
	}
	sort.SliceStable(out, func(i, j int) bool {
		a, b := out[i], out[j]
		if a.Points != b.Points {
			return a.Points > b.Points
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

// LeagueStatistics aggregates competition-wide figures.
type LeagueStatistics struct {
	Competition string
	Season      int
	Matches     int
	TotalGoals  int
	AvgGoals    float64
	HomeWins    int
	AwayWins    int
	Draws       int
	HomeWinRate float64
	BiggestWins []Match // top matches by goal margin, newest tie-break
}

// LeagueStats computes aggregate statistics, optionally scoped to a competition
// and/or season. biggestN controls how many biggest-victory matches to return.
func (s *Store) LeagueStats(competition string, season int, biggestN int) LeagueStatistics {
	stats := LeagueStatistics{Competition: competition, Season: season}
	var scoped []Match
	for _, m := range s.matches {
		if competition != "" && !containsFold(m.Competition, competition) {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}
		scoped = append(scoped, m)
		stats.Matches++
		stats.TotalGoals += m.HomeGoals + m.AwayGoals
		switch {
		case m.HomeGoals > m.AwayGoals:
			stats.HomeWins++
		case m.HomeGoals < m.AwayGoals:
			stats.AwayWins++
		default:
			stats.Draws++
		}
	}
	if stats.Matches > 0 {
		stats.AvgGoals = float64(stats.TotalGoals) / float64(stats.Matches)
		stats.HomeWinRate = 100 * float64(stats.HomeWins) / float64(stats.Matches)
	}
	sort.SliceStable(scoped, func(i, j int) bool {
		mi := abs(scoped[i].HomeGoals - scoped[i].AwayGoals)
		mj := abs(scoped[j].HomeGoals - scoped[j].AwayGoals)
		if mi != mj {
			return mi > mj
		}
		ti := scoped[i].HomeGoals + scoped[i].AwayGoals
		tj := scoped[j].HomeGoals + scoped[j].AwayGoals
		return ti > tj
	})
	if biggestN <= 0 {
		biggestN = 5
	}
	if len(scoped) > biggestN {
		scoped = scoped[:biggestN]
	}
	stats.BiggestWins = scoped
	return stats
}

func abs(n int) int {
	if n < 0 {
		return -n
	}
	return n
}
