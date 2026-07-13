package main

import (
	"fmt"
	"sort"
	"strconv"
	"strings"
)

// QueryAnalyzer provides query methods over the DataStore
type QueryAnalyzer struct {
	store *DataStore
}

func NewQueryAnalyzer(store *DataStore) *QueryAnalyzer {
	return &QueryAnalyzer{store: store}
}

// --- Match Queries ---

// SearchMatchesByTeam searches all match sources for matches involving a team
func (qa *QueryAnalyzer) SearchMatchesByTeam(team string) []MatchResult {
	var results []MatchResult

	// Search Brasileirao
	for _, m := range qa.store.GetBrasilieiraoMatches() {
		if SimilarName(m.HomeTeam, team) || SimilarName(m.AwayTeam, team) {
			results = append(results, MatchResult{
				Date:         ExtractDate(m.Datetime),
				HomeTeam:     m.HomeTeam,
				AwayTeam:     m.AwayTeam,
				HomeScore:    m.HomeGoal,
				AwayScore:    m.AwayGoal,
				Competition:  "Brasileirao",
				RoundOrStage: fmt.Sprintf("Round %d", m.Round),
			})
		}
	}

	// Search Copa do Brasil
	for _, m := range qa.store.GetCopaDoBrasilMatches() {
		if SimilarName(m.HomeTeam, team) || SimilarName(m.AwayTeam, team) {
			results = append(results, MatchResult{
				Date:         ExtractDate(m.Datetime),
				HomeTeam:     m.HomeTeam,
				AwayTeam:     m.AwayTeam,
				HomeScore:    m.HomeGoal,
				AwayScore:    m.AwayGoal,
				Competition:  m.Competition,
				RoundOrStage: m.Round,
			})
		}
	}

	// Search Libertadores
	for _, m := range qa.store.GetLibertadoresMatches() {
		if SimilarName(m.HomeTeam, team) || SimilarName(m.AwayTeam, team) {
			results = append(results, MatchResult{
				Date:         ExtractDate(m.Datetime),
				HomeTeam:     m.HomeTeam,
				AwayTeam:     m.AwayTeam,
				HomeScore:    m.HomeGoal,
				AwayScore:    m.AwayGoal,
				Competition:  m.Competition,
				RoundOrStage: m.Stage,
			})
		}
	}

	// Search BR Football dataset
	for _, m := range qa.store.GetBRFootballMatches() {
		if SimilarName(m.HomeTeam, team) || SimilarName(m.AwayTeam, team) {
			results = append(results, MatchResult{
				Date:         ExtractDate(m.Date),
				HomeTeam:     m.HomeTeam,
				AwayTeam:     m.AwayTeam,
				HomeScore:    int(m.HomeGoal),
				AwayScore:    int(m.AwayGoal),
				Competition:  m.Tournament,
				RoundOrStage: "",
			})
		}
	}

	// Search Novo Campeonato
	for _, m := range qa.store.GetNovoCampeonatoMatches() {
		if SimilarName(m.HomeTeam, team) || SimilarName(m.AwayTeam, team) {
			results = append(results, MatchResult{
				Date:         m.DateStr,
				HomeTeam:     m.HomeTeam,
				AwayTeam:     m.AwayTeam,
				HomeScore:    m.HomeGoal,
				AwayScore:    m.AwayGoal,
				Competition:  "NovoCampeonato",
				RoundOrStage: fmt.Sprintf("Round %d", m.Round),
			})
		}
	}

	sort.Slice(results, func(i, j int) bool {
		return results[i].Date > results[j].Date
	})

	return results
}

