package main

import (
	"sort"
	"strings"
	"time"
)

// Store holds all match and player data loaded from the provided datasets,
// along with indexes that make common lookups fast.
type Store struct {
	Matches []Match
	Players []Player

	matchesByTeamKey map[string][]int
	playersByClubKey map[string][]int
}

// BuildIndexes populates lookup indexes used to keep query methods fast even
// as the dataset grows. Must be called after Matches/Players are populated.
func (s *Store) BuildIndexes() {
	s.matchesByTeamKey = make(map[string][]int)
	for i, m := range s.Matches {
		s.matchesByTeamKey[m.HomeTeamKey] = append(s.matchesByTeamKey[m.HomeTeamKey], i)
		if m.AwayTeamKey != m.HomeTeamKey {
			s.matchesByTeamKey[m.AwayTeamKey] = append(s.matchesByTeamKey[m.AwayTeamKey], i)
		}
	}
	s.playersByClubKey = make(map[string][]int)
	for i, p := range s.Players {
		s.playersByClubKey[p.ClubKey] = append(s.playersByClubKey[p.ClubKey], i)
	}
}

const defaultLimit = 25

// competitionMatches reports whether m's competition satisfies a
// (lower-cased) competition query. It is a substring match, e.g. "brasileirao"
// matches "Brasileirao", with one carve-out: a bare "brasileirao"/"copa"-style
// query never pulls in "Brasileirao Serie B"/"Serie C" results, since those
// are a different division from the flagship Serie A that a generic query is
// almost always asking about. Mention "serie" explicitly to include them.
func competitionMatches(matchCompetition, queryLower string) bool {
	c := strings.ToLower(matchCompetition)
	if !strings.Contains(c, queryLower) {
		return false
	}
	if (strings.Contains(c, "serie b") || strings.Contains(c, "serie c")) && !strings.Contains(queryLower, "serie") {
		return false
	}
	return true
}

// MatchFilter describes the criteria for a match search.
type MatchFilter struct {
	Team        string // canonical or raw team name; matches home or away
	Opponent    string // if set, the other side of the match must be this team
	Competition string // substring match, case-insensitive
	Season      int    // 0 = any season
	DateFrom    *time.Time
	DateTo      *time.Time
	Limit       int
}

// FilterMatches returns matches satisfying every non-zero field of f, most
// recent first.
func (s *Store) FilterMatches(f MatchFilter) []Match {
	var candidates []Match

	if f.Team != "" {
		teamKey, _ := NormalizeTeamName(f.Team)
		for _, idx := range s.matchesByTeamKey[teamKey] {
			candidates = append(candidates, s.Matches[idx])
		}
	} else {
		candidates = append(candidates, s.Matches...)
	}

	var oppKey string
	if f.Opponent != "" {
		oppKey, _ = NormalizeTeamName(f.Opponent)
	}

	compLower := strings.ToLower(f.Competition)

	result := make([]Match, 0, len(candidates))
	for _, m := range candidates {
		if oppKey != "" && m.HomeTeamKey != oppKey && m.AwayTeamKey != oppKey {
			continue
		}
		if compLower != "" && !competitionMatches(m.Competition, compLower) {
			continue
		}
		if f.Season != 0 && m.Season != f.Season {
			continue
		}
		if f.DateFrom != nil && m.HasDate && m.Date.Before(*f.DateFrom) {
			continue
		}
		if f.DateTo != nil && m.HasDate && m.Date.After(*f.DateTo) {
			continue
		}
		result = append(result, m)
	}

	sort.SliceStable(result, func(i, j int) bool {
		return result[i].Date.After(result[j].Date)
	})

	limit := f.Limit
	if limit <= 0 {
		limit = defaultLimit
	}
	if len(result) > limit {
		result = result[:limit]
	}
	return result
}

// HeadToHeadResult summarizes every meeting between two teams.
type HeadToHeadResult struct {
	TeamA, TeamB string
	Matches      []Match
	WinsA        int
	WinsB        int
	Draws        int
	GoalsA       int
	GoalsB       int
	TotalMatches int
}

