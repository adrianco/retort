package server

import (
	"fmt"
	"sort"
	"strconv"
	"strings"
)

// QueryResult represents a query result
type QueryResult struct {
	Matches   []Match   `json:"matches"`
	Players   []Player  `json:"players"`
	TeamStats []TeamStats `json:"team_stats"`
	Table     CompetitionTable `json:"table"`
	Message   string    `json:"message"`
	Count     int       `json:"count"`
	Error     string    `json:"error,omitempty"`
}

// QueryContext represents the context of a query
type QueryContext struct {
	Team1        string
	Team2        string
	Season       int
	Competition  string
	PlayerName   string
	Club         string
	Nationality  string
	Position     string
	Limit        int
	Offset       int
	SortBy       string
	SortOrder    string
}

// QueryEngine handles query processing
type QueryEngine struct {
	store *DataStore
}

// NewQueryEngine creates a new query engine
func NewQueryEngine(store *DataStore) *QueryEngine {
	return &QueryEngine{store: store}
}

// Query processes a natural language query and returns results
func (qe *QueryEngine) Query(query string) QueryResult {
	queryLower := strings.ToLower(query)

	// Determine query type
	if strings.Contains(queryLower, "vs") || strings.Contains(queryLower, "versus") || strings.Contains(queryLower, "head to head") {
		return qe.handleTeamVsTeamQuery(query)
	}
	if strings.Contains(queryLower, "statistic") || strings.Contains(queryLower, "record") || strings.Contains(queryLower, "wins") || strings.Contains(queryLower, "losses") {
		return qe.handleTeamStatsQuery(query)
	}
	if strings.Contains(queryLower, "player") || strings.Contains(queryLower, "who is") {
		return qe.handlePlayerQuery(query)
	}
	if strings.Contains(queryLower, "table") || strings.Contains(queryLower, "standings") || strings.Contains(queryLower, "winner") {
		return qe.handleTableQuery(query)
	}
	if strings.Contains(queryLower, "average") || strings.Contains(queryLower, "biggest") || strings.Contains(queryLower, "most") {
		return qe.handleStatisticalQuery(query)
	}

	// Default to team match search
	return qe.handleDefaultTeamMatchQuery(query)
}

func (qe *QueryEngine) handleTeamVsTeamQuery(query string) QueryResult {
	// Extract team names
	team1, team2, found := extractTeamPair(query)
	if !found {
		return QueryResult{
			Message: "Could not identify two teams in the query",
			Count:   0,
		}
	}

	matches := qe.store.GetMatchesByTeams(team1, team2, 20)

	if len(matches) == 0 {
		return QueryResult{
			Message: fmt.Sprintf("No matches found between %s and %s", team1, team2),
			Count:   0,
		}
	}

	team1Wins, team2Wins, draws := qe.store.GetHeadToHead(team1, team2)

	message := fmt.Sprintf("%s vs %s:\n", team1, team2)
	for _, match := range matches {
		date := match.Datetime.Format("2006-01-02")
		var competition string
		if match.Tournament != "" {
			competition = match.Tournament
		} else if match.Round > 0 {
			competition = fmt.Sprintf("Round %d", match.Round)
		} else {
			competition = fmt.Sprintf("Season %d", match.Season)
		}

		var homeTeam, awayTeam string
		if strings.Contains(match.HomeTeam, team1) {
			homeTeam, awayTeam = team1, team2
		} else {
			homeTeam, awayTeam = team2, team1
		}

		message += fmt.Sprintf("- %s: %s %d-%d %s (%s)\n",
			date, homeTeam, match.HomeGoal, match.AwayGoal, awayTeam, competition)
	}

	message += fmt.Sprintf("\nHead-to-head: %s %d wins, %s %d wins, %d draws",
		team1, team1Wins, team2, team2Wins, draws)

	return QueryResult{
		Matches: matches,
		Message: message,
		Count:   len(matches),
	}
}

