package main

// Executable specifications for the Brazilian Soccer MCP server.
// Written in the language of the domain; they say nothing about MCP or CSV.

import "testing"

func TestShouldListAllMatchesBetweenTwoRivals(t *testing.T) {
	s := newSoccerDSL(t)
	s.WhenAskingForMatchesBetween("Flamengo", "Fluminense")
	s.ThenAnswerMentions("Flamengo", "Fluminense", "Head-to-head")
}

func TestShouldFindMatchesForATeamInASeason(t *testing.T) {
	s := newSoccerDSL(t)
	s.WhenAskingForMatches("team: Palmeiras", "season: 2023")
	s.ThenAnswerMentions("Palmeiras", "2023-")
}

func TestShouldFindCopaDoBrasilFinals(t *testing.T) {
	s := newSoccerDSL(t)
	s.WhenAskingForMatches("competition: Copa do Brasil", "stage: final", "season: 2019")
	s.ThenAnswerMentions("Found 2 matches", "Athletico", "Internacional")
	s.WhenAskingForMatches("competition: Copa do Brasil", "stage: final", "limit: 100")
	s.ThenAnswerDoesNotMention("(Copa do Brasil)")
}

func TestShouldFindLibertadoresMatches(t *testing.T) {
	s := newSoccerDSL(t)
	s.WhenAskingForMatches("competition: Libertadores", "season: 2018", "stage: final")
	s.ThenAnswerMentions("Libertadores", "2018-")
}

func TestShouldFindMatchesInADateRange(t *testing.T) {
	s := newSoccerDSL(t)
	s.WhenAskingForMatches("team: Corinthians", "from: 2022-01-01", "to: 2022-12-31")
	s.ThenAnswerMentions("2022-")
	s.ThenAnswerDoesNotMention("2021-", "2023-")
}

func TestShouldTreatTeamNameVariationsAsTheSameTeam(t *testing.T) {
	s := newSoccerDSL(t)
	s.WhenAskingForMatches("team: Palmeiras-SP", "season: 2019")
	withSuffix := s.answer
	s.WhenAskingForMatches("team: palmeiras", "season: 2019")
	s.ThenAnswerEquals(withSuffix)
}

func TestShouldHandleAccentedTeamNames(t *testing.T) {
	s := newSoccerDSL(t)
	s.WhenAskingForMatches("team: Grêmio", "season: 2015")
	s.ThenAnswerMentions("Grêmio")
	s.WhenAskingForMatches("team: Gremio", "season: 2015")
	s.ThenAnswerMentions("Grêmio")
}

func TestShouldReportMostRecentMatchBetweenTwoTeams(t *testing.T) {
	s := newSoccerDSL(t)
	s.WhenAskingForLastMatchBetween("Flamengo", "Corinthians")
	s.ThenAnswerMentions("Last match", "Flamengo", "Corinthians")
}

func TestShouldReportHomeRecordForATeamInASeason(t *testing.T) {
	s := newSoccerDSL(t)
	s.WhenAskingForTeamRecord("team: Corinthians", "season: 2022", "venue: home", "competition: Brasileirão")
	s.ThenAnswerMentions("Matches: 19", "Win rate:")
}

func TestShouldCompareTwoTeamsHeadToHead(t *testing.T) {
	s := newSoccerDSL(t)
	s.WhenAskingForMatchesBetween("Palmeiras", "Santos")
	s.ThenAnswerMentions("Palmeiras", "Santos", "wins", "draws")
}

func TestShouldCalculateSeasonStandingsWithChampion(t *testing.T) {
	s := newSoccerDSL(t)
	s.WhenAskingForStandings("season: 2019")
	s.ThenAnswerMentions("1. Flamengo - 90 pts", "Champion")
}

func TestShouldIdentifyRelegatedTeams(t *testing.T) {
	s := newSoccerDSL(t)
	s.WhenAskingForStandings("season: 2020")
	s.ThenAnswerMentions("Relegated")
}

