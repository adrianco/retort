// Executable specifications: how teams have performed.
package acceptance

import (
	"testing"

	"brsoccer/acceptance/dsl"
)

func TestTeamPerformance_ShouldReportAHomeRecordForASeason(t *testing.T) {
	s := dsl.NewScenario(t)
	s.Records.Match("season: 2022", "home: Corinthians-SP", "away: Santos-SP", "score: 2-0")
	s.Records.Match("season: 2022", "home: Corinthians-SP", "away: Palmeiras-SP", "score: 1-1")
	s.Records.Match("season: 2022", "home: Corinthians-SP", "away: Flamengo-RJ", "score: 0-1")
	s.Records.Match("season: 2022", "home: Corinthians-SP", "away: Gremio-RS", "score: 3-1")
	s.Records.Match("season: 2022", "home: Santos-SP", "away: Corinthians-SP", "score: 4-0")
	s.Records.Match("season: 2021", "home: Corinthians-SP", "away: Santos-SP", "score: 5-0")

	s.Teams.Record("Corinthians", "season: 2022", "venue: home")

	s.Teams.ConfirmRecord("matches: 4", "wins: 2", "draws: 1", "losses: 1", "goals for: 6", "goals against: 3", "win rate: 50.0")
}

func TestTeamPerformance_ShouldReportAnAwayRecord(t *testing.T) {
	s := dsl.NewScenario(t)
	s.Records.Match("home: Santos-SP", "away: Corinthians-SP", "score: 0-2")
	s.Records.Match("home: Corinthians-SP", "away: Santos-SP", "score: 0-3")

	s.Teams.Record("Corinthians", "venue: away")

	s.Teams.ConfirmRecord("matches: 1", "wins: 1", "goals for: 2", "goals against: 0")
}

func TestTeamPerformance_ShouldCompareTwoTeamsHeadToHead(t *testing.T) {
	s := dsl.NewScenario(t)
	s.Records.Match("home: Palmeiras-SP", "away: Santos-SP", "score: 3-1")
	s.Records.Match("home: Santos-SP", "away: Palmeiras-SP", "score: 2-2")
	s.Records.Match("competition: Copa do Brasil", "home: Santos - SP", "away: Palmeiras - SP", "score: 1-0")
	s.Records.Match("home: Palmeiras-SP", "away: Flamengo-RJ", "score: 5-0")

	s.Teams.HeadToHead("Palmeiras", "Santos")

	s.Teams.ConfirmHeadToHead("matches: 3", "Palmeiras wins: 1", "Santos wins: 1", "draws: 1", "Palmeiras goals: 5", "Santos goals: 4")
}

func TestTeamPerformance_ShouldIdentifyTheHighestScoringTeamInASeason(t *testing.T) {
	s := dsl.NewScenario(t)
	s.Records.Match("season: 2023", "home: Palmeiras-SP", "away: Santos-SP", "score: 3-1")
	s.Records.Match("season: 2023", "home: Botafogo-RJ", "away: Palmeiras-SP", "score: 4-0")
	s.Records.Match("season: 2023", "home: Botafogo-RJ", "away: Santos-SP", "score: 2-2")

	s.Teams.Rank("by: goals scored", "season: 2023", "competition: Brasileirão")

	s.Teams.ConfirmRankedFirst("Botafogo", "value: 6")
}

func TestTeamPerformance_ShouldIdentifyTheBestAwayRecord(t *testing.T) {
	s := dsl.NewScenario(t)
	s.Records.Match("home: Santos-SP", "away: Palmeiras-SP", "score: 0-1")
	s.Records.Match("home: Flamengo-RJ", "away: Palmeiras-SP", "score: 0-2")
	s.Records.Match("home: Palmeiras-SP", "away: Flamengo-RJ", "score: 0-3")
	s.Records.Match("home: Santos-SP", "away: Flamengo-RJ", "score: 2-2")

	s.Teams.Rank("by: win rate", "venue: away")

	s.Teams.ConfirmRankedFirst("Palmeiras", "value: 100.0")
}

func TestTeamPerformance_ShouldListTheCompetitionsATeamHasPlayedIn(t *testing.T) {
	s := dsl.NewScenario(t)
	s.Records.Match("home: Palmeiras-SP", "away: Santos-SP")
	s.Records.Match("competition: Copa Libertadores", "home: Palmeiras", "away: Boca Juniors")
	s.Records.Match("competition: Copa do Brasil", "home: Palmeiras - SP", "away: Bahia - BA")
	s.Records.Match("competition: Série B", "home: Vila Nova", "away: Guarani SP")

	s.Teams.CompetitionsPlayed("Palmeiras")

	s.Teams.ConfirmCompetitions("Brasileirão Série A", "Copa Libertadores", "Copa do Brasil")
}

func TestTeamPerformance_ShouldGiveAnOverviewCombiningResultsAndSquad(t *testing.T) {
	s := dsl.NewScenario(t)
	s.Records.Match("home: Gremio-RS", "away: Santos-SP", "score: 2-0")
	s.Records.Player("name: Everton", "club: Grêmio", "overall: 80")
	s.Records.Player("name: Kannemann", "club: Grêmio", "overall: 76", "nationality: Argentina")

	s.Teams.Overview("Grêmio")

	s.Teams.ConfirmRecord("matches: 1", "wins: 1")
	s.Teams.ConfirmSquad("players: 2", "best player: Everton")
}
