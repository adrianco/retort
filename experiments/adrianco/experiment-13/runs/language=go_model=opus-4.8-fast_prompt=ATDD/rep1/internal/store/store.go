package store

import (
	"sort"
	"strings"
	"time"
)

// Store holds the loaded datasets and answers domain queries.
type Store struct {
	matches []Match
	players []Player

	teamDisplay map[string]string // identity key -> display name

	// Loading-time bookkeeping (nil after Load returns).
	dedup        map[string]bool            // exact-duplicate guard within/across files
	loadedPairs  map[string]bool            // (competition|season) claimed by earlier files
	currentPairs map[string]bool            // (competition|season) seen in the current file
	teamStates   map[string]map[string]bool // base key -> set of state codes
}

// Counts returns how many matches and players are loaded (for diagnostics).
func (s *Store) Counts() (matches, players int) {
	return len(s.matches), len(s.players)
}

// display returns the canonical display name for a team key.
func (s *Store) display(key string) string {
	if d, ok := s.teamDisplay[key]; ok {
		return d
	}
	return key
}

// MatchFilter describes the criteria for finding matches.
type MatchFilter struct {
	Team        string // primary team (optional)
	Opponent    string // other team (optional)
	Competition string // canonical competition (optional)
	Season      int    // 0 = any
	Venue       string // "home", "away" or "either"/"" relative to Team
	StartDate   *time.Time
	EndDate     *time.Time
	Limit       int // 0 = no limit
}

// matchesFilter returns the subset of matches satisfying a filter, most recent
// first when dates are known.
func (s *Store) matchesFilter(f MatchFilter) []Match {
	comp := ""
	if f.Competition != "" {
		comp = NormalizeCompetition(f.Competition)
	}
	venue := strings.ToLower(strings.TrimSpace(f.Venue))

	var out []Match
	for _, m := range s.matches {
		if comp != "" && m.Competition != comp {
			continue
		}
		if f.Season != 0 && m.Season != f.Season {
			continue
		}
		if f.StartDate != nil && (!m.HasDate || m.Date.Before(*f.StartDate)) {
			continue
		}
		if f.EndDate != nil && (!m.HasDate || m.Date.After(*f.EndDate)) {
			continue
		}
		if f.Team != "" {
			home := teamNameMatches(m.HomeKey, f.Team)
			away := teamNameMatches(m.AwayKey, f.Team)
			switch venue {
			case "home":
				if !home {
					continue
				}
			case "away":
				if !away {
					continue
				}
			default:
				if !home && !away {
					continue
				}
			}
		}
		if f.Opponent != "" {
			if !teamNameMatches(m.HomeKey, f.Opponent) && !teamNameMatches(m.AwayKey, f.Opponent) {
				continue
			}
			// When both team and opponent are set, ensure they are the two sides.
			if f.Team != "" {
				a := teamNameMatches(m.HomeKey, f.Team) && teamNameMatches(m.AwayKey, f.Opponent)
				b := teamNameMatches(m.AwayKey, f.Team) && teamNameMatches(m.HomeKey, f.Opponent)
				if !a && !b {
					continue
				}
			}
		}
		out = append(out, m)
	}

	sortMatchesByDateDesc(out)
	if f.Limit > 0 && len(out) > f.Limit {
		out = out[:f.Limit]
	}
	return out
}

func sortMatchesByDateDesc(ms []Match) {
	sort.SliceStable(ms, func(i, j int) bool {
		if ms[i].HasDate != ms[j].HasDate {
			return ms[i].HasDate // dated matches first
		}
		return ms[i].Date.After(ms[j].Date)
	})
}

// FindMatches returns matches for a filter together with a head-to-head summary
// when both Team and Opponent are provided.
func (s *Store) FindMatches(f MatchFilter) ([]Match, *HeadToHead) {
	ms := s.matchesFilter(f)
	if f.Team == "" || f.Opponent == "" {
		return ms, nil
	}
	h := s.headToHeadFrom(ms, f.Team, f.Opponent)
	return ms, &h
}

