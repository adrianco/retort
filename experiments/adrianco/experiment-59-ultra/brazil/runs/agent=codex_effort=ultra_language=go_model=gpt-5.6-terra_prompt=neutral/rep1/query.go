package main

import (
	"fmt"
	"math"
	"sort"
	"strconv"
	"strings"
	"time"
)

// SearchMatches finds fixtures by the supplied criteria. With no source set it
// uses one authoritative source per competition/season so overlapping Kaggle
// files do not double-count a result. source="all" exposes every raw source.
func (db *Database) SearchMatches(filter MatchFilter) MatchSearchResult {
	matches := db.filteredMatches(filter)
	sortMatchesNewestFirst(matches)
	total := len(matches)

	offset := filter.Offset
	if offset < 0 {
		offset = 0
	}
	if offset > total {
		offset = total
	}
	limit := normalizedLimit(filter.Limit)
	end := offset + limit
	if end > total {
		end = total
	}
	page := append([]Match(nil), matches[offset:end]...)
	result := MatchSearchResult{Matches: page, Total: total}
	if end < total {
		next := end
		result.NextOffset = &next
	}
	return result
}

// matchesWithUnknown returns the full selected fixture set and its completeness
// signal. It is shared by standings/natural-language responses so unknown
// source rows are visible to callers without entering an aggregate.
func (db *Database) matchesWithUnknown(filter MatchFilter) ([]Match, int) {
	filter.IncludeUnplayed = true
	matches := db.filteredMatches(filter)
	unknown := 0
	for _, match := range matches {
		if !match.ScoreKnown {
			unknown++
		}
	}
	return matches, unknown
}

func (db *Database) filteredMatches(filter MatchFilter) []Match {
	team := normalizeTeam(filter.Team)
	opponent := normalizeTeam(filter.Opponent)
	homeTeam := normalizeTeam(filter.HomeTeam)
	awayTeam := normalizeTeam(filter.AwayTeam)
	competition := normalizeCompetition(filter.Competition)
	source := normalizeSourceScope(filter.Source)
	stage := normalizeText(filter.Stage)
	round := normalizeText(filter.Round)

	var candidates []int
	if team != "" {
		candidates = db.teamIndex[team]
	}
	if candidates == nil {
		candidates = make([]int, len(db.Matches))
		for i := range db.Matches {
			candidates[i] = i
		}
	}

	results := make([]Match, 0, len(candidates))
	for _, index := range candidates {
		match := db.Matches[index]
		if team != "" && match.HomeKey != team && match.AwayKey != team {
			continue
		}
		if opponent != "" {
			if team != "" {
				if !((match.HomeKey == team && match.AwayKey == opponent) || (match.HomeKey == opponent && match.AwayKey == team)) {
					continue
				}
			} else if match.HomeKey != opponent && match.AwayKey != opponent {
				continue
			}
		}
		if homeTeam != "" && match.HomeKey != homeTeam {
			continue
		}
		if awayTeam != "" && match.AwayKey != awayTeam {
			continue
		}
		if competition != "" && !competitionMatches(match, competition) {
			continue
		}
		if !matchInSourceScope(match, source) {
			continue
		}
		if filter.Season != 0 {
			if match.Season != 0 && match.Season != filter.Season {
				continue
			}
			if match.Season == 0 && (match.Date.IsZero() || match.Date.Year() != filter.Season) {
				continue
			}
		}
		if filter.DateFrom != nil && (match.Date.IsZero() || match.Date.Before(startOfDay(*filter.DateFrom))) {
			continue
		}
		if filter.DateTo != nil && (match.Date.IsZero() || match.Date.After(endOfDay(*filter.DateTo))) {
			continue
		}
		if round != "" && normalizeText(match.Round) != round {
			continue
		}
		if stage != "" && !db.stageMatches(match, stage) {
			continue
		}
		if !filter.IncludeUnplayed && !match.ScoreKnown {
			continue
		}
		results = append(results, match)
	}
	return results
}

