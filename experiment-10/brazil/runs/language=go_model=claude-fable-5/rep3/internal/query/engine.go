// Package query implements the analysis layer of the Brazilian Soccer MCP
// server.
//
// Context: it operates on the deduplicated data.Dataset and answers the
// query categories required by TASK.md — match search, head-to-head,
// team statistics, league standings calculated from results, player
// search, and aggregate statistics (goals per match, home win rate,
// biggest wins). All team inputs go through data.NormalizeTeam so user
// queries match every dataset spelling.
package query

import (
	"fmt"
	"sort"
	"strings"
	"time"

	"brazilian-soccer-mcp/internal/data"
)

// Engine wraps a loaded dataset with query methods.
type Engine struct {
	DS *data.Dataset
}

func New(ds *data.Dataset) *Engine { return &Engine{DS: ds} }

// DisplayName returns the presentation name for a normalized team key.
func (e *Engine) DisplayName(norm string) string {
	if n, ok := e.DS.TeamNames[norm]; ok {
		return n
	}
	return norm
}

// resolveTeam maps a user-supplied team query to a normalized key present
// in the dataset, preferring an exact normalized match over a substring
// match (shortest substring match wins to avoid e.g. "santos" hitting
// "santos laguna" first).
func (e *Engine) resolveTeam(query string) (string, bool) {
	q := data.NormalizeTeam(query)
	if q == "" {
		return "", false
	}
	if _, ok := e.DS.TeamNames[q]; ok {
		return q, true
	}
	best := ""
	for norm := range e.DS.TeamNames {
		if strings.Contains(norm, q) && (best == "" || len(norm) < len(best)) {
			best = norm
		}
	}
	return best, best != ""
}

// MatchFilter selects matches; zero values mean "any".
type MatchFilter struct {
	Team        string // either side
	Opponent    string // requires Team; restricts to fixtures between the two
	Competition string // substring match on competition name
	Season      int
	DateFrom    time.Time
	DateTo      time.Time
}

func matchesCompetition(comp, query string) bool {
	if query == "" {
		return true
	}
	c := data.FoldAccents(comp)
	q := data.FoldAccents(query)
	if strings.Contains(c, q) {
		return true
	}
	// Friendly synonyms.
	switch {
	case strings.Contains(q, "brasileir") || q == "serie a":
		return c == data.FoldAccents(data.CompSerieA)
	case strings.Contains(q, "libertadores"):
		return c == data.FoldAccents(data.CompLibertadores)
	case strings.Contains(q, "copa do brasil") || strings.Contains(q, "cup"):
		return c == data.FoldAccents(data.CompCopaDoBrasil)
	}
	return false
}

// FindMatches returns matches satisfying the filter, newest first.
func (e *Engine) FindMatches(f MatchFilter) []*data.Match {
	var teamNorm, oppNorm string
	if f.Team != "" {
		var ok bool
		if teamNorm, ok = e.resolveTeam(f.Team); !ok {
			return nil
		}
	}
	if f.Opponent != "" {
		var ok bool
		if oppNorm, ok = e.resolveTeam(f.Opponent); !ok {
			return nil
		}
	}
	var out []*data.Match
	for _, m := range e.DS.Matches {
		if teamNorm != "" && !m.Involves(teamNorm) {
			continue
		}
		if oppNorm != "" && !m.Involves(oppNorm) {
			continue
		}
		if teamNorm != "" && oppNorm != "" && teamNorm == oppNorm {
			continue
		}
		if !matchesCompetition(m.Competition, f.Competition) {
			continue
		}
		if f.Season != 0 && m.Season != f.Season {
			continue
		}
		if !f.DateFrom.IsZero() && m.Date.Before(f.DateFrom) {
			continue
		}
		if !f.DateTo.IsZero() && m.Date.After(f.DateTo) {
			continue
		}
		out = append(out, m)
	}
	sort.Slice(out, func(i, j int) bool { return out[i].Date.After(out[j].Date) })
	return out
}

