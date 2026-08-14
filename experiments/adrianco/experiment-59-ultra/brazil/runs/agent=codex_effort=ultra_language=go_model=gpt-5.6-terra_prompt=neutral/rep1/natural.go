package main

import (
	"fmt"
	"regexp"
	"sort"
	"strconv"
	"strings"
)

var yearInQuestion = regexp.MustCompile(`\b(19|20)\d{2}\b`)

// answerQuestion deliberately handles the recurring question shapes in TASK.md
// without pretending to be an LLM. MCP clients can instead let an LLM choose
// the typed tools; this convenience tool remains fully local and deterministic.
func (server *MCPServer) answerQuestion(question string) (interface{}, string, *toolExecutionError) {
	query := normalizeText(question)
	if query == "" {
		return nil, "", invalidArgument(fmt.Errorf("question is required"))
	}
	filter := MatchFilter{Competition: questionCompetition(query), Season: questionYear(query), IncludeUnplayed: true, Limit: 20}
	teams := server.teamsMentioned(query)

	if strings.Contains(query, "top scorer") || strings.Contains(query, "top scorers") {
		return nil, "", &toolExecutionError{Code: "DATA_UNAVAILABLE", Message: "Top scorers cannot be calculated because the supplied datasets contain match scores but no goalscorer events."}
	}
	if strings.Contains(query, "bracket") {
		return nil, "", &toolExecutionError{Code: "DATA_UNAVAILABLE", Message: "A reliable knockout bracket cannot be reconstructed from these rows because they lack tie and advancement metadata."}
	}
	if strings.Contains(query, "derby") || strings.Contains(query, "derbies") {
		matches := derbyMatches(server.Database, filter)
		result := pageMatches(matches, 0, filter.Limit)
		return map[string]interface{}{"matches": result.Matches, "total": result.Total, "note": "Static traditional-rivalry map."}, formatMatchSearch(result), nil
	}
	if isPlayerQuestion(query) {
		playerFilter := playerFilterFromQuestion(question, query)
		players, total, next := server.Database.SearchPlayers(playerFilter)
		return map[string]interface{}{"players": players, "total": total, "nextOffset": next, "source": "fifa_players"}, formatPlayers(players, total), nil
	}
	if strings.Contains(query, "compare") && strings.Contains(query, "season") {
		years := questionYears(query)
		if len(years) >= 2 {
			competition := filter.Competition
			if competition == "" {
				competition = "brasileirao"
			}
			comparisons := make([]StatisticsResult, 0, len(years))
			for _, season := range years {
				result, err := server.Database.AnalyzeMatches(MatchFilter{Competition: competition, Season: season, IncludeUnplayed: true}, "summary")
				if err != nil {
					return nil, "", invalidArgument(err)
				}
				comparisons = append(comparisons, result)
			}
			return map[string]interface{}{"competition": competition, "seasons": comparisons}, formatSeasonComparison(competition, comparisons), nil
		}
	}
	if strings.Contains(query, "relegat") {
		if filter.Season == 0 {
			return nil, "", invalidArgument(fmt.Errorf("please include a season for relegation lookup"))
		}
		if filter.Competition == "" {
			filter.Competition = "brasileirao"
		}
		standings, err := server.Database.CompetitionStandings(filter.Competition, filter.Season, "")
		if err != nil {
			return nil, "", invalidArgument(err)
		}
		standingMatches, unplayedExcluded := server.Database.matchesWithUnknown(MatchFilter{Competition: filter.Competition, Season: filter.Season})
		bottom := append([]Standing(nil), standings[max(0, len(standings)-4):]...)
		return map[string]interface{}{"competition": filter.Competition, "season": filter.Season, "bottomFour": bottom, "sourceScope": "canonical", "dataSources": sourceNames(standingMatches), "unplayedExcluded": unplayedExcluded, "note": "Bottom four in the calculated table; the supplied rows do not carry official relegation metadata."}, formatRelegationCandidates(filter.Competition, filter.Season, bottom), nil
	}
	if strings.Contains(query, "who won") || strings.Contains(query, "standings") || strings.Contains(query, "table") {
		if filter.Season == 0 {
			return nil, "", invalidArgument(fmt.Errorf("please include a season for standings"))
		}
		if filter.Competition == "" {
			filter.Competition = "brasileirao"
		}
		if normalizeCompetition(filter.Competition) != "brasileirao" {
			filter.Stage = "final"
			result := server.Database.SearchMatches(filter)
			return map[string]interface{}{"matches": result.Matches, "total": result.Total, "nextOffset": result.NextOffset, "note": "Knockout winners are represented by final match results, not a league standings table."}, formatMatchSearch(result), nil
		}
		standings, err := server.Database.CompetitionStandings(filter.Competition, filter.Season, "")
		if err != nil {
			return nil, "", invalidArgument(err)
		}
		standingMatches, unplayedExcluded := server.Database.matchesWithUnknown(MatchFilter{Competition: filter.Competition, Season: filter.Season})
		return map[string]interface{}{"competition": filter.Competition, "season": filter.Season, "standings": standings, "sourceScope": "canonical", "dataSources": sourceNames(standingMatches), "unplayedExcluded": unplayedExcluded}, formatStandingsWithExclusions(filter.Competition, filter.Season, standings, unplayedExcluded), nil
	}
	if strings.Contains(query, "average goals") || strings.Contains(query, "goals per match") {
		result, err := server.Database.AnalyzeMatches(filter, "goals_per_match")
		if err != nil {
			return nil, "", invalidArgument(err)
		}
		return result, formatStatistics(result), nil
	}
	if strings.Contains(query, "best home") {
		result, err := server.Database.AnalyzeMatches(filter, "best_home_record")
		if err != nil {
			return nil, "", invalidArgument(err)
		}
		return result, formatStatistics(result), nil
	}
	if strings.Contains(query, "best away") {
		result, err := server.Database.AnalyzeMatches(filter, "best_away_record")
		if err != nil {
			return nil, "", invalidArgument(err)
		}
		return result, formatStatistics(result), nil
	}
	if strings.Contains(query, "biggest win") || strings.Contains(query, "biggest victories") || strings.Contains(query, "biggest victory") {
		result, err := server.Database.AnalyzeMatches(filter, "biggest_wins")
		if err != nil {
			return nil, "", invalidArgument(err)
		}
		return result, formatStatistics(result), nil
	}
	if strings.Contains(query, "final") && filter.Competition != "" {
		filter.Stage = "final"
		result := server.Database.SearchMatches(filter)
		return map[string]interface{}{"matches": result.Matches, "total": result.Total, "nextOffset": result.NextOffset}, formatMatchSearch(result), nil
	}
	if strings.Contains(query, "scored the most") || strings.Contains(query, "top scoring") || strings.Contains(query, "most goals") {
		result, err := server.Database.AnalyzeMatches(filter, "top_scoring_teams")
		if err != nil {
			return nil, "", invalidArgument(err)
		}
		return result, formatStatistics(result), nil
	}
	if len(teams) >= 2 {
		filter.Team, filter.Opponent = teams[0], teams[1]
		summary, matches, err := server.Database.CompareTeams(teams[0], teams[1], filter)
		if err != nil {
			return nil, "", invalidArgument(err)
		}
		limit := filter.Limit
		if strings.Contains(query, "last") || strings.Contains(query, "most recent") {
			limit = 1
		}
		page := pageMatches(matches, 0, limit)
		return map[string]interface{}{"headToHead": summary, "matches": page.Matches, "total": page.Total}, formatHeadToHead(summary, page), nil
	}
	if len(teams) == 1 && (strings.Contains(query, "competition") || strings.Contains(query, "competitions")) {
		filter.Team = teams[0]
		matches := server.Database.filteredMatches(filter)
		competitions := competitionsFor(matches)
		display := server.Database.displayName(normalizeTeam(teams[0]), teams[0])
		return map[string]interface{}{"team": display, "competitions": competitions, "dataSources": sourceNames(matches)}, fmt.Sprintf("%s has matches in: %s.", display, strings.Join(competitions, ", ")), nil
	}
	if len(teams) == 1 && strings.Contains(query, "record") {
		filter.Team = teams[0]
		venue := "all"
		if strings.Contains(query, "home") {
			venue = "home"
		} else if strings.Contains(query, "away") {
			venue = "away"
		}
		stats, err := server.Database.TeamStatistics(teams[0], filter, venue)
		if err != nil {
			return nil, "", invalidArgument(err)
		}
		return stats, formatTeamStats(stats), nil
	}
	if len(teams) == 1 {
		filter.Team = teams[0]
		if strings.Contains(query, "last") || strings.Contains(query, "most recent") {
			filter.Limit = 1
		}
		result := server.Database.SearchMatches(filter)
		return map[string]interface{}{"matches": result.Matches, "total": result.Total, "nextOffset": result.NextOffset}, formatMatchSearch(result), nil
	}
	result, err := server.Database.AnalyzeMatches(filter, "summary")
	if err != nil {
		return nil, "", invalidArgument(err)
	}
	return result, formatStatistics(result), nil
}