func (qe *QueryEngine) handleTeamStatsQuery(query string) QueryResult {
	team := extractTeamName(query)
	if team == "" {
		return QueryResult{
			Message: "Could not identify a team in the query",
			Count:   0,
		}
	}

	// Extract season if present
	season := extractSeason(query)

	stats := qe.store.GetTeamStats(team, season, "")

	if stats.Matches == 0 {
		return QueryResult{
			Message: fmt.Sprintf("No statistics found for %s", team),
			Count:   0,
		}
	}

	winRate := float64(stats.Wins) / float64(stats.Matches) * 100

	message := fmt.Sprintf("%s Statistics:\n", team)
	message += fmt.Sprintf("- Matches: %d\n", stats.Matches)
	message += fmt.Sprintf("- Wins: %d, Draws: %d, Losses: %d\n", stats.Wins, stats.Draws, stats.Losses)
	message += fmt.Sprintf("- Goals For: %d, Goals Against: %d\n", stats.GoalsFor, stats.GoalsAgainst)
	message += fmt.Sprintf("- Win rate: %.1f%%\n", winRate)

	if stats.HomeMatches > 0 {
		homeWinRate := float64(stats.HomeWins) / float64(stats.HomeMatches) * 100
		message += fmt.Sprintf("\nHome record:\n")
		message += fmt.Sprintf("- Matches: %d\n", stats.HomeMatches)
		message += fmt.Sprintf("- Wins: %d, Draws: %d, Losses: %d\n", stats.HomeWins, stats.HomeDraws, stats.HomeLosses)
		message += fmt.Sprintf("- Goals For: %d, Goals Against: %d\n", stats.HomeGF, stats.HomeGA)
		message += fmt.Sprintf("- Home win rate: %.1f%%\n", homeWinRate)
	}

	if stats.AwayMatches > 0 {
		awayWinRate := float64(stats.AwayWins) / float64(stats.AwayMatches) * 100
		message += fmt.Sprintf("\nAway record:\n")
		message += fmt.Sprintf("- Matches: %d\n", stats.AwayMatches)
		message += fmt.Sprintf("- Wins: %d, Draws: %d, Losses: %d\n", stats.AwayWins, stats.AwayDraws, stats.AwayLosses)
		message += fmt.Sprintf("- Goals For: %d, Goals Against: %d\n", stats.AwayGF, stats.AwayGA)
		message += fmt.Sprintf("- Away win rate: %.1f%%\n", awayWinRate)
	}

	return QueryResult{
		TeamStats: []TeamStats{stats},
		Message:   message,
		Count:     1,
	}
}

func (qe *QueryEngine) handlePlayerQuery(query string) QueryResult {
	name := extractPlayerName(query)
	if name == "" {
		return QueryResult{
			Message: "Could not identify a player in the query",
			Count:   0,
		}
	}

	players := qe.store.GetPlayerByName(name, 20)

	if len(players) == 0 {
		return QueryResult{
			Message: fmt.Sprintf("No players found matching '%s'", name),
			Count:   0,
		}
	}

	message := fmt.Sprintf("Players matching '%s':\n", name)
	for _, player := range players {
		message += fmt.Sprintf("- %s: Overall %d, Position: %s, Club: %s\n",
			player.Name, player.Overall, player.Position, player.Club)
	}

	return QueryResult{
		Players: players,
		Message: message,
		Count:   len(players),
	}
}

func (qe *QueryEngine) handleTableQuery(query string) QueryResult {
	// Extract competition and season
	comp := extractCompetition(query)
	season := extractSeason(query)

	if season == 0 {
		season = 2023 // Default to most recent season
	}

	table := qe.calculateLeagueTable(comp, season)

	if len(table.Teams) == 0 {
		return QueryResult{
			Message: fmt.Sprintf("No league table data found for %s %d", comp, season),
			Count:   0,
		}
	}

	message := fmt.Sprintf("%s %d Final Standings:\n", comp, season)
	for i, standing := range table.Teams {
		teamName := standing.Team
		if i == 0 {
			teamName += " - Champion"
		}
		message += fmt.Sprintf("%d. %s - %d pts (%dW, %dD, %dL)\n",
			i+1, teamName, standing.Points, standing.Won, standing.Drawn, standing.Lost)
	}

	return QueryResult{
		Table:   table,
		Message: message,
		Count:   len(table.Teams),
	}
}

func (qe *QueryEngine) handleStatisticalQuery(query string) QueryResult {
	queryLower := strings.ToLower(query)

	if strings.Contains(queryLower, "average goals") || strings.Contains(queryLower, "goals per match") {
		return qe.handleAverageGoalsQuery()
	}

	if strings.Contains(queryLower, "biggest") || strings.Contains(queryLower, "biggest wins") {
		return qe.handleBiggestWinsQuery()
	}

	if strings.Contains(queryLower, "best home record") {
		return qe.handleBestHomeRecordQuery()
	}

	return QueryResult{
		Message: "Could not understand the statistical query",
		Count:   0,
	}
}

