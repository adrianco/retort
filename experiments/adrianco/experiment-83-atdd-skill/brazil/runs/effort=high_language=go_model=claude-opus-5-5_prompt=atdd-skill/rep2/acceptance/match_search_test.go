// Executable specifications: finding matches.
//
// These specs speak only the language of Brazilian football. They say nothing
// about MCP, CSV files or JSON — the DSL and protocol drivers translate.
package acceptance

import (
	"testing"

	"brsoccer/acceptance/dsl"
)

func TestMatchSearch_ShouldFindEveryMeetingBetweenTwoRivals(t *testing.T) {
	s := dsl.NewScenario(t)
	s.Records.Match("date: 2023-09-03", "home: Flamengo-RJ", "away: Fluminense-RJ", "score: 2-1")
	s.Records.Match("date: 2023-05-28", "home: Fluminense-RJ", "away: Flamengo-RJ", "score: 1-0")
	s.Records.Match("date: 2023-06-10", "home: Flamengo-RJ", "away: Palmeiras-SP", "score: 3-0")

	s.Matches.Between("Flamengo", "Fluminense")

	s.Matches.ConfirmShown("2023-09-03: Flamengo 2-1 Fluminense", "2023-05-28: Fluminense 1-0 Flamengo")
	s.Matches.ConfirmCount(2)
}

func TestMatchSearch_ShouldSummariseHeadToHeadAlongsideTheMeetings(t *testing.T) {
	s := dsl.NewScenario(t)
	s.Records.Match("home: Flamengo-RJ", "away: Fluminense-RJ", "score: 2-1")
	s.Records.Match("home: Fluminense-RJ", "away: Flamengo-RJ", "score: 1-0")
	s.Records.Match("home: Fluminense-RJ", "away: Flamengo-RJ", "score: 3-0", "season: 2022")
	s.Records.Match("home: Flamengo-RJ", "away: Fluminense-RJ", "score: 1-1", "season: 2022")

	s.Matches.Between("Flamengo", "Fluminense")

	s.Matches.ConfirmHeadToHead("Flamengo wins: 1", "Fluminense wins: 2", "draws: 1")
}

func TestMatchSearch_ShouldFindAllOfATeamsMatchesInASeasonAcrossCompetitions(t *testing.T) {
	s := dsl.NewScenario(t)
	s.Records.Match("season: 2023", "home: Palmeiras-SP", "away: Santos-SP")
	s.Records.Match("season: 2023", "competition: Copa Libertadores", "home: Boca Juniors", "away: Palmeiras")
	s.Records.Match("season: 2023", "competition: Copa do Brasil", "home: Palmeiras - SP", "away: Bahia - BA")
	s.Records.Match("season: 2022", "home: Palmeiras-SP", "away: Gremio-RS")

	s.Matches.PlayedBy("Palmeiras", "season: 2023")

	s.Matches.ConfirmCount(3)
	s.Matches.ConfirmCompetitionsCovered("Brasileirão Série A", "Copa Libertadores", "Copa do Brasil")
}

func TestMatchSearch_ShouldFindMatchesWithinADateRange(t *testing.T) {
	s := dsl.NewScenario(t)
	s.Records.Match("source: historical Brasileirão", "date: 2005-03-10", "home: Santos", "away: Corinthians")
	s.Records.Match("source: historical Brasileirão", "date: 2005-06-15", "home: Corinthians", "away: Santos")
	s.Records.Match("source: historical Brasileirão", "date: 2005-11-20", "home: Santos", "away: Corinthians")

	s.Matches.PlayedBy("Corinthians", "from: 2005-04-01", "to: 2005-10-31")

	s.Matches.ConfirmShown("2005-06-15: Corinthians 1-0 Santos")
	s.Matches.ConfirmCount(1)
}

func TestMatchSearch_ShouldFindHomeMatchesOnly(t *testing.T) {
	s := dsl.NewScenario(t)
	s.Records.Match("home: Gremio-RS", "away: Internacional-RS", "score: 2-0")
	s.Records.Match("home: Internacional-RS", "away: Gremio-RS", "score: 1-1")

	s.Matches.PlayedBy("Grêmio", "venue: home")

	s.Matches.ConfirmShown("Grêmio 2-0 Internacional")
	s.Matches.ConfirmCount(1)
}

func TestMatchSearch_ShouldFindOnlyTheCompetitionAskedFor(t *testing.T) {
	s := dsl.NewScenario(t)
	s.Records.Match("competition: Copa Libertadores", "home: Flamengo", "away: River Plate", "score: 2-1")
	s.Records.Match("competition: Brasileirão", "home: Flamengo-RJ", "away: Santos-SP", "score: 1-0")

	s.Matches.PlayedBy("Flamengo", "competition: Libertadores")

	s.Matches.ConfirmShown("Flamengo 2-1 River Plate")
	s.Matches.ConfirmCount(1)
}

func TestMatchSearch_ShouldFindCopaDoBrasilFinals(t *testing.T) {
	s := dsl.NewScenario(t)
	s.Records.Match("competition: Copa do Brasil", "season: 2019", "round: 7", "home: Athletico Paranaense - PR", "away: Grêmio - RS", "score: 1-1")
	s.Records.Match("competition: Copa do Brasil", "season: 2019", "round: 8", "home: Athletico Paranaense - PR", "away: Internacional - RS", "score: 1-0")
	s.Records.Match("competition: Copa do Brasil", "season: 2019", "round: 8", "home: Internacional - RS", "away: Athletico Paranaense - PR", "score: 1-2")

	s.Matches.Finals("competition: Copa do Brasil")

	s.Matches.ConfirmCount(2)
	s.Matches.ConfirmShown("Athletico Paranaense 1-0 Internacional", "Internacional 1-2 Athletico Paranaense")
}

func TestMatchSearch_ShouldFindTheMostRecentMeetingAndItsScore(t *testing.T) {
	s := dsl.NewScenario(t)
	s.Records.Match("date: 2021-08-01", "home: Flamengo-RJ", "away: Corinthians-SP", "score: 1-0")
	s.Records.Match("date: 2022-10-30", "home: Corinthians-SP", "away: Flamengo-RJ", "score: 1-2")
	s.Records.Match("date: 2022-03-05", "home: Flamengo-RJ", "away: Corinthians-SP", "score: 2-2")

	s.Matches.LastMeeting("Flamengo", "Corinthians")

	s.Matches.ConfirmShown("2022-10-30: Corinthians 1-2 Flamengo")
	s.Matches.ConfirmCount(1)
}

func TestMatchSearch_ShouldShowExtendedStatisticsWhenTheyWereRecorded(t *testing.T) {
	s := dsl.NewScenario(t)
	s.Records.Match("source: extended statistics", "date: 2023-09-24", "competition: Copa do Brasil", "home: Sao Paulo", "away: Flamengo", "score: 1-1", "corners: 2-4", "shots: 8-13")

	s.Matches.Between("São Paulo", "Flamengo")

	s.Matches.ConfirmStatistics("corners: 2-4", "shots: 8-13")
}

func TestMatchSearch_ShouldTellTheFanWhenATeamIsUnknown(t *testing.T) {
	s := dsl.NewScenario(t)
	s.Records.Match("home: Flamengo-RJ", "away: Santos-SP")

	s.Matches.PlayedBy("Real Madrid")

	s.Matches.ConfirmNoMatchesFound()
}
