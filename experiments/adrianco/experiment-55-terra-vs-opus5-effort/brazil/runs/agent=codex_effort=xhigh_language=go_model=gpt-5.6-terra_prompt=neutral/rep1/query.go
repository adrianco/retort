package main

import (
	"fmt"
	"sort"
	"strconv"
	"strings"
	"time"
)

// SearchMatches searches all match files. Search results are intentionally not
// deduplicated: the Source field lets callers inspect each dataset's record.
func (d *DataStore) SearchMatches(filter MatchFilter) []Match {
	limit := boundedLimit(filter.Limit, 50, 500)
	matched := d.matchingMatches(filter)
	if len(matched) > limit {
		return matched[:limit]
	}
	return matched
}

func (d *DataStore) matchingMatches(filter MatchFilter) []Match {
	matched := make([]Match, 0)
	for _, m := range d.Matches {
		if !matchMatchesFilter(m, filter) {
			continue
		}
		matched = append(matched, m)
	}
	sort.SliceStable(matched, func(i, j int) bool {
		if matched[i].Date.Equal(matched[j].Date) {
			return matched[i].Source < matched[j].Source
		}
		return matched[i].Date.After(matched[j].Date)
	})
	return matched
}

func matchMatchesFilter(m Match, f MatchFilter) bool {
	home, away := canonicalTeam(m.HomeTeam), canonicalTeam(m.AwayTeam)
	if f.Team != "" {
		team := canonicalTeam(f.Team)
		if home != team && away != team {
			return false
		}
	}
	if f.Opponent != "" {
		opponent := canonicalTeam(f.Opponent)
		if home != opponent && away != opponent {
			return false
		}
	}
	if f.HomeTeam != "" && home != canonicalTeam(f.HomeTeam) {
		return false
	}
	if f.AwayTeam != "" && away != canonicalTeam(f.AwayTeam) {
		return false
	}
	if f.Team != "" && f.Opponent != "" {
		a, b := canonicalTeam(f.Team), canonicalTeam(f.Opponent)
		if !((home == a && away == b) || (home == b && away == a)) {
			return false
		}
	}
	if f.Competition != "" && canonicalCompetition(m.Competition) != canonicalCompetition(f.Competition) {
		return false
	}
	if f.Season != 0 && m.Season != f.Season {
		return false
	}
	if !f.DateFrom.IsZero() && m.Date.Before(startOfDay(f.DateFrom)) {
		return false
	}
	if !f.DateTo.IsZero() && m.Date.After(endOfDay(f.DateTo)) {
		return false
	}
	if f.Round != "" && !strings.EqualFold(strings.TrimSpace(m.Round), strings.TrimSpace(f.Round)) {
		return false
	}
	if f.Stage != "" && !strings.Contains(canonicalText(m.Stage), canonicalText(f.Stage)) {
		return false
	}
	return true
}

func (d *DataStore) TeamStatistics(team string, season int, competition, venue string) TeamStatistics {
	result := TeamStatistics{Team: team, Season: season, Competition: competition, Venue: venue}
	if result.Venue == "" {
		result.Venue = "all"
	}
	canonical := canonicalTeam(team)
	for _, m := range d.uniqueFilteredMatches(MatchFilter{Season: season, Competition: competition}) {
		home, away := canonicalTeam(m.HomeTeam), canonicalTeam(m.AwayTeam)
		isHome, isAway := home == canonical, away == canonical
		if (!isHome && !isAway) || (venue == "home" && !isHome) || (venue == "away" && !isAway) {
			continue
		}
		result.Matches++
		goalsFor, goalsAgainst := m.HomeGoals, m.AwayGoals
		if isAway {
			goalsFor, goalsAgainst = m.AwayGoals, m.HomeGoals
		}
		result.GoalsFor += goalsFor
		result.GoalsAgainst += goalsAgainst
		switch {
		case goalsFor > goalsAgainst:
			result.Wins++
			result.Points += 3
		case goalsFor < goalsAgainst:
			result.Losses++
		default:
			result.Draws++
			result.Points++
		}
	}
	if result.Matches > 0 {
		result.WinRate = percentage(result.Wins, result.Matches)
		result.GoalsPerMatch = round2(float64(result.GoalsFor) / float64(result.Matches))
		result.ConcededPerGame = round2(float64(result.GoalsAgainst) / float64(result.Matches))
	}
	return result
}