// HeadToHead returns every match between teamA and teamB (optionally
// restricted to a competition), most recent first, along with aggregate
// win/draw/goal totals.
func (s *Store) HeadToHead(teamA, teamB, competition string) HeadToHeadResult {
	keyA, dispA := NormalizeTeamName(teamA)
	keyB, dispB := NormalizeTeamName(teamB)
	compLower := strings.ToLower(competition)

	res := HeadToHeadResult{TeamA: dispA, TeamB: dispB}

	var matches []Match
	for _, idx := range s.matchesByTeamKey[keyA] {
		m := s.Matches[idx]
		if m.HomeTeamKey != keyB && m.AwayTeamKey != keyB {
			continue
		}
		if compLower != "" && !competitionMatches(m.Competition, compLower) {
			continue
		}
		matches = append(matches, m)
	}
	sort.SliceStable(matches, func(i, j int) bool { return matches[i].Date.After(matches[j].Date) })

	for _, m := range matches {
		homeIsA := m.HomeTeamKey == keyA
		var goalsA, goalsB int
		if homeIsA {
			goalsA, goalsB = m.HomeGoals, m.AwayGoals
		} else {
			goalsA, goalsB = m.AwayGoals, m.HomeGoals
		}
		res.GoalsA += goalsA
		res.GoalsB += goalsB
		switch {
		case goalsA > goalsB:
			res.WinsA++
		case goalsB > goalsA:
			res.WinsB++
		default:
			res.Draws++
		}
	}

	res.TotalMatches = len(matches)
	res.Matches = matches
	return res
}

// TeamRecordResult summarizes a team's win/loss/draw record.
type TeamRecordResult struct {
	Team          string
	MatchesPlayed int
	Wins          int
	Draws         int
	Losses        int
	GoalsFor      int
	GoalsAgainst  int
}

// WinRate returns the fraction (0-1) of matches won.
func (r TeamRecordResult) WinRate() float64 {
	if r.MatchesPlayed == 0 {
		return 0
	}
	return float64(r.Wins) / float64(r.MatchesPlayed)
}

// TeamRecord computes a team's record, optionally scoped to a season,
// competition, and/or venue ("home", "away", or "" for both).
func (s *Store) TeamRecord(team string, season int, competition string, venue string) TeamRecordResult {
	key, disp := NormalizeTeamName(team)
	compLower := strings.ToLower(competition)
	venue = strings.ToLower(venue)

	res := TeamRecordResult{Team: disp}
	for _, idx := range s.matchesByTeamKey[key] {
		m := s.Matches[idx]
		isHome := m.HomeTeamKey == key
		isAway := m.AwayTeamKey == key
		if !isHome && !isAway {
			continue
		}
		if venue == "home" && !isHome {
			continue
		}
		if venue == "away" && !isAway {
			continue
		}
		if season != 0 && m.Season != season {
			continue
		}
		if compLower != "" && !competitionMatches(m.Competition, compLower) {
			continue
		}

		var goalsFor, goalsAgainst int
		if isHome {
			goalsFor, goalsAgainst = m.HomeGoals, m.AwayGoals
		} else {
			goalsFor, goalsAgainst = m.AwayGoals, m.HomeGoals
		}
		res.MatchesPlayed++
		res.GoalsFor += goalsFor
		res.GoalsAgainst += goalsAgainst
		switch {
		case goalsFor > goalsAgainst:
			res.Wins++
		case goalsFor < goalsAgainst:
			res.Losses++
		default:
			res.Draws++
		}
	}
	return res
}

// StandingRow is one row of a computed league table.
type StandingRow struct {
	Position     int
	Team         string
	Played       int
	Wins         int
	Draws        int
	Losses       int
	GoalsFor     int
	GoalsAgainst int
	Points       int
	Relegated    bool
}

// GoalDiff returns goals-for minus goals-against.
func (r StandingRow) GoalDiff() int { return r.GoalsFor - r.GoalsAgainst }