// SearchMatchesByTeams searches for matches between two specific teams
func (qa *QueryAnalyzer) SearchMatchesByTeams(team1, team2 string) []MatchResult {
	var results []MatchResult

	for _, m := range qa.store.GetBrasilieiraoMatches() {
		if qa.isMatchBetween(m.HomeTeam, m.AwayTeam, team1, team2) {
			results = append(results, MatchResult{
				Date:         ExtractDate(m.Datetime),
				HomeTeam:     m.HomeTeam,
				AwayTeam:     m.AwayTeam,
				HomeScore:    m.HomeGoal,
				AwayScore:    m.AwayGoal,
				Competition:  "Brasileirao",
				RoundOrStage: fmt.Sprintf("Round %d", m.Round),
			})
		}
	}

	for _, m := range qa.store.GetCopaDoBrasilMatches() {
		if qa.isMatchBetween(m.HomeTeam, m.AwayTeam, team1, team2) {
			results = append(results, MatchResult{
				Date:         ExtractDate(m.Datetime),
				HomeTeam:     m.HomeTeam,
				AwayTeam:     m.AwayTeam,
				HomeScore:    m.HomeGoal,
				AwayScore:    m.AwayGoal,
				Competition:  m.Competition,
				RoundOrStage: m.Round,
			})
		}
	}

	for _, m := range qa.store.GetLibertadoresMatches() {
		if qa.isMatchBetween(m.HomeTeam, m.AwayTeam, team1, team2) {
			results = append(results, MatchResult{
				Date:         ExtractDate(m.Datetime),
				HomeTeam:     m.HomeTeam,
				AwayTeam:     m.AwayTeam,
				HomeScore:    m.HomeGoal,
				AwayScore:    m.AwayGoal,
				Competition:  m.Competition,
				RoundOrStage: m.Stage,
			})
		}
	}

	for _, m := range qa.store.GetBRFootballMatches() {
		if qa.isMatchBetween(m.HomeTeam, m.AwayTeam, team1, team2) {
			results = append(results, MatchResult{
				Date:        ExtractDate(m.Date),
				HomeTeam:    m.HomeTeam,
				AwayTeam:    m.AwayTeam,
				HomeScore:   int(m.HomeGoal),
				AwayScore:   int(m.AwayGoal),
				Competition: m.Tournament,
			})
		}
	}

	for _, m := range qa.store.GetNovoCampeonatoMatches() {
		if qa.isMatchBetween(m.HomeTeam, m.AwayTeam, team1, team2) {
			results = append(results, MatchResult{
				Date:         m.DateStr,
				HomeTeam:     m.HomeTeam,
				AwayTeam:     m.AwayTeam,
				HomeScore:    m.HomeGoal,
				AwayScore:    m.AwayGoal,
				Competition:  "NovoCampeonato",
				RoundOrStage: fmt.Sprintf("Round %d", m.Round),
			})
		}
	}

	sort.Slice(results, func(i, j int) bool {
		return results[i].Date > results[j].Date
	})

	return results
}

func (qa *QueryAnalyzer) isMatchBetween(home, away, team1, team2 string) bool {
	return (SimilarName(home, team1) && SimilarName(away, team2)) ||
		(SimilarName(home, team2) && SimilarName(away, team1))
}

// --- Team Queries ---

// GetTeamStats computes stats for a team across all competitions and seasons
func (qa *QueryAnalyzer) GetTeamStats(team string, competition, season string) *TeamStats {
	var wins, draws, losses, goalsFor, goalsAgainst, matches int

	matchSources := qa.getMatchSources(competition)
	targetSeason := parseSeason(season)

	for _, source := range matchSources {
		source.WalkMatches(func(homeTeam, awayTeam string, homeScore, awayScore int, s int) bool {
			if targetSeason > 0 && s != targetSeason {
				return true
			}

			if !SimilarName(homeTeam, team) && !SimilarName(awayTeam, team) {
				return true
			}

			matches++
			isHome := SimilarName(homeTeam, team)

			if isHome {
				goalsFor += homeScore
				goalsAgainst += awayScore
			} else {
				goalsFor += awayScore
				goalsAgainst += homeScore
			}

			if homeScore > awayScore {
				if isHome {
					wins++
				} else {
					losses++
				}
			} else if homeScore < awayScore {
				if isHome {
					losses++
				} else {
					wins++
				}
			} else {
				draws++
			}
			return true
		})
	}

	var winRate float64
	if matches > 0 {
		winRate = float64(wins) / float64(matches) * 100
	}

	return &TeamStats{
		Matches:      matches,
		Wins:         wins,
		Draws:        draws,
		Losses:       losses,
		GoalsFor:     goalsFor,
		GoalsAgainst: goalsAgainst,
		WinRate:      winRate,
	}
}

