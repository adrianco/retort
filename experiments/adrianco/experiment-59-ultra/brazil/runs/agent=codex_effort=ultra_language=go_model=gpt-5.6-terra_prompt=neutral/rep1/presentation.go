package main

import (
	"fmt"
	"sort"
	"strings"
)

func pageMatches(matches []Match, offset, limit int) MatchSearchResult {
	total := len(matches)
	if offset < 0 {
		offset = 0
	}
	if offset > total {
		offset = total
	}
	end := offset + normalizedLimit(limit)
	if end > total {
		end = total
	}
	result := MatchSearchResult{Matches: append([]Match(nil), matches[offset:end]...), Total: total}
	if end < total {
		next := end
		result.NextOffset = &next
	}
	return result
}

func sourceNames(matches []Match) []string {
	seen := make(map[string]struct{})
	for _, match := range matches {
		if match.Source != "" {
			seen[match.Source] = struct{}{}
		}
	}
	sources := make([]string, 0, len(seen))
	for source := range seen {
		sources = append(sources, source)
	}
	sort.Strings(sources)
	return sources
}

func competitionsFor(matches []Match) []string {
	seen := make(map[string]struct{})
	for _, match := range matches {
		if match.Competition != "" {
			seen[match.Competition] = struct{}{}
		}
	}
	competitions := make([]string, 0, len(seen))
	for competition := range seen {
		competitions = append(competitions, competition)
	}
	sort.Strings(competitions)
	return competitions
}

func formatMatchSearch(result MatchSearchResult) string {
	if result.Total == 0 {
		return "No matching matches were found in the selected data sources."
	}
	var builder strings.Builder
	fmt.Fprintf(&builder, "Found %d matching match(es); showing %d.\n", result.Total, len(result.Matches))
	for _, match := range result.Matches {
		fmt.Fprintf(&builder, "- %s\n", formatMatch(match))
	}
	if result.NextOffset != nil {
		fmt.Fprintf(&builder, "More results are available from offset %d.", *result.NextOffset)
	}
	return strings.TrimSpace(builder.String())
}

func formatMatch(match Match) string {
	score := "score unavailable"
	if match.ScoreKnown {
		score = fmt.Sprintf("%d-%d", match.HomeGoals, match.AwayGoals)
	}
	details := []string{match.Competition}
	if match.Round != "" {
		details = append(details, "Round "+match.Round)
	}
	if match.Stage != "" {
		details = append(details, match.Stage)
	}
	if match.Source != "" {
		details = append(details, "source: "+match.Source)
	}
	date := match.DateText
	if date == "" {
		date = "date unavailable"
	}
	return fmt.Sprintf("%s: %s %s %s (%s)", date, match.HomeTeam, score, match.AwayTeam, strings.Join(details, ", "))
}

func formatTeamStats(stats TeamStats) string {
	context := stats.Team
	if stats.Competition != "" {
		context += " — " + stats.Competition
	}
	if stats.Season != 0 {
		context += fmt.Sprintf(" %d", stats.Season)
	}
	text := fmt.Sprintf("%s %s record: %d matches, %dW-%dD-%dL, %d goals for, %d against, %.1f%% win rate.", context, stats.Venue, stats.Matches, stats.Wins, stats.Draws, stats.Losses, stats.GoalsFor, stats.GoalsAgainst, stats.WinRate)
	if stats.UnknownFixturesExcluded > 0 {
		text += fmt.Sprintf(" %d unknown or scheduled fixture(s) excluded.", stats.UnknownFixturesExcluded)
	}
	if len(stats.DataSources) > 0 {
		text += " Sources: " + strings.Join(stats.DataSources, ", ") + "."
	}
	return text
}

func formatHeadToHead(summary HeadToHead, matches MatchSearchResult) string {
	text := fmt.Sprintf("%s vs %s: %d completed match(es), %s %d wins, %s %d wins, %d draws.", summary.TeamA, summary.TeamB, summary.Matches, summary.TeamA, summary.TeamAWins, summary.TeamB, summary.TeamBWins, summary.Draws)
	if len(summary.DataSources) > 0 {
		text += " Sources: " + strings.Join(summary.DataSources, ", ") + "."
	}
	if len(matches.Matches) == 0 {
		return text
	}
	return text + "\n" + formatMatchSearch(matches)
}

