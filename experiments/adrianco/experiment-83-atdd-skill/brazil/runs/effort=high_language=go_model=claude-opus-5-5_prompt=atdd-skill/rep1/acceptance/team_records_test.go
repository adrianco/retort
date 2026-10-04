// Executable specifications: team records, comparisons and rankings.
package acceptance

import (
	"testing"

	"brsoccer/acceptance/dsl"
)

func TestShouldReportATeamsHomeRecordForASeason(t *testing.T) {
	s := dsl.New(t)
	s.Matches.Played("home: Corinthians", "away: Santos", "score: 2-0", "date: 2022-04-10")
	s.Matches.Played("home: Corinthians", "away: Goiás", "score: 1-1", "date: 2022-05-10")
	s.Matches.Played("home: Corinthians", "away: Palmeiras", "score: 0-3", "date: 2022-06-10")
	s.Matches.Played("home: Bahia", "away: Corinthians", "score: 0-1", "date: 2022-07-10")
	s.Matches.Played("home: Corinthians", "away: Santos", "score: 4-0", "date: 2021-04-10")

	s.Teams.RecordFor("team: Corinthians", "season: 2022", "venue: home")

	s.Teams.ConfirmRecord("matches: 3", "wins: 1", "draws: 1", "losses: 1", "goals for: 3", "goals against: 4", "win rate: 33.3%")
}

func TestShouldReportATeamsRecordInEachCompetition(t *testing.T) {
	s := dsl.New(t)
	s.Matches.Played("home: Palmeiras", "away: Santos", "score: 2-0", "competition: Brasileirão")
	s.Matches.Played("home: Palmeiras", "away: River Plate", "score: 0-1", "competition: Libertadores")

	s.Teams.RecordFor("team: Palmeiras")

	s.Teams.ConfirmCompetitionRecord("competition: Libertadores", "matches: 1", "losses: 1")
}

func TestShouldCompareTwoTeamsHeadToHead(t *testing.T) {
	s := dsl.New(t)
	s.Matches.Played("home: Palmeiras", "away: Santos", "score: 3-0", "competition: Brasileirão")
	s.Matches.Played("home: Santos", "away: Palmeiras", "score: 1-0", "competition: Copa do Brasil")
	s.Matches.Played("home: Santos", "away: Palmeiras", "score: 1-1", "competition: Brasileirão")
	s.Matches.Played("home: Palmeiras", "away: Grêmio", "score: 5-0")

	s.Teams.CompareHeadToHead("Palmeiras", "Santos")

	s.Teams.ConfirmHeadToHead("meetings: 3", "Palmeiras wins: 1", "Santos wins: 1", "draws: 1", "Palmeiras goals: 4", "Santos goals: 2")
}

func TestShouldListTheCompetitionsATeamHasPlayedIn(t *testing.T) {
	s := dsl.New(t)
	s.Matches.Played("home: Palmeiras", "away: Santos", "competition: Brasileirão")
	s.Matches.Played("home: Palmeiras", "away: Boca Juniors", "competition: Libertadores")
	s.Matches.Played("home: Palmeiras", "away: Goiás", "competition: Copa do Brasil")
	s.Matches.Played("home: Santos", "away: Goiás", "competition: Série B")

	s.Teams.CompetitionsPlayedBy("Palmeiras")

	s.Teams.ConfirmPlayedIn("Brasileirão Série A", "Copa Libertadores", "Copa do Brasil")
}

func TestShouldIdentifyTheTeamThatScoredMostGoalsInASeason(t *testing.T) {
	s := dsl.New(t)
	s.Matches.Played("home: Palmeiras", "away: Santos", "score: 3-1", "date: 2023-05-01")
	s.Matches.Played("home: Botafogo", "away: Palmeiras", "score: 4-0", "date: 2023-06-01")
	s.Matches.Played("home: Santos", "away: Botafogo", "score: 2-2", "date: 2023-07-01")
	s.Matches.Played("home: Santos", "away: Grêmio", "score: 9-0", "date: 2022-07-01")

	s.Teams.Rank("by: goals scored", "season: 2023", "competition: Brasileirão")

	s.Teams.ConfirmRankedFirst("team: Botafogo", "value: 6")
}

func TestShouldIdentifyTheTeamWithTheBestAwayRecord(t *testing.T) {
	s := dsl.New(t)
	s.Matches.Played("home: Santos", "away: Grêmio", "score: 0-1")
	s.Matches.Played("home: Bahia", "away: Grêmio", "score: 1-1")
	s.Matches.Played("home: Grêmio", "away: Bahia", "score: 0-3")
	s.Matches.Played("home: Santos", "away: Bahia", "score: 0-2")
	s.Matches.Played("home: Grêmio", "away: Santos", "score: 2-2")

	s.Teams.Rank("by: win rate", "venue: away")

	s.Teams.ConfirmRankedFirst("team: Bahia", "value: 100.0%")
}

func TestShouldIdentifyTheTeamWithTheBestHomeRecord(t *testing.T) {
	s := dsl.New(t)
	s.Matches.Played("home: Fortaleza", "away: Ceará", "score: 2-0")
	s.Matches.Played("home: Fortaleza", "away: Sport", "score: 1-1")
	s.Matches.Played("home: Ceará", "away: Fortaleza", "score: 2-0")
	s.Matches.Played("home: Ceará", "away: Sport", "score: 3-0")

	s.Teams.Rank("by: win rate", "venue: home")

	s.Teams.ConfirmRankedFirst("team: Ceará", "value: 100.0%")
}

func TestShouldResolveTheNameVariationsOfATeam(t *testing.T) {
	s := dsl.New(t)
	s.Matches.Played("home: Vasco da Gama-RJ", "away: Botafogo-RJ", "source: Série A results")
	s.Matches.Played("home: Vasco", "away: Botafogo-RJ", "source: historical archive")

	s.Teams.FindTeam("Vasco da Gama")

	s.Teams.ConfirmKnownAs("Vasco da Gama-RJ", "Vasco")
}