func competitionMatches(match Match, requested string) bool {
	actual := normalizeCompetition(match.Competition)
	if actual == requested {
		return true
	}
	// Historical Brasileirão is the authoritative league source through 2019,
	// while still answering the natural user filter "Brasileirão".
	return requested == "brasileirao" && actual == "brasileirao historical"
}

func (db *Database) stageMatches(match Match, stage string) bool {
	if canonicalStage(match.Stage) == canonicalStage(stage) && canonicalStage(stage) != "" {
		return true
	}
	// The supplied Copa do Brasil file represents a final with its highest
	// numeric round, and that number changes by tournament format/season.
	if stage != "final" || normalizeCompetition(match.Competition) != "copa do brasil" {
		return false
	}
	current, err := strconv.Atoi(strings.TrimSpace(match.Round))
	if err != nil || current == 0 || !match.ScoreKnown {
		return false
	}
	maxRound := 0
	completeMaxRound := true
	for _, candidate := range db.Matches {
		if candidate.Source != match.Source || candidate.Season != match.Season || normalizeCompetition(candidate.Competition) != "copa do brasil" {
			continue
		}
		if round, roundErr := strconv.Atoi(strings.TrimSpace(candidate.Round)); roundErr == nil {
			if round > maxRound {
				maxRound = round
				completeMaxRound = candidate.ScoreKnown
			} else if round == maxRound && !candidate.ScoreKnown {
				completeMaxRound = false
			}
		}
	}
	return completeMaxRound && current == maxRound
}

func canonicalStage(value string) string {
	stage := normalizeText(value)
	replacements := map[string]string{
		"finals": "final", "semi final": "semifinal", "semi finals": "semifinal", "semifinals": "semifinal",
		"quarter final": "quarterfinal", "quarter finals": "quarterfinal", "quarterfinals": "quarterfinal",
		"group stages": "group stage",
	}
	if replacement, ok := replacements[stage]; ok {
		return replacement
	}
	return stage
}

func matchInSourceScope(match Match, scope string) bool {
	if scope == "" || scope == "canonical" || scope == "default" {
		return canonicalSourceFor(match)
	}
	if scope == "all" || scope == "raw" {
		return true
	}
	return normalizeText(match.Source) == scope
}

func normalizeSourceScope(scope string) string {
	scope = normalizeText(scope)
	aliases := map[string]string{
		"brasileirao matches":       "brasileirao",
		"brasileirao matches csv":   "brasileirao",
		"brazilian cup matches":     "brazilian cup",
		"brazilian cup matches csv": "brazilian cup",
		"libertadores matches":      "libertadores",
		"libertadores matches csv":  "libertadores",
		"br football":               "extended statistics",
		"br football dataset":       "extended statistics",
		"extended":                  "extended statistics",
		"historical":                "historical brasileirao",
	}
	if alias, ok := aliases[scope]; ok {
		return alias
	}
	return scope
}

// canonicalSourceFor picks the source designed for each competition. Historical
// Brasileirão is authoritative through 2019, then the dedicated season file;
// the extended statistics source fills the newer 2023-only data.
func canonicalSourceFor(match Match) bool {
	switch normalizeCompetition(match.Competition) {
	case "brasileirao historical":
		return match.Source == "historical_brasileirao"
	case "brasileirao":
		if match.Season != 0 && match.Season <= 2019 {
			return match.Source == "historical_brasileirao"
		}
		if match.Source == "extended_statistics" && !match.Date.IsZero() && match.Date.Year() >= 2023 {
			return match.Source == "extended_statistics"
		}
		return match.Source == "brasileirao"
	case "copa do brasil":
		return match.Source == "brazilian_cup"
	case "libertadores":
		return match.Source == "libertadores"
	default:
		return match.Source == "extended_statistics"
	}
}

