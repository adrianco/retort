package main

import (
	"fmt"
	"math"
	"sort"
	"strings"
)

// PlayerFilter controls a case- and accent-insensitive player search.
type PlayerFilter struct {
	Name        string
	Nationality string
	Club        string
	Position    string
	MinOverall  int
	Limit       int
}

// PlayerSearchResult carries both the complete result count and the requested
// page. This prevents an LLM from mistaking a safety limit for the full count.
type PlayerSearchResult struct {
	Total   int      `json:"total"`
	Players []Player `json:"players"`
}

// TeamCompetition summarizes where a team appears across the supplied files.
type TeamCompetition struct {
	Competition string   `json:"competition"`
	Matches     int      `json:"matches"`
	FirstSeason int      `json:"first_season,omitempty"`
	LastSeason  int      `json:"last_season,omitempty"`
	Sources     []string `json:"sources"`
}

// BiggestWin includes the margin explicitly, so a caller does not have to
// infer which side won from the score.
type BiggestWin struct {
	Match  Match  `json:"match"`
	Winner string `json:"winner"`
	Margin int    `json:"margin"`
}

// SeasonComparison is used for questions such as "compare 2018 and 2019".
type SeasonComparison struct {
	Competition string               `json:"competition"`
	Seasons     []CompetitionSummary `json:"seasons"`
}

func roundPercent(value float64) float64 {
	return math.Round(value*10) / 10
}

func (d *DataStore) TeamStatistics(team string, filter MatchFilter, scope string) TeamStatistics {
	if scope == "" {
		scope = "all"
	}
	scope = strings.ToLower(strings.TrimSpace(scope))
	if scope != "home" && scope != "away" {
		scope = "all"
	}
	filter.Team = team
	filter.Limit = 0
	matches := d.SearchMatches(filter)
	stats := TeamStatistics{
		Team: d.DisplayTeam(team), Competition: normalizeCompetition(filter.Competition), Season: filter.Season, Scope: scope,
	}
	teamKey := normalizeTeam(team)
	for _, match := range matches {
		isHome := teamNameMatches(match.HomeKey, teamKey)
		isAway := teamNameMatches(match.AwayKey, teamKey)
		if (scope == "home" && !isHome) || (scope == "away" && !isAway) || !match.HasScore {
			continue
		}
		// A malformed record with the same club in both columns should not be
		// counted twice. Such records are not present in the supplied data, but
		// treating the home side as authoritative makes the behavior deterministic.
		goalsFor, goalsAgainst := match.HomeGoals, match.AwayGoals
		if !isHome && isAway {
			goalsFor, goalsAgainst = match.AwayGoals, match.HomeGoals
		}
		stats.Matches++
		stats.GoalsFor += goalsFor
		stats.GoalsAgainst += goalsAgainst
		switch {
		case goalsFor > goalsAgainst:
			stats.Wins++
			stats.Points += 3
		case goalsFor == goalsAgainst:
			stats.Draws++
			stats.Points++
		default:
			stats.Losses++
		}
	}
	stats.GoalDifference = stats.GoalsFor - stats.GoalsAgainst
	if stats.Matches > 0 {
		stats.WinRate = roundPercent(100 * float64(stats.Wins) / float64(stats.Matches))
		stats.GoalsPerMatch = roundPercent(float64(stats.GoalsFor) / float64(stats.Matches))
	}
	return stats
}

func (d *DataStore) HeadToHead(team, opponent string, filter MatchFilter) HeadToHeadRecord {
	filter.Team = team
	filter.Opponent = opponent
	filter.Limit = 0
	matches := d.SearchMatches(filter)
	record := HeadToHeadRecord{Team: d.DisplayTeam(team), Opponent: d.DisplayTeam(opponent)}
	teamKey := normalizeTeam(team)
	for _, match := range matches {
		if !match.HasScore {
			continue
		}
		teamHome := teamNameMatches(match.HomeKey, teamKey)
		teamGoals, opponentGoals := match.AwayGoals, match.HomeGoals
		if teamHome {
			teamGoals, opponentGoals = match.HomeGoals, match.AwayGoals
		}
		record.Matches++
		record.TeamGoals += teamGoals
		record.OpponentGoals += opponentGoals
		switch {
		case teamGoals > opponentGoals:
			record.TeamWins++
		case teamGoals < opponentGoals:
			record.OpponentWins++
		default:
			record.Draws++
		}
	}
	if record.Matches > 0 {
		record.TeamWinRate = roundPercent(100 * float64(record.TeamWins) / float64(record.Matches))
	}
	return record
}

