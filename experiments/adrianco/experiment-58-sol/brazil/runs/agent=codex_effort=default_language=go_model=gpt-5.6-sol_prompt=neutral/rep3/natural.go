package main

import (
	"fmt"
	"regexp"
	"sort"
	"strconv"
	"strings"
)

var yearPattern = regexp.MustCompile(`\b(19\d{2}|20\d{2})\b`)

var rivalPairs = [][2]string{
	{"Flamengo", "Fluminense"}, {"Flamengo", "Vasco"}, {"Flamengo", "Botafogo"},
	{"Corinthians", "Palmeiras"}, {"Corinthians", "São Paulo"}, {"Palmeiras", "São Paulo"},
	{"Grêmio", "Internacional"}, {"Atlético-MG", "Cruzeiro"}, {"Bahia", "Vitória"},
	{"Athletico-PR", "Coritiba"}, {"Santos", "São Paulo"}, {"Sport", "Náutico"},
}

func (db *Database) Answer(question string) string {
	q := fold(question)
	season := extractYear(q)
	competition := competitionFromQuestion(q)
	teams := db.mentionedTeams(question)

	switch {
	case strings.Contains(q, "top scorer"):
		return "The provided match files contain team scores but no goal-scorer events, so individual top scorers cannot be inferred reliably from these datasets."
	case strings.Contains(q, "bracket"):
		matches := db.SearchMatches(MatchFilter{Competition: competition, Season: season, Limit: 200})
		var knockout []Match
		for _, m := range matches {
			stage := fold(m.Stage)
			if stage != "group stage" {
				knockout = append(knockout, m)
			}
		}
		return formatMatches(fmt.Sprintf("%d %s knockout bracket results", season, displayCompetition(competition)), knockout, 100)
	case strings.Contains(q, "derb") || strings.Contains(q, "classico"):
		return db.answerDerbies(season)
	case strings.Contains(q, "biggest win") || strings.Contains(q, "biggest victor") || strings.Contains(q, "maiores goleadas"):
		return formatMatches("Biggest victories", db.BiggestWins(MatchFilter{Competition: competition, Season: season}, 10), 10)
	case strings.Contains(q, "average goal") || strings.Contains(q, "goals per match") || strings.Contains(q, "media de gols"):
		return formatCompetitionStats(db.AggregateStats(MatchFilter{Competition: competition, Season: season}))
	case strings.Contains(q, "relegat"):
		table := db.Standings(defaultCompetition(competition), season)
		if len(table) == 0 {
			return noResults(question)
		}
		start := len(table) - 4
		if start < 0 {
			start = 0
		}
		return formatStandings(fmt.Sprintf("Relegation places for %d", season), table[start:], len(table[start:]))
	case strings.Contains(q, "who won") || strings.Contains(q, "champion") || strings.Contains(q, "campeao"):
		table := db.Standings(defaultCompetition(competition), season)
		if len(table) == 0 {
			return noResults(question)
		}
		return fmt.Sprintf("%s won the calculated %d %s table with %d points (%dW, %dD, %dL).", table[0].Team, season, displayCompetition(defaultCompetition(competition)), table[0].Points, table[0].Wins, table[0].Draws, table[0].Losses)
	case strings.Contains(q, "standing") || strings.Contains(q, "table") || strings.Contains(q, "classificacao"):
		return formatStandings(fmt.Sprintf("%d %s standings", season, displayCompetition(defaultCompetition(competition))), db.Standings(defaultCompetition(competition), season), 20)
	case strings.Contains(q, "compare") && len(yearPattern.FindAllString(q, -1)) >= 2:
		years := yearPattern.FindAllString(q, -1)
		y1, _ := strconv.Atoi(years[0])
		y2, _ := strconv.Atoi(years[1])
		return formatSeasonComparison(db.AggregateStats(MatchFilter{Competition: defaultCompetition(competition), Season: y1}), db.AggregateStats(MatchFilter{Competition: defaultCompetition(competition), Season: y2}))
	case (strings.Contains(q, "head to head") || strings.Contains(q, "compare") || strings.Contains(q, " vs ") || strings.Contains(q, "versus")) && len(teams) >= 2:
		return formatHeadToHead(db.HeadToHead(teams[0], teams[1], MatchFilter{Competition: competition, Season: season, Limit: 100}), 20)
	case strings.Contains(q, "last play") && len(teams) >= 2:
		matches := db.SearchMatches(MatchFilter{Team: teams[0], Opponent: teams[1], Limit: 1})
		return formatMatches("Most recent meeting", matches, 1)
	case strings.Contains(q, "competition") && len(teams) >= 1:
		items := db.CompetitionsForTeam(teams[0])
		if len(items) == 0 {
			return noResults(question)
		}
		return fmt.Sprintf("%s appears in: %s.", cleanTeamName(teams[0]), strings.Join(items, ", "))
	case strings.Contains(q, "most goals") || strings.Contains(q, "best home record") || strings.Contains(q, "best away record"):
		return db.answerTeamRanking(q, competition, season)
	case (strings.Contains(q, "record") || strings.Contains(q, "stat")) && len(teams) >= 1:
		filter := MatchFilter{Competition: competition, Season: season}
		if strings.Contains(q, "home") {
			filter.HomeOnly = true
		}
		if strings.Contains(q, "away") {
			filter.AwayOnly = true
		}
		return formatTeamStats(db.TeamStatistics(teams[0], filter))
	case strings.Contains(q, "highest rated") || strings.Contains(q, "top rated") || strings.Contains(q, "top brazilian"):
		filter := PlayerFilter{Limit: 20}
		if strings.Contains(q, "brazil") {
			filter.Nationality = "Brazil"
		}
		if len(teams) > 0 {
			filter.Club = teams[0]
		}
		return formatPlayers("Top-rated players", db.SearchPlayers(filter), 20)
	case strings.Contains(q, "player") && strings.Contains(q, "brazil"):
		return formatPlayers("Brazilian players", db.SearchPlayers(PlayerFilter{Nationality: "Brazil", Limit: 50}), 50)
	case (strings.Contains(q, "forward") || strings.Contains(q, "midfielder") || strings.Contains(q, "defender") || strings.Contains(q, "goalkeeper")):
		position := "forward"
		for _, p := range []string{"goalkeeper", "midfielder", "defender", "forward"} {
			if strings.Contains(q, p) {
				position = p
				break
			}
		}
		club := ""
		if len(teams) > 0 {
			club = teams[0]
		}
		return formatPlayers(strings.Title(position)+"s", db.SearchPlayers(PlayerFilter{Club: club, Position: position, Limit: 50}), 50)
	case strings.HasPrefix(q, "who is "):
		name := strings.Trim(strings.TrimSpace(question[len("who is "):]), " ?.!")
		return formatPlayers("Player search", db.SearchPlayers(PlayerFilter{Name: name, Limit: 10}), 10)
	case strings.Contains(q, "final"):
		return formatMatches("Final-stage matches", db.SearchMatches(MatchFilter{Competition: competition, Season: season, Stage: "final", Limit: 100}), 30)
	case len(teams) >= 1:
		return formatMatches(fmt.Sprintf("Matches for %s", teams[0]), db.SearchMatches(MatchFilter{Team: teams[0], Competition: competition, Season: season, Limit: 100}), 30)
	default:
		return "I could not map that question to the provided data. Try naming a team, player, competition, or season, or use the specialized MCP tools for exact filters."
	}
}

