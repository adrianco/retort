// Executable specifications: competitions, standings and statistics.
package acceptance

import (
	"testing"

	"brsoccer/acceptance/dsl"
)

func TestCompetitions_ShouldCalculateTheChampionFromResults(t *testing.T) {
	s := dsl.NewScenario(t)
	s.Records.Match("season: 2019", "home: Flamengo-RJ", "away: Santos-SP", "score: 3-0")
	s.Records.Match("season: 2019", "home: Santos-SP", "away: Palmeiras-SP", "score: 1-1")
	s.Records.Match("season: 2019", "home: Palmeiras-SP", "away: Flamengo-RJ", "score: 0-2")

	s.Competitions.Standings("season: 2019")

	s.Competitions.ConfirmChampion("Flamengo", "points: 6", "wins: 2")
	s.Competitions.ConfirmFinishingOrder("Flamengo", "Palmeiras", "Santos")
}

func TestCompetitions_ShouldIdentifyRelegatedTeams(t *testing.T) {
	s := dsl.NewScenario(t)
	s.Records.SeasonFinishingInOrder("season: 2020",
		"Flamengo-RJ", "Internacional-RS", "Atletico-MG", "Sao Paulo-SP", "Vasco da Gama-RJ", "Goias-GO", "Coritiba-PR", "Botafogo-RJ")

	s.Competitions.Standings("season: 2020")

	s.Competitions.ConfirmRelegated("Vasco da Gama", "Goiás", "Coritiba", "Botafogo")
}

func TestCompetitions_ShouldShowTheLibertadoresKnockoutBracket(t *testing.T) {
	s := dsl.NewScenario(t)
	s.Records.Match("competition: Copa Libertadores", "season: 2018", "stage: group stage", "home: Palmeiras", "away: Boca Juniors")
	s.Records.Match("competition: Copa Libertadores", "season: 2018", "stage: semifinals", "home: Boca Juniors", "away: Palmeiras", "score: 2-0")
	s.Records.Match("competition: Copa Libertadores", "season: 2018", "stage: semifinals", "home: Palmeiras", "away: Boca Juniors", "score: 2-2")
	s.Records.Match("competition: Copa Libertadores", "season: 2018", "stage: final", "home: Boca Juniors", "away: River Plate", "score: 2-2")
	s.Records.Match("competition: Copa Libertadores", "season: 2018", "stage: final", "home: River Plate", "away: Boca Juniors", "score: 3-1")

	s.Competitions.Bracket("competition: Libertadores", "season: 2018")

	s.Competitions.ConfirmTie("stage: semifinals", "winner: Boca Juniors", "aggregate: Boca Juniors 4-2 Palmeiras")
	s.Competitions.ConfirmTie("stage: final", "winner: River Plate", "aggregate: River Plate 5-3 Boca Juniors")
	s.Competitions.ConfirmNoStage("group stage")
}

func TestStatistics_ShouldCalculateAverageGoalsAndHomeAdvantage(t *testing.T) {
	s := dsl.NewScenario(t)
	s.Records.Match("home: Flamengo-RJ", "away: Santos-SP", "score: 3-1")
	s.Records.Match("home: Santos-SP", "away: Palmeiras-SP", "score: 0-0")
	s.Records.Match("home: Palmeiras-SP", "away: Flamengo-RJ", "score: 1-2")
	s.Records.Match("home: Gremio-RS", "away: Bahia-BA", "score: 2-1")

	s.Statistics.ForCompetition("competition: Brasileirão")

	s.Statistics.Confirm("matches: 4", "average goals per match: 2.50", "home win rate: 50.0", "draw rate: 25.0", "away win rate: 25.0")
}

func TestStatistics_ShouldListTheBiggestWins(t *testing.T) {
	s := dsl.NewScenario(t)
	s.Records.Match("date: 2015-09-13", "home: Palmeiras-SP", "away: Sao Paulo-SP", "score: 6-0")
	s.Records.Match("date: 2019-10-27", "home: Flamengo-RJ", "away: Gremio-RS", "score: 5-0")
	s.Records.Match("date: 2012-05-27", "competition: Copa Libertadores", "home: Santos", "away: Bolívar", "score: 8-0")
	s.Records.Match("date: 2016-01-01", "home: Santos-SP", "away: Vasco da Gama-RJ", "score: 3-2")

	s.Statistics.BiggestWins()

	s.Statistics.ConfirmWinsInOrder("Santos 8-0 Bolívar", "Palmeiras 6-0 São Paulo", "Flamengo 5-0 Grêmio")
}

func TestStatistics_ShouldCompareTwoSeasons(t *testing.T) {
	s := dsl.NewScenario(t)
	s.Records.Match("season: 2018", "home: Palmeiras-SP", "away: Santos-SP", "score: 1-0")
	s.Records.Match("season: 2018", "home: Santos-SP", "away: Flamengo-RJ", "score: 1-1")
	s.Records.Match("season: 2019", "home: Flamengo-RJ", "away: Santos-SP", "score: 4-1")

	s.Statistics.CompareSeasons("2018", "2019")

	s.Statistics.ConfirmSeason("2018", "matches: 2", "average goals per match: 1.50", "champion: Palmeiras")
	s.Statistics.ConfirmSeason("2019", "matches: 1", "average goals per match: 5.00", "champion: Flamengo")
}

func TestStatistics_ShouldFindDerbiesInASeason(t *testing.T) {
	s := dsl.NewScenario(t)
	s.Records.Match("season: 2023", "home: Flamengo-RJ", "away: Fluminense-RJ")
	s.Records.Match("season: 2023", "home: Gremio-RS", "away: Internacional-RS")
	s.Records.Match("season: 2023", "home: Flamengo-RJ", "away: Gremio-RS")
	s.Records.Match("season: 2022", "home: Palmeiras-SP", "away: Corinthians-SP")

	s.Statistics.Derbies("season: 2023")

	s.Statistics.ConfirmDerbies("Fla-Flu", "Grenal")
	s.Statistics.ConfirmDerbyCount(2)
}