func (db *Database) TeamStatistics(team string, filter MatchFilter, venue string) (TeamStats, error) {
	if err := requireAggregateSource(filter.Source); err != nil {
		return TeamStats{}, err
	}
	key := normalizeTeam(team)
	if key == "" {
		return TeamStats{}, fmt.Errorf("team is required")
	}
	filter.Team = team
	filter.IncludeUnplayed = true
	matches := db.filteredMatches(filter)
	venue = normalizeText(venue)
	if venue == "" {
		venue = "all"
	}
	if venue != "all" && venue != "home" && venue != "away" {
		return TeamStats{}, fmt.Errorf("venue must be home, away, or all")
	}

	stats := TeamStats{
		Team:        db.displayName(key, team),
		Competition: filter.Competition,
		Season:      filter.Season,
		Venue:       venue,
		SourceScope: sourceScopeForOutput(filter.Source),
		DataSources: sourceNames(matches),
	}
	for _, match := range matches {
		isHome := match.HomeKey == key
		if (venue == "home" && !isHome) || (venue == "away" && isHome) {
			continue
		}
		if !match.ScoreKnown {
			stats.UnknownFixturesExcluded++
			continue
		}
		stats.Matches++
		goalsFor, goalsAgainst := match.AwayGoals, match.HomeGoals
		if isHome {
			goalsFor, goalsAgainst = match.HomeGoals, match.AwayGoals
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
	if stats.Matches > 0 {
		stats.WinRate = roundTo(float64(stats.Wins)*100/float64(stats.Matches), 1)
	}
	return stats, nil
}

func (db *Database) CompareTeams(teamA, teamB string, filter MatchFilter) (HeadToHead, []Match, error) {
	if err := requireAggregateSource(filter.Source); err != nil {
		return HeadToHead{}, nil, err
	}
	keyA, keyB := normalizeTeam(teamA), normalizeTeam(teamB)
	if keyA == "" || keyB == "" {
		return HeadToHead{}, nil, fmt.Errorf("team_a and team_b are required")
	}
	if keyA == keyB {
		return HeadToHead{}, nil, fmt.Errorf("team_a and team_b must be different")
	}
	filter.Team, filter.Opponent, filter.IncludeUnplayed = teamA, teamB, true
	matches := db.filteredMatches(filter)
	sortMatchesNewestFirst(matches)
	result := HeadToHead{
		TeamA:       db.displayName(keyA, teamA),
		TeamB:       db.displayName(keyB, teamB),
		SourceScope: sourceScopeForOutput(filter.Source),
		DataSources: sourceNames(matches),
	}
	for _, match := range matches {
		if !match.ScoreKnown {
			continue
		}
		result.Matches++
		goalsA, goalsB := match.AwayGoals, match.HomeGoals
		if match.HomeKey == keyA {
			goalsA, goalsB = match.HomeGoals, match.AwayGoals
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
	return result, matches, nil
}

func (db *Database) SearchPlayers(filter PlayerFilter) ([]Player, int, *int) {
	name := normalizeText(filter.Name)
	nationality := normalizeText(filter.Nationality)
	if nationality == "brazilian" || nationality == "brasileiro" || nationality == "brasileira" {
		nationality = "brazil"
	}
	club := normalizeTeam(filter.Club)
	position := normalizeText(filter.Position)
	players := make([]Player, 0)
	for _, player := range db.Players {
		if name != "" && !strings.Contains(player.NameKey, name) {
			continue
		}
		if nationality != "" && !strings.Contains(normalizeText(player.Nationality), nationality) {
			continue
		}
		if club != "" && !strings.Contains(player.ClubKey, club) && !strings.Contains(normalizeText(player.Club), club) {
			continue
		}
		if position != "" && !strings.Contains(normalizeText(player.Position), position) {
			continue
		}
		if filter.MinOverall > 0 && player.Overall < filter.MinOverall {
			continue
		}
		if filter.MaxOverall > 0 && player.Overall > filter.MaxOverall {
			continue
		}
		if filter.MinAge > 0 && player.Age < filter.MinAge {
			continue
		}
		if filter.MaxAge > 0 && player.Age > filter.MaxAge {
			continue
		}
		players = append(players, player)
	}
	sortPlayers(players, filter.SortBy, filter.SortOrder)
	total := len(players)
	offset := filter.Offset
	if offset < 0 {
		offset = 0
	}
	if offset > total {
		offset = total
	}
	end := offset + normalizedLimit(filter.Limit)
	if end > total {
		end = total
	}
	page := append([]Player(nil), players[offset:end]...)
	var next *int
	if end < total {
		nextValue := end
		next = &nextValue
	}
	return page, total, next
}

func sortPlayers(players []Player, requestedField, requestedOrder string) {
	field := normalizeText(requestedField)
	if field == "" {
		field = "overall"
	}
	order := normalizeText(requestedOrder)
	if order == "" {
		order = "desc"
	}
	descending := order != "asc"
	compareInt := func(left, right int) bool {
		if descending {
			return left > right
		}
		return left < right
	}
	sort.SliceStable(players, func(i, j int) bool {
		left, right := players[i], players[j]
		if field == "name" {
			leftName, rightName := normalizeText(left.Name), normalizeText(right.Name)
			if leftName != rightName {
				if descending {
					return leftName > rightName
				}
				return leftName < rightName
			}
			return left.ID < right.ID
		}
		var leftValue, rightValue int
		switch field {
		case "potential":
			leftValue, rightValue = left.Potential, right.Potential
		case "age":
			leftValue, rightValue = left.Age, right.Age
		default:
			leftValue, rightValue = left.Overall, right.Overall
		}
		if leftValue != rightValue {
			return compareInt(leftValue, rightValue)
		}
		if left.Overall != right.Overall {
			return compareInt(left.Overall, right.Overall)
		}
		return normalizeText(left.Name) < normalizeText(right.Name)
	})
}

func (db *Database) CompetitionStandings(competition string, season int, source string) ([]Standing, error) {
	if season <= 0 {
		return nil, fmt.Errorf("season is required")
	}
	if normalized := normalizeCompetition(competition); normalized != "brasileirao" {
		return nil, fmt.Errorf("standings are available only for league competition Brasileirao; use search_matches for cup and Libertadores results")
	}
	if err := requireAggregateSource(source); err != nil {
		return nil, err
	}
	matches := db.filteredMatches(MatchFilter{Competition: competition, Season: season, Source: source, IncludeUnplayed: true})
	byTeam := make(map[string]*Standing)
	for _, match := range matches {
		if !match.ScoreKnown {
			continue
		}
		home := standingFor(byTeam, match.HomeKey, db.displayName(match.HomeKey, match.HomeTeam))
		away := standingFor(byTeam, match.AwayKey, db.displayName(match.AwayKey, match.AwayTeam))
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
		standing.GoalDiff = standing.GoalsFor - standing.GoalsAgainst
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
		if left.GoalDiff != right.GoalDiff {
			return left.GoalDiff > right.GoalDiff
		}
		if left.GoalsFor != right.GoalsFor {
			return left.GoalsFor > right.GoalsFor
		}
		return normalizeText(left.Team) < normalizeText(right.Team)
	})
	for i := range standings {
		standings[i].Position = i + 1
	}
	return standings, nil
}

func standingFor(byTeam map[string]*Standing, key, display string) *Standing {
	if existing, ok := byTeam[key]; ok {
		return existing
	}
	standing := &Standing{Team: display}
	byTeam[key] = standing
	return standing
}

func (db *Database) AnalyzeMatches(filter MatchFilter, metric string) (StatisticsResult, error) {
	if err := requireAggregateSource(filter.Source); err != nil {
		return StatisticsResult{}, err
	}
	metric = normalizeText(metric)
	metric = strings.ReplaceAll(metric, " ", "_")
	aliases := map[string]string{
		"average_goals": "goals_per_match", "average_goals_per_match": "goals_per_match",
		"best_home": "best_home_record", "best_away": "best_away_record",
		"biggest_victories": "biggest_wins", "top_scoring": "top_scoring_teams",
		"home_away": "home_advantage", "home_away_performance": "home_advantage",
		"summary": "summary",
	}
	if mapped, ok := aliases[metric]; ok {
		metric = mapped
	}
	if metric == "" {
		metric = "summary"
	}
	filter.IncludeUnplayed = true
	matches := db.filteredMatches(filter)
	played := make([]Match, 0, len(matches))
	for _, match := range matches {
		if match.ScoreKnown {
			played = append(played, match)
		}
	}
	result := StatisticsResult{
		Metric: metric, Competition: filter.Competition, Season: filter.Season,
		SourceScope: sourceScopeForOutput(filter.Source), DataSources: sourceNames(matches),
		Matches: len(played), UnknownFixturesExcluded: len(matches) - len(played),
	}
	switch metric {
	case "goals_per_match":
		goals := 0
		for _, match := range played {
			goals += match.HomeGoals + match.AwayGoals
		}
		average := 0.0
		if len(played) > 0 {
			average = roundTo(float64(goals)/float64(len(played)), 2)
		}
		result.Value = map[string]interface{}{"averageGoalsPerMatch": average, "totalGoals": goals, "unplayedExcluded": len(matches) - len(played)}
	case "home_advantage":
		homeWins, draws, awayWins := 0, 0, 0
		for _, match := range played {
			switch {
			case match.HomeGoals > match.AwayGoals:
				homeWins++
			case match.HomeGoals < match.AwayGoals:
				awayWins++
			default:
				draws++
			}
		}
		result.Value = map[string]interface{}{"homeWins": homeWins, "draws": draws, "awayWins": awayWins, "homeWinRate": percentage(homeWins, len(played))}
	case "best_home_record", "best_away_record":
		venue := "home"
		if metric == "best_away_record" {
			venue = "away"
		}
		records := db.venueRecords(played, venue)
		if len(records) == 0 {
			result.Value = []TeamStats{}
			break
		}
		result.Value = records[:min(10, len(records))]
	case "biggest_wins":
		sort.SliceStable(played, func(i, j int) bool {
			left := abs(played[i].HomeGoals - played[i].AwayGoals)
			right := abs(played[j].HomeGoals - played[j].AwayGoals)
			if left != right {
				return left > right
			}
			return played[i].Date.After(played[j].Date)
		})
		result.Value = played[:min(10, len(played))]
	case "top_scoring_teams":
		goals := make(map[string]int)
		for _, match := range played {
			goals[match.HomeKey] += match.HomeGoals
			goals[match.AwayKey] += match.AwayGoals
		}
		type scorer struct {
			Team  string `json:"team"`
			Goals int    `json:"goals"`
		}
		scorers := make([]scorer, 0, len(goals))
		for key, total := range goals {
			scorers = append(scorers, scorer{Team: db.displayName(key, key), Goals: total})
		}
		sort.Slice(scorers, func(i, j int) bool {
			if scorers[i].Goals != scorers[j].Goals {
				return scorers[i].Goals > scorers[j].Goals
			}
			return normalizeText(scorers[i].Team) < normalizeText(scorers[j].Team)
		})
		result.Value = scorers[:min(10, len(scorers))]
	case "summary":
		goals, homeWins, draws, awayWins := 0, 0, 0, 0
		for _, match := range played {
			goals += match.HomeGoals + match.AwayGoals
			if match.HomeGoals > match.AwayGoals {
				homeWins++
			} else if match.HomeGoals < match.AwayGoals {
				awayWins++
			} else {
				draws++
			}
		}
		average := 0.0
		if len(played) > 0 {
			average = roundTo(float64(goals)/float64(len(played)), 2)
		}
		result.Value = map[string]interface{}{"totalGoals": goals, "averageGoalsPerMatch": average, "homeWins": homeWins, "draws": draws, "awayWins": awayWins, "unplayedExcluded": len(matches) - len(played)}
	default:
		return StatisticsResult{}, fmt.Errorf("unsupported metric %q", metric)
	}
	return result, nil
}

func requireAggregateSource(source string) error {
	scope := normalizeSourceScope(source)
	if scope == "all" || scope == "raw" {
		return fmt.Errorf("source=all is only supported for raw match search; choose canonical or one named source for aggregates")
	}
	return nil
}

func (db *Database) venueRecords(matches []Match, venue string) []TeamStats {
	records := make(map[string]*TeamStats)
	for _, match := range matches {
		key, display, goalsFor, goalsAgainst := match.HomeKey, db.displayName(match.HomeKey, match.HomeTeam), match.HomeGoals, match.AwayGoals
		if venue == "away" {
			key, display, goalsFor, goalsAgainst = match.AwayKey, db.displayName(match.AwayKey, match.AwayTeam), match.AwayGoals, match.HomeGoals
		}
		stats := records[key]
		if stats == nil {
			stats = &TeamStats{Team: display, Venue: venue}
			records[key] = stats
		}
		stats.Matches++
		stats.GoalsFor += goalsFor
		stats.GoalsAgainst += goalsAgainst
		if goalsFor > goalsAgainst {
			stats.Wins++
		} else if goalsFor < goalsAgainst {
			stats.Losses++
		} else {
			stats.Draws++
		}
	}
	output := make([]TeamStats, 0, len(records))
	for _, stats := range records {
		if stats.Matches > 0 {
			stats.WinRate = roundTo(float64(stats.Wins)*100/float64(stats.Matches), 1)
		}
		output = append(output, *stats)
	}
	sort.Slice(output, func(i, j int) bool {
		leftPoints := output[i].Wins*3 + output[i].Draws
		rightPoints := output[j].Wins*3 + output[j].Draws
		if leftPoints != rightPoints {
			return leftPoints > rightPoints
		}
		if output[i].WinRate != output[j].WinRate {
			return output[i].WinRate > output[j].WinRate
		}
		goalDiffI := output[i].GoalsFor - output[i].GoalsAgainst
		goalDiffJ := output[j].GoalsFor - output[j].GoalsAgainst
		if goalDiffI != goalDiffJ {
			return goalDiffI > goalDiffJ
		}
		return normalizeText(output[i].Team) < normalizeText(output[j].Team)
	})
	return output
}

func (db *Database) displayName(key, fallback string) string {
	if name, ok := db.teamDisplay[key]; ok && name != "" {
		return name
	}
	return cleanDisplayTeam(fallback)
}

func sortMatchesNewestFirst(matches []Match) {
	sort.SliceStable(matches, func(i, j int) bool {
		left, right := matches[i], matches[j]
		if left.Date.IsZero() != right.Date.IsZero() {
			return !left.Date.IsZero()
		}
		if !left.Date.Equal(right.Date) {
			return left.Date.After(right.Date)
		}
		if left.Competition != right.Competition {
			return left.Competition < right.Competition
		}
		if left.HomeTeam != right.HomeTeam {
			return left.HomeTeam < right.HomeTeam
		}
		return left.AwayTeam < right.AwayTeam
	})
}

func startOfDay(value time.Time) time.Time {
	return time.Date(value.Year(), value.Month(), value.Day(), 0, 0, 0, 0, time.UTC)
}
func endOfDay(value time.Time) time.Time {
	return startOfDay(value).Add(24*time.Hour - time.Nanosecond)
}
func normalizedLimit(value int) int {
	if value <= 0 {
		return 20
	}
	if value > 100 {
		return 100
	}
	return value
}
func roundTo(value float64, places int) float64 {
	scale := math.Pow(10, float64(places))
	return math.Round(value*scale) / scale
}
func percentage(value, total int) float64 {
	if total == 0 {
		return 0
	}
	return roundTo(float64(value)*100/float64(total), 1)
}
func abs(value int) int {
	if value < 0 {
		return -value
	}
	return value
}
func min(left, right int) int {
	if left < right {
		return left
	}
	return right
}