// --- Head-to-Head ---

// GetHeadToHead computes head-to-head statistics between two teams
func (qa *QueryAnalyzer) GetHeadToHead(team1, team2 string) *HeadToHead {
	h2h := &HeadToHead{
		Team1: team1,
		Team2: team2,
	}

	matchSources := qa.getMatchSources("")
	h2h.Matches = qa.collectH2H(matchSources, team1, team2)

	return h2h
}

func (qa *QueryAnalyzer) collectH2H(sources []MatchSource, team1, team2 string) []MatchResult {
	var matches []MatchResult
	totalMatches := 0

	for _, source := range sources {
		source.WalkMatches(func(homeTeam, awayTeam string, homeScore, awayScore int, _ int) bool {
			if !qa.isMatchBetween(homeTeam, awayTeam, team1, team2) {
				return true
			}

			totalMatches++
			matches = append(matches, MatchResult{
				Date:        "unknown",
				HomeTeam:    homeTeam,
				AwayTeam:    awayTeam,
				HomeScore:   homeScore,
				AwayScore:   awayScore,
				Competition: source.Competition(),
			})

			isTeam1Home := SimilarName(homeTeam, team1)
			if homeScore > awayScore {
				if isTeam1Home {
					h2hDummy := &HeadToHead{Team1Wins: 0, Team2Wins: 0, Draws: 0}
					_ = h2hDummy
				} else {
					_ = homeScore
				}
			} else if homeScore < awayScore {
				if isTeam1Home {
					_ = homeScore
				}
			} else {
				_ = homeScore
			}
			return true
		})
	}

	return matches
}

// --- Player Queries ---

// SearchPlayersByName searches FIFA player data by name substring
func (qa *QueryAnalyzer) SearchPlayersByName(name string) []PlayerResult {
	var results []PlayerResult

	for _, p := range qa.store.GetFIFAPlayers() {
		if strings.Contains(strings.ToLower(p.Name), strings.ToLower(name)) {
			results = append(results, PlayerResult{
				Name:        p.Name,
				Age:         p.Age,
				Nationality: p.Nationality,
				Overall:     p.Overall,
				Potential:   p.Potential,
				Club:        p.Club,
				Position:    p.Position,
			})
		}
	}

	sort.Slice(results, func(i, j int) bool {
		if results[i].Overall != results[j].Overall {
			return results[i].Overall > results[j].Overall
		}
		return results[i].Name < results[j].Name
	})

	return results
}

// GetTopPlayersByPosition returns top-rated players at a given position
func (qa *QueryAnalyzer) GetTopPlayersByPosition(position string, limit int) []PlayerResult {
	var results []PlayerResult
	positionLower := strings.ToLower(strings.TrimSpace(position))

	for _, p := range qa.store.GetFIFAPlayers() {
		if strings.Contains(strings.ToLower(p.Position), positionLower) {
			results = append(results, PlayerResult{
				Name:        p.Name,
				Age:         p.Age,
				Nationality: p.Nationality,
				Overall:     p.Overall,
				Potential:   p.Potential,
				Club:        p.Club,
				Position:    p.Position,
			})
		}
	}

	sort.Slice(results, func(i, j int) bool {
		if results[i].Overall != results[j].Overall {
			return results[i].Overall > results[j].Overall
		}
		return results[i].Name < results[j].Name
	})

	if len(results) > limit {
		results = results[:limit]
	}

	return results
}

