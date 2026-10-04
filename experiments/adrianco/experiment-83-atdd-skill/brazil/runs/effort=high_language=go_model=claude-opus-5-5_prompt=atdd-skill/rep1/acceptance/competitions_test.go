// Executable specifications: competitions — standings, champions,
// relegation and knockout brackets, all calculated from match results.
package acceptance

import (
	"testing"

	"brsoccer/acceptance/dsl"
)

func TestShouldNameTheChampionCalculatedFromMatchResults(t *testing.T) {
	s := dsl.New(t)
	s.Matches.Played("home: Flamengo", "away: Santos", "score: 3-0", "date: 2019-06-01")
	s.Matches.Played("home: Santos", "away: Palmeiras", "score: 2-1", "date: 2019-07-01")
	s.Matches.Played("home: Palmeiras", "away: Flamengo", "score: 1-1", "date: 2019-08-01")

	s.Competitions.Standings("season: 2019")

	s.Competitions.ConfirmChampion("team: Flamengo", "points: 4", "wins: 1", "draws: 1", "losses: 0")
}

func TestShouldRankLevelTeamsByWinsThenGoalDifference(t *testing.T) {
	s := dsl.New(t)
	s.Matches.Played("home: Grêmio", "away: Bahia", "score: 5-0", "date: 2018-06-01")
	s.Matches.Played("home: Internacional", "away: Bahia", "score: 1-0", "date: 2018-06-02")

	s.Competitions.Standings("season: 2018")

	s.Competitions.ConfirmPosition("position: 1", "team: Grêmio", "points: 3", "goal difference: 5")
	s.Competitions.ConfirmPosition("position: 2", "team: Internacional", "points: 3", "goal difference: 1")
}

func TestShouldIdentifyTheTeamsRelegatedInASeason(t *testing.T) {
	s := dsl.New(t)
	s.Competitions.LeagueSeasonFinishedInOrder("season: 2020",
		"order: Flamengo, Internacional, Atlético-MG, São Paulo, Fluminense, Grêmio, Palmeiras, Santos, "+
			"Athletico-PR, Bragantino, Ceará, Corinthians, Atlético-GO, Bahia, Sport, Fortaleza, "+
			"Vasco, Goiás, Coritiba, Botafogo")

	s.Competitions.Standings("season: 2020")

	s.Competitions.ConfirmRelegated("Vasco", "Goiás", "Coritiba", "Botafogo")
}

func TestShouldNotNameAChampionWhenTheDataMissesPartOfTheSeason(t *testing.T) {
	s := dsl.New(t)
	s.Competitions.LeagueSeasonFinishedInOrder("season: 2023", "unrecorded matches: 3",
		"order: Grêmio, Palmeiras, Atlético-MG, Flamengo, Botafogo, Bragantino, Athletico-PR, Internacional, "+
			"Fluminense, Fortaleza, Cuiabá, São Paulo, Corinthians, Cruzeiro, Bahia, Santos, "+
			"Vasco, Goiás, Coritiba, América-MG")

	s.Competitions.Standings("season: 2023")

	s.Competitions.ConfirmNoChampionNamed()
}

func TestShouldShowTheKnockoutBracketForALibertadoresSeason(t *testing.T) {
	s := dsl.New(t)
	s.Matches.Played("competition: Libertadores", "stage: group stage", "home: Palmeiras", "away: Junior de Barranquilla", "date: 2018-03-01")
	s.Matches.Played("competition: Libertadores", "stage: semifinals", "home: Boca Juniors", "away: Palmeiras", "score: 2-0", "date: 2018-10-24")
	s.Matches.Played("competition: Libertadores", "stage: semifinals", "home: Palmeiras", "away: Boca Juniors", "score: 2-2", "date: 2018-10-31")
	s.Matches.Played("competition: Libertadores", "stage: final", "home: Boca Juniors", "away: River Plate", "score: 2-2", "date: 2018-11-11")
	s.Matches.Played("competition: Libertadores", "stage: final", "home: River Plate", "away: Boca Juniors", "score: 3-1", "date: 2018-12-09")

	s.Competitions.Bracket("competition: Libertadores", "season: 2018")

	s.Competitions.ConfirmTie("stage: final", "teams: Boca Juniors v River Plate", "aggregate: 3-5", "winner: River Plate")
	s.Competitions.ConfirmTie("stage: semifinals", "teams: Boca Juniors v Palmeiras", "aggregate: 4-2", "winner: Boca Juniors")
	s.Competitions.ConfirmNoStage("group stage")
}
