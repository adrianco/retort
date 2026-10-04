// Executable specifications against the provided Kaggle datasets.
//
// Most specs build their own synthetic records (see dsl.Records). These few
// exist because TASK.md makes requirements of the provided data itself: every
// file must load, sample questions must be answerable, and answers must come
// back quickly. They share one read-only system instance.
package acceptance

import (
	"testing"

	"brsoccer/acceptance/dsl"
)

func TestProvidedData_ShouldLoadAllSixDatasets(t *testing.T) {
	s := dsl.ProvidedDataScenario(t)

	s.Datasets.List()

	s.Datasets.ConfirmLoaded("Brasileirão results", "records: 4180")
	s.Datasets.ConfirmLoaded("Copa do Brasil results", "records: 1337")
	s.Datasets.ConfirmLoaded("Libertadores results", "records: 1255")
	s.Datasets.ConfirmLoaded("extended statistics", "records: 10296")
	s.Datasets.ConfirmLoaded("historical Brasileirão", "records: 6886")
	s.Datasets.ConfirmLoaded("FIFA player ratings", "records: 18207")
}

func TestProvidedData_ShouldNameFlamengoThe2019Champions(t *testing.T) {
	s := dsl.ProvidedDataScenario(t)

	s.Competitions.Standings("season: 2019")

	s.Competitions.ConfirmChampion("Flamengo", "points: 90", "wins: 28", "draws: 6", "losses: 4")
	s.Competitions.ConfirmTeamsInTable(20)
	s.Fan.ConfirmAnsweredWithin("seconds: 5")
}

func TestProvidedData_ShouldNameThe2020RelegatedTeams(t *testing.T) {
	s := dsl.ProvidedDataScenario(t)

	s.Competitions.Standings("season: 2020")

	s.Competitions.ConfirmRelegated("Vasco da Gama", "Goiás", "Coritiba", "Botafogo")
}

func TestProvidedData_ShouldCalculateHistoricalSeasonsFromTheArchive(t *testing.T) {
	s := dsl.ProvidedDataScenario(t)

	s.Competitions.Standings("season: 2008")

	s.Competitions.ConfirmChampion("São Paulo", "points: 75")
}

func TestProvidedData_ShouldFindThe2019CopaDoBrasilFinal(t *testing.T) {
	s := dsl.ProvidedDataScenario(t)

	s.Matches.Finals("competition: Copa do Brasil", "season: 2019")

	s.Matches.ConfirmShown("Athletico Paranaense 1-0 Internacional", "Internacional 1-2 Athletico Paranaense")
	s.Fan.ConfirmAnsweredWithin("seconds: 2")
}

func TestProvidedData_ShouldShowRiverPlateWinningThe2018Libertadores(t *testing.T) {
	s := dsl.ProvidedDataScenario(t)

	s.Competitions.Bracket("competition: Libertadores", "season: 2018")

	s.Competitions.ConfirmTie("stage: final", "winner: River Plate", "aggregate: River Plate 5-3 Boca Juniors")
	s.Competitions.ConfirmTie("stage: semifinals", "winner: Boca Juniors", "aggregate: Boca Juniors 4-2 Palmeiras")
}

func TestProvidedData_ShouldFindTheTopScoringTeamOf2023(t *testing.T) {
	s := dsl.ProvidedDataScenario(t)

	s.Teams.Rank("by: goals scored", "season: 2023", "competition: Brasileirão")

	s.Teams.ConfirmRankedFirst("Grêmio", "value: 63")
	s.Fan.ConfirmAnsweredWithin("seconds: 5")
}

func TestProvidedData_ShouldFindFlaFluMeetingsAcrossSources(t *testing.T) {
	s := dsl.ProvidedDataScenario(t)

	s.Matches.Between("Flamengo", "Fluminense")

	s.Matches.ConfirmShown("2019-10-20: Flamengo 2-0 Fluminense", "2004-05-23: Flamengo 1-2 Fluminense")
	s.Matches.ConfirmNoDuplicates()
	s.Fan.ConfirmAnsweredWithin("seconds: 2")
}