func (d *DataStore) HeadToHead(teamA, teamB, competition string, season, limit int) HeadToHead {
	result := HeadToHead{TeamA: teamA, TeamB: teamB}
	filter := MatchFilter{Team: teamA, Opponent: teamB, Competition: competition, Season: season}
	matches := d.matchingMatches(filter)
	// A single match can occur in two supplied datasets. For a historical
	// record, a head-to-head count should describe fixtures rather than CSV rows.
	matches = deduplicateMatches(matches)
	result.MatchesList = limitMatches(matches, limit)
	a := canonicalTeam(teamA)
	for _, m := range matches {
		result.Matches++
		goalsA, goalsB := m.HomeGoals, m.AwayGoals
		if canonicalTeam(m.AwayTeam) == a {
			goalsA, goalsB = goalsB, goalsA
		}
		result.TeamAGoals += goalsA
		result.TeamBGoals += goalsB
		switch {
		case goalsA > goalsB:
			result.TeamAWins++
		case goalsB > goalsA:
			result.TeamBWins++
		default:
			result.Draws++
		}
	}
	return result
}

func (d *DataStore) SearchPlayers(name, nationality, club, position string, limit int) []Player {
	limit = boundedLimit(limit, 50, 500)
	matched := make([]Player, 0)
	for _, p := range d.Players {
		if !containsFold(p.Name, name) || !matchesNationality(p.Nationality, nationality) || !matchesClub(p.Club, club) || !matchesPosition(p.Position, position) {
			continue
		}
		matched = append(matched, p)
	}
	sort.SliceStable(matched, func(i, j int) bool {
		if matched[i].Overall == matched[j].Overall {
			return canonicalText(matched[i].Name) < canonicalText(matched[j].Name)
		}
		return matched[i].Overall > matched[j].Overall
	})
	if len(matched) > limit {
		return matched[:limit]
	}
	return matched
}

