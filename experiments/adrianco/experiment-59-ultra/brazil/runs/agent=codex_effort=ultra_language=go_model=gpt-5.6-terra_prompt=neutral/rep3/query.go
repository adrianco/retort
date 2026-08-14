package main

import (
	"fmt"
	"regexp"
	"sort"
	"strconv"
	"strings"
	"time"
)

const (
	defaultLimit = 50
	maxLimit     = 500
)

// SearchMatches finds fixtures across the loaded datasets. Unless a source is
// requested explicitly, it selects the preferred source for each competition and
// season to avoid counting the overlapping source datasets multiple times.
func (store *DataStore) SearchMatches(filter MatchFilter) []Match {
	matches, _ := store.selectMatches(filter)
	sortMatchesNewestFirst(matches)
	return limitMatches(matches, filter.Limit)
}

func (store *DataStore) selectMatches(filter MatchFilter) ([]Match, string) {
	if filter.IncludeAllSources || strings.EqualFold(strings.TrimSpace(filter.Source), "all") {
		return store.matchingMatches(filter), "all supplied sources"
	}
	if strings.TrimSpace(filter.Source) != "" {
		return store.matchingMatches(filter), "explicit source"
	}

	// Determine the canonical source before applying team/date/stage predicates.
	// This keeps a competition-season's aggregation source stable across related
	// queries instead of switching sources merely because a particular filter has
	// no matching row in the preferred file.
	selectedSources := store.preferredSourceGroups(filter)
	matches := make([]Match, 0)
	for _, match := range store.Matches {
		if sourceKey(selectedSources[competitionSeasonKey(match)]) != sourceKey(match.Source) {
			continue
		}
		if matchMatchesFilter(match, filter) {
			matches = append(matches, match)
		}
	}
	return matches, "preferred source per competition and season"
}

func (store *DataStore) matchingMatches(filter MatchFilter) []Match {
	matches := make([]Match, 0)
	for _, match := range store.Matches {
		if matchMatchesFilter(match, filter) {
			matches = append(matches, match)
		}
	}
	return matches
}

func (store *DataStore) preferredSourceGroups(filter MatchFilter) map[string]string {
	selected := make(map[string]string)
	for _, match := range store.Matches {
		if !matchesPolicyScope(match, filter) {
			continue
		}
		key := competitionSeasonKey(match)
		current, exists := selected[key]
		if !exists || sourceRank(match.Competition, match.Source) < sourceRank(match.Competition, current) {
			selected[key] = match.Source
		}
	}
	return selected
}

func matchesPolicyScope(match Match, filter MatchFilter) bool {
	if filter.Competition != "" && normalizedCompetition(match.Competition) != normalizedCompetition(filter.Competition) {
		return false
	}
	return filter.Season == 0 || match.Season == filter.Season
}

func competitionSeasonKey(match Match) string {
	return normalizedCompetition(match.Competition) + "|" + strconv.Itoa(match.Season)
}

func matchMatchesFilter(match Match, filter MatchFilter) bool {
	if filter.Team != "" && !teamMatches(match.HomeTeam, filter.Team) && !teamMatches(match.AwayTeam, filter.Team) {
		return false
	}
	if filter.Opponent != "" && !teamMatches(match.HomeTeam, filter.Opponent) && !teamMatches(match.AwayTeam, filter.Opponent) {
		return false
	}
	if filter.HomeTeam != "" && !teamMatches(match.HomeTeam, filter.HomeTeam) {
		return false
	}
	if filter.AwayTeam != "" && !teamMatches(match.AwayTeam, filter.AwayTeam) {
		return false
	}
	if filter.Competition != "" && normalizedCompetition(match.Competition) != normalizedCompetition(filter.Competition) {
		return false
	}
	if filter.Source != "" && !strings.EqualFold(filter.Source, "all") && !matchesSource(match.Source, filter.Source) {
		return false
	}
	if filter.Season != 0 && match.Season != filter.Season {
		return false
	}
	if filter.Round != "" && !roundMatches(match.Round, filter.Round) {
		return false
	}
	if filter.Stage != "" && !strings.Contains(normalizeText(match.Stage), normalizeText(filter.Stage)) {
		return false
	}
	if !filter.StartDate.IsZero() && (match.Date.IsZero() || match.Date.Before(startOfDay(filter.StartDate))) {
		return false
	}
	if !filter.EndDate.IsZero() && (match.Date.IsZero() || match.Date.After(endOfDay(filter.EndDate))) {
		return false
	}
	return true
}