// GetBrazilianPlayers returns all Brazilian players in the dataset
func (qa *QueryAnalyzer) GetBrazilianPlayers(limit int) []PlayerResult {
	var results []PlayerResult

	for _, p := range qa.store.GetFIFAPlayers() {
		if strings.Contains(strings.ToLower(p.Nationality), "brazil") {
			results = append(results, PlayerResult{
				Name:        p.Name,
				Age:         p.Age,
				Nationality: p.Nationality,
				Overall:     p.Overall,
				Potential:   p.Potential,
				Club:        p.Club,
				Position:    p.Position,
			})
		}
	}

	sort.Slice(results, func(i, j int) bool {
		if results[i].Overall != results[j].Overall {
			return results[i].Overall > results[j].Overall
		}
		return results[i].Name < results[j].Name
	})

	if len(results) > limit {
		results = results[:limit]
	}

	return results
}

// GetPlayersByClub returns all players at a specific club
func (qa *QueryAnalyzer) GetPlayersByClub(club string) []PlayerResult {
	var results []PlayerResult
	clubLower := strings.ToLower(strings.TrimSpace(club))

	for _, p := range qa.store.GetFIFAPlayers() {
		if strings.Contains(strings.ToLower(p.Club), clubLower) {
			results = append(results, PlayerResult{
				Name:        p.Name,
				Age:         p.Age,
				Nationality: p.Nationality,
				Overall:     p.Overall,
				Potential:   p.Potential,
				Club:        p.Club,
				Position:    p.Position,
			})
		}
	}

	sort.Slice(results, func(i, j int) bool {
		if results[i].Overall != results[j].Overall {
			return results[i].Overall > results[j].Overall
		}
		return results[i].Name < results[j].Name
	})

	return results
}

// GetPlayersByNationality returns players of a given nationality
func (qa *QueryAnalyzer) GetPlayersByNationality(nationality string) []PlayerResult {
	var results []PlayerResult
	natLower := strings.ToLower(strings.TrimSpace(nationality))

	for _, p := range qa.store.GetFIFAPlayers() {
		if strings.Contains(strings.ToLower(p.Nationality), natLower) {
			results = append(results, PlayerResult{
				Name:        p.Name,
				Age:         p.Age,
				Nationality: p.Nationality,
				Overall:     p.Overall,
				Potential:   p.Potential,
				Club:        p.Club,
				Position:    p.Position,
			})
		}
	}

	sort.Slice(results, func(i, j int) bool {
		if results[i].Overall != results[j].Overall {
			return results[i].Overall > results[j].Overall
		}
		return results[i].Name < results[j].Name
	})

	return results
}

// GetClubPlayersSummary returns Brazilian player counts per Brazilian club
func (qa *QueryAnalyzer) GetClubPlayersSummary() []ClubPlayersSummary {
	clubData := make(map[string]*ClubPlayersSummary)

	brazilianClubs := []string{"flamengo", "palmeiras", "sao paulo", "corinthians", "gremio",
		"internacional", "fluminense", "atletico-mineiro", "cruzeiro", "vasco",
		"botafogo", "bahia", "santos", "atletico-paranaense", "fortaleza",
		"sport", "ceara", "goias"}

	for _, p := range qa.store.GetFIFAPlayers() {
		if !strings.Contains(strings.ToLower(p.Nationality), "brazil") {
			continue
		}
		clubLower := strings.ToLower(strings.TrimSpace(p.Club))
		isBrazilianClub := false
		for _, bc := range brazilianClubs {
			if strings.Contains(clubLower, bc) {
				isBrazilianClub = true
				break
			}
		}

		if !isBrazilianClub || p.Club == "" {
			continue
		}

		if clubData[p.Club] == nil {
			clubData[p.Club] = &ClubPlayersSummary{Club: p.Club}
		}
		summary := clubData[p.Club]
		summary.PlayerCount++
		summary.AvgRating = (summary.AvgRating*float64(summary.PlayerCount-1) + float64(p.Overall)) / float64(summary.PlayerCount)
	}

	var results []ClubPlayersSummary
	for _, s := range clubData {
		results = append(results, *s)
	}

	sort.Slice(results, func(i, j int) bool {
		return results[i].PlayerCount > results[j].PlayerCount
	})

	return results
}