func (d *DataStore) Standings(competition string, season int) []Standing {
	rows := map[string]*Standing{}
	for _, m := range d.uniqueFilteredMatches(MatchFilter{Competition: competition, Season: season}) {
		homeName, awayName := canonicalTeam(m.HomeTeam), canonicalTeam(m.AwayTeam)
		home := rows[homeName]
		if home == nil {
			home = &Standing{Team: preferredTeamName(m.HomeTeam)}
			rows[homeName] = home
		}
		away := rows[awayName]
		if away == nil {
			away = &Standing{Team: preferredTeamName(m.AwayTeam)}
			rows[awayName] = away
		}
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
	standings := make([]Standing, 0, len(rows))
	for _, row := range rows {
		row.GoalDiff = row.GoalsFor - row.GoalsAgainst
		row.WinRate = percentage(row.Wins, row.Played)
		standings = append(standings, *row)
	}
	sort.SliceStable(standings, func(i, j int) bool {
		a, b := standings[i], standings[j]
		if a.Points != b.Points {
			return a.Points > b.Points
		}
		if a.Wins != b.Wins {
			return a.Wins > b.Wins
		}
		if a.GoalDiff != b.GoalDiff {
			return a.GoalDiff > b.GoalDiff
		}
		if a.GoalsFor != b.GoalsFor {
			return a.GoalsFor > b.GoalsFor
		}
		return canonicalText(a.Team) < canonicalText(b.Team)
	})
	for i := range standings {
		standings[i].Position = i + 1
	}
	return standings
}

// TeamRankings returns a standings view sorted by a useful analytical metric.
// metric may be points, goals_for, home_win_rate, or away_win_rate.
func (d *DataStore) TeamRankings(competition string, season int, metric string, limit int) ([]Standing, error) {
	if metric == "" {
		metric = "points"
	}
	if metric == "points" {
		return limitStandings(d.Standings(competition, season), limit), nil
	}
	if metric != "goals_for" && metric != "home_win_rate" && metric != "away_win_rate" {
		return nil, fmt.Errorf("unsupported metric %q", metric)
	}
	rows := map[string]*Standing{}
	for _, m := range d.uniqueFilteredMatches(MatchFilter{Competition: competition, Season: season}) {
		name, isHome := canonicalTeam(m.HomeTeam), true
		for _, side := range []struct {
			name    string
			display string
			gf, ga  int
			home    bool
		}{
			{name, m.HomeTeam, m.HomeGoals, m.AwayGoals, isHome},
			{canonicalTeam(m.AwayTeam), m.AwayTeam, m.AwayGoals, m.HomeGoals, false},
		} {
			row := rows[side.name]
			if row == nil {
				row = &Standing{Team: preferredTeamName(side.display)}
				rows[side.name] = row
			}
			row.Played++
			row.GoalsFor += side.gf
			row.GoalsAgainst += side.ga
			if side.gf > side.ga {
				row.Wins++
				row.Points += 3
			} else if side.gf == side.ga {
				row.Draws++
				row.Points++
			} else {
				row.Losses++
			}
		}
	}
	items := make([]Standing, 0, len(rows))
	for _, row := range rows {
		row.GoalDiff = row.GoalsFor - row.GoalsAgainst
		row.WinRate = percentage(row.Wins, row.Played)
		items = append(items, *row)
	}
	if metric == "home_win_rate" || metric == "away_win_rate" {
		// Use team statistics to calculate the requested venue-specific rate,
		// while retaining common aggregate fields in every response.
		for i := range items {
			items[i].WinRate = d.TeamStatistics(items[i].Team, season, competition, strings.TrimSuffix(metric, "_win_rate")).WinRate
		}
	}
	sort.SliceStable(items, func(i, j int) bool {
		if items[i].WinRate != items[j].WinRate {
			return items[i].WinRate > items[j].WinRate
		}
		if items[i].GoalsFor != items[j].GoalsFor {
			return items[i].GoalsFor > items[j].GoalsFor
		}
		return canonicalText(items[i].Team) < canonicalText(items[j].Team)
	})
	if metric == "goals_for" {
		sort.SliceStable(items, func(i, j int) bool {
			if items[i].GoalsFor != items[j].GoalsFor {
				return items[i].GoalsFor > items[j].GoalsFor
			}
			return canonicalText(items[i].Team) < canonicalText(items[j].Team)
		})
	}
	for i := range items {
		items[i].Position = i + 1
	}
	return limitStandings(items, limit), nil
}

func (d *DataStore) CompetitionStatistics(competition string, season int) CompetitionStatistics {
	result := CompetitionStatistics{Competition: competition, Season: season}
	for _, m := range d.uniqueFilteredMatches(MatchFilter{Competition: competition, Season: season}) {
		result.Matches++
		result.Goals += m.HomeGoals + m.AwayGoals
		if m.HomeGoals > m.AwayGoals {
			result.HomeWins++
		} else if m.HomeGoals < m.AwayGoals {
			result.AwayWins++
		} else {
			result.Draws++
		}
	}
	if result.Matches > 0 {
		result.GoalsPerMatch = round2(float64(result.Goals) / float64(result.Matches))
		result.HomeWinRate = percentage(result.HomeWins, result.Matches)
	}
	return result
}

func (d *DataStore) BiggestWins(competition string, season, limit int) []Match {
	items := d.uniqueFilteredMatches(MatchFilter{Competition: competition, Season: season})
	sort.SliceStable(items, func(i, j int) bool {
		di, dj := abs(items[i].HomeGoals-items[i].AwayGoals), abs(items[j].HomeGoals-items[j].AwayGoals)
		if di != dj {
			return di > dj
		}
		gi, gj := items[i].HomeGoals+items[i].AwayGoals, items[j].HomeGoals+items[j].AwayGoals
		if gi != gj {
			return gi > gj
		}
		return items[i].Date.After(items[j].Date)
	})
	return limitMatches(items, limit)
}

type DerbyMatch struct {
	Derby string `json:"derby"`
	Match Match  `json:"match"`
}

func (d *DataStore) Derbies(season int, competition string, limit int) []DerbyMatch {
	rivalries := map[string]string{
		"flamengo|fluminense": "Fla-Flu", "corinthians|palmeiras": "Derby Paulista", "corinthians|sao paulo": "Majestoso",
		"gremio|internacional": "Grenal", "atletico mineiro|cruzeiro": "Clássico Mineiro", "santos|corinthians": "Clássico Alvinegro",
		"palmeiras|sao paulo": "Choque-Rei", "flamengo|vasco da gama": "Clássico dos Milhões", "fluminense|vasco da gama": "Clássico dos Gigantes",
	}
	var result []DerbyMatch
	for _, m := range d.uniqueFilteredMatches(MatchFilter{Season: season, Competition: competition}) {
		a, b := canonicalTeam(m.HomeTeam), canonicalTeam(m.AwayTeam)
		key := a + "|" + b
		if a > b {
			key = b + "|" + a
		}
		if derby, ok := rivalries[key]; ok {
			result = append(result, DerbyMatch{Derby: derby, Match: m})
		}
	}
	sort.SliceStable(result, func(i, j int) bool { return result[i].Match.Date.After(result[j].Match.Date) })
	if len(result) > boundedLimit(limit, 50, 500) {
		return result[:boundedLimit(limit, 50, 500)]
	}
	return result
}

func (d *DataStore) TeamCompetitions(team string) []string {
	found := map[string]bool{}
	for _, m := range d.Matches {
		if canonicalTeam(m.HomeTeam) == canonicalTeam(team) || canonicalTeam(m.AwayTeam) == canonicalTeam(team) {
			found[m.Competition] = true
		}
	}
	items := make([]string, 0, len(found))
	for c := range found {
		items = append(items, c)
	}
	sort.Strings(items)
	return items
}

func (d *DataStore) uniqueFilteredMatches(filter MatchFilter) []Match {
	return selectPreferredSources(deduplicateMatches(d.matchingMatches(filter)))
}

// Several datasets overlap. Search tools preserve every source row, but a
// table or record must use one authoritative dataset per competition/season.
// The purpose-built competition CSVs take precedence over historical and
// extended statistics; the historical CSV is then the fallback for older
// Brasileirão seasons.
func selectPreferredSources(matches []Match) []Match {
	priority := map[string]int{
		"Brasileirao_Matches.csv":        1,
		"Brazilian_Cup_Matches.csv":      1,
		"Libertadores_Matches.csv":       1,
		"novo_campeonato_brasileiro.csv": 2,
		"BR-Football-Dataset.csv":        3,
	}
	best := map[string]int{}
	for _, match := range matches {
		group := canonicalCompetition(match.Competition) + "|" + strconv.Itoa(match.Season)
		if current, found := best[group]; !found || priority[match.Source] < current {
			best[group] = priority[match.Source]
		}
	}
	selected := make([]Match, 0, len(matches))
	for _, match := range matches {
		group := canonicalCompetition(match.Competition) + "|" + strconv.Itoa(match.Season)
		if priority[match.Source] == best[group] {
			selected = append(selected, match)
		}
	}
	return selected
}

func deduplicateMatches(matches []Match) []Match {
	seen := make(map[string]bool, len(matches))
	result := make([]Match, 0, len(matches))
	for _, m := range matches {
		key := fmt.Sprintf("%s|%s|%s|%s|%d|%d", canonicalCompetition(m.Competition), m.Date.Format("2006-01-02"), canonicalTeam(m.HomeTeam), canonicalTeam(m.AwayTeam), m.HomeGoals, m.AwayGoals)
		if !seen[key] {
			seen[key] = true
			result = append(result, m)
		}
	}
	return result
}

func containsFold(value, query string) bool {
	return query == "" || strings.Contains(canonicalText(value), canonicalText(query))
}
func matchesNationality(value, query string) bool {
	return query == "" || strings.Contains(canonicalNationality(value), canonicalNationality(query))
}
func matchesClub(value, query string) bool {
	if query == "" {
		return true
	}
	if strings.TrimSpace(value) == "" {
		return false
	}
	return canonicalTeam(value) == canonicalTeam(query) || containsFold(value, query)
}
func matchesPosition(value, query string) bool {
	q := canonicalText(query)
	if q == "" || strings.Contains(canonicalText(value), q) {
		return true
	}
	position := strings.ToLower(strings.TrimSpace(value))
	groups := map[string]map[string]bool{
		"forward":    {"st": true, "cf": true, "lw": true, "rw": true, "lf": true, "rf": true},
		"midfielder": {"cm": true, "cam": true, "cdm": true, "lm": true, "rm": true},
		"defender":   {"cb": true, "lb": true, "rb": true, "lwb": true, "rwb": true},
		"goalkeeper": {"gk": true},
	}
	if strings.HasSuffix(q, "s") {
		q = strings.TrimSuffix(q, "s")
	}
	return groups[q][position]
}
func boundedLimit(value, fallback, maximum int) int {
	if value <= 0 {
		return fallback
	}
	if value > maximum {
		return maximum
	}
	return value
}
func percentage(n, d int) float64 {
	if d == 0 {
		return 0
	}
	return round2(100 * float64(n) / float64(d))
}
func round2(value float64) float64 { return float64(int(value*100+0.5)) / 100 }
func abs(n int) int {
	if n < 0 {
		return -n
	}
	return n
}
func startOfDay(value time.Time) time.Time {
	return time.Date(value.Year(), value.Month(), value.Day(), 0, 0, 0, 0, time.UTC)
}
func endOfDay(value time.Time) time.Time {
	return startOfDay(value).AddDate(0, 0, 1).Add(-time.Nanosecond)
}
func preferredTeamName(value string) string {
	return strings.TrimSpace(strings.TrimSuffix(strings.TrimSuffix(value, "-SP"), "-RJ"))
}
func limitMatches(items []Match, limit int) []Match {
	limit = boundedLimit(limit, 10, 500)
	if len(items) > limit {
		return items[:limit]
	}
	return items
}
func limitStandings(items []Standing, limit int) []Standing {
	limit = boundedLimit(limit, 50, 500)
	if len(items) > limit {
		return items[:limit]
	}
	return items
}