// Standings computes a league table for the given season and competition
// (substring match, e.g. "brasileirao") from the match results, sorted by
// points, then goal difference, then goals for. The bottom four teams are
// flagged as relegated when the table has 20 or more teams, matching the
// modern Brasileirao Serie A format.
func (s *Store) Standings(season int, competition string) []StandingRow {
	compLower := strings.ToLower(competition)
	totals := make(map[string]*StandingRow)
	var order []string

	for _, m := range s.Matches {
		if season != 0 && m.Season != season {
			continue
		}
		if compLower != "" && !competitionMatches(m.Competition, compLower) {
			continue
		}
		for _, side := range []struct {
			key, disp              string
			goalsFor, goalsAgainst int
		}{
			{m.HomeTeamKey, m.HomeTeam, m.HomeGoals, m.AwayGoals},
			{m.AwayTeamKey, m.AwayTeam, m.AwayGoals, m.HomeGoals},
		} {
			row, ok := totals[side.key]
			if !ok {
				row = &StandingRow{Team: side.disp}
				totals[side.key] = row
				order = append(order, side.key)
			}
			row.Played++
			row.GoalsFor += side.goalsFor
			row.GoalsAgainst += side.goalsAgainst
			switch {
			case side.goalsFor > side.goalsAgainst:
				row.Wins++
				row.Points += 3
			case side.goalsFor < side.goalsAgainst:
				row.Losses++
			default:
				row.Draws++
				row.Points++
			}
		}
	}

	rows := make([]StandingRow, 0, len(order))
	for _, key := range order {
		rows = append(rows, *totals[key])
	}
	sort.SliceStable(rows, func(i, j int) bool {
		if rows[i].Points != rows[j].Points {
			return rows[i].Points > rows[j].Points
		}
		if rows[i].GoalDiff() != rows[j].GoalDiff() {
			return rows[i].GoalDiff() > rows[j].GoalDiff()
		}
		return rows[i].GoalsFor > rows[j].GoalsFor
	})
	for i := range rows {
		rows[i].Position = i + 1
		if len(rows) >= 20 && i >= len(rows)-4 {
			rows[i].Relegated = true
		}
	}
	return rows
}

// PlayerFilter describes the criteria for a player search.
type PlayerFilter struct {
	Name        string // substring match, case-insensitive
	Nationality string // substring match, case-insensitive
	Club        string // matched against normalized club name
	Position    string // exact match, case-insensitive
	MinOverall  int
	Limit       int
}

func (s *Store) filterPlayers(f PlayerFilter) []Player {
	var clubKey string
	if f.Club != "" {
		clubKey, _ = NormalizeTeamName(f.Club)
	}
	nameLower := strings.ToLower(f.Name)
	natLower := strings.ToLower(f.Nationality)
	posLower := strings.ToLower(f.Position)

	var candidates []Player
	if clubKey != "" {
		for _, idx := range s.playersByClubKey[clubKey] {
			candidates = append(candidates, s.Players[idx])
		}
	} else {
		candidates = s.Players
	}

	result := make([]Player, 0, len(candidates))
	for _, p := range candidates {
		if nameLower != "" && !strings.Contains(strings.ToLower(p.Name), nameLower) {
			continue
		}
		if natLower != "" && !strings.Contains(strings.ToLower(p.Nationality), natLower) {
			continue
		}
		if posLower != "" && strings.ToLower(p.Position) != posLower {
			continue
		}
		if f.MinOverall != 0 && p.Overall < f.MinOverall {
			continue
		}
		result = append(result, p)
	}
	return result
}

// SearchPlayers returns players matching f, sorted by descending Overall
// rating.
func (s *Store) SearchPlayers(f PlayerFilter) []Player {
	result := s.filterPlayers(f)
	sort.SliceStable(result, func(i, j int) bool { return result[i].Overall > result[j].Overall })
	limit := f.Limit
	if limit <= 0 {
		limit = defaultLimit
	}
	if len(result) > limit {
		result = result[:limit]
	}
	return result
}

// TeamPlayersResult summarizes the FIFA-dataset players associated with a
// club, joined to the club's canonical name via team-name normalization.
type TeamPlayersResult struct {
	Team           string
	Players        []Player
	AverageOverall float64
}

// TeamPlayers returns every FIFA player whose club normalizes to the same
// canonical team as `team`, most highly rated first.
func (s *Store) TeamPlayers(team string, limit int) TeamPlayersResult {
	key, disp := NormalizeTeamName(team)
	var players []Player
	for _, idx := range s.playersByClubKey[key] {
		players = append(players, s.Players[idx])
	}
	sort.SliceStable(players, func(i, j int) bool { return players[i].Overall > players[j].Overall })

	var sum int
	for _, p := range players {
		sum += p.Overall
	}
	avg := 0.0
	if len(players) > 0 {
		avg = float64(sum) / float64(len(players))
	}

	if limit <= 0 {
		limit = defaultLimit
	}
	shown := players
	if len(shown) > limit {
		shown = shown[:limit]
	}

	return TeamPlayersResult{Team: disp, Players: shown, AverageOverall: avg}
}