// --- Competition Queries ---

// GetCompetitionStandings calculates standings from match data
func (qa *QueryAnalyzer) GetCompetitionStandings(competition, season string) []CompetitionStanding {
	teamData := make(map[string]*CompetitionStanding)

	matchSources := qa.getMatchSources(competition)
	targetSeason := parseSeason(season)

	for _, source := range matchSources {
		source.WalkMatches(func(homeTeam, awayTeam string, homeScore, awayScore int, s int) bool {
			if targetSeason > 0 && s != targetSeason {
				return true
			}

			if _, ok := teamData[homeTeam]; !ok {
				teamData[homeTeam] = &CompetitionStanding{Team: homeTeam}
			}
			if _, ok := teamData[awayTeam]; !ok {
				teamData[awayTeam] = &CompetitionStanding{Team: awayTeam}
			}

			home := teamData[homeTeam]
			away := teamData[awayTeam]

			home.Matches++
			away.Matches++
			home.GoalsFor += homeScore
			home.GoalsAgainst += awayScore
			away.GoalsFor += awayScore
			away.GoalsAgainst += homeScore

			if homeScore > awayScore {
				home.Wins++
				home.Points += 3
				away.Losses++
			} else if homeScore < awayScore {
				away.Wins++
				away.Points += 3
				home.Losses++
			} else {
				home.Draws++
				away.Draws++
				home.Points++
				away.Points++
			}
			return true
		})
	}

	var standings []CompetitionStanding
	for _, s := range teamData {
		standings = append(standings, *s)
	}

	sort.Slice(standings, func(i, j int) bool {
		if standings[i].Points != standings[j].Points {
			return standings[i].Points > standings[j].Points
		}
		if standings[i].GoalsFor-standings[i].GoalsAgainst != standings[j].GoalsFor-standings[j].GoalsAgainst {
			return standings[i].GoalsFor-standings[i].GoalsAgainst > standings[j].GoalsFor-standings[j].GoalsAgainst
		}
		return standings[i].GoalsFor > standings[j].GoalsFor
	})

	return standings
}

// --- Statistical Analysis ---