// Standings calculates a conventional three-points-for-a-win league table.
// Ties are ordered by points, wins, goal difference, goals scored, then name.
func (d *DataStore) Standings(competition string, season int, source string) ([]Standing, error) {
	if season <= 0 {
		return nil, fmt.Errorf("season is required for standings")
	}
	competition = normalizeCompetition(competition)
	if competition == "" {
		competition = "Brasileirão Série A"
	}
	matches := d.SearchMatches(MatchFilter{Competition: competition, Season: season, Source: source})
	byTeam := make(map[string]*Standing)
	ensure := func(key, display string) *Standing {
		if current, ok := byTeam[key]; ok {
			return current
		}
		standing := &Standing{Team: d.DisplayTeam(display)}
		byTeam[key] = standing
		return standing
	}
	for _, match := range matches {
		if !match.HasScore {
			continue
		}
		home := ensure(match.HomeKey, match.HomeTeam)
		away := ensure(match.AwayKey, match.AwayTeam)
		home.Played++
		away.Played++
		home.GoalsFor += match.HomeGoals
		home.GoalsAgainst += match.AwayGoals
		away.GoalsFor += match.AwayGoals
		away.GoalsAgainst += match.HomeGoals
		switch {
		case match.HomeGoals > match.AwayGoals:
			home.Wins++
			home.Points += 3
			away.Losses++
		case match.HomeGoals < match.AwayGoals:
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
	standings := make([]Standing, 0, len(byTeam))
	for _, standing := range byTeam {
		standing.GoalDifference = standing.GoalsFor - standing.GoalsAgainst
		standings = append(standings, *standing)
	}
	sort.Slice(standings, func(i, j int) bool {
		left, right := standings[i], standings[j]
		if left.Points != right.Points {
			return left.Points > right.Points
		}
		if left.Wins != right.Wins {
			return left.Wins > right.Wins
		}
		if left.GoalDifference != right.GoalDifference {
			return left.GoalDifference > right.GoalDifference
		}
		if left.GoalsFor != right.GoalsFor {
			return left.GoalsFor > right.GoalsFor
		}
		return normalizeText(left.Team) < normalizeText(right.Team)
	})
	for index := range standings {
		standings[index].Rank = index + 1
	}
	if len(standings) == 0 {
		return nil, fmt.Errorf("no scored %s matches found for season %d", competition, season)
	}
	return standings, nil
}

func (d *DataStore) CompetitionStatistics(filter MatchFilter) (CompetitionSummary, []BiggestWin) {
	filter.Limit = 0
	matches := d.SearchMatches(filter)
	summary := CompetitionSummary{Competition: normalizeCompetition(filter.Competition), Season: filter.Season}
	biggest := make([]BiggestWin, 0)
	for _, match := range matches {
		if !match.HasScore {
			continue
		}
		summary.Matches++
		summary.TotalGoals += match.HomeGoals + match.AwayGoals
		switch {
		case match.HomeGoals > match.AwayGoals:
			summary.HomeWins++
			biggest = append(biggest, BiggestWin{Match: match, Winner: match.HomeTeam, Margin: match.HomeGoals - match.AwayGoals})
		case match.HomeGoals < match.AwayGoals:
			summary.AwayWins++
			biggest = append(biggest, BiggestWin{Match: match, Winner: match.AwayTeam, Margin: match.AwayGoals - match.HomeGoals})
		default:
			summary.Draws++
		}
	}
	if summary.Matches > 0 {
		count := float64(summary.Matches)
		summary.AverageGoals = roundPercent(float64(summary.TotalGoals) / count)
		summary.HomeWinRate = roundPercent(100 * float64(summary.HomeWins) / count)
		summary.DrawRate = roundPercent(100 * float64(summary.Draws) / count)
		summary.AwayWinRate = roundPercent(100 * float64(summary.AwayWins) / count)
	}
	sort.Slice(biggest, func(i, j int) bool {
		if biggest[i].Margin != biggest[j].Margin {
			return biggest[i].Margin > biggest[j].Margin
		}
		return biggest[i].Match.Date.After(biggest[j].Match.Date)
	})
	return summary, biggest
}

// BestTeamRecord ranks teams by win rate in the selected home, away, or all
// scope. Match count breaks a percentage tie to avoid favoring a one-match run.
func (d *DataStore) BestTeamRecord(filter MatchFilter, scope string) (TeamStatistics, bool) {
	matches := d.SearchMatches(filter)
	keys := make(map[string]string)
	for _, match := range matches {
		keys[match.HomeKey] = match.HomeTeam
		keys[match.AwayKey] = match.AwayTeam
	}
	var best TeamStatistics
	found := false
	for key, display := range keys {
		stats := d.TeamStatistics(key, filter, scope)
		if stats.Matches == 0 {
			continue
		}
		if !found || betterRecord(stats, best) {
			stats.Team = d.DisplayTeam(display)
			best, found = stats, true
		}
	}
	return best, found
}

// MostGoalsScorer returns the team with the most goals in the selected match
// set. Player top-scorer data cannot be inferred from these match-level CSVs,
// but team goals are present in every scored match.
func (d *DataStore) MostGoalsScorer(filter MatchFilter) (TeamStatistics, bool) {
	filter.Limit = 0
	matches := d.SearchMatches(filter)
	byTeam := make(map[string]*TeamStatistics)
	ensure := func(key, display string) *TeamStatistics {
		if current, ok := byTeam[key]; ok {
			return current
		}
		stats := &TeamStatistics{Team: d.DisplayTeam(display), Competition: normalizeCompetition(filter.Competition), Season: filter.Season, Scope: "all"}
		byTeam[key] = stats
		return stats
	}
	addResult := func(stats *TeamStatistics, goalsFor, goalsAgainst int) {
		stats.Matches++
		stats.GoalsFor += goalsFor
		stats.GoalsAgainst += goalsAgainst
		switch {
		case goalsFor > goalsAgainst:
			stats.Wins++
			stats.Points += 3
		case goalsFor == goalsAgainst:
			stats.Draws++
			stats.Points++
		default:
			stats.Losses++
		}
	}
	for _, match := range matches {
		if !match.HasScore {
			continue
		}
		addResult(ensure(match.HomeKey, match.HomeTeam), match.HomeGoals, match.AwayGoals)
		addResult(ensure(match.AwayKey, match.AwayTeam), match.AwayGoals, match.HomeGoals)
	}
	var best TeamStatistics
	found := false
	for _, stats := range byTeam {
		stats.GoalDifference = stats.GoalsFor - stats.GoalsAgainst
		if stats.Matches > 0 {
			stats.WinRate = roundPercent(100 * float64(stats.Wins) / float64(stats.Matches))
			stats.GoalsPerMatch = roundPercent(float64(stats.GoalsFor) / float64(stats.Matches))
		}
		if !found || stats.GoalsFor > best.GoalsFor || (stats.GoalsFor == best.GoalsFor && (stats.GoalsPerMatch > best.GoalsPerMatch || (stats.GoalsPerMatch == best.GoalsPerMatch && betterRecord(*stats, best)))) {
			best, found = *stats, true
		}
	}
	return best, found
}

func betterRecord(left, right TeamStatistics) bool {
	if left.WinRate != right.WinRate {
		return left.WinRate > right.WinRate
	}
	if left.Points != right.Points {
		return left.Points > right.Points
	}
	if left.Matches != right.Matches {
		return left.Matches > right.Matches
	}
	if left.GoalDifference != right.GoalDifference {
		return left.GoalDifference > right.GoalDifference
	}
	return normalizeText(left.Team) < normalizeText(right.Team)
}

func positionMatches(candidate, requested string) bool {
	requested = normalizeText(requested)
	if requested == "" || requested == "all" || requested == "any" {
		return true
	}
	candidate = strings.ToUpper(strings.TrimSpace(candidate))
	if strings.EqualFold(candidate, requested) {
		return true
	}
	groups := map[string]map[string]bool{
		"goalkeeper": {"GK": true}, "keeper": {"GK": true},
		"defender":   {"CB": true, "LCB": true, "RCB": true, "LB": true, "RB": true, "LWB": true, "RWB": true},
		"midfielder": {"CM": true, "CDM": true, "CAM": true, "LCM": true, "RCM": true, "LM": true, "RM": true},
		"forward":    {"ST": true, "CF": true, "LF": true, "RF": true, "LW": true, "RW": true},
		"attacker":   {"ST": true, "CF": true, "LF": true, "RF": true, "LW": true, "RW": true},
	}
	if group, ok := groups[requested]; ok {
		return group[candidate]
	}
	return strings.Contains(normalizeText(candidate), requested)
}

func nationalityMatches(candidate, requested string) bool {
	requested = normalizeText(requested)
	if requested == "" || requested == "all" || requested == "any" {
		return true
	}
	if requested == "brazilian" || requested == "brasileiro" || requested == "brasileira" {
		requested = "brazil"
	}
	return strings.Contains(normalizeText(candidate), requested)
}

func clubMatches(candidate, requested string) bool {
	requested = normalizeTeam(requested)
	if requested == "" {
		return true
	}
	candidateKey := normalizeTeam(candidate)
	if candidateKey == "" {
		return false
	}
	return strings.Contains(candidateKey, requested) || strings.Contains(requested, candidateKey)
}

func (d *DataStore) SearchPlayers(filter PlayerFilter) PlayerSearchResult {
	matched := make([]Player, 0)
	name := normalizeText(filter.Name)
	for _, player := range d.Players {
		if name != "" && !strings.Contains(normalizeText(player.Name), name) {
			continue
		}
		if !nationalityMatches(player.Nationality, filter.Nationality) {
			continue
		}
		if !clubMatches(player.Club, filter.Club) {
			continue
		}
		if !positionMatches(player.Position, filter.Position) {
			continue
		}
		if filter.MinOverall > 0 && player.Overall < filter.MinOverall {
			continue
		}
		matched = append(matched, player)
	}
	sort.Slice(matched, func(i, j int) bool {
		left, right := matched[i], matched[j]
		leftExact := name != "" && normalizeText(left.Name) == name
		rightExact := name != "" && normalizeText(right.Name) == name
		if leftExact != rightExact {
			return leftExact
		}
		if left.Overall != right.Overall {
			return left.Overall > right.Overall
		}
		return normalizeText(left.Name) < normalizeText(right.Name)
	})
	result := PlayerSearchResult{Total: len(matched), Players: matched}
	if filter.Limit > 0 && len(result.Players) > filter.Limit {
		result.Players = result.Players[:filter.Limit]
	}
	return result
}

func (d *DataStore) TeamCompetitions(team string, source string) []TeamCompetition {
	matches := d.SearchMatches(MatchFilter{Team: team, Source: source})
	byCompetition := make(map[string]*TeamCompetition)
	for _, match := range matches {
		competition := normalizeCompetition(match.Competition)
		current, ok := byCompetition[competition]
		if !ok {
			current = &TeamCompetition{Competition: competition}
			byCompetition[competition] = current
		}
		current.Matches++
		if current.FirstSeason == 0 || (match.Season != 0 && match.Season < current.FirstSeason) {
			current.FirstSeason = match.Season
		}
		if match.Season > current.LastSeason {
			current.LastSeason = match.Season
		}
		if !containsString(current.Sources, match.Source) {
			current.Sources = append(current.Sources, match.Source)
		}
	}
	result := make([]TeamCompetition, 0, len(byCompetition))
	for _, competition := range byCompetition {
		sort.Strings(competition.Sources)
		result = append(result, *competition)
	}
	sort.Slice(result, func(i, j int) bool { return result[i].Competition < result[j].Competition })
	return result
}

func containsString(values []string, requested string) bool {
	for _, value := range values {
		if value == requested {
			return true
		}
	}
	return false
}

func (d *DataStore) CompareSeasons(competition string, seasons []int, source string) SeasonComparison {
	competition = normalizeCompetition(competition)
	if competition == "" {
		competition = "Brasileirão Série A"
	}
	result := SeasonComparison{Competition: competition}
	seen := make(map[int]bool)
	for _, season := range seasons {
		if season <= 0 || seen[season] {
			continue
		}
		seen[season] = true
		summary, _ := d.CompetitionStatistics(MatchFilter{Competition: competition, Season: season, Source: source})
		result.Seasons = append(result.Seasons, summary)
	}
	sort.Slice(result.Seasons, func(i, j int) bool { return result.Seasons[i].Season < result.Seasons[j].Season })
	return result
}