// HeadToHead summarises results between a team and an opponent from the team's
// perspective.
type HeadToHead struct {
	Team          string
	Opponent      string
	Matches       int
	TeamWins      int
	OpponentWins  int
	Draws         int
	TeamGoals     int
	OpponentGoals int
}

func (s *Store) headToHeadFrom(ms []Match, team, opponent string) HeadToHead {
	h := HeadToHead{
		Team:     s.canonicalName(team),
		Opponent: s.canonicalName(opponent),
	}
	for _, m := range ms {
		var teamGoals, oppGoals int
		switch {
		case teamNameMatches(m.HomeKey, team):
			teamGoals, oppGoals = m.HomeGoals, m.AwayGoals
		case teamNameMatches(m.AwayKey, team):
			teamGoals, oppGoals = m.AwayGoals, m.HomeGoals
		default:
			continue
		}
		h.Matches++
		h.TeamGoals += teamGoals
		h.OpponentGoals += oppGoals
		switch {
		case teamGoals > oppGoals:
			h.TeamWins++
		case teamGoals < oppGoals:
			h.OpponentWins++
		default:
			h.Draws++
		}
	}
	return h
}

// canonicalName resolves a query to a display name for labelling results. When
// the query matches a single team it returns that team's display name; when the
// base name is shared across several state variants it returns the plain base
// name (without a state qualifier) rather than arbitrarily picking one variant.
func (s *Store) canonicalName(query string) string {
	q := NormalizeTeam(query)
	exact := ""
	exactCount := 0
	best := ""
	for key, disp := range s.teamDisplay {
		base, _ := splitIdentity(key)
		if base == q {
			exact = disp
			exactCount++
			continue
		}
		if best == "" && (strings.Contains(base, q) || strings.Contains(q, base)) {
			best = disp
		}
	}
	switch {
	case exactCount == 1:
		return exact
	case exactCount > 1:
		return CleanTeamName(query) // ambiguous base name; use the plain name
	case best != "":
		return best
	default:
		return CleanTeamName(query)
	}
}

// TeamStats aggregates a team's record under a filter.
type TeamStats struct {
	Team           string
	Matches        int
	Wins           int
	Draws          int
	Losses         int
	GoalsFor       int
	GoalsAgainst   int
	GoalDifference int
	Points         int
	WinRate        float64
}

// TeamStats computes a team's win/draw/loss record and goals.
func (s *Store) TeamStats(f MatchFilter) TeamStats {
	ms := s.matchesFilter(f)
	venue := strings.ToLower(strings.TrimSpace(f.Venue))
	ts := TeamStats{Team: s.canonicalName(f.Team)}
	for _, m := range ms {
		var gf, ga int
		switch {
		case teamNameMatches(m.HomeKey, f.Team) && venue != "away":
			gf, ga = m.HomeGoals, m.AwayGoals
		case teamNameMatches(m.AwayKey, f.Team) && venue != "home":
			gf, ga = m.AwayGoals, m.HomeGoals
		default:
			continue
		}
		ts.Matches++
		ts.GoalsFor += gf
		ts.GoalsAgainst += ga
		switch {
		case gf > ga:
			ts.Wins++
		case gf < ga:
			ts.Losses++
		default:
			ts.Draws++
		}
	}
	ts.GoalDifference = ts.GoalsFor - ts.GoalsAgainst
	ts.Points = ts.Wins*3 + ts.Draws
	if ts.Matches > 0 {
		ts.WinRate = round3(float64(ts.Wins) / float64(ts.Matches))
	}
	return ts
}

// HeadToHead compares two teams across all competitions.
func (s *Store) HeadToHead(teamA, teamB string) HeadToHead {
	ms := s.matchesFilter(MatchFilter{Team: teamA, Opponent: teamB})
	return s.headToHeadFrom(ms, teamA, teamB)
}