func roundMatches(actual, query string) bool {
	actual = normalizeText(actual)
	query = normalizeText(query)
	if actual == query {
		return true
	}
	if actualNumber, actualErr := strconv.Atoi(actual); actualErr == nil {
		if queryNumber, queryErr := strconv.Atoi(query); queryErr == nil {
			return actualNumber == queryNumber
		}
	}
	return strings.Contains(actual, query)
}

func matchesSource(actual, requested string) bool {
	requestedKey := sourceKey(requested)
	actualKey := sourceKey(actual)
	if actualKey == requestedKey {
		return true
	}
	aliases := map[string]string{
		"brasileirao":    brasileiraoFile,
		"serie a":        brasileiraoFile,
		"cup":            cupFile,
		"copa do brasil": cupFile,
		"libertadores":   libertadoresFile,
		"extended":       extendedFile,
		"historical":     historicalFile,
		"history":        historicalFile,
	}
	if resolved, ok := aliases[requestedKey]; ok {
		return actualKey == sourceKey(resolved)
	}
	return strings.Contains(actualKey, requestedKey)
}

func startOfDay(value time.Time) time.Time {
	return time.Date(value.Year(), value.Month(), value.Day(), 0, 0, 0, 0, value.Location())
}

func endOfDay(value time.Time) time.Time {
	return time.Date(value.Year(), value.Month(), value.Day(), 23, 59, 59, int(time.Second-time.Nanosecond), value.Location())
}

func sourcePreference(competition string) []string {
	switch normalizedCompetition(competition) {
	case "brasileirao":
		return []string{brasileiraoFile, historicalFile, extendedFile}
	case "copa do brasil":
		return []string{cupFile, extendedFile}
	case "libertadores":
		return []string{libertadoresFile}
	default:
		return []string{extendedFile, brasileiraoFile, cupFile, libertadoresFile, historicalFile}
	}
}

func sourceRank(competition, source string) int {
	for rank, preferred := range sourcePreference(competition) {
		if sourceKey(source) == sourceKey(preferred) {
			return rank
		}
	}
	return len(sourcePreference(competition)) + 1
}

func sortMatchesNewestFirst(matches []Match) {
	sort.SliceStable(matches, func(left, right int) bool {
		if matches[left].Date.Equal(matches[right].Date) {
			if matches[left].Competition == matches[right].Competition {
				if matches[left].HomeTeam == matches[right].HomeTeam {
					return matches[left].AwayTeam < matches[right].AwayTeam
				}
				return matches[left].HomeTeam < matches[right].HomeTeam
			}
			return matches[left].Competition < matches[right].Competition
		}
		if matches[left].Date.IsZero() {
			return false
		}
		if matches[right].Date.IsZero() {
			return true
		}
		return matches[left].Date.After(matches[right].Date)
	})
}

func limitMatches(matches []Match, requested int) []Match {
	limit := boundedLimit(requested)
	if len(matches) <= limit {
		return matches
	}
	return matches[:limit]
}

func boundedLimit(requested int) int {
	if requested <= 0 {
		return defaultLimit
	}
	if requested > maxLimit {
		return maxLimit
	}
	return requested
}

