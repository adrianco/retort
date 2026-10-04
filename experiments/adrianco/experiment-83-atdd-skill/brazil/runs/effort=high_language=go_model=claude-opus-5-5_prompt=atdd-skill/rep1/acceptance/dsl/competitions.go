package dsl

import (
	"fmt"
	"time"

	"brsoccer/acceptance/driver"
)

// Competitions is the part of the language about leagues and cups.
type Competitions struct {
	ctx     *context
	driver  driver.SoccerDriver
	matches *Matches
}

// LeagueSeasonFinishedInOrder records a double round-robin season in
// which every team beat each team below it in the given order. With
// "unrecorded matches: n", the last n matches of the season are missing
// from the data.
func (c *Competitions) LeagueSeasonFinishedInOrder(args ...string) {
	t := c.ctx.t
	t.Helper()
	p := parseParams(t, args...)
	season := p.Int(t, "season", 2023)
	competition := p.Get("competition", "Brasileirão")
	unrecorded := p.Int(t, "unrecorded matches", 0)
	teams := p.List("order")
	if len(teams) < 2 {
		t.Fatalf("a league season needs at least two teams in its order")
	}
	day := 0
	recordable := len(teams)*(len(teams)-1) - unrecorded
	for i, better := range teams {
		for _, worse := range teams[i+1:] {
			for _, home := range []bool{true, false} {
				h, a, score := better, worse, "2-0"
				if !home {
					h, a, score = worse, better, "0-1"
				}
				date := time.Date(season, 2, 1, 0, 0, 0, 0, time.UTC).AddDate(0, 0, day/2).Format("2006-01-02")
				day++
				if day > recordable {
					continue
				}
				c.matches.Played("home: "+h, "away: "+a, "score: "+score,
					"date: "+date, fmt.Sprintf("season: %d", season), "competition: "+competition)
			}
		}
	}
}

// Standings asks for a league table: season, competition (default Brasileirão).
func (c *Competitions) Standings(args ...string) {
	c.ctx.t.Helper()
	c.driver.Standings(parseParams(c.ctx.t, args...))
}

// ConfirmChampion checks the team at the top: team, points, wins, draws, losses.
func (c *Competitions) ConfirmChampion(args ...string) {
	c.ctx.t.Helper()
	p := parseParams(c.ctx.t, args...)
	p["position"] = "1"
	c.driver.ConfirmStanding(p)
	c.driver.ConfirmChampionNamed(p.Get("team", ""))
}

// ConfirmPosition checks one line of the table: position, team, points, goal difference.
func (c *Competitions) ConfirmPosition(args ...string) {
	c.ctx.t.Helper()
	c.driver.ConfirmStanding(parseParams(c.ctx.t, args...))
}

func (c *Competitions) ConfirmNoChampionNamed() {
	c.ctx.t.Helper()
	c.driver.ConfirmChampionNamed("")
}

func (c *Competitions) ConfirmRelegated(teams ...string) {
	c.ctx.t.Helper()
	c.driver.ConfirmRelegated(teams)
}

// Bracket asks for the knockout ties of a cup: competition, season.
func (c *Competitions) Bracket(args ...string) {
	c.ctx.t.Helper()
	c.driver.Bracket(parseParams(c.ctx.t, args...))
}

// ConfirmTie checks a knockout tie: stage, teams ("A v B"), aggregate, winner.
func (c *Competitions) ConfirmTie(args ...string) {
	c.ctx.t.Helper()
	c.driver.ConfirmTie(parseParams(c.ctx.t, args...))
}

func (c *Competitions) ConfirmNoStage(stage string) {
	c.ctx.t.Helper()
	c.driver.ConfirmNoStage(stage)
}
