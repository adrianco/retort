// Executable specifications: finding players and squads.
package acceptance

import (
	"testing"

	"brsoccer/acceptance/dsl"
)

func TestShouldFindAPlayerByName(t *testing.T) {
	s := dsl.New(t)
	s.Players.Registered("name: Gabriel Barbosa", "club: Santos", "overall: 78", "position: ST")
	s.Players.Registered("name: Gabriel Jesus", "club: Manchester City", "overall: 83")

	s.Players.LookUp("Gabriel Barbosa")

	s.Players.ConfirmProfile("name: Gabriel Barbosa", "club: Santos", "overall: 78", "position: ST", "nationality: Brazil")
}

func TestShouldFindAPlayerWhoseNameIsWrittenWithoutAccents(t *testing.T) {
	s := dsl.New(t)
	s.Players.Registered("name: Éverton Ribeiro", "club: Flamengo")

	s.Players.LookUp("everton ribeiro")

	s.Players.ConfirmProfile("name: Éverton Ribeiro")
}

func TestShouldListBrazilianPlayersFromTheHighestRated(t *testing.T) {
	s := dsl.New(t)
	s.Players.Registered("name: Casemiro", "nationality: Brazil", "overall: 89")
	s.Players.Registered("name: Neymar Jr", "nationality: Brazil", "overall: 92")
	s.Players.Registered("name: L. Messi", "nationality: Argentina", "overall: 94")
	s.Players.Registered("name: Alisson", "nationality: Brazil", "overall: 89")

	s.Players.Search("nationality: Brazil")

	s.Players.ConfirmFoundInOrder("Neymar Jr", "Alisson", "Casemiro")
}

func TestShouldListTheHighestRatedPlayersAtAClub(t *testing.T) {
	s := dsl.New(t)
	s.Players.Registered("name: Diego Alves", "club: Flamengo", "overall: 80")
	s.Players.Registered("name: Éverton Ribeiro", "club: Flamengo", "overall: 82")
	s.Players.Registered("name: Gustavo Scarpa", "club: Fluminense", "overall: 79")

	s.Players.Search("club: Flamengo")

	s.Players.ConfirmFoundInOrder("Éverton Ribeiro", "Diego Alves")
}

func TestShouldFindTheForwardsAtAClub(t *testing.T) {
	s := dsl.New(t)
	s.Players.Registered("name: Pato", "club: São Paulo", "position: ST")
	s.Players.Registered("name: Luciano", "club: São Paulo", "position: LW")
	s.Players.Registered("name: Miranda", "club: São Paulo", "position: CB")
	s.Players.Registered("name: Rony", "club: Palmeiras", "position: ST")

	s.Players.Search("club: São Paulo FC", "position: forward")

	s.Players.ConfirmFound("Pato", "Luciano")
	s.Players.ConfirmFoundExactly(2)
}

func TestShouldSummariseBrazilianPlayersAtBrazilianClubs(t *testing.T) {
	s := dsl.New(t)
	s.Matches.Played("home: Grêmio", "away: Cruzeiro")
	s.Players.Registered("name: Geromel", "club: Grêmio", "nationality: Brazil", "overall: 80")
	s.Players.Registered("name: Kannemann", "club: Grêmio", "nationality: Argentina", "overall: 78")
	s.Players.Registered("name: Maicon", "club: Grêmio", "nationality: Brazil", "overall: 76")
	s.Players.Registered("name: Fábio", "club: Cruzeiro", "nationality: Brazil", "overall: 78")
	s.Players.Registered("name: Casemiro", "club: Real Madrid", "nationality: Brazil", "overall: 89")

	s.Players.SummariseBrazilianPlayersAtBrazilianClubs()

	s.Players.ConfirmClubSummary("club: Grêmio", "players: 2", "average rating: 78.0")
	s.Players.ConfirmClubNotInSummary("Real Madrid")
}

func TestShouldNotMistakeAForeignClubForTheBrazilianClubSharingItsName(t *testing.T) {
	s := dsl.New(t)
	s.Matches.Played("home: Boavista - RJ", "away: Vasco", "competition: Copa do Brasil")
	s.Players.Registered("name: Bracali", "club: Boavista FC", "nationality: Brazil")
	s.Players.Registered("name: Rafael Costa", "club: Boavista FC", "nationality: Portugal")
	s.Players.Registered("name: Idris", "club: Boavista FC", "nationality: Portugal")

	s.Players.SummariseBrazilianPlayersAtBrazilianClubs()

	s.Players.ConfirmClubNotInSummary("Boavista FC")
}

func TestShouldDescribeAClubUsingBothItsSquadAndItsResults(t *testing.T) {
	s := dsl.New(t)
	s.Players.Registered("name: Geromel", "club: Grêmio", "overall: 80")
	s.Matches.Played("home: Gremio-RS", "away: Internacional-RS", "score: 2-1", "source: Série A results")
	s.Matches.Played("home: Internacional", "away: Grêmio", "score: 0-0", "source: historical archive")

	s.Teams.ProfileClub("Grêmio")

	s.Teams.ConfirmSquadIncludes("Geromel")
	s.Teams.ConfirmRecord("matches: 2", "wins: 1", "draws: 1", "losses: 0")
}
