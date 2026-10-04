// Executable specifications: finding matches.
//
// Each spec starts its own soccer knowledge server over a small, synthetic
// set of match records, so it states only the facts it depends on.
package acceptance

import (
	"testing"

	"brsoccer/acceptance/dsl"
)

func TestShouldListEveryMeetingBetweenTwoTeams(t *testing.T) {
	s := dsl.New(t)
	s.Matches.Played("home: Flamengo", "away: Fluminense", "score: 2-1", "date: 2023-09-03")
	s.Matches.Played("home: Fluminense", "away: Flamengo", "score: 1-0", "date: 2023-05-28")
	s.Matches.Played("home: Flamengo", "away: Vasco", "score: 3-0")

	s.Matches.Search("team: Flamengo", "opponent: Fluminense")

	s.Matches.ConfirmFound("Flamengo 2-1 Fluminense on 2023-09-03", "Fluminense 1-0 Flamengo on 2023-05-28")
}

func TestShouldSummariseHeadToHeadWhenSearchingForMeetings(t *testing.T) {
	s := dsl.New(t)
	s.Matches.Played("home: Flamengo", "away: Fluminense", "score: 2-1")
	s.Matches.Played("home: Fluminense", "away: Flamengo", "score: 1-0")
	s.Matches.Played("home: Flamengo", "away: Fluminense", "score: 1-1")

	s.Matches.Search("team: Flamengo", "opponent: Fluminense")

	s.Matches.ConfirmHeadToHead("Flamengo wins: 1", "Fluminense wins: 1", "draws: 1")
}

func TestShouldFindTheMatchesATeamPlayedInASeason(t *testing.T) {
	s := dsl.New(t)
	s.Matches.Played("home: Palmeiras", "away: Santos", "date: 2023-04-15")
	s.Matches.Played("home: Botafogo", "away: Palmeiras", "date: 2023-08-01")
	s.Matches.Played("home: Palmeiras", "away: Santos", "date: 2022-04-15")
	s.Matches.Played("home: Botafogo", "away: Santos", "date: 2023-06-01")

	s.Matches.Search("team: Palmeiras", "season: 2023")

	s.Matches.ConfirmFoundExactly(2)
}

func TestShouldFindMatchesByCompetition(t *testing.T) {
	s := dsl.New(t)
	s.Matches.Played("home: Palmeiras", "away: Boca Juniors", "competition: Libertadores")
	s.Matches.Played("home: Palmeiras", "away: Santos", "competition: Brasileirão")
	s.Matches.Played("home: Palmeiras", "away: Goiás", "competition: Copa do Brasil")

	s.Matches.Search("team: Palmeiras", "competition: Libertadores")

	s.Matches.ConfirmFound("Palmeiras 1-0 Boca Juniors")
	s.Matches.ConfirmFoundExactly(1)
}

func TestShouldFindCupFinals(t *testing.T) {
	s := dsl.New(t)
	s.Matches.Played("competition: Copa do Brasil", "stage: semifinals", "home: Grêmio", "away: Athletico-PR", "date: 2019-08-14")
	s.Matches.Played("competition: Copa do Brasil", "stage: final", "home: Athletico-PR", "away: Internacional", "score: 1-0", "date: 2019-09-11")
	s.Matches.Played("competition: Copa do Brasil", "stage: final", "home: Internacional", "away: Athletico-PR", "score: 1-2", "date: 2019-09-18")

	s.Matches.Search("competition: Copa do Brasil", "stage: final")

	s.Matches.ConfirmFound("Athletico-PR 1-0 Internacional on 2019-09-11", "Internacional 1-2 Athletico-PR on 2019-09-18")
	s.Matches.ConfirmFoundExactly(2)
}

func TestShouldFindTheMostRecentMeetingAndItsScore(t *testing.T) {
	s := dsl.New(t)
	s.Matches.Played("home: Flamengo", "away: Corinthians", "score: 1-0", "date: 2022-10-12")
	s.Matches.Played("home: Corinthians", "away: Flamengo", "score: 2-2", "date: 2023-07-02")
	s.Matches.Played("home: Flamengo", "away: Corinthians", "score: 3-1", "date: 2021-05-20")

	s.Matches.FindLastMeeting("Flamengo", "Corinthians")

	s.Matches.ConfirmFound("Corinthians 2-2 Flamengo on 2023-07-02")
	s.Matches.ConfirmFoundExactly(1)
}

func TestShouldFindMatchesWithinADateRange(t *testing.T) {
	s := dsl.New(t)
	s.Matches.Played("home: Santos", "away: Grêmio", "date: 2019-03-30")
	s.Matches.Played("home: Santos", "away: Bahia", "date: 2019-04-20")
	s.Matches.Played("home: Santos", "away: Ceará", "date: 2019-05-11")

	s.Matches.Search("team: Santos", "from: 2019-04-01", "to: 2019-04-30")

	s.Matches.ConfirmFound("Santos 1-0 Bahia on 2019-04-20")
	s.Matches.ConfirmFoundExactly(1)
}

