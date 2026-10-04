package dsl

import (
	"strconv"
	"strings"
	"testing"
	"time"

	"brsoccer/acceptance/drivers"
)

// Records describes the match results and player ratings the system knows.
type Records struct {
	t         *testing.T
	driver    drivers.RecordsDriver
	matchSeq  int
	playerSeq int
}

// Match records one match. Defaults: a Brasileirão Série A match in 2023,
// won 1-0 by the home side, recorded in the dataset that normally holds that
// competition, on a generated date unique within the test.
func (r *Records) Match(args ...string) {
	r.t.Helper()
	p := NewParams(r.t, args...)
	r.requireRecords()

	competition := canonicalCompetition(p.Optional("competition", "Brasileirão"))
	date, season := r.dateAndSeason(p)
	homeGoals, awayGoals, known := r.score(p.Optional("score", "1-0"))

	m := drivers.MatchRecord{
		Source:      p.Optional("source", defaultSource(competition)),
		Competition: competition,
		Season:      season,
		Date:        date,
		Round:       p.Int("round", 1),
		Stage:       p.Optional("stage", "group stage"),
		Home:        p.Required("home"),
		Away:        p.Required("away"),
		HomeGoals:   homeGoals,
		AwayGoals:   awayGoals,
		ScoreKnown:  known,
	}
	if p.Has("corners") || p.Has("shots") {
		m.HasStats = true
		m.Corners = r.pair(p.Optional("corners", "0-0"))
		m.Shots = r.pair(p.Optional("shots", "0-0"))
	}
	r.driver.AddMatch(m)
}

// SeasonFinishingInOrder records a league season in which every team beats
// every team listed after it, so the final table follows the given order.
func (r *Records) SeasonFinishingInOrder(season string, teams ...string) {
	r.t.Helper()
	for i := range teams {
		for j := i + 1; j < len(teams); j++ {
			r.Match(season, "home: "+teams[i], "away: "+teams[j], "score: 1-0")
		}
	}
}

// Player records one player in the FIFA ratings. Defaults: a 25-year-old
// Brazilian central midfielder rated 70, without a club.
func (r *Records) Player(args ...string) {
	r.t.Helper()
	p := NewParams(r.t, args...)
	r.requireRecords()
	r.playerSeq++
	r.driver.AddPlayer(drivers.PlayerRecord{
		ID:          900000 + r.playerSeq,
		Name:        p.Required("name"),
		Nationality: p.Optional("nationality", "Brazil"),
		Club:        p.Optional("club", ""),
		Position:    p.Optional("position", "CM"),
		Overall:     p.Int("overall", 70),
		Age:         p.Int("age", 25),
	})
}

func (r *Records) requireRecords() {
	r.t.Helper()
	if r.driver == nil {
		r.t.Fatal("this scenario uses the provided datasets; it cannot add records")
	}
}

func (r *Records) dateAndSeason(p Params) (time.Time, int) {
	r.t.Helper()
	r.matchSeq++
	if p.Has("date") {
		d, err := time.Parse("2006-01-02", p.Required("date"))
		if err != nil {
			r.t.Fatalf("match date %q should look like 2023-09-03", p.Required("date"))
		}
		return d, p.Int("season", d.Year())
	}
	season := p.Int("season", 2023)
	// A week apart, so generated matches never look like the same fixture.
	d := time.Date(season, time.April, 1, 0, 0, 0, 0, time.UTC).AddDate(0, 0, 7*r.matchSeq)
	return d, season
}

func (r *Records) score(s string) (int, int, bool) {
	r.t.Helper()
	if strings.EqualFold(s, "unknown") {
		return 0, 0, false
	}
	pr := r.pair(s)
	return pr[0], pr[1], true
}

func (r *Records) pair(s string) [2]int {
	r.t.Helper()
	a, b, ok := strings.Cut(s, "-")
	x, err1 := strconv.Atoi(strings.TrimSpace(a))
	y, err2 := strconv.Atoi(strings.TrimSpace(b))
	if !ok || err1 != nil || err2 != nil {
		r.t.Fatalf("%q should look like 2-1", s)
	}
	return [2]int{x, y}
}

func canonicalCompetition(name string) string {
	n := strings.ToLower(name)
	switch {
	case strings.Contains(n, "libertadores"):
		return "Copa Libertadores"
	case strings.Contains(n, "copa do brasil"):
		return "Copa do Brasil"
	case strings.Contains(n, "série b"), strings.Contains(n, "serie b"):
		return "Série B"
	case strings.Contains(n, "série c"), strings.Contains(n, "serie c"):
		return "Série C"
	default:
		return "Brasileirão"
	}
}

func defaultSource(competition string) string {
	switch competition {
	case "Copa Libertadores":
		return "Libertadores results"
	case "Copa do Brasil":
		return "Copa do Brasil results"
	case "Série B", "Série C":
		return "extended statistics"
	default:
		return "Brasileirão results"
	}
}
