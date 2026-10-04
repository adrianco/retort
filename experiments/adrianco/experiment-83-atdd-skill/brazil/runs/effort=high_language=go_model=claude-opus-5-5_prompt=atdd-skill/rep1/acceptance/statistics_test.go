// Executable specifications: aggregated statistics.
package acceptance

import (
	"testing"

	"brsoccer/acceptance/dsl"
)

func TestShouldCalculateAverageGoalsPerMatchAndHomeWinRate(t *testing.T) {
	s := dsl.New(t)
	s.Matches.Played("home: Santos", "away: Bahia", "score: 3-1")
	s.Matches.Played("home: Bahia", "away: Grêmio", "score: 2-0")
	s.Matches.Played("home: Grêmio", "away: Santos", "score: 0-0")
	s.Matches.Played("home: Ceará", "away: Santos", "score: 0-4")

	s.Statistics.Summarise("competition: Brasileirão")

	s.Statistics.ConfirmSummary("matches: 4", "average goals: 2.50", "home win rate: 50.0%", "draw rate: 25.0%", "away win rate: 25.0%")
}

func TestShouldOnlySummariseTheRequestedCompetition(t *testing.T) {
	s := dsl.New(t)
	s.Matches.Played("home: Santos", "away: Bahia", "score: 3-1", "competition: Brasileirão")
	s.Matches.Played("home: Santos", "away: Bolívar", "score: 8-0", "competition: Libertadores")

	s.Statistics.Summarise("competition: Brasileirão")

	s.Statistics.ConfirmSummary("matches: 1", "average goals: 4.00")
}

func TestShouldListTheBiggestWinsFromTheLargestMargin(t *testing.T) {
	s := dsl.New(t)
	s.Matches.Played("home: Palmeiras", "away: São Paulo", "score: 6-0", "date: 2015-09-13")
	s.Matches.Played("home: Santos", "away: Bolívar", "score: 8-0", "date: 2012-05-27", "competition: Libertadores")
	s.Matches.Played("home: Flamengo", "away: Grêmio", "score: 5-0", "date: 2019-10-27")
	s.Matches.Played("home: Bahia", "away: Vitória", "score: 2-1")

	s.Statistics.BiggestWins()

	s.Statistics.ConfirmBiggestWinsInOrder("Santos 8-0 Bolívar", "Palmeiras 6-0 São Paulo", "Flamengo 5-0 Grêmio")
}

func TestShouldCompareTwoSeasons(t *testing.T) {
	s := dsl.New(t)
	s.Matches.Played("home: Santos", "away: Bahia", "score: 3-1", "date: 2018-06-01")
	s.Matches.Played("home: Bahia", "away: Santos", "score: 0-0", "date: 2018-09-01")
	s.Matches.Played("home: Flamengo", "away: Bahia", "score: 1-0", "date: 2019-06-01")

	s.Statistics.CompareSeasons("2018", "2019")

	s.Statistics.ConfirmSeason("season: 2018", "matches: 2", "average goals: 2.00", "champion: Santos")
	s.Statistics.ConfirmSeason("season: 2019", "matches: 1", "average goals: 1.00", "champion: Flamengo")
}

func TestShouldReportAverageCornersWhereTheDataRecordsThem(t *testing.T) {
	s := dsl.New(t)
	s.Matches.Played("home: Santos", "away: Bahia", "corners: 6-2")
	s.Matches.Played("home: Bahia", "away: Santos", "corners: 3-1")

	s.Statistics.Summarise("competition: Brasileirão")

	s.Statistics.ConfirmSummary("average corners: 6.00")
}