func extractYear(q string) int { y, _ := strconv.Atoi(yearPattern.FindString(q)); return y }

func competitionFromQuestion(q string) string {
	switch {
	case strings.Contains(q, "libertadores"):
		return "Copa Libertadores"
	case strings.Contains(q, "copa do brasil"), strings.Contains(q, "brazilian cup"):
		return "Copa do Brasil"
	case strings.Contains(q, "brasileir"), strings.Contains(q, "serie a"):
		return "Brasileirão Série A"
	case strings.Contains(q, "serie b"):
		return "Serie B"
	case strings.Contains(q, "serie c"):
		return "Serie C"
	default:
		return ""
	}
}

func defaultCompetition(s string) string {
	if s == "" {
		return "Brasileirão Série A"
	}
	return s
}

func displayCompetition(s string) string {
	switch canonicalCompetition(s) {
	case "serie a":
		return "Brasileirão Série A"
	case "copa do brasil":
		return "Copa do Brasil"
	case "libertadores":
		return "Copa Libertadores"
	default:
		return s
	}
}

func (db *Database) mentionedTeams(question string) []string {
	q := " " + normalizeTeam(question) + " "
	type candidate struct{ name, key string }
	byKey := map[string]string{}
	for _, m := range db.Matches {
		for _, name := range []string{m.HomeTeam, m.AwayTeam} {
			key := normalizeTeam(name)
			if key != "" && strings.Contains(q, " "+key+" ") {
				byKey[key] = displayTeam(name)
			}
		}
	}
	var found []candidate
	for key, name := range byKey {
		found = append(found, candidate{name, key})
	}
	sort.Slice(found, func(i, j int) bool {
		return strings.Index(q, " "+found[i].key+" ") < strings.Index(q, " "+found[j].key+" ")
	})
	result := make([]string, 0, len(found))
	for _, c := range found {
		contained := false
		for _, existing := range result {
			if fuzzyEqual(existing, c.name) {
				contained = true
				break
			}
		}
		if !contained {
			result = append(result, c.name)
		}
	}
	return result
}