func (store *DataStore) SearchPlayers(filter PlayerFilter) []Player {
	players := make([]Player, 0)
	for _, player := range store.Players {
		if filter.Name != "" && !containsNormalized(player.Name, filter.Name) {
			continue
		}
		if filter.Nationality != "" && !containsNormalized(player.Nationality, filter.Nationality) {
			continue
		}
		if filter.Club != "" && !containsNormalized(player.Club, filter.Club) {
			continue
		}
		if filter.Position != "" && !containsNormalized(player.Position, filter.Position) {
			continue
		}
		if filter.MinOverall != 0 && player.Overall < filter.MinOverall {
			continue
		}
		players = append(players, player)
	}
	sort.SliceStable(players, func(left, right int) bool {
		if players[left].Overall == players[right].Overall {
			return normalizeText(players[left].Name) < normalizeText(players[right].Name)
		}
		return players[left].Overall > players[right].Overall
	})
	return limitPlayers(players, filter.Limit)
}

func containsNormalized(value, query string) bool {
	return strings.Contains(normalizeText(value), normalizeText(query))
}

func limitPlayers(players []Player, requested int) []Player {
	limit := boundedLimit(requested)
	if len(players) <= limit {
		return players
	}
	return players[:limit]
}

func (store *DataStore) TeamStatistics(team string, filter MatchFilter, venue string) (TeamStats, error) {
	if strings.TrimSpace(team) == "" {
		return TeamStats{}, fmt.Errorf("team is required")
	}
	venue = normalizeText(venue)
	if venue == "" {
		venue = "all"
	}
	if venue != "all" && venue != "home" && venue != "away" {
		return TeamStats{}, fmt.Errorf("venue must be one of all, home, or away")
	}
	filter.Team = team
	matches, _ := store.selectMatches(filter)
	stats := TeamStats{
		Team:        team,
		Venue:       venue,
		Competition: canonicalCompetition(filter.Competition),
		Season:      filter.Season,
		Source:      filter.Source,
	}
	for _, match := range matches {
		home := teamMatches(match.HomeTeam, team)
		away := teamMatches(match.AwayTeam, team)
		if (!home && !away) || (venue == "home" && !home) || (venue == "away" && !away) {
			continue
		}
		if !match.Played() {
			stats.UnplayedMatches++
			continue
		}
		stats.Matches++
		stats.PlayedFixtures++
		goalsFor, goalsAgainst := *match.HomeGoals, *match.AwayGoals
		if away && !home {
			goalsFor, goalsAgainst = goalsAgainst, goalsFor
		}
		stats.GoalsFor += goalsFor
		stats.GoalsAgainst += goalsAgainst
		switch {
		case goalsFor > goalsAgainst:
			stats.Wins++
		case goalsFor < goalsAgainst:
			stats.Losses++
		default:
			stats.Draws++
		}
	}
	stats.GoalDifference = stats.GoalsFor - stats.GoalsAgainst
	if stats.Matches > 0 {
		stats.WinRate = percentage(stats.Wins, stats.Matches)
		stats.GoalsPerMatch = decimal(float64(stats.GoalsFor) / float64(stats.Matches))
	}
	return stats, nil
}

// TeamProfile follows the team relationship across the match and player
// datasets. FIFA's club field is a point-in-time snapshot, so an empty player
// list is a real result rather than an inference about a team's roster.
func (store *DataStore) TeamProfile(team string, filter MatchFilter, playerLimit int) (map[string]any, error) {
	stats, err := store.TeamStatistics(team, filter, "all")
	if err != nil {
		return nil, err
	}
	filter.Team = team
	matches, policy := store.selectMatches(filter)
	sortMatchesNewestFirst(matches)
	totalMatches := len(matches)
	recentMatches := limitMatches(matches, filter.Limit)
	players := store.SearchPlayers(PlayerFilter{Club: parseTeamName(team).base, Limit: playerLimit})
	competitions := make([]string, 0, len(matches))
	for _, match := range matches {
		competitions = append(competitions, match.Competition)
	}
	return map[string]any{
		"team":                       team,
		"statistics":                 stats,
		"recent_matches":             recentMatches,
		"match_count":                totalMatches,
		"competitions":               uniqueStrings(competitions),
		"players":                    players,
		"fifa_snapshot_player_count": len(players),
		"source_policy":              policy,
		"player_data_note":           "Player results use the FIFA dataset's current-club snapshot and are not historical rosters.",
	}, nil
}

