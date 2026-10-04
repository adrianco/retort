// Executable specifications: finding players.
package acceptance

import (
	"testing"

	"brsoccer/acceptance/dsl"
)

func TestPlayerSearch_ShouldFindAPlayerByName(t *testing.T) {
	s := dsl.NewScenario(t)
	s.Records.Player("name: Gabriel Barbosa", "club: Santos", "position: ST", "overall: 78")
	s.Records.Player("name: Gabriel Jesus", "club: Manchester City", "overall: 83")

	s.Players.Find("name: gabriel barbosa")

	s.Players.ConfirmListed("Gabriel Barbosa")
	s.Players.ConfirmNotListed("Gabriel Jesus")
	s.Players.ConfirmDetails("Gabriel Barbosa", "club: Santos", "position: ST", "overall: 78")
}

func TestPlayerSearch_ShouldFindPlayersRegardlessOfAccents(t *testing.T) {
	s := dsl.NewScenario(t)
	s.Records.Player("name: Hélder Barbosa", "nationality: Portugal")

	s.Players.Find("name: Helder")

	s.Players.ConfirmListed("Hélder Barbosa")
}

func TestPlayerSearch_ShouldSuggestSimilarPlayersWhenNoneMatchTheName(t *testing.T) {
	s := dsl.NewScenario(t)
	s.Records.Player("name: M. Barbosa", "nationality: Argentina")
	s.Records.Player("name: Casemiro")

	s.Players.Find("name: Gabriel Barbosa")

	s.Players.ConfirmSuggested("M. Barbosa")
}

func TestPlayerSearch_ShouldListBrazilianPlayersBestFirst(t *testing.T) {
	s := dsl.NewScenario(t)
	s.Records.Player("name: Alisson", "nationality: Brazil", "overall: 89")
	s.Records.Player("name: Neymar Jr", "nationality: Brazil", "overall: 92")
	s.Records.Player("name: L. Messi", "nationality: Argentina", "overall: 94")
	s.Records.Player("name: Casemiro", "nationality: Brazil", "overall: 88")

	s.Players.Find("nationality: Brazil")

	s.Players.ConfirmListedInOrder("Neymar Jr", "Alisson", "Casemiro")
	s.Players.ConfirmNotListed("L. Messi")
}

func TestPlayerSearch_ShouldListAClubsPlayersBestFirst(t *testing.T) {
	s := dsl.NewScenario(t)
	s.Records.Player("name: Diego", "club: Flamengo", "overall: 74")
	s.Records.Player("name: Everton Ribeiro", "club: Flamengo", "overall: 78")
	s.Records.Player("name: Dudu", "club: Palmeiras", "overall: 80")

	s.Players.Find("club: Flamengo")

	s.Players.ConfirmListedInOrder("Everton Ribeiro", "Diego")
	s.Players.ConfirmNotListed("Dudu")
}

func TestPlayerSearch_ShouldFindForwardsAtAClub(t *testing.T) {
	s := dsl.NewScenario(t)
	s.Records.Player("name: Pato", "club: São Paulo", "position: ST")
	s.Records.Player("name: Brenner", "club: São Paulo", "position: LW")
	s.Records.Player("name: Hernanes", "club: São Paulo", "position: CM")
	s.Records.Player("name: Kaká", "club: Orlando City", "position: CAM")

	s.Players.Find("club: Sao Paulo", "position: forward")

	s.Players.ConfirmListed("Pato", "Brenner")
	s.Players.ConfirmNotListed("Hernanes", "Kaká")
}

func TestPlayerSearch_ShouldSummariseBrazilianPlayersAtBrazilianClubs(t *testing.T) {
	s := dsl.NewScenario(t)
	s.Records.Match("home: Santos-SP", "away: Gremio-RS")
	s.Records.Player("name: Rodrygo", "nationality: Brazil", "club: Santos", "overall: 70")
	s.Records.Player("name: Gabigol", "nationality: Brazil", "club: Santos", "overall: 80")
	s.Records.Player("name: Luan", "nationality: Brazil", "club: Grêmio", "overall: 81")
	s.Records.Player("name: Kannemann", "nationality: Argentina", "club: Grêmio", "overall: 76")
	s.Records.Player("name: Neymar Jr", "nationality: Brazil", "club: Paris Saint-Germain", "overall: 92")

	s.Players.BrazilianPlayersAtBrazilianClubs()

	s.Players.ConfirmClubSummary("Santos", "players: 2", "average rating: 75")
	s.Players.ConfirmClubSummary("Grêmio", "players: 1", "average rating: 81")
	s.Players.ConfirmClubNotSummarised("Paris Saint-Germain")
}