func (qe *QueryEngine) handleAverageGoalsQuery() QueryResult {
	allMatches := qe.getAllMatches()

	if len(allMatches) == 0 {
		return QueryResult{
			Message: "No matches found in the dataset",
			Count:   0,
		}
	}

	totalGoals := 0
	for _, match := range allMatches {
		totalGoals += match.HomeGoal + match.AwayGoal
	}

	avgGoals := float64(totalGoals) / float64(len(allMatches))

	// Count home wins, away wins, draws
	homeWins := 0
	awayWins := 0
	draws := 0
	for _, match := range allMatches {
		if match.HomeGoal > match.AwayGoal {
			homeWins++
		} else if match.HomeGoal < match.AwayGoal {
			awayWins++
		} else {
			draws++
		}
	}

	homeWinRate := float64(homeWins) / float64(len(allMatches)) * 100

	message := fmt.Sprintf("Statistical Analysis:\n")
	message += fmt.Sprintf("- Average goals per match: %.2f\n", avgGoals)
	message += fmt.Sprintf("- Home wins: %d (%.1f%%)\n", homeWins, homeWinRate)
	message += fmt.Sprintf("- Draws: %d\n", draws)
	message += fmt.Sprintf("- Away wins: %d\n", awayWins)

	return QueryResult{
		Message: message,
		Count:   1,
	}
}

func (qe *QueryEngine) handleBiggestWinsQuery() QueryResult {
	allMatches := qe.getAllMatches()

	if len(allMatches) == 0 {
		return QueryResult{
			Message: "No matches found in the dataset",
			Count:   0,
		}
	}

	// Calculate goal difference for each match
	type matchDiff struct {
		match Match
		diff  int
	}

	var diffs []matchDiff
	for _, match := range allMatches {
		diff := abs(match.HomeGoal - match.AwayGoal)
		diffs = append(diffs, matchDiff{match: match, diff: diff})
	}

	// Sort by goal difference descending
	sort.Slice(diffs, func(i, j int) bool {
		return diffs[i].diff > diffs[j].diff
	})

	message := "Biggest victories in dataset:\n"
	count := 0
	for _, d := range diffs {
		if d.diff > 0 {
			message += fmt.Sprintf("- %s: %s %d-%d %s (%s)\n",
				d.match.Datetime.Format("2006-01-02"),
				d.match.HomeTeam, d.match.HomeGoal, d.match.AwayGoal, d.match.AwayTeam,
				getCompetitionName(&d.match))
			count++
			if count >= 10 {
				break
			}
		}
	}

	return QueryResult{
		Message: message,
		Count:   count,
	}
}

func (qe *QueryEngine) handleBestHomeRecordQuery() QueryResult {
	allMatches := qe.getAllMatches()

	teamStats := make(map[string]*TeamStats)

	for _, match := range allMatches {
		homeTeam := NormalizeTeamName(match.HomeTeam)

		if _, exists := teamStats[homeTeam]; !exists {
			teamStats[homeTeam] = &TeamStats{TeamName: homeTeam}
		}

		stats := teamStats[homeTeam]
		stats.HomeMatches++
		stats.HomeGF += match.HomeGoal
		stats.HomeGA += match.AwayGoal

		if match.HomeGoal > match.AwayGoal {
			stats.HomeWins++
			stats.Points += 3
		} else if match.HomeGoal == match.AwayGoal {
			stats.HomeDraws++
			stats.Points += 1
		} else {
			stats.HomeLosses++
		}
	}

	// Convert to slice and sort
	var teams []TeamStats
	for _, stats := range teamStats {
		teams = append(teams, *stats)
	}

	sort.Slice(teams, func(i, j int) bool {
		return float64(teams[i].HomeWins)/float64(teams[i].HomeMatches) >
			float64(teams[j].HomeWins)/float64(teams[j].HomeMatches)
	})

	message := "Teams with best home records:\n"
	count := 0
	for _, stats := range teams {
		if stats.HomeMatches > 0 {
			winRate := float64(stats.HomeWins) / float64(stats.HomeMatches) * 100
			message += fmt.Sprintf("- %s: %d wins in %d home matches (%.1f%% win rate)\n",
				stats.TeamName, stats.HomeWins, stats.HomeMatches, winRate)
			count++
			if count >= 10 {
				break
			}
		}
	}

	return QueryResult{
		Message: message,
		Count:   count,
	}
}