// PlayerFilter describes the criteria for searching players.
type PlayerFilter struct {
	Name        string
	Nationality string
	Club        string
	Position    string
	Limit       int
}

// SearchPlayers returns matching players sorted by overall rating (desc).
func (s *Store) SearchPlayers(f PlayerFilter) []Player {
	var out []Player
	for _, p := range s.players {
		if f.Name != "" && !containsFold(p.Name, f.Name) {
			continue
		}
		if f.Nationality != "" && !containsFold(p.Nationality, f.Nationality) {
			continue
		}
		if f.Club != "" && !containsFold(p.Club, f.Club) {
			continue
		}
		if f.Position != "" && !strings.EqualFold(strings.TrimSpace(p.Position), strings.TrimSpace(f.Position)) {
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

// Standing is a single row of a calculated league table.
type Standing struct {
	Position       int
	Team           string
	Points         int
	Played         int
	Wins           int
	Draws          int
	Losses         int
	GoalsFor       int
	GoalsAgainst   int
	GoalDifference int
}

// Standings computes a league table for a competition and season from results.
func (s *Store) Standings(competition string, season int) []Standing {
	comp := NormalizeCompetition(competition)
	agg := map[string]*Standing{}
	get := func(key, display string) *Standing {
		if st, ok := agg[key]; ok {
			return st
		}
		st := &Standing{Team: display}
		agg[key] = st
		return st
	}
	for _, m := range s.matches {
		if comp != "" && m.Competition != comp {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}
		home := get(m.HomeKey, m.HomeTeam)
		away := get(m.AwayKey, m.AwayTeam)
		home.Played++
		away.Played++
		home.GoalsFor += m.HomeGoals
		home.GoalsAgainst += m.AwayGoals
		away.GoalsFor += m.AwayGoals
		away.GoalsAgainst += m.HomeGoals
		switch {
		case m.HomeGoals > m.AwayGoals:
			home.Wins++
			away.Losses++
		case m.HomeGoals < m.AwayGoals:
			away.Wins++
			home.Losses++
		default:
			home.Draws++
			away.Draws++
		}
	}

	table := make([]Standing, 0, len(agg))
	for _, st := range agg {
		st.Points = st.Wins*3 + st.Draws
		st.GoalDifference = st.GoalsFor - st.GoalsAgainst
		table = append(table, *st)
	}
	sort.SliceStable(table, func(i, j int) bool {
		a, b := table[i], table[j]
		if a.Points != b.Points {
			return a.Points > b.Points
		}
		if a.Wins != b.Wins {
			return a.Wins > b.Wins
		}
		if a.GoalDifference != b.GoalDifference {
			return a.GoalDifference > b.GoalDifference
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

// BiggestWin is a lopsided result for the statistical-analysis tool.
type BiggestWin struct {
	Match  Match
	Margin int
}

// LeagueStats aggregates competition-wide statistics.
type LeagueStats struct {
	TotalMatches     int
	TotalGoals       int
	AvgGoalsPerMatch float64
	HomeWins         int
	AwayWins         int
	Draws            int
	HomeWinRate      float64
	BiggestWins      []BiggestWin
}

// LeagueStats computes aggregate stats for a competition/season filter.
func (s *Store) LeagueStats(competition string, season int) LeagueStats {
	comp := ""
	if competition != "" {
		comp = NormalizeCompetition(competition)
	}
	var ls LeagueStats
	var wins []BiggestWin
	for _, m := range s.matches {
		if comp != "" && m.Competition != comp {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}
		ls.TotalMatches++
		ls.TotalGoals += m.HomeGoals + m.AwayGoals
		switch {
		case m.HomeGoals > m.AwayGoals:
			ls.HomeWins++
		case m.HomeGoals < m.AwayGoals:
			ls.AwayWins++
		default:
			ls.Draws++
		}
		margin := m.HomeGoals - m.AwayGoals
		if margin < 0 {
			margin = -margin
		}
		wins = append(wins, BiggestWin{Match: m, Margin: margin})
	}
	if ls.TotalMatches > 0 {
		ls.AvgGoalsPerMatch = round3(float64(ls.TotalGoals) / float64(ls.TotalMatches))
		ls.HomeWinRate = round3(float64(ls.HomeWins) / float64(ls.TotalMatches))
	}
	sort.SliceStable(wins, func(i, j int) bool {
		if wins[i].Margin != wins[j].Margin {
			return wins[i].Margin > wins[j].Margin
		}
		ti, tj := wins[i].Match.HomeGoals+wins[i].Match.AwayGoals, wins[j].Match.HomeGoals+wins[j].Match.AwayGoals
		return ti > tj
	})
	if len(wins) > 10 {
		wins = wins[:10]
	}
	ls.BiggestWins = wins
	return ls
}

// Ranking is a single entry in a team ranking.
type Ranking struct {
	Team  string
	Value float64
}

// TeamRankings ranks teams by a metric, optionally restricted to a venue.
// Supported metrics: goals_for, goals_against, wins, draws, losses, points,
// win_rate, matches.
func (s *Store) TeamRankings(competition string, season int, metric, venue string, limit int) []Ranking {
	comp := ""
	if competition != "" {
		comp = NormalizeCompetition(competition)
	}
	venue = strings.ToLower(strings.TrimSpace(venue))
	type acc struct {
		display                     string
		played, wins, draws, losses int
		goalsFor, goalsAgainst      int
	}
	agg := map[string]*acc{}
	get := func(key, display string) *acc {
		if a, ok := agg[key]; ok {
			return a
		}
		a := &acc{display: display}
		agg[key] = a
		return a
	}
	record := func(a *acc, gf, ga int) {
		a.played++
		a.goalsFor += gf
		a.goalsAgainst += ga
		switch {
		case gf > ga:
			a.wins++
		case gf < ga:
			a.losses++
		default:
			a.draws++
		}
	}
	for _, m := range s.matches {
		if comp != "" && m.Competition != comp {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}
		if venue != "away" {
			record(get(m.HomeKey, m.HomeTeam), m.HomeGoals, m.AwayGoals)
		}
		if venue != "home" {
			record(get(m.AwayKey, m.AwayTeam), m.AwayGoals, m.HomeGoals)
		}
	}

	metric = strings.ToLower(strings.TrimSpace(metric))
	if metric == "" {
		metric = "points"
	}
	value := func(a *acc) float64 {
		switch metric {
		case "goals_for", "goals", "scored":
			return float64(a.goalsFor)
		case "goals_against", "conceded":
			return float64(a.goalsAgainst)
		case "wins":
			return float64(a.wins)
		case "draws":
			return float64(a.draws)
		case "losses":
			return float64(a.losses)
		case "matches", "played":
			return float64(a.played)
		case "win_rate":
			if a.played == 0 {
				return 0
			}
			return round3(float64(a.wins) / float64(a.played))
		default: // points
			return float64(a.wins*3 + a.draws)
		}
	}
	ascending := metric == "goals_against" || metric == "conceded" || metric == "losses"

	out := make([]Ranking, 0, len(agg))
	for _, a := range agg {
		out = append(out, Ranking{Team: a.display, Value: value(a)})
	}
	sort.SliceStable(out, func(i, j int) bool {
		if out[i].Value != out[j].Value {
			if ascending {
				return out[i].Value < out[j].Value
			}
			return out[i].Value > out[j].Value
		}
		return out[i].Team < out[j].Team
	})
	if limit > 0 && len(out) > limit {
		out = out[:limit]
	}
	return out
}

// round3 rounds to three decimal places.
func round3(f float64) float64 {
	return float64(int64(f*1000+0.5)) / 1000
}