// TeamRecord is an aggregate win/draw/loss record.
type TeamRecord struct {
	Team         string
	Matches      int
	Wins         int
	Draws        int
	Losses       int
	GoalsFor     int
	GoalsAgainst int
}

func (r *TeamRecord) Points() int   { return r.Wins*3 + r.Draws }
func (r *TeamRecord) GoalDiff() int { return r.GoalsFor - r.GoalsAgainst }
func (r *TeamRecord) WinRate() float64 {
	if r.Matches == 0 {
		return 0
	}
	return float64(r.Wins) / float64(r.Matches) * 100
}

func (r *TeamRecord) add(gf, ga int) {
	r.Matches++
	r.GoalsFor += gf
	r.GoalsAgainst += ga
	switch {
	case gf > ga:
		r.Wins++
	case gf < ga:
		r.Losses++
	default:
		r.Draws++
	}
}

// TeamStats computes a team's record. venue is "all", "home" or "away".
func (e *Engine) TeamStats(team string, season int, competition, venue string) (*TeamRecord, []*data.Match, error) {
	norm, ok := e.resolveTeam(team)
	if !ok {
		return nil, nil, fmt.Errorf("team %q not found in dataset", team)
	}
	matches := e.FindMatches(MatchFilter{Team: norm, Season: season, Competition: competition})
	rec := &TeamRecord{Team: e.DisplayName(norm)}
	var used []*data.Match
	for _, m := range matches {
		home := m.HomeNorm == norm
		if venue == "home" && !home || venue == "away" && home {
			continue
		}
		if home {
			rec.add(m.HomeGoals, m.AwayGoals)
		} else {
			rec.add(m.AwayGoals, m.HomeGoals)
		}
		used = append(used, m)
	}
	return rec, used, nil
}

// HeadToHead summarizes fixtures between two teams.
type HeadToHead struct {
	Team1, Team2                string
	Team1Wins, Team2Wins, Draws int
	Team1Goals, Team2Goals      int
	Matches                     []*data.Match
}

func (e *Engine) HeadToHead(team1, team2, competition string) (*HeadToHead, error) {
	n1, ok1 := e.resolveTeam(team1)
	n2, ok2 := e.resolveTeam(team2)
	if !ok1 {
		return nil, fmt.Errorf("team %q not found in dataset", team1)
	}
	if !ok2 {
		return nil, fmt.Errorf("team %q not found in dataset", team2)
	}
	if n1 == n2 {
		return nil, fmt.Errorf("%q and %q resolve to the same team", team1, team2)
	}
	h := &HeadToHead{Team1: e.DisplayName(n1), Team2: e.DisplayName(n2)}
	h.Matches = e.FindMatches(MatchFilter{Team: n1, Opponent: n2, Competition: competition})
	for _, m := range h.Matches {
		g1, g2 := m.HomeGoals, m.AwayGoals
		if m.HomeNorm != n1 {
			g1, g2 = g2, g1
		}
		h.Team1Goals += g1
		h.Team2Goals += g2
		switch {
		case g1 > g2:
			h.Team1Wins++
		case g2 > g1:
			h.Team2Wins++
		default:
			h.Draws++
		}
	}
	return h, nil
}

// Standings calculates a league table from match results for one season of
// a competition (3 points per win, ordered by points, wins, goal
// difference, goals for).
func (e *Engine) Standings(season int, competition string) []*TeamRecord {
	if competition == "" {
		competition = data.CompSerieA
	}
	table := map[string]*TeamRecord{}
	for _, m := range e.DS.Matches {
		if m.Season != season || !matchesCompetition(m.Competition, competition) {
			continue
		}
		for _, side := range []struct {
			norm   string
			gf, ga int
		}{
			{m.HomeNorm, m.HomeGoals, m.AwayGoals},
			{m.AwayNorm, m.AwayGoals, m.HomeGoals},
		} {
			rec, ok := table[side.norm]
			if !ok {
				rec = &TeamRecord{Team: e.DisplayName(side.norm)}
				table[side.norm] = rec
			}
			rec.add(side.gf, side.ga)
		}
	}
	out := make([]*TeamRecord, 0, len(table))
	for _, r := range table {
		out = append(out, r)
	}
	sort.Slice(out, func(i, j int) bool {
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
		return a.GoalsFor > b.GoalsFor
	})
	return out
}