func (qe *QueryEngine) getAllMatches() []Match {
	return append(append(append(append(
		qe.store.BrasileiraoMatches,
		qe.store.CopaDoBrasilMatches...),
		qe.store.CopaLibertadoresMatches...),
		qe.store.BRFootballMatches...),
		qe.store.NovoCampeonatoMatches...)
}

func (qe *QueryEngine) calculateLeagueTable(competition string, season int) CompetitionTable {
	allMatches := qe.getAllMatches()

	teamStats := make(map[string]*TeamStanding)

	for _, match := range allMatches {
		if match.Season != season {
			continue
		}

		// Check if this match belongs to the specified competition
		if !matchBelongsToCompetition(&match, competition) {
			continue
		}

		homeTeam := NormalizeTeamName(match.HomeTeam)
		awayTeam := NormalizeTeamName(match.AwayTeam)

		if _, exists := teamStats[homeTeam]; !exists {
			teamStats[homeTeam] = &TeamStanding{Team: homeTeam}
		}
		if _, exists := teamStats[awayTeam]; !exists {
			teamStats[awayTeam] = &TeamStanding{Team: awayTeam}
		}

		homeStats := teamStats[homeTeam]
		awayStats := teamStats[awayTeam]

		homeStats.Played++
		awayStats.Played++
		homeStats.GoalsFor += match.HomeGoal
		homeStats.GoalsAgainst += match.AwayGoal
		awayStats.GoalsFor += match.AwayGoal
		awayStats.GoalsAgainst += match.HomeGoal

		if match.HomeGoal > match.AwayGoal {
			homeStats.Won++
			homeStats.Points += 3
			awayStats.Lost++
		} else if match.HomeGoal < match.AwayGoal {
			awayStats.Won++
			awayStats.Points += 3
			homeStats.Lost++
		} else {
			homeStats.Drawn++
			awayStats.Drawn++
			homeStats.Points += 1
			awayStats.Points += 1
		}
	}

	// Convert to slice and sort
	var teams []TeamStanding
	for _, stats := range teamStats {
		stats.GoalDifference = stats.GoalsFor - stats.GoalsAgainst
		teams = append(teams, *stats)
	}

	sort.Slice(teams, func(i, j int) bool {
		if teams[i].Points == teams[j].Points {
			return teams[i].GoalDifference > teams[j].GoalDifference
		}
		return teams[i].Points > teams[j].Points
	})

	return CompetitionTable{
		Competition: competition,
		Season:      season,
		Teams:       teams,
	}
}

func matchBelongsToCompetition(match *Match, competition string) bool {
	if competition == "" {
		return true
	}

	compLower := strings.ToLower(competition)

	// Check tournament name
	if match.Tournament != "" && strings.Contains(strings.ToLower(match.Tournament), compLower) {
		return true
	}

	// Check for Brasileirão/Brasileirao
	if compLower == "brasileirao" || compLower == "brasileirão" {
		// Check if it's a Brasileirão match
		if strings.Contains(strings.ToLower(match.HomeTeam), "brasileirao") ||
			strings.Contains(strings.ToLower(match.AwayTeam), "brasileirao") {
			return true
		}
		// Check season 2003-2019 data
		if match.Season >= 2003 && match.Season <= 2019 {
			return true
		}
		return false
	}

	// Check other competitions
	if strings.Contains(strings.ToLower(match.Tournament), compLower) ||
		strings.Contains(strings.ToLower(match.HomeTeam), compLower) ||
		strings.Contains(strings.ToLower(match.AwayTeam), compLower) {
		return true
	}

	return false
}

// Helper functions for extracting query components

func extractTeamPair(query string) (string, string, bool) {
	// Try to find two team names
	teams := findTeamsInQuery(query)
	if len(teams) >= 2 {
		return teams[0], teams[1], true
	}
	return "", "", false
}

func extractTeamName(query string) string {
	teams := findTeamsInQuery(query)
	if len(teams) > 0 {
		return teams[0]
	}
	return ""
}