func formatPlayers(players []Player, total int) string {
	if total == 0 {
		return "No players matched the supplied FIFA snapshot filters."
	}
	var builder strings.Builder
	fmt.Fprintf(&builder, "Found %d player(s); showing %d.\n", total, len(players))
	for _, player := range players {
		club := player.Club
		if club == "" {
			club = "no club listed"
		}
		fmt.Fprintf(&builder, "- %s — Overall %d, %s, %s, %s\n", player.Name, player.Overall, player.Position, club, player.Nationality)
	}
	return strings.TrimSpace(builder.String())
}

func formatStandings(competition string, season int, standings []Standing) string {
	if len(standings) == 0 {
		return fmt.Sprintf("No completed %s matches were found for season %d.", competition, season)
	}
	var builder strings.Builder
	fmt.Fprintf(&builder, "%s %d standings (points, wins, goal difference, goals scored):\n", competition, season)
	for _, standing := range standings {
		fmt.Fprintf(&builder, "%d. %s — %d pts (%dW, %dD, %dL; %d-%d)\n", standing.Position, standing.Team, standing.Points, standing.Wins, standing.Draws, standing.Losses, standing.GoalsFor, standing.GoalsAgainst)
	}
	return strings.TrimSpace(builder.String())
}

func formatStandingsWithExclusions(competition string, season int, standings []Standing, excluded int) string {
	text := formatStandings(competition, season, standings)
	if excluded > 0 {
		text += fmt.Sprintf(" %d unknown or scheduled fixture(s) excluded.", excluded)
	}
	return text
}

func formatStatistics(result StatisticsResult) string {
	context := result.Metric
	if result.Competition != "" {
		context += " for " + result.Competition
	}
	if result.Season != 0 {
		context += fmt.Sprintf(" %d", result.Season)
	}
	text := fmt.Sprintf("%s, calculated from %d completed match(es): %v", context, result.Matches, result.Value)
	if result.UnknownFixturesExcluded > 0 {
		text += fmt.Sprintf(" (%d unknown or scheduled fixture(s) excluded)", result.UnknownFixturesExcluded)
	}
	if len(result.DataSources) > 0 {
		text += ". Sources: " + strings.Join(result.DataSources, ", ")
	}
	return text
}

func formatSources(database *Database) string {
	keys := make([]string, 0, len(database.Report.Sources))
	for name := range database.Report.Sources {
		keys = append(keys, name)
	}
	sort.Strings(keys)
	var builder strings.Builder
	fmt.Fprintf(&builder, "Loaded %d match rows and %d FIFA player rows from six CSV files:\n", len(database.Matches), len(database.Players))
	for _, name := range keys {
		report := database.Report.Sources[name]
		fmt.Fprintf(&builder, "- %s: %d loaded, %d skipped (%s)\n", name, report.Loaded, report.Skipped, report.Path)
	}
	return strings.TrimSpace(builder.String())
}

type derbyPair struct {
	Name  string
	TeamA string
	TeamB string
}

var traditionalDerbies = []derbyPair{
	{Name: "Fla-Flu", TeamA: "Flamengo", TeamB: "Fluminense"},
	{Name: "Derby Paulista", TeamA: "Palmeiras", TeamB: "Corinthians"},
	{Name: "Majestoso", TeamA: "Corinthians", TeamB: "São Paulo"},
	{Name: "San-São", TeamA: "Santos", TeamB: "São Paulo"},
	{Name: "Grenal", TeamA: "Grêmio", TeamB: "Internacional"},
	{Name: "Clássico Mineiro", TeamA: "Atlético-MG", TeamB: "Cruzeiro"},
	{Name: "Ba-Vi", TeamA: "Bahia", TeamB: "Vitória"},
	{Name: "Clássico dos Clássicos", TeamA: "Sport", TeamB: "Náutico"},
}

func derbyMatches(database *Database, filter MatchFilter) []Match {
	base := database.filteredMatches(filter)
	pairs := make(map[string]struct{}, len(traditionalDerbies))
	for _, derby := range traditionalDerbies {
		left, right := normalizeTeam(derby.TeamA), normalizeTeam(derby.TeamB)
		pairs[left+"|"+right], pairs[right+"|"+left] = struct{}{}, struct{}{}
	}
	matches := make([]Match, 0)
	for _, match := range base {
		if _, ok := pairs[match.HomeKey+"|"+match.AwayKey]; ok {
			matches = append(matches, match)
		}
	}
	sortMatchesNewestFirst(matches)
	return matches
}