// PlayerFilter selects players; zero values mean "any".
type PlayerFilter struct {
	Name        string
	Nationality string
	Club        string
	Position    string
	MinOverall  int
}

// FindPlayers returns players satisfying the filter, highest rated first.
func (e *Engine) FindPlayers(f PlayerFilter) []*data.Player {
	name := data.FoldAccents(f.Name)
	nat := data.FoldAccents(f.Nationality)
	club := data.NormalizeTeam(f.Club)
	pos := strings.ToUpper(strings.TrimSpace(f.Position))
	var out []*data.Player
	for _, p := range e.DS.Players {
		if name != "" && !strings.Contains(p.NameNorm, name) {
			continue
		}
		if nat != "" && !strings.Contains(data.FoldAccents(p.Nationality), nat) {
			continue
		}
		if club != "" && !strings.Contains(p.ClubNorm, club) {
			continue
		}
		if pos != "" && !strings.EqualFold(p.Position, pos) {
			continue
		}
		if f.MinOverall > 0 && p.Overall < f.MinOverall {
			continue
		}
		out = append(out, p)
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].Overall != out[j].Overall {
			return out[i].Overall > out[j].Overall
		}
		return out[i].Name < out[j].Name
	})
	return out
}

// CompetitionStats aggregates goal statistics over a set of matches.
type CompetitionStats struct {
	Competition string
	Season      int
	Matches     int
	TotalGoals  int
	HomeWins    int
	AwayWins    int
	Draws       int
}

func (s *CompetitionStats) AvgGoals() float64 {
	if s.Matches == 0 {
		return 0
	}
	return float64(s.TotalGoals) / float64(s.Matches)
}

func (s *CompetitionStats) HomeWinRate() float64 {
	if s.Matches == 0 {
		return 0
	}
	return float64(s.HomeWins) / float64(s.Matches) * 100
}

func (e *Engine) CompetitionStats(competition string, season int) *CompetitionStats {
	st := &CompetitionStats{Competition: competition, Season: season}
	for _, m := range e.DS.Matches {
		if !matchesCompetition(m.Competition, competition) {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}
		st.Matches++
		st.TotalGoals += m.HomeGoals + m.AwayGoals
		switch {
		case m.HomeGoals > m.AwayGoals:
			st.HomeWins++
		case m.AwayGoals > m.HomeGoals:
			st.AwayWins++
		default:
			st.Draws++
		}
	}
	return st
}

// BiggestWins returns matches sorted by margin of victory (then total
// goals), largest first.
func (e *Engine) BiggestWins(competition string, season, limit int) []*data.Match {
	var out []*data.Match
	for _, m := range e.DS.Matches {
		if !matchesCompetition(m.Competition, competition) {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}
		if m.HomeGoals != m.AwayGoals {
			out = append(out, m)
		}
	}
	margin := func(m *data.Match) int {
		d := m.HomeGoals - m.AwayGoals
		if d < 0 {
			d = -d
		}
		return d
	}
	sort.Slice(out, func(i, j int) bool {
		if margin(out[i]) != margin(out[j]) {
			return margin(out[i]) > margin(out[j])
		}
		ti := out[i].HomeGoals + out[i].AwayGoals
		tj := out[j].HomeGoals + out[j].AwayGoals
		if ti != tj {
			return ti > tj
		}
		return out[i].Date.After(out[j].Date)
	})
	if limit > 0 && len(out) > limit {
		out = out[:limit]
	}
	return out
}

// ListTeams returns display names of teams whose key contains the query
// (all teams when query is empty), sorted alphabetically.
func (e *Engine) ListTeams(queryStr string) []string {
	q := data.NormalizeTeam(queryStr)
	var out []string
	for norm, name := range e.DS.TeamNames {
		if q == "" || strings.Contains(norm, q) {
			out = append(out, name)
		}
	}
	sort.Strings(out)
	return out
}