func (server *MCPServer) teamsMentioned(query string) []string {
	matched := make([]string, 0, 2)
	padded := " " + query + " "
	add := func(key string) {
		if key == "" || len(matched) >= 2 {
			return
		}
		if _, known := server.Database.teamIndex[key]; !known {
			return
		}
		for _, prior := range matched {
			if prior == key {
				return
			}
		}
		matched = append(matched, key)
	}
	aliases := make([]string, 0, len(teamAliases))
	for alias := range teamAliases {
		aliases = append(aliases, alias)
	}
	sort.Slice(aliases, func(i, j int) bool {
		if len(aliases[i]) != len(aliases[j]) {
			return len(aliases[i]) > len(aliases[j])
		}
		return aliases[i] < aliases[j]
	})
	for _, alias := range aliases {
		if strings.Contains(padded, " "+alias+" ") {
			add(teamAliases[alias])
		}
	}

	keys := append([]string(nil), server.Database.teamKeys...)
	sort.Slice(keys, func(i, j int) bool {
		if len(keys[i]) != len(keys[j]) {
			return len(keys[i]) > len(keys[j])
		}
		return keys[i] < keys[j]
	})
	for _, key := range keys {
		if strings.Contains(padded, " "+key+" ") {
			add(key)
		}
	}
	return matched
}