func TestProvidedData_ShouldListNeymarAsTheTopBrazilianPlayer(t *testing.T) {
	s := dsl.ProvidedDataScenario(t)

	s.Players.Find("nationality: Brazil")

	s.Players.ConfirmListedInOrder("Neymar Jr")
	s.Fan.ConfirmAnsweredWithin("seconds: 2")
}

func TestProvidedData_ShouldSuggestAlternativesForAPlayerNotInTheRatings(t *testing.T) {
	s := dsl.ProvidedDataScenario(t)

	s.Players.Find("name: Gabriel Barbosa")

	s.Players.ConfirmSuggested("M. Barbosa")
}

func TestProvidedData_ShouldSummariseBrazilianPlayersAtBrazilianClubs(t *testing.T) {
	s := dsl.ProvidedDataScenario(t)

	s.Players.BrazilianPlayersAtBrazilianClubs()

	s.Players.ConfirmClubSummary("Grêmio")
	s.Players.ConfirmClubSummary("Atlético Mineiro")
	s.Players.ConfirmClubNotSummarised("Boavista FC")
	s.Fan.ConfirmAnsweredWithin("seconds: 5")
}

func TestProvidedData_ShouldAnswerAggregateQuestionsQuickly(t *testing.T) {
	s := dsl.ProvidedDataScenario(t)

	s.Statistics.ForCompetition("competition: Brasileirão")
	s.Fan.ConfirmAnsweredWithin("seconds: 5")
	s.Statistics.BiggestWins()
	s.Fan.ConfirmAnsweredWithin("seconds: 5")
	s.Teams.Rank("by: win rate", "venue: home", "minimum matches: 50")
	s.Fan.ConfirmAnsweredWithin("seconds: 5")
	s.Statistics.CompareSeasons("2018", "2019")
	s.Fan.ConfirmAnsweredWithin("seconds: 5")
	s.Statistics.Derbies("season: 2023")
	s.Fan.ConfirmAnsweredWithin("seconds: 5")
	s.Teams.Overview("Palmeiras")
	s.Fan.ConfirmAnsweredWithin("seconds: 5")
}

func TestProvidedData_ShouldReportCorinthiansHomeRecordFor2022(t *testing.T) {
	s := dsl.ProvidedDataScenario(t)

	s.Teams.Record("Corinthians", "season: 2022", "venue: home", "competition: Brasileirão")

	s.Teams.ConfirmRecord("matches: 19", "wins: 12", "draws: 4", "losses: 3", "goals for: 24", "goals against: 11", "win rate: 63.2")
	s.Fan.ConfirmAnsweredWithin("seconds: 2")
}

func TestProvidedData_ShouldFindWhenFlamengoLastPlayedCorinthians(t *testing.T) {
	s := dsl.ProvidedDataScenario(t)

	s.Matches.LastMeeting("Flamengo", "Corinthians")

	s.Matches.ConfirmShown("2023-10-08: Corinthians 1-1 Flamengo")
	s.Fan.ConfirmAnsweredWithin("seconds: 2")
}

func TestProvidedData_ShouldListTheCompetitionsPalmeirasHasPlayedIn(t *testing.T) {
	s := dsl.ProvidedDataScenario(t)

	s.Teams.CompetitionsPlayed("Palmeiras")

	s.Teams.ConfirmCompetitions("Brasileirão Série A", "Copa do Brasil", "Copa Libertadores")
}

func TestProvidedData_ShouldFindForwardsAtGremio(t *testing.T) {
	s := dsl.ProvidedDataScenario(t)

	s.Players.Find("club: Grêmio", "position: forward")

	s.Players.ConfirmListedInOrder("Ronaldo Cabrais", "José Mirazar")
	s.Fan.ConfirmAnsweredWithin("seconds: 2")
}

func TestProvidedData_ShouldCompareTwoClubsAcrossEveryCompetition(t *testing.T) {
	s := dsl.ProvidedDataScenario(t)

	s.Teams.HeadToHead("Palmeiras", "Santos")

	s.Teams.ConfirmHeadToHead("matches: 41", "Palmeiras wins: 17", "Santos wins: 16", "draws: 8")
	s.Fan.ConfirmAnsweredWithin("seconds: 2")
}