func (store *DataStore) HeadToHead(teamA, teamB string, filter MatchFilter) (HeadToHead, error) {
	if strings.TrimSpace(teamA) == "" || strings.TrimSpace(teamB) == "" {
		return HeadToHead{}, fmt.Errorf("team_a and team_b are required")
	}
	matches, _ := store.selectMatches(filter)
	result := HeadToHead{TeamA: teamA, TeamB: teamB, Competition: canonicalCompetition(filter.Competition), Season: filter.Season}
	for _, match := range matches {
		teamAHome := teamMatches(match.HomeTeam, teamA)
		teamAAway := teamMatches(match.AwayTeam, teamA)
		teamBHome := teamMatches(match.HomeTeam, teamB)
		teamBAway := teamMatches(match.AwayTeam, teamB)
		if !(teamAHome && teamBAway || teamAAway && teamBHome) {
			continue
		}
		result.Total++
		result.Matches = append(result.Matches, match)
		if !match.Played() {
			result.Unplayed++
			continue
		}
		result.Played++
		if *match.HomeGoals == *match.AwayGoals {
			result.Draws++
		} else if (*match.HomeGoals > *match.AwayGoals && teamAHome) || (*match.AwayGoals > *match.HomeGoals && teamAAway) {
			result.TeamAWins++
		} else {
			result.TeamBWins++
		}
	}
	sortMatchesNewestFirst(result.Matches)
	result.Matches = limitMatches(result.Matches, filter.Limit)
	return result, nil
}