func findTeamsInQuery(query string) []string {
	// Known Brazilian teams
	knownTeams := []string{
		"flamengo", "fluminense", "palmeiras", "sao paulo",
		"corinthians", "santos", "vasco", "botafogo",
		"gremio", "internacional", "atletico",
		"cruzeiro", "america", "bahia", "fortaleza",
		"ceara", "sport", "paysandu",
		"brasiliense", "galo", "tigre",
	}

	// Check for team names in query
	var foundTeams []string
	queryLower := strings.ToLower(query)

	for _, team := range knownTeams {
		if strings.Contains(queryLower, team) {
			foundTeams = append(foundTeams, normalizeTeamName(team))
		}
	}

	return foundTeams
}

func extractPlayerName(query string) string {
	// Common player name patterns
	queries := []string{"neymar", "messi", "ronaldo", "casemiro", "vinicius",
		"mbappe", "haaland", "kylian", "rodrygo", "pele", "maradona",
		"zico", "romario", "bebeto", "rivaldo",
	}

	queryLower := strings.ToLower(query)
	for _, q := range queries {
		if strings.Contains(queryLower, q) {
			return q
		}
	}

	// Try to extract from "who is [name]" pattern
	if idx := strings.Index(queryLower, "who is"); idx >= 0 {
		rest := strings.TrimSpace(query[idx+8:])
		if len(rest) > 0 {
			return rest
		}
	}

	return ""
}

func extractSeason(query string) int {
	// Look for 4-digit year patterns
	for i := 0; i <= len(query)-4; i++ {
		substr := query[i : i+4]
		if isYear(substr) {
			year, _ := strconv.Atoi(substr)
			return year
		}
	}
	return 0
}

func isYear(s string) bool {
	if len(s) != 4 {
		return false
	}
	for i := 0; i < 4; i++ {
		if s[i] < '0' || s[i] > '9' {
			return false
		}
	}
	year, _ := strconv.Atoi(s)
	return year >= 1900 && year <= 2100
}

func extractCompetition(query string) string {
	queryLower := strings.ToLower(query)

	competitions := map[string]string{
		"brasileirao":    "Brasileirão",
		"brasileirão":    "Brasileirão",
		"copa do brasil": "Copa do Brasil",
		"libertadores":   "Copa Libertadores",
	}

	for key, comp := range competitions {
		if strings.Contains(queryLower, key) {
			return comp
		}
	}

	return "Brasileirão"
}

func normalizeTeamName(name string) string {
	return NormalizeTeamName(name)
}

func getCompetitionName(match *Match) string {
	if match.Tournament != "" {
		return match.Tournament
	}
	if match.Round > 0 {
		return fmt.Sprintf("Round %d", match.Round)
	}
	return fmt.Sprintf("Season %d", match.Season)
}

func abs(x int) int {
	if x < 0 {
		return -x
	}
	return x
}

func (qe *QueryEngine) handleDefaultTeamMatchQuery(query string) QueryResult {
	team := extractTeamName(query)
	if team == "" {
		return QueryResult{
			Message: "Could not identify a team in the query",
			Count:   0,
		}
	}

	matches := qe.store.GetMatchesByTeams(team, "", 20)

	if len(matches) == 0 {
		return QueryResult{
			Message: fmt.Sprintf("No matches found for %s", team),
			Count:   0,
		}
	}

	message := fmt.Sprintf("Matches for %s:\n", team)
	for _, match := range matches {
		date := match.Datetime.Format("2006-01-02")
		var competition string
		if match.Tournament != "" {
			competition = match.Tournament
		} else if match.Round > 0 {
			competition = fmt.Sprintf("Round %d", match.Round)
		} else {
			competition = fmt.Sprintf("Season %d", match.Season)
		}

		var homeTeam, awayTeam string
		if NormalizeTeamName(match.HomeTeam) == NormalizeTeamName(team) {
			homeTeam, awayTeam = match.HomeTeam, match.AwayTeam
		} else {
			homeTeam, awayTeam = match.AwayTeam, match.HomeTeam
		}

		message += fmt.Sprintf("- %s: %s %d-%d %s (%s)\n",
			date, homeTeam, match.HomeGoal, match.AwayGoal, awayTeam, competition)
	}

	return QueryResult{
		Matches: matches,
		Message: message,
		Count:   len(matches),
	}
}
