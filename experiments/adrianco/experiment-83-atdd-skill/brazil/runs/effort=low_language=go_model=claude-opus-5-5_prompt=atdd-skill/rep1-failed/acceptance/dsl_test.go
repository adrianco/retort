package acceptance

// DSL layer: domain vocabulary with named parameters and defaults.
// Each area delegates to the protocol driver at the same level of abstraction.

import (
	"testing"
	"time"
)

type Param func(map[string]any)

func Team(v string) Param        { return func(m map[string]any) { m["team"] = v } }
func Opponent(v string) Param    { return func(m map[string]any) { m["opponent"] = v } }
func Season(v int) Param         { return func(m map[string]any) { m["season"] = v } }
func Competition(v string) Param { return func(m map[string]any) { m["competition"] = v } }
func From(v string) Param        { return func(m map[string]any) { m["date_from"] = v } }
func To(v string) Param          { return func(m map[string]any) { m["date_to"] = v } }
func Venue(v string) Param       { return func(m map[string]any) { m["venue"] = v } }
func By(v string) Param          { return func(m map[string]any) { m["by"] = v } }
func Name(v string) Param        { return func(m map[string]any) { m["name"] = v } }
func Nationality(v string) Param { return func(m map[string]any) { m["nationality"] = v } }
func Club(v string) Param        { return func(m map[string]any) { m["club"] = v } }
func Position(v string) Param    { return func(m map[string]any) { m["position"] = v } }

func args(defaults map[string]any, ps []Param) map[string]any {
	m := map[string]any{}
	for k, v := range defaults {
		m[k] = v
	}
	for _, p := range ps {
		p(m)
	}
	return m
}

type Soccer struct {
	Matches      *Matches
	Teams        *Teams
	Players      *Players
	Competitions *Competitions
	Stats        *Stats
}

func NewSoccer(t *testing.T) *Soccer {
	t.Helper()
	d := NewMCPDriver(t)
	return &Soccer{&Matches{d}, &Teams{d}, &Players{d}, &Competitions{d}, &Stats{d}}
}

type Matches struct{ d *MCPDriver }

func (m *Matches) Find(ps ...Param) {
	m.d.Ask("search_matches", args(map[string]any{"limit": 500}, ps))
}
func (m *Matches) FindFinals(competition string) {
	m.d.Ask("search_matches", map[string]any{"competition": competition, "finals_only": true, "limit": 500})
}
func (m *Matches) FindLastMeeting(a, b string) {
	m.d.Ask("last_meeting", map[string]any{"team_a": a, "team_b": b})
}
func (m *Matches) ShouldInclude(text ...string) { m.d.ShouldContain(text...) }
func (m *Matches) ShouldReportHeadToHead()      { m.d.ShouldContain("Head-to-head") }
func (m *Matches) ShouldAllBeIn(year int)       { m.d.ShouldListMatchesOnlyIn(year) }
func (m *Matches) ShouldAllBeFrom(c string)     { m.d.ShouldListMatchesOnlyFrom(c) }
func (m *Matches) Count() int                   { return m.d.MatchCount() }
func (m *Matches) ShouldCount(n int)            { m.d.ShouldHaveMatchCount(n) }

type Teams struct{ d *MCPDriver }

func (t *Teams) Record(ps ...Param) { t.d.Ask("team_record", args(nil, ps)) }
func (t *Teams) HeadToHead(a, b string) {
	t.d.Ask("head_to_head", map[string]any{"team_a": a, "team_b": b})
}
func (t *Teams) Competitions(team string) {
	t.d.Ask("team_competitions", map[string]any{"team": team})
}
func (t *Teams) Ranking(ps ...Param) {
	t.d.Ask("team_ranking", args(map[string]any{"by": "points"}, ps))
}
func (t *Teams) ShouldHavePlayed(n int)      { t.d.ShouldHavePlayed(n) }
func (t *Teams) ShouldShow(text ...string)   { t.d.ShouldContain(text...) }
func (t *Teams) ShouldRankFirst(team string) { t.d.ShouldRankFirst(team) }

type Players struct{ d *MCPDriver }

func (p *Players) Find(ps ...Param)             { p.d.Ask("search_players", args(map[string]any{"limit": 20}, ps)) }
func (p *Players) ClubSummary(ps ...Param)      { p.d.Ask("club_summary", args(nil, ps)) }
func (p *Players) ShouldInclude(text ...string) { p.d.ShouldContain(text...) }
func (p *Players) ShouldShow(text ...string)    { p.d.ShouldContain(text...) }
func (p *Players) ShouldRankFirst(name string)  { p.d.ShouldRankFirst(name) }

type Competitions struct{ d *MCPDriver }

func (c *Competitions) Standings(ps ...Param) {
	c.d.Ask("standings", args(map[string]any{"competition": "Brasileirão Série A"}, ps))
}
func (c *Competitions) Bracket(ps ...Param) { c.d.Ask("libertadores_bracket", args(nil, ps)) }
func (c *Competitions) ShouldHaveChampion(team string, points int) {
	c.d.ShouldHaveChampion(team, points)
}
func (c *Competitions) ShouldRelegate(teams ...string) { c.d.ShouldMarkRelegated(teams...) }
func (c *Competitions) ShouldShow(text ...string)      { c.d.ShouldContain(text...) }

type Stats struct{ d *MCPDriver }

func (s *Stats) Summary(ps ...Param) { s.d.Ask("stats_summary", args(nil, ps)) }
func (s *Stats) BiggestWins(ps ...Param) {
	s.d.Ask("biggest_wins", args(map[string]any{"limit": 10}, ps))
}
func (s *Stats) ShouldShow(text ...string) { s.d.ShouldContain(text...) }
func (s *Stats) ShouldAnswerWithin(seconds int, question func()) {
	s.d.ShouldTakeLessThan(time.Duration(seconds)*time.Second, question)
}