func (store *DataStore) Standings(competition string, season int, source string, includeAllSources bool) (StandingsResult, error) {
	if strings.TrimSpace(competition) == "" {
		return StandingsResult{}, fmt.Errorf("competition is required")
	}
	if season <= 0 {
		return StandingsResult{}, fmt.Errorf("season is required")
	}
	filter := MatchFilter{Competition: competition, Season: season, Source: source, IncludeAllSources: includeAllSources}
	matches, policy := store.selectMatches(filter)
	standings := make(map[string]*Standing)
	for _, match := range matches {
		if !match.Played() {
			continue
		}
		home := standingFor(standings, match.HomeTeam)
		away := standingFor(standings, match.AwayTeam)
		home.Played++
		away.Played++
		home.GoalsFor += *match.HomeGoals
		home.GoalsAgainst += *match.AwayGoals
		away.GoalsFor += *match.AwayGoals
		away.GoalsAgainst += *match.HomeGoals
		switch {
		case *match.HomeGoals > *match.AwayGoals:
			home.Wins++
			home.Points += 3
			away.Losses++
		case *match.HomeGoals < *match.AwayGoals:
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
	result := StandingsResult{
		Competition:  canonicalCompetition(competition),
		Season:       season,
		SourcePolicy: policy,
		Sources:      sourcesFor(matches),
	}
	for _, match := range matches {
		if match.Played() {
			result.PlayedMatches++
		} else {
			result.IgnoredMatches++
		}
	}
	result.Standings = make([]Standing, 0, len(standings))
	for _, standing := range standings {
		standing.GoalDifference = standing.GoalsFor - standing.GoalsAgainst
		result.Standings = append(result.Standings, *standing)
	}
	sort.Slice(result.Standings, func(left, right int) bool {
		first, second := result.Standings[left], result.Standings[right]
		switch {
		case first.Points != second.Points:
			return first.Points > second.Points
		case first.Wins != second.Wins:
			return first.Wins > second.Wins
		case first.GoalDifference != second.GoalDifference:
			return first.GoalDifference > second.GoalDifference
		case first.GoalsFor != second.GoalsFor:
			return first.GoalsFor > second.GoalsFor
		default:
			return normalizeText(first.Team) < normalizeText(second.Team)
		}
	})
	for index := range result.Standings {
		result.Standings[index].Rank = index + 1
	}
	return result, nil
}

func standingFor(standings map[string]*Standing, team string) *Standing {
	parsed := parseTeamName(team)
	key := parsed.base + "|" + parsed.state
	if standing, ok := standings[key]; ok {
		return standing
	}
	standing := &Standing{Team: displayTeam(team)}
	standings[key] = standing
	return standing
}

func (store *DataStore) Statistics(filter MatchFilter) CompetitionStats {
	matches, policy := store.selectMatches(filter)
	result := CompetitionStats{
		Competition:  canonicalCompetition(filter.Competition),
		Season:       filter.Season,
		SourcePolicy: policy,
		Sources:      sourcesFor(matches),
		Fixtures:     len(matches),
	}
	biggest := make([]Match, 0)
	for _, match := range matches {
		if !match.Played() {
			result.UnplayedMatches++
			continue
		}
		result.PlayedMatches++
		result.TotalGoals += *match.HomeGoals + *match.AwayGoals
		switch {
		case *match.HomeGoals > *match.AwayGoals:
			result.HomeWins++
		case *match.HomeGoals < *match.AwayGoals:
			result.AwayWins++
		default:
			result.Draws++
		}
		if match.GoalDifference() > 0 {
			biggest = append(biggest, match)
		}
	}
	if result.PlayedMatches > 0 {
		result.AverageGoals = decimal(float64(result.TotalGoals) / float64(result.PlayedMatches))
		result.HomeWinRate = percentage(result.HomeWins, result.PlayedMatches)
		result.AwayWinRate = percentage(result.AwayWins, result.PlayedMatches)
	}
	sort.SliceStable(biggest, func(left, right int) bool {
		if biggest[left].GoalDifference() == biggest[right].GoalDifference() {
			return biggest[left].Date.After(biggest[right].Date)
		}
		return biggest[left].GoalDifference() > biggest[right].GoalDifference()
	})
	if len(biggest) > 10 {
		biggest = biggest[:10]
	}
	result.BiggestWins = biggest
	return result
}

// TeamRankings supports the competition questions that compare the best scoring,
// home, or away teams without pretending scorer-level data exists in these files.
type teamRankingRecord struct {
	team    string
	matches int
	wins    int
	goals   int
}

func (store *DataStore) TeamRankings(filter MatchFilter, metric string, limit int) ([]TeamRanking, error) {
	metric = normalizeText(metric)
	if metric == "" {
		metric = "goals scored"
	}
	if metric != "goals scored" && metric != "best home record" && metric != "best away record" {
		return nil, fmt.Errorf("metric must be goals_scored, best_home_record, or best_away_record")
	}
	matches, _ := store.selectMatches(filter)
	records := make(map[string]*teamRankingRecord)
	for _, match := range matches {
		if !match.Played() {
			continue
		}
		if metric == "goals scored" || metric == "best home record" {
			entry := rankingRecordFor(records, match.HomeTeam)
			entry.matches++
			entry.goals += *match.HomeGoals
			if *match.HomeGoals > *match.AwayGoals {
				entry.wins++
			}
		}
		if metric == "goals scored" || metric == "best away record" {
			entry := rankingRecordFor(records, match.AwayTeam)
			entry.matches++
			entry.goals += *match.AwayGoals
			if *match.AwayGoals > *match.HomeGoals {
				entry.wins++
			}
		}
	}
	result := make([]TeamRanking, 0, len(records))
	for _, entry := range records {
		value := float64(entry.goals)
		if metric != "goals scored" && entry.matches > 0 {
			value = percentage(entry.wins, entry.matches)
		}
		result = append(result, TeamRanking{Team: entry.team, Value: value, Matches: entry.matches, Goals: entry.goals})
	}
	sort.Slice(result, func(left, right int) bool {
		if result[left].Value == result[right].Value {
			if result[left].Goals == result[right].Goals {
				return normalizeText(result[left].Team) < normalizeText(result[right].Team)
			}
			return result[left].Goals > result[right].Goals
		}
		return result[left].Value > result[right].Value
	})
	if len(result) > boundedLimit(limit) {
		result = result[:boundedLimit(limit)]
	}
	for index := range result {
		result[index].Rank = index + 1
	}
	return result, nil
}

func rankingRecordFor(records map[string]*teamRankingRecord, team string) *teamRankingRecord {
	parsed := parseTeamName(team)
	key := parsed.base + "|" + parsed.state
	if entry, ok := records[key]; ok {
		return entry
	}
	entry := &teamRankingRecord{team: displayTeam(team)}
	records[key] = entry
	return entry
}

func sourcesFor(matches []Match) []string {
	sources := make([]string, 0, len(matches))
	for _, match := range matches {
		sources = append(sources, match.Source)
	}
	return uniqueStrings(sources)
}

func percentage(numerator, denominator int) float64 {
	if denominator == 0 {
		return 0
	}
	return decimal(float64(numerator) * 100 / float64(denominator))
}

func decimal(value float64) float64 {
	return float64(int(value*100+0.5)) / 100
}

var yearInQuestion = regexp.MustCompile(`\b(19|20)\d{2}\b`)

// AnswerNaturalQuery is a small, deterministic convenience layer for common
// questions. The MCP tools stay structured so a connected LLM can make precise
// calls without relying on a brittle free-text parser.
func (store *DataStore) AnswerNaturalQuery(question string, limit int) (any, error) {
	question = strings.TrimSpace(question)
	if question == "" {
		return nil, fmt.Errorf("query is required")
	}
	normalized := normalizeText(question)
	season := yearFromQuestion(question)
	competition := competitionFromQuestion(normalized)
	teams := store.mentionedTeams(normalized)
	playerName, asksWhoIs := nameInWhoIsQuestion(question)

	switch {
	case strings.Contains(normalized, "top scorer") || strings.Contains(normalized, "top scorers"):
		return map[string]any{
			"query":   question,
			"message": "Top scorers cannot be calculated because the supplied datasets contain match scores but no goal-scorer records.",
		}, nil
	case strings.Contains(normalized, "standings") || strings.Contains(normalized, "who won") || strings.Contains(normalized, "champion"):
		if season == 0 {
			return map[string]any{"query": question, "message": "Please include a season to calculate standings."}, nil
		}
		if competition == "" {
			competition = "Brasileirão"
		}
		return store.Standings(competition, season, "", false)
	case strings.Contains(normalized, "average goals") || strings.Contains(normalized, "biggest win") || strings.Contains(normalized, "biggest victories"):
		return store.Statistics(MatchFilter{Competition: competition, Season: season}), nil
	case len(teams) >= 2 && (strings.Contains(normalized, " vs ") || strings.Contains(normalized, " versus ") || strings.Contains(normalized, " contra ") || strings.Contains(normalized, "compare") || strings.Contains(normalized, "head to head")):
		return store.HeadToHead(teams[0], teams[1], MatchFilter{Competition: competition, Season: season, Limit: limit})
	case len(teams) >= 2 && (strings.Contains(normalized, "last play") || strings.Contains(normalized, "last match") || strings.Contains(normalized, "last game")):
		return store.SearchMatches(MatchFilter{Team: teams[0], Opponent: teams[1], Competition: competition, Season: season, Limit: 1}), nil
	case len(teams) > 0 && strings.Contains(normalized, "home record"):
		return store.TeamStatistics(teams[0], MatchFilter{Competition: competition, Season: season}, "home")
	case len(teams) > 0 && (strings.Contains(normalized, "players") || strings.Contains(normalized, "competitions")):
		return store.TeamProfile(teams[0], MatchFilter{Competition: competition, Season: season, Limit: limit}, limit)
	case len(teams) > 0 && (strings.Contains(normalized, "matches") || strings.Contains(normalized, "played")):
		return store.SearchMatches(MatchFilter{Team: teams[0], Competition: competition, Season: season, Limit: limit}), nil
	case asksWhoIs:
		return store.SearchPlayers(PlayerFilter{Name: playerName, Limit: limit}), nil
	case strings.Contains(normalized, "brazilian players") || strings.Contains(normalized, "brazilian player"):
		return store.SearchPlayers(PlayerFilter{Nationality: "Brazil", Limit: limit}), nil
	default:
		return map[string]any{
			"query":   question,
			"message": "I could not confidently parse that question. Use search_matches, team_statistics, head_to_head, search_players, competition_standings, or competition_statistics for a precise result.",
		}, nil
	}
}

func yearFromQuestion(question string) int {
	value := yearInQuestion.FindString(question)
	if value == "" {
		return 0
	}
	var year int
	_, _ = fmt.Sscan(value, &year)
	return year
}

func competitionFromQuestion(question string) string {
	switch {
	case strings.Contains(question, "libertadores"):
		return "Copa Libertadores"
	case strings.Contains(question, "copa do brasil"):
		return "Copa do Brasil"
	case strings.Contains(question, "brasileirao"), strings.Contains(question, "serie a"):
		return "Brasileirão"
	default:
		return ""
	}
}

func nameInWhoIsQuestion(question string) (string, bool) {
	words := strings.Fields(question)
	if len(words) < 3 || normalizeText(words[0]) != "who" || normalizeText(words[1]) != "is" {
		return "", false
	}
	name := strings.Trim(strings.Join(words[2:], " "), " ?!.,;:")
	return name, name != ""
}

func (store *DataStore) mentionedTeams(question string) []string {
	type candidate struct {
		team   string
		length int
	}
	seen := make(map[string]candidate)
	for _, match := range store.Matches {
		for _, team := range []string{match.HomeTeam, match.AwayTeam} {
			parsed := parseTeamName(team)
			if len(parsed.base) < 4 || !strings.Contains(question, parsed.base) {
				continue
			}
			key := parsed.base + "|" + parsed.state
			if existing, ok := seen[key]; !ok || len(parsed.base) > existing.length {
				seen[key] = candidate{team: displayTeam(team), length: len(parsed.base)}
			}
		}
	}
	values := make([]candidate, 0, len(seen))
	for _, candidate := range seen {
		values = append(values, candidate)
	}
	sort.Slice(values, func(left, right int) bool {
		if values[left].length == values[right].length {
			return values[left].team < values[right].team
		}
		return values[left].length > values[right].length
	})
	result := make([]string, 0, len(values))
	explicitStates := make(map[string]struct{})
	for _, candidate := range values {
		parsed := parseTeamName(candidate.team)
		if parsed.state != "" && strings.Contains(question, parsed.base+" "+strings.ToLower(parsed.state)) {
			explicitStates[parsed.base] = struct{}{}
		}
	}
	usedBase := make(map[string]struct{})
	for _, candidate := range values {
		parsed := parseTeamName(candidate.team)
		base := parsed.base
		stateIsExplicit := parsed.state != "" && strings.Contains(question, base+" "+strings.ToLower(parsed.state))
		if _, hasExplicitState := explicitStates[base]; hasExplicitState && !stateIsExplicit {
			continue
		}
		if _, ok := usedBase[base]; ok && !stateIsExplicit {
			continue
		}
		if !stateIsExplicit {
			usedBase[base] = struct{}{}
		}
		result = append(result, candidate.team)
	}
	return result
}