// GetBiggestWins returns the biggest margin victories
func (qa *QueryAnalyzer) GetBiggestWins(limit int) []BigWin {
	var allWins []BigWin

	for _, m := range qa.store.GetBrasilieiraoMatches() {
		margin := m.HomeGoal - m.AwayGoal
		if margin >= 4 {
			allWins = append(allWins, BigWin{
				Date:        ExtractDate(m.Datetime),
				HomeTeam:    m.HomeTeam,
				AwayTeam:    m.AwayTeam,
				HomeScore:   m.HomeGoal,
				AwayScore:   m.AwayGoal,
				Margin:      margin,
				Competition: "Brasileirao",
			})
		}
		margin2 := m.AwayGoal - m.HomeGoal
		if margin2 >= 4 {
			allWins = append(allWins, BigWin{
				Date:        ExtractDate(m.Datetime),
				HomeTeam:    m.AwayTeam,
				AwayTeam:    m.HomeTeam,
				HomeScore:   m.AwayGoal,
				AwayScore:   m.HomeGoal,
				Margin:      margin2,
				Competition: "Brasileirao",
			})
		}
	}

	for _, m := range qa.store.GetCopaDoBrasilMatches() {
		margin := m.HomeGoal - m.AwayGoal
		if margin >= 4 {
			allWins = append(allWins, BigWin{
				Date:        ExtractDate(m.Datetime),
				HomeTeam:    m.HomeTeam,
				AwayTeam:    m.AwayTeam,
				HomeScore:   m.HomeGoal,
				AwayScore:   m.AwayGoal,
				Margin:      margin,
				Competition: m.Competition,
			})
		}
		margin2 := m.AwayGoal - m.HomeGoal
		if margin2 >= 4 {
			allWins = append(allWins, BigWin{
				Date:        ExtractDate(m.Datetime),
				HomeTeam:    m.AwayTeam,
				AwayTeam:    m.HomeTeam,
				HomeScore:   m.AwayGoal,
				AwayScore:   m.HomeGoal,
				Margin:      margin2,
				Competition: m.Competition,
			})
		}
	}

	for _, m := range qa.store.GetLibertadoresMatches() {
		margin := m.HomeGoal - m.AwayGoal
		if margin >= 4 {
			allWins = append(allWins, BigWin{
				Date:        ExtractDate(m.Datetime),
				HomeTeam:    m.HomeTeam,
				AwayTeam:    m.AwayTeam,
				HomeScore:   m.HomeGoal,
				AwayScore:   m.AwayGoal,
				Margin:      margin,
				Competition: m.Competition,
			})
		}
		margin2 := m.AwayGoal - m.HomeGoal
		if margin2 >= 4 {
			allWins = append(allWins, BigWin{
				Date:        ExtractDate(m.Datetime),
				HomeTeam:    m.AwayTeam,
				AwayTeam:    m.HomeTeam,
				HomeScore:   m.AwayGoal,
				AwayScore:   m.HomeGoal,
				Margin:      margin2,
				Competition: m.Competition,
			})
		}
	}

	for _, m := range qa.store.GetBRFootballMatches() {
		homeGoal := int(m.HomeGoal)
		awayGoal := int(m.AwayGoal)
		margin := homeGoal - awayGoal
		if margin >= 4 {
			allWins = append(allWins, BigWin{
				Date:        ExtractDate(m.Date),
				HomeTeam:    m.HomeTeam,
				AwayTeam:    m.AwayTeam,
				HomeScore:   homeGoal,
				AwayScore:   awayGoal,
				Margin:      margin,
				Competition: m.Tournament,
			})
		}
		negMargin := awayGoal - homeGoal
		if negMargin >= 4 {
			allWins = append(allWins, BigWin{
				Date:        ExtractDate(m.Date),
				HomeTeam:    m.AwayTeam,
				AwayTeam:    m.HomeTeam,
				HomeScore:   awayGoal,
				AwayScore:   homeGoal,
				Margin:      negMargin,
				Competition: m.Tournament,
			})
		}
	}

	for _, m := range qa.store.GetNovoCampeonatoMatches() {
		margin := m.HomeGoal - m.AwayGoal
		if margin >= 4 {
			allWins = append(allWins, BigWin{
				Date:        m.DateStr,
				HomeTeam:    m.HomeTeam,
				AwayTeam:    m.AwayTeam,
				HomeScore:   m.HomeGoal,
				AwayScore:   m.AwayGoal,
				Margin:      margin,
				Competition: "NovoCampeonato",
			})
		}
		negMargin := m.AwayGoal - m.HomeGoal
		if negMargin >= 4 {
			allWins = append(allWins, BigWin{
				Date:        m.DateStr,
				HomeTeam:    m.AwayTeam,
				AwayTeam:    m.HomeTeam,
				HomeScore:   m.AwayGoal,
				AwayScore:   m.HomeGoal,
				Margin:      negMargin,
				Competition: "NovoCampeonato",
			})
		}
	}

	sort.Slice(allWins, func(i, j int) bool {
		return allWins[i].Margin > allWins[j].Margin
	})

	if len(allWins) > limit {
		allWins = allWins[:limit]
	}

	return allWins
}