func TestShouldFindTopScoringTeamOfASeason(t *testing.T) {
	s := newSoccerDSL(t)
	s.WhenAskingForStandings("season: 2022", "sort: goals")
	s.ThenAnswerMentions("GF")
}

func TestShouldFindPlayersByName(t *testing.T) {
	s := newSoccerDSL(t)
	s.WhenSearchingForPlayers("name: Neymar")
	s.ThenAnswerMentions("Neymar Jr", "Paris Saint-Germain")
}

func TestShouldListTopBrazilianPlayers(t *testing.T) {
	s := newSoccerDSL(t)
	s.WhenSearchingForPlayers("nationality: Brazil", "limit: 3")
	s.ThenAnswerMentions("1. Neymar Jr - Overall: 92")
}

func TestShouldFindPlayersAtAClub(t *testing.T) {
	s := newSoccerDSL(t)
	s.WhenSearchingForPlayers("club: Juventus", "position: ST")
	s.ThenAnswerMentions("Cristiano Ronaldo")
}

func TestShouldExplainWhenNoPlayersMatch(t *testing.T) {
	s := newSoccerDSL(t)
	s.WhenSearchingForPlayers("club: Flamengo")
	s.ThenAnswerMentions("No players found")
}

func TestShouldSummariseBrazilianPlayersByClub(t *testing.T) {
	s := newSoccerDSL(t)
	s.WhenAskingForBrazilianPlayersByClub()
	s.ThenAnswerMentions("players (avg rating:")
}

func TestShouldReportAverageGoalsPerMatch(t *testing.T) {
	s := newSoccerDSL(t)
	s.WhenAskingForStatistics("competition: Brasileirão")
	s.ThenAnswerMentions("Average goals per match:", "Home win rate:")
}

func TestShouldCompareTwoSeasons(t *testing.T) {
	s := newSoccerDSL(t)
	s.WhenAskingForStatistics("competition: Brasileirão", "season: 2018")
	s.ThenAnswerMentions("2018")
	s.WhenAskingForStatistics("competition: Brasileirão", "season: 2019")
	s.ThenAnswerMentions("2019")
}

func TestShouldShowBiggestWins(t *testing.T) {
	s := newSoccerDSL(t)
	s.WhenAskingForBiggestWins("limit: 5")
	s.ThenAnswerMentions("1. ")
}

func TestShouldRankTeamsByAwayRecord(t *testing.T) {
	s := newSoccerDSL(t)
	s.WhenAskingForBestRecord("venue: away", "competition: Brasileirão")
	s.ThenAnswerMentions("1. ", "win rate")
}

func TestShouldListCompetitionsATeamHasPlayedIn(t *testing.T) {
	s := newSoccerDSL(t)
	s.WhenAskingForCompetitionsOf("Palmeiras")
	s.ThenAnswerMentions("Brasileirão", "Copa do Brasil", "Libertadores")
}

func TestShouldFindDerbiesInASeason(t *testing.T) {
	s := newSoccerDSL(t)
	s.WhenAskingForDerbies("season: 2019")
	s.ThenAnswerMentions("Fla-Flu")
}

func TestShouldCoverEveryProvidedDataset(t *testing.T) {
	s := newSoccerDSL(t)
	s.WhenAskingWhatDataIsAvailable()
	s.ThenAnswerMentions("Brasileirao_Matches.csv", "Brazilian_Cup_Matches.csv", "Libertadores_Matches.csv",
		"BR-Football-Dataset.csv", "novo_campeonato_brasileiro.csv", "fifa_data.csv")
}

func TestShouldAnswerCrossDatasetPlayerAndTeamQuestions(t *testing.T) {
	s := newSoccerDSL(t)
	s.WhenAskingForTeamProfile("Santos")
	s.ThenAnswerMentions("Santos", "Record", "Players")
}

func TestShouldAnswerAggregateQuestionsQuickly(t *testing.T) {
	s := newSoccerDSL(t)
	s.WhenAskingForBestRecord("venue: home")
	s.ThenAnswerArrivedWithinSeconds(5)
}