func (db *Database) answerDerbies(season int) string {
	var all []Match
	for _, pair := range rivalPairs {
		all = append(all, db.SearchMatches(MatchFilter{Team: pair[0], Opponent: pair[1], Season: season, Limit: 100})...)
	}
	sort.SliceStable(all, func(i, j int) bool { return all[i].Date.After(all[j].Date) })
	return formatMatches(fmt.Sprintf("Traditional derbies in %d", season), all, 50)
}

func (db *Database) answerTeamRanking(q, competition string, season int) string {
	table := db.Standings(defaultCompetition(competition), season)
	if len(table) == 0 {
		return noResults(q)
	}
	if strings.Contains(q, "most goals") {
		sort.SliceStable(table, func(i, j int) bool { return table[i].GoalsFor > table[j].GoalsFor })
		return fmt.Sprintf("%s scored the most goals in the calculated dataset view: %d in %d matches.", table[0].Team, table[0].GoalsFor, table[0].Played)
	}
	away := strings.Contains(q, "away")
	type ranked struct {
		name  string
		stats TeamStats
	}
	var ranks []ranked
	for _, row := range table {
		f := MatchFilter{Competition: defaultCompetition(competition), Season: season, HomeOnly: !away, AwayOnly: away}
		s := db.TeamStatistics(row.Team, f)
		if s.Matches > 0 {
			ranks = append(ranks, ranked{row.Team, s})
		}
	}
	sort.SliceStable(ranks, func(i, j int) bool {
		if ranks[i].stats.WinRate != ranks[j].stats.WinRate {
			return ranks[i].stats.WinRate > ranks[j].stats.WinRate
		}
		return ranks[i].stats.Matches > ranks[j].stats.Matches
	})
	if len(ranks) == 0 {
		return noResults(q)
	}
	where := "home"
	if away {
		where = "away"
	}
	return fmt.Sprintf("%s has the best %s win rate: %.1f%% (%d wins in %d matches).", ranks[0].name, where, ranks[0].stats.WinRate, ranks[0].stats.Wins, ranks[0].stats.Matches)
}

func noResults(q string) string {
	return fmt.Sprintf("No matching records were found in the provided datasets for %q.", q)
}
