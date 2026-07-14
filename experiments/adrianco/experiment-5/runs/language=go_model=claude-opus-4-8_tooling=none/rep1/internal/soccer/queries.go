// Context:
//   - This file is the analytical heart of the knowledge base. It turns the
//     unified Match/Player slices into the answers the MCP tools expose:
//     match search, head-to-head records, team statistics, league standings
//     (computed from results), league-wide aggregates and player search.
//   - All inputs are loose, user-friendly filters (team substrings, competition
//     shorthands, optional season / date range). Matching reuses the
//     normalization helpers so "flamengo", "Flamengo-RJ" and "Flamengo" all hit
//     the same records.
//   - Standings use the conventional 3-1-0 points system and the usual
//     tie-breakers (points, goal difference, goals for).
package soccer

import (
	"sort"
	"strings"
	"time"
)

// MatchQuery describes the filters for SearchMatches. Zero-value fields are
// ignored.
type MatchQuery struct {
	Team        string // matches either side
	Opponent    string // when set with Team, restricts to games between the two
	Competition string
	Season      int
	From        time.Time
	To          time.Time
	Venue       string // "home", "away" or "" (relative to Team)
	Limit       int
}

// SearchMatches returns matches passing every set filter, sorted most-recent
// first. A Limit of 0 means "no limit".
func (s *Store) SearchMatches(q MatchQuery) []Match {
	var out []Match
	for _, m := range s.Matches {
		if q.Season != 0 && m.Season != q.Season {
			continue
		}
		if !CompetitionMatches(q.Competition, m.Competition) {
			continue
		}
		if !q.From.IsZero() && (!m.HasDate || m.Date.Before(q.From)) {
			continue
		}
		if !q.To.IsZero() && (!m.HasDate || m.Date.After(q.To)) {
			continue
		}
		if q.Team != "" {
			home := TeamMatches(q.Team, m.HomeNorm)
			away := TeamMatches(q.Team, m.AwayNorm)
			if !home && !away {
				continue
			}
			switch strings.ToLower(q.Venue) {
			case "home":
				if !home {
					continue
				}
			case "away":
				if !away {
					continue
				}
			}
			if q.Opponent != "" {
				oppHome := TeamMatches(q.Opponent, m.HomeNorm)
				oppAway := TeamMatches(q.Opponent, m.AwayNorm)
				if !((home && oppAway) || (away && oppHome)) {
					continue
				}
			}
		}
		out = append(out, m)
	}
	sortByDateDesc(out)
	if q.Limit > 0 && len(out) > q.Limit {
		out = out[:q.Limit]
	}
	return out
}

func sortByDateDesc(ms []Match) {
	sort.SliceStable(ms, func(i, j int) bool {
		if ms[i].Date.Equal(ms[j].Date) {
			return ms[i].Season > ms[j].Season
		}
		return ms[i].Date.After(ms[j].Date)
	})
}

// HeadToHead summarises the record between two teams.
type HeadToHead struct {
	Team1, Team2           string
	Team1Wins, Team2Wins   int
	Draws                  int
	Team1Goals, Team2Goals int
	Matches                []Match
}