func questionYear(query string) int {
	years := questionYears(query)
	if len(years) == 0 {
		return 0
	}
	return years[0]
}

func questionYears(query string) []int {
	values := yearInQuestion.FindAllString(query, -1)
	years := make([]int, 0, len(values))
	seen := make(map[int]struct{}, len(values))
	for _, value := range values {
		year, _ := strconv.Atoi(value)
		if _, exists := seen[year]; !exists {
			seen[year] = struct{}{}
			years = append(years, year)
		}
	}
	return years
}

func formatSeasonComparison(competition string, comparisons []StatisticsResult) string {
	if len(comparisons) == 0 {
		return "No seasons were available to compare."
	}
	parts := make([]string, 0, len(comparisons))
	for _, comparison := range comparisons {
		parts = append(parts, fmt.Sprintf("%d: %v", comparison.Season, comparison.Value))
	}
	return fmt.Sprintf("%s season comparison — %s.", competition, strings.Join(parts, "; "))
}

func formatRelegationCandidates(competition string, season int, bottom []Standing) string {
	if len(bottom) == 0 {
		return fmt.Sprintf("No completed %s table was available for %d.", competition, season)
	}
	parts := make([]string, 0, len(bottom))
	for _, standing := range bottom {
		parts = append(parts, fmt.Sprintf("%s (%d pts)", standing.Team, standing.Points))
	}
	return fmt.Sprintf("Calculated bottom four for %s %d: %s. The source has no official relegation metadata.", competition, season, strings.Join(parts, ", "))
}

func max(left, right int) int {
	if left > right {
		return left
	}
	return right
}

func questionCompetition(query string) string {
	if strings.Contains(query, "libertadores") {
		return "libertadores"
	}
	if strings.Contains(query, "copa do brasil") || strings.Contains(query, "brazilian cup") {
		return "copa do brasil"
	}
	if strings.Contains(query, "brasileirao") || strings.Contains(query, "serie a") || strings.Contains(query, "campeonato brasileiro") {
		return "brasileirao"
	}
	return ""
}

func isPlayerQuestion(query string) bool {
	return strings.Contains(query, "player") || strings.Contains(query, "players") || strings.Contains(query, "who is ") || strings.Contains(query, "highest rated") || strings.Contains(query, "rating") || strings.Contains(query, "forward")
}

func playerFilterFromQuestion(original, query string) PlayerFilter {
	filter := PlayerFilter{Limit: 20}
	if strings.Contains(query, "brazilian") || strings.Contains(query, "brazil players") {
		filter.Nationality = "Brazil"
	}
	for _, marker := range []string{" at ", " for ", " from "} {
		if index := strings.LastIndex(query, marker); index >= 0 {
			candidate := strings.TrimSpace(query[index+len(marker):])
			if candidate != "" {
				filter.Club = candidate
			}
		}
	}
	if strings.Contains(query, "forward") {
		filter.Position = "ST"
	}
	if strings.HasPrefix(query, "who is ") {
		filter.Name = strings.TrimSpace(original[len("Who is "):])
	}
	return filter
}
