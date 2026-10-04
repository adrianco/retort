// Executable specifications: recognising clubs however the records name them.
package acceptance

import (
	"testing"

	"brsoccer/acceptance/dsl"
)

func TestTeamIdentity_ShouldRecogniseAClubUnderEveryNameTheRecordsUse(t *testing.T) {
	s := dsl.NewScenario(t)
	s.Records.Match("source: Brasileirão results", "season: 2015", "home: Palmeiras-SP", "away: Santos-SP")
	s.Records.Match("source: historical Brasileirão", "season: 2008", "home: Palmeiras", "away: Santos")
	s.Records.Match("source: Copa do Brasil results", "season: 2015", "home: Palmeiras - SP", "away: Santos - SP")
	s.Records.Match("source: extended statistics", "date: 2023-05-01", "home: Palmeiras", "away: Santos")

	s.Teams.Record("Palmeiras")

	s.Teams.ConfirmRecord("matches: 4")
}

func TestTeamIdentity_ShouldRecogniseFullClubNames(t *testing.T) {
	s := dsl.NewScenario(t)
	s.Records.Match("home: Corinthians-SP", "away: Santos-SP", "score: 2-0")

	s.Teams.Record("Sport Club Corinthians Paulista")

	s.Teams.ConfirmRecord("matches: 1", "wins: 1")
}

func TestTeamIdentity_ShouldMatchNamesRegardlessOfAccents(t *testing.T) {
	s := dsl.NewScenario(t)
	s.Records.Match("source: historical Brasileirão", "season: 2010", "home: São Paulo", "away: Grêmio")
	s.Records.Match("source: Brasileirão results", "home: Sao Paulo-SP", "away: Gremio-RS")

	s.Teams.Record("Sao Paulo")

	s.Teams.ConfirmRecord("matches: 2")
}

func TestTeamIdentity_ShouldKeepDifferentClubsWithSimilarNamesApart(t *testing.T) {
	s := dsl.NewScenario(t)
	s.Records.Match("home: Atletico-MG", "away: Cruzeiro-MG")
	s.Records.Match("home: Atletico-PR", "away: Coritiba-PR")
	s.Records.Match("source: historical Brasileirão", "season: 2011", "home: Athletico-PR", "away: Coritiba")

	s.Teams.Record("Athletico Paranaense")

	s.Teams.ConfirmRecord("matches: 2")
}

func TestTeamIdentity_ShouldCountAMatchOnceEvenWhenSeveralRecordsDescribeIt(t *testing.T) {
	s := dsl.NewScenario(t)
	s.Records.Match("source: Brasileirão results", "date: 2019-10-20", "home: Flamengo-RJ", "away: Fluminense-RJ", "score: 2-0")
	s.Records.Match("source: historical Brasileirão", "date: 2019-10-20", "home: Flamengo", "away: Fluminense", "score: 2-0")
	s.Records.Match("source: extended statistics", "date: 2019-10-20", "home: Flamengo", "away: Fluminense", "score: 2-0")

	s.Matches.Between("Flamengo", "Fluminense")

	s.Matches.ConfirmCount(1)
}

func TestTeamIdentity_ShouldTakeAMissingScoreFromAnotherRecordOfTheSameMatch(t *testing.T) {
	s := dsl.NewScenario(t)
	s.Records.Match("source: Brasileirão results", "date: 2022-10-09", "home: Fluminense-RJ", "away: America-MG", "score: unknown")
	s.Records.Match("source: extended statistics", "date: 2022-10-09", "home: Fluminense RJ", "away: America MG", "score: 3-0")

	s.Matches.PlayedBy("Fluminense")

	s.Matches.ConfirmShown("2022-10-09: Fluminense 3-0 América")
	s.Matches.ConfirmCount(1)
}

func TestTeamIdentity_ShouldLeaveMatchesWithoutAKnownScoreOutOfRecords(t *testing.T) {
	s := dsl.NewScenario(t)
	s.Records.Match("home: Cuiaba-MT", "away: Flamengo-RJ", "score: unknown")
	s.Records.Match("home: Flamengo-RJ", "away: Cuiaba-MT", "score: 2-0")

	s.Teams.Record("Flamengo")

	s.Teams.ConfirmRecord("matches: 1", "wins: 1")
}