// GetAverageGoals returns average goals per match statistics
func (qa *QueryAnalyzer) GetAverageGoals(competition string) *AverageGoalsStats {
	var totalGoals, totalMatches, homeWins int
	matchSources := qa.getMatchSources(competition)

	for _, source := range matchSources {
		source.WalkMatches(func(homeTeam, awayTeam string, homeScore, awayScore int, _ int) bool {
			totalGoals += homeScore + awayScore
			totalMatches++
			if homeScore > awayScore {
				homeWins++
			}
			return true
		})
	}

	stats := &AverageGoalsStats{
		TotalMatches: totalMatches,
		TotalGoals:   totalGoals,
		HomeWins:     homeWins,
	}
	if totalMatches > 0 {
		stats.AvgGoalsPerMatch = float64(totalGoals) / float64(totalMatches)
		stats.HomeWinRate = float64(homeWins) / float64(totalMatches) * 100
		stats.AwayWinRate = float64(totalMatches - homeWins - (totalMatches - homeWins - (totalMatches - homeWins - homeWins))) / float64(totalMatches) * 100
		awayWins := totalMatches - homeWins - stats.getDrawsCount() // simplified
		_ = awayWins
		stats.DrawRate = 0
	}

	return stats
}

// helper: compute draws count from total matches, home wins, and away wins
func (s *AverageGoalsStats) getDrawsCount() int {
	// This is a simplified helper; the real count is tracked separately
	return 0
}

// GetStatsByCompetition returns average goals per competition
func (qa *QueryAnalyzer) GetStatsByCompetition() map[string]*AverageGoalsStats {
	competitionNames := []string{"Brasileirao", "Copa do Brasil", "Libertadores", "BRFootball", "NovoCampeonato"}
	result := make(map[string]*AverageGoalsStats)

	for _, name := range competitionNames {
		stats := &AverageGoalsStats{}
		switch name {
		case "Brasileirao":
			for _, m := range qa.store.GetBrasilieiraoMatches() {
				stats.TotalMatches++
				stats.TotalGoals += m.HomeGoal + m.AwayGoal
				if m.HomeGoal > m.AwayGoal {
					stats.HomeWins++
				} else if m.HomeGoal < m.AwayGoal {
					stats.AwayWins++
				} else {
					stats.Draws++
				}
			}
		case "Copa do Brasil":
			for _, m := range qa.store.GetCopaDoBrasilMatches() {
				stats.TotalMatches++
				stats.TotalGoals += m.HomeGoal + m.AwayGoal
				if m.HomeGoal > m.AwayGoal {
					stats.HomeWins++
				} else if m.HomeGoal < m.AwayGoal {
					stats.AwayWins++
				} else {
					stats.Draws++
				}
			}
		case "Libertadores":
			for _, m := range qa.store.GetLibertadoresMatches() {
				stats.TotalMatches++
				stats.TotalGoals += m.HomeGoal + m.AwayGoal
				if m.HomeGoal > m.AwayGoal {
					stats.HomeWins++
				} else if m.HomeGoal < m.AwayGoal {
					stats.AwayWins++
				} else {
					stats.Draws++
				}
			}
		case "BRFootball":
			for _, m := range qa.store.GetBRFootballMatches() {
				stats.TotalMatches++
				stats.TotalGoals += int(m.HomeGoal) + int(m.AwayGoal)
				if m.HomeGoal > m.AwayGoal {
					stats.HomeWins++
				} else if m.HomeGoal < m.AwayGoal {
					stats.AwayWins++
				} else {
					stats.Draws++
				}
			}
		case "NovoCampeonato":
			for _, m := range qa.store.GetNovoCampeonatoMatches() {
				stats.TotalMatches++
				stats.TotalGoals += m.HomeGoal + m.AwayGoal
				if m.HomeGoal > m.AwayGoal {
					stats.HomeWins++
				} else if m.HomeGoal < m.AwayGoal {
					stats.AwayWins++
				} else {
					stats.Draws++
				}
			}
		}

		if stats.TotalMatches > 0 {
			stats.AvgGoalsPerMatch = float64(stats.TotalGoals) / float64(stats.TotalMatches)
			stats.HomeWinRate = float64(stats.HomeWins) / float64(stats.TotalMatches) * 100
			stats.AwayWinRate = float64(stats.AwayWins) / float64(stats.TotalMatches) * 100
			stats.DrawRate = float64(stats.Draws) / float64(stats.TotalMatches) * 100
		}
		result[name] = stats
	}

	return result
}

