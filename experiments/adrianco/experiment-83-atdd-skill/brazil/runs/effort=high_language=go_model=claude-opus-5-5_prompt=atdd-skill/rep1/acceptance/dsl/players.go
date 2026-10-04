package dsl

import (
	"fmt"

	"brsoccer/acceptance/driver"
)

// Players is the part of the language about individual players.
type Players struct {
	ctx    *context
	driver driver.SoccerDriver
}

// Registered records a player in the player database.
//
//	name         default: a unique generated name
//	nationality  default Brazil
//	club         default "Free Agent FC"
//	overall      rating, default 70; potential defaults to overall
//	position     default CM
//	age          default 25
func (pl *Players) Registered(args ...string) {
	t := pl.ctx.t
	t.Helper()
	p := parseParams(t, args...)
	n := pl.ctx.nextPlayer
	pl.ctx.nextPlayer++
	overall := p.Int(t, "overall", 70)
	pl.driver.RecordPlayer(driver.PlayerFixture{
		ID:          100000 + n,
		Name:        p.Get("name", fmt.Sprintf("Player %d", n)),
		Nationality: p.Get("nationality", "Brazil"),
		Club:        p.Get("club", "Free Agent FC"),
		Overall:     overall,
		Potential:   p.Int(t, "potential", overall),
		Position:    p.Get("position", "CM"),
		Age:         p.Int(t, "age", 25),
		Jersey:      p.Int(t, "jersey", n%99+1),
	})
}

// Search asks for players: name, nationality, club, position.
func (pl *Players) Search(args ...string) {
	pl.ctx.t.Helper()
	pl.driver.SearchPlayers(parseParams(pl.ctx.t, args...))
}

// LookUp asks who a player is.
func (pl *Players) LookUp(name string) {
	pl.ctx.t.Helper()
	pl.driver.LookUpPlayer(name)
}

// ConfirmProfile checks the player described: name, club, overall, position, nationality.
func (pl *Players) ConfirmProfile(args ...string) {
	pl.ctx.t.Helper()
	pl.driver.ConfirmPlayerProfile(parseParams(pl.ctx.t, args...))
}

// ConfirmFoundInOrder checks the first players listed, best first.
func (pl *Players) ConfirmFoundInOrder(names ...string) {
	pl.ctx.t.Helper()
	pl.driver.ConfirmPlayersInOrder(names)
}

func (pl *Players) ConfirmFound(names ...string) {
	pl.ctx.t.Helper()
	pl.driver.ConfirmPlayersFound(names)
}

func (pl *Players) ConfirmFoundExactly(count int) {
	pl.ctx.t.Helper()
	pl.driver.ConfirmPlayerCount(count, true)
}

func (pl *Players) ConfirmFoundAtLeast(count int) {
	pl.ctx.t.Helper()
	pl.driver.ConfirmPlayerCount(count, false)
}

// ConfirmTotal checks how many players matched in all, however many were listed.
func (pl *Players) ConfirmTotal(count int) {
	pl.ctx.t.Helper()
	pl.driver.ConfirmPlayerTotal(count)
}

func (pl *Players) SummariseBrazilianPlayersAtBrazilianClubs() {
	pl.ctx.t.Helper()
	pl.driver.SummariseBrazilianPlayersAtBrazilianClubs()
}

// ConfirmClubSummary checks one club's line: club, players, average rating.
func (pl *Players) ConfirmClubSummary(args ...string) {
	pl.ctx.t.Helper()
	pl.driver.ConfirmClubSummary(parseParams(pl.ctx.t, args...))
}

func (pl *Players) ConfirmClubNotInSummary(club string) {
	pl.ctx.t.Helper()
	pl.driver.ConfirmClubNotInSummary(club)
}