// HeadToHead returns the all-competitions head-to-head record between two teams.
func (s *Store) HeadToHead(team1, team2 string) HeadToHead {
	h := HeadToHead{Team1: team1, Team2: team2}
	matches := s.SearchMatches(MatchQuery{Team: team1, Opponent: team2})
	for _, m := range matches {
		if !m.HasScore {
			h.Matches = append(h.Matches, m)
			continue
		}
		// Orient goals relative to team1.
		var t1Goals, t2Goals int
		if TeamMatches(team1, m.HomeNorm) {
			t1Goals, t2Goals = m.HomeGoals, m.AwayGoals
		} else {
			t1Goals, t2Goals = m.AwayGoals, m.HomeGoals
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
		h.Matches = append(h.Matches, m)
	}
	return h
}

// TeamRecord is a win/draw/loss + goals summary for a team.
type TeamRecord struct {
	Team         string
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

// Points returns the 3-1-0 points total.
func (r TeamRecord) Points() int { return r.Wins*3 + r.Draws }

// GoalDiff returns goals for minus goals against.
func (r TeamRecord) GoalDiff() int { return r.GoalsFor - r.GoalsAgainst }

// WinRate returns the fraction of played games won, in the range 0..1.
func (r TeamRecord) WinRate() float64 {
	if r.Played == 0 {
		return 0
	}
	return float64(r.Wins) / float64(r.Played)
}

// TeamStats computes a team's record, optionally filtered by season,
// competition and venue ("home"/"away").
func (s *Store) TeamStats(team string, season int, competition, venue string) TeamRecord {
	rec := TeamRecord{Team: team, Season: season, Competition: competition, Venue: venue}
	matches := s.SearchMatches(MatchQuery{
		Team:        team,
		Competition: competition,
		Season:      season,
		Venue:       venue,
	})
	for _, m := range matches {
		if !m.HasScore {
			continue
		}
		var gf, ga int
		if TeamMatches(team, m.HomeNorm) {
			gf, ga = m.HomeGoals, m.AwayGoals
		} else {
			gf, ga = m.AwayGoals, m.HomeGoals
		}
		rec.Played++
		rec.GoalsFor += gf
		rec.GoalsAgainst += ga
		switch {
		case gf > ga:
			rec.Wins++
		case ga > gf:
			rec.Losses++
		default:
			rec.Draws++
		}
	}
	return rec
}

// Standing is a single row of a computed league table.
type Standing struct {
	Position int
	TeamRecord
}

// Standings computes the final table for a competition + season from results.
func (s *Store) Standings(competition string, season int) []Standing {
	byTeam := map[string]*TeamRecord{}
	display := map[string]string{}
	for _, m := range s.Matches {
		if m.Season != season || !CompetitionMatches(competition, m.Competition) || !m.HasScore {
			continue
		}
		hr := ensureRec(byTeam, m.HomeNorm)
		ar := ensureRec(byTeam, m.AwayNorm)
		display[m.HomeNorm] = m.HomeTeam
		display[m.AwayNorm] = m.AwayTeam

		hr.Played++
		ar.Played++
		hr.GoalsFor += m.HomeGoals
		hr.GoalsAgainst += m.AwayGoals
		ar.GoalsFor += m.AwayGoals
		ar.GoalsAgainst += m.HomeGoals
		switch m.Winner() {
		case "home":
			hr.Wins++
			ar.Losses++
		case "away":
			ar.Wins++
			hr.Losses++
		default:
			hr.Draws++
			ar.Draws++
		}
	}

	table := make([]Standing, 0, len(byTeam))
	for norm, rec := range byTeam {
		rec.Team = display[norm]
		rec.Competition = canonicalCompetition(competition)
		rec.Season = season
		table = append(table, Standing{TeamRecord: *rec})
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
	for i := range table {
		table[i].Position = i + 1
	}
	return table
}

func ensureRec(m map[string]*TeamRecord, key string) *TeamRecord {
	if r, ok := m[key]; ok {
		return r
	}
	r := &TeamRecord{}
	m[key] = r
	return r
}

// LeagueStats are aggregate figures for a competition (optionally a season).
type LeagueStats struct {
	Competition string
	Season      int
	Matches     int
	TotalGoals  int
	HomeWins    int
	AwayWins    int
	Draws       int
	BiggestWins []Match
}

// AvgGoals returns the mean goals per match.
func (l LeagueStats) AvgGoals() float64 {
	if l.Matches == 0 {
		return 0
	}
	return float64(l.TotalGoals) / float64(l.Matches)
}

// HomeWinRate returns the fraction of matches won by the home side.
func (l LeagueStats) HomeWinRate() float64 {
	if l.Matches == 0 {
		return 0
	}
	return float64(l.HomeWins) / float64(l.Matches)
}

// LeagueAggregate computes league-wide statistics and the biggest wins.
// season == 0 means all seasons. topN controls how many biggest wins to return.
func (s *Store) LeagueAggregate(competition string, season, topN int) LeagueStats {
	stats := LeagueStats{Competition: competition, Season: season}
	var played []Match
	for _, m := range s.Matches {
		if season != 0 && m.Season != season {
			continue
		}
		if !CompetitionMatches(competition, m.Competition) || !m.HasScore {
			continue
		}
		stats.Matches++
		stats.TotalGoals += m.TotalGoals()
		switch m.Winner() {
		case "home":
			stats.HomeWins++
		case "away":
			stats.AwayWins++
		default:
			stats.Draws++
		}
		played = append(played, m)
	}
	sort.SliceStable(played, func(i, j int) bool {
		di := abs(played[i].HomeGoals - played[i].AwayGoals)
		dj := abs(played[j].HomeGoals - played[j].AwayGoals)
		if di != dj {
			return di > dj
		}
		return played[i].TotalGoals() > played[j].TotalGoals()
	})
	if topN <= 0 {
		topN = 10
	}
	if len(played) > topN {
		played = played[:topN]
	}
	stats.BiggestWins = played
	return stats
}

func abs(n int) int {
	if n < 0 {
		return -n
	}
	return n
}

// PlayerQuery describes the filters for SearchPlayers. Zero-value fields are
// ignored.
type PlayerQuery struct {
	Name        string
	Nationality string
	Club        string
	Position    string
	MinOverall  int
	Limit       int
}

// SearchPlayers returns players passing every set filter, sorted by overall
// rating (highest first).
func (s *Store) SearchPlayers(q PlayerQuery) []Player {
	name := normalizeText(q.Name)
	nat := normalizeText(q.Nationality)
	club := normalizeText(q.Club)
	pos := strings.ToUpper(strings.TrimSpace(q.Position))

	var out []Player
	for _, p := range s.Players {
		if name != "" && !strings.Contains(p.NameNorm, name) {
			continue
		}
		if nat != "" && normalizeText(p.Nationality) != nat && !strings.Contains(normalizeText(p.Nationality), nat) {
			continue
		}
		if club != "" && !strings.Contains(p.ClubNorm, club) {
			continue
		}
		if pos != "" && strings.ToUpper(p.Position) != pos {
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