func TestShouldDistinguishHomeMatchesFromAwayMatches(t *testing.T) {
	s := dsl.New(t)
	s.Matches.Played("home: Cruzeiro", "away: Atlético-MG")
	s.Matches.Played("home: Atlético-MG", "away: Cruzeiro")
	s.Matches.Played("home: Atlético-MG", "away: América-MG")

	s.Matches.Search("team: Cruzeiro", "venue: away")

	s.Matches.ConfirmFound("Atlético-MG 1-0 Cruzeiro")
	s.Matches.ConfirmFoundExactly(1)
}

func TestShouldFindMatchesFromEverySourceDespiteDifferentDateFormats(t *testing.T) {
	s := dsl.New(t)
	s.Matches.Played("home: Guarani", "away: Vasco", "score: 4-2", "date: 2003-03-29", "source: historical archive")
	s.Matches.Played("home: Sport", "away: Flamengo", "score: 1-1", "date: 2012-05-19", "source: Série A results")
	s.Matches.Played("home: Ceará", "away: Fortaleza", "score: 0-2", "date: 2023-06-10", "source: extended statistics")

	s.Matches.Search("from: 2003-01-01", "to: 2023-12-31")

	s.Matches.ConfirmFound("Guarani 4-2 Vasco on 2003-03-29", "Sport 1-1 Flamengo on 2012-05-19", "Ceará 0-2 Fortaleza on 2023-06-10")
}

func TestShouldRecogniseATeamWhateverNameTheSourceUses(t *testing.T) {
	s := dsl.New(t)
	s.Matches.Played("home: Palmeiras-SP", "away: Santos-SP", "date: 2015-06-01", "source: Série A results")
	s.Matches.Played("home: Palmeiras - SP", "away: Santos - SP", "date: 2015-12-02", "competition: Copa do Brasil")
	s.Matches.Played("home: Palmeiras", "away: Santos", "date: 2023-06-10", "source: extended statistics")

	s.Matches.Search("team: Sociedade Esportiva Palmeiras")

	s.Matches.ConfirmFoundExactly(3)
}

func TestShouldTreatAccentedAndUnaccentedNamesAsTheSameTeam(t *testing.T) {
	s := dsl.New(t)
	s.Matches.Played("home: São Paulo", "away: Grêmio", "date: 2018-07-01", "source: historical archive")
	s.Matches.Played("home: Sao Paulo", "away: Gremio", "date: 2023-07-01", "source: extended statistics")

	s.Matches.Search("team: Sao Paulo FC", "opponent: Grêmio")

	s.Matches.ConfirmFoundExactly(2)
}

func TestShouldCountAMatchOnceWhenSeveralSourcesRecordIt(t *testing.T) {
	s := dsl.New(t)
	s.Matches.Played("home: Flamengo", "away: Fluminense", "score: 2-0", "date: 2019-10-20", "source: Série A results")
	s.Matches.Played("home: Flamengo", "away: Fluminense", "score: 2-0", "date: 2019-10-20", "source: historical archive")
	s.Matches.Played("home: Flamengo", "away: Fluminense", "score: 2-0", "date: 2019-10-21", "source: extended statistics")

	s.Matches.Search("team: Flamengo", "opponent: Fluminense")

	s.Matches.ConfirmFoundExactly(1)
}

func TestShouldReportExtendedStatisticsForAMatchWhenKnown(t *testing.T) {
	s := dsl.New(t)
	s.Matches.Played("home: Internacional", "away: Grêmio", "score: 1-1", "corners: 7-3", "shots: 14-6")

	s.Matches.Search("team: Internacional")

	s.Matches.ConfirmMatchStatistics("corners: 7-3", "shots: 14-6")
}

func TestShouldFindTraditionalDerbiesInASeason(t *testing.T) {
	s := dsl.New(t)
	s.Matches.Played("home: Grêmio", "away: Internacional", "date: 2023-07-08")
	s.Matches.Played("home: Corinthians", "away: Palmeiras", "date: 2023-08-12")
	s.Matches.Played("home: Flamengo", "away: Bahia", "date: 2023-08-19")
	s.Matches.Played("home: Fluminense", "away: Flamengo", "date: 2022-08-19")

	s.Matches.SearchDerbies("season: 2023")

	s.Matches.ConfirmFound("Grêmio 1-0 Internacional", "Corinthians 1-0 Palmeiras")
	s.Matches.ConfirmFoundExactly(2)
}

func TestShouldTellTheUserWhenATeamIsUnknown(t *testing.T) {
	s := dsl.New(t)
	s.Matches.Played("home: Flamengo", "away: Fluminense")

	s.Matches.Search("team: Real Madrid")

	s.ConfirmToldUnknown("Real Madrid")
}
