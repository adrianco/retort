package dsl

import (
	"testing"

	"brsoccer/acceptance/drivers"
)

// Players is the language for asking about players and their ratings.
type Players struct {
	t      *testing.T
	driver drivers.SystemDriver
}

// Find searches players, e.g. Find("nationality: Brazil", "club: Santos").
func (p *Players) Find(args ...string) {
	p.t.Helper()
	p.driver.FindPlayers(NewParams(p.t, args...).Criteria())
}

func (p *Players) BrazilianPlayersAtBrazilianClubs() {
	p.t.Helper()
	p.driver.BrazilianPlayersAtBrazilianClubs()
}

func (p *Players) ConfirmListed(names ...string) {
	p.t.Helper()
	p.driver.ConfirmPlayersListed(names...)
}

func (p *Players) ConfirmNotListed(names ...string) {
	p.t.Helper()
	p.driver.ConfirmPlayersNotListed(names...)
}

func (p *Players) ConfirmListedInOrder(names ...string) {
	p.t.Helper()
	p.driver.ConfirmPlayersInOrder(names...)
}

func (p *Players) ConfirmDetails(name string, facts ...string) {
	p.t.Helper()
	p.driver.ConfirmPlayerDetails(name, NewParams(p.t, facts...).Expectations())
}

func (p *Players) ConfirmSuggested(names ...string) {
	p.t.Helper()
	p.driver.ConfirmPlayersSuggested(names...)
}

func (p *Players) ConfirmClubSummary(club string, facts ...string) {
	p.t.Helper()
	p.driver.ConfirmClubSummary(club, NewParams(p.t, facts...).Expectations())
}

func (p *Players) ConfirmClubNotSummarised(club string) {
	p.t.Helper()
	p.driver.ConfirmClubNotSummarised(club)
}