// BiggestWins returns the largest victories (by absolute goal difference)
// matching the given competition/season filters, biggest first.
func (s *Store) BiggestWins(competition string, season int, limit int) []Match {
	compLower := strings.ToLower(competition)
	var result []Match
	for _, m := range s.Matches {
		if season != 0 && m.Season != season {
			continue
		}
		if compLower != "" && !competitionMatches(m.Competition, compLower) {
			continue
		}
		if m.Winner() == "draw" {
			continue
		}
		result = append(result, m)
	}
	sort.SliceStable(result, func(i, j int) bool {
		if result[i].GoalDiff() != result[j].GoalDiff() {
			return result[i].GoalDiff() > result[j].GoalDiff()
		}
		return result[i].Date.After(result[j].Date)
	})
	if limit <= 0 {
		limit = defaultLimit
	}
	if len(result) > limit {
		result = result[:limit]
	}
	return result
}

// StatsSummaryResult holds aggregate statistics over a set of matches.
type StatsSummaryResult struct {
	MatchesConsidered int
	AvgGoalsPerMatch  float64
	HomeWinRate       float64
	AwayWinRate       float64
	DrawRate          float64
	BiggestWin        *Match
}

// StatsSummary computes aggregate statistics (average goals, home/away/draw
// rates, biggest win) over matches filtered by competition and season.
func (s *Store) StatsSummary(competition string, season int) StatsSummaryResult {
	compLower := strings.ToLower(competition)
	var res StatsSummaryResult
	var totalGoals, home, away, draw int
	var biggest *Match

	for i := range s.Matches {
		m := &s.Matches[i]
		if season != 0 && m.Season != season {
			continue
		}
		if compLower != "" && !competitionMatches(m.Competition, compLower) {
			continue
		}
		res.MatchesConsidered++
		totalGoals += m.HomeGoals + m.AwayGoals
		switch m.Winner() {
		case "home":
			home++
		case "away":
			away++
		default:
			draw++
		}
		if biggest == nil || m.GoalDiff() > biggest.GoalDiff() {
			biggest = m
		}
	}

	if res.MatchesConsidered > 0 {
		n := float64(res.MatchesConsidered)
		res.AvgGoalsPerMatch = float64(totalGoals) / n
		res.HomeWinRate = float64(home) / n
		res.AwayWinRate = float64(away) / n
		res.DrawRate = float64(draw) / n
		res.BiggestWin = biggest
	}
	return res
}

// BestRecord ranks teams by win rate for the given competition/season and
// venue ("home", "away", or "" for both), requiring at least minMatches
// played, best record first.
func (s *Store) BestRecord(competition string, season int, venue string, minMatches int, limit int) []TeamRecordResult {
	compLower := strings.ToLower(competition)
	venue = strings.ToLower(venue)
	totals := make(map[string]*TeamRecordResult)
	var order []string

	for _, m := range s.Matches {
		if season != 0 && m.Season != season {
			continue
		}
		if compLower != "" && !competitionMatches(m.Competition, compLower) {
			continue
		}
		sides := []struct {
			key, disp              string
			isHome                 bool
			goalsFor, goalsAgainst int
		}{}
		if venue != "away" {
			sides = append(sides, struct {
				key, disp              string
				isHome                 bool
				goalsFor, goalsAgainst int
			}{m.HomeTeamKey, m.HomeTeam, true, m.HomeGoals, m.AwayGoals})
		}
		if venue != "home" {
			sides = append(sides, struct {
				key, disp              string
				isHome                 bool
				goalsFor, goalsAgainst int
			}{m.AwayTeamKey, m.AwayTeam, false, m.AwayGoals, m.HomeGoals})
		}
		for _, side := range sides {
			row, ok := totals[side.key]
			if !ok {
				row = &TeamRecordResult{Team: side.disp}
				totals[side.key] = row
				order = append(order, side.key)
			}
			row.MatchesPlayed++
			row.GoalsFor += side.goalsFor
			row.GoalsAgainst += side.goalsAgainst
			switch {
			case side.goalsFor > side.goalsAgainst:
				row.Wins++
			case side.goalsFor < side.goalsAgainst:
				row.Losses++
			default:
				row.Draws++
			}
		}
	}

	rows := make([]TeamRecordResult, 0, len(order))
	for _, key := range order {
		r := *totals[key]
		if r.MatchesPlayed < minMatches {
			continue
		}
		rows = append(rows, r)
	}
	sort.SliceStable(rows, func(i, j int) bool {
		if rows[i].WinRate() != rows[j].WinRate() {
			return rows[i].WinRate() > rows[j].WinRate()
		}
		return rows[i].MatchesPlayed > rows[j].MatchesPlayed
	})
	if limit <= 0 {
		limit = defaultLimit
	}
	if len(rows) > limit {
		rows = rows[:limit]
	}
	return rows
}