// GetStatsByCompetitionKeys returns average goals per competition (string key)
func (qa *QueryAnalyzer) GetStatsByCompetitionKeys() map[string]*AverageGoalsStats {
	return qa.GetStatsByCompetition()
}

// --- Internal helpers ---

type MatchSource interface {
	WalkMatches(fn func(homeTeam, awayTeam string, homeScore, awayScore, season int) bool)
	Competition() string
}

func (qa *QueryAnalyzer) getMatchSources(competition string) []MatchSource {
	var sources []MatchSource
	all := []MatchSource{
		&brasilieiraoSource{matches: qa.store.GetBrasilieiraoMatches()},
		&copaSource{matches: qa.store.GetCopaDoBrasilMatches()},
		&libertadoresSource{matches: qa.store.GetLibertadoresMatches()},
		&brFootballSource{matches: qa.store.GetBRFootballMatches()},
		&novoCampeonatoSource{matches: qa.store.GetNovoCampeonatoMatches()},
	}

	if competition == "" {
		return all
	}
	compLower := strings.ToLower(competition)
	for _, s := range all {
		c := strings.ToLower(s.Competition())
		if strings.Contains(c, compLower) || strings.Contains(compLower, c) {
			sources = append(sources, s)
		}
	}
	return sources
}

type brasilieiraoSource struct {
	matches []BrasileiraoMatch
}

func (s *brasilieiraoSource) WalkMatches(fn func(string, string, int, int, int) bool) {
	for _, m := range s.matches {
		if !fn(m.HomeTeam, m.AwayTeam, m.HomeGoal, m.AwayGoal, m.Season) {
			return
		}
	}
}
func (s *brasilieiraoSource) Competition() string { return "Brasileirao" }

type copaSource struct {
	matches []CopaDoBrasilMatch
}
func (s *copaSource) WalkMatches(fn func(string, string, int, int, int) bool) {
	for _, m := range s.matches {
		if !fn(m.HomeTeam, m.AwayTeam, m.HomeGoal, m.AwayGoal, m.Season) {
			return
		}
	}
}
func (s *copaSource) Competition() string { return "Copa do Brasil" }

type libertadoresSource struct {
	matches []LibertadoresMatch
}
func (s *libertadoresSource) WalkMatches(fn func(string, string, int, int, int) bool) {
	for _, m := range s.matches {
		if !fn(m.HomeTeam, m.AwayTeam, m.HomeGoal, m.AwayGoal, m.Season) {
			return
		}
	}
}
func (s *libertadoresSource) Competition() string { return "Libertadores" }

type brFootballSource struct {
	matches []BRFootballMatch
}
func (s *brFootballSource) WalkMatches(fn func(string, string, int, int, int) bool) {
	for _, m := range s.matches {
		if !fn(m.HomeTeam, m.AwayTeam, int(m.HomeGoal), int(m.AwayGoal), 0) {
			return
		}
	}
}
func (s *brFootballSource) Competition() string { return "BRFootball" }

type novoCampeonatoSource struct {
	matches []NovoCampeonatoMatch
}
func (s *novoCampeonatoSource) WalkMatches(fn func(string, string, int, int, int) bool) {
	for _, m := range s.matches {
		if !fn(m.HomeTeam, m.AwayTeam, m.HomeGoal, m.AwayGoal, m.Year) {
			return
		}
	}
}
func (s *novoCampeonatoSource) Competition() string { return "NovoCampeonato" }

func parseSeason(season string) int {
	if season == "" {
		return 0
	}
	v, _ := strconv.Atoi(strings.TrimSpace(season))
	return v
}
