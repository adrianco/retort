// query_test.go covers the individual filters and edge cases of the query
// layer that the scenario tests exercise only indirectly.
package soccer

import (
	"strings"
	"testing"
)

func TestMatchFilterDateRange(t *testing.T) {
	g := LoadTestGraph(t)

	res, err := g.SearchMatches(MatchFilter{
		Team: "Flamengo", DateFrom: "2019-01-01", DateTo: "2019-12-31", Limit: 200,
	})
	if err != nil {
		t.Fatalf("SearchMatches: %v", err)
	}
	if res.Total == 0 {
		t.Fatal("no matches in 2019")
	}
	for _, m := range res.Matches {
		if m.Date < "2019-01-01" || m.Date > "2019-12-31" {
			t.Errorf("match outside the requested range: %s", m.Summary)
		}
	}

	if _, err := g.SearchMatches(MatchFilter{DateFrom: "yesterday"}); err == nil {
		t.Error("expected an unparseable date_from to be rejected")
	}
}

func TestMatchFilterRoundAndMargin(t *testing.T) {
	g := LoadTestGraph(t)

	res, err := g.SearchMatches(MatchFilter{Competition: "serie-a", Season: 2019, Round: 1, Limit: 50})
	if err != nil {
		t.Fatalf("SearchMatches: %v", err)
	}
	if res.Total != 10 {
		t.Errorf("round 1 of a 20-club season has %d matches, want 10", res.Total)
	}

	res, err = g.SearchMatches(MatchFilter{Competition: "serie-a", MinGoalDiff: 6, Limit: 50})
	if err != nil {
		t.Fatalf("SearchMatches: %v", err)
	}
	if res.Total == 0 {
		t.Fatal("no six-goal wins found in twenty Série A seasons")
	}
	for _, m := range res.Matches {
		if abs(m.HomeGoals-m.AwayGoals) < 6 {
			t.Errorf("margin filter leaked: %s", m.Summary)
		}
	}

	res, err = g.SearchMatches(MatchFilter{MinGoals: 10, Limit: 50})
	if err != nil {
		t.Fatalf("SearchMatches: %v", err)
	}
	for _, m := range res.Matches {
		if m.HomeGoals+m.AwayGoals < 10 {
			t.Errorf("total-goals filter leaked: %s", m.Summary)
		}
	}
}

func TestMatchFilterHomeAndAway(t *testing.T) {
	g := LoadTestGraph(t)

	res, err := g.SearchMatches(MatchFilter{HomeTeam: "Santos", AwayTeam: "Corinthians", Limit: 50})
	if err != nil {
		t.Fatalf("SearchMatches: %v", err)
	}
	if res.Total == 0 {
		t.Fatal("no Santos home matches against Corinthians")
	}
	for _, m := range res.Matches {
		if m.HomeTeam != "Santos" || m.AwayTeam != "Corinthians" {
			t.Errorf("home/away filter leaked: %s", m.Summary)
		}
	}
}

func TestResolveCompetitionSynonyms(t *testing.T) {
	cases := map[string]string{
		"serie-a":               CompSerieA,
		"Serie A":               CompSerieA,
		"Brasileirão":           CompSerieA,
		"campeonato brasileiro": CompSerieA,
		"serie b":               CompSerieB,
		"Copa do Brasil":        CompCopaDoBrasil,
		"libertadores":          CompLibertadores,
		"Copa Libertadores":     CompLibertadores,
	}
	for in, want := range cases {
		got, err := ResolveCompetition(in)
		if err != nil {
			t.Errorf("ResolveCompetition(%q): %v", in, err)
			continue
		}
		if got != want {
			t.Errorf("ResolveCompetition(%q) = %q, want %q", in, got, want)
		}
	}
	if _, err := ResolveCompetition("Premier League"); err == nil {
		t.Error("expected an unknown competition to be rejected")
	}
}

func TestNormalizeStage(t *testing.T) {
	cases := map[string]struct {
		want  string
		exact bool
	}{
		"final":       {"final", true},
		"Finals":      {"final", true},
		"semifinals":  {"semifinals", true},
		"quarter":     {"quarterfinals", true},
		"round of 16": {"roundof16", true},
		"group stage": {"groupstage", true},
		"Round 3":     {"round3", false},
		"":            {"", false},
	}
	for in, want := range cases {
		got, exact := normalizeStage(in)
		if got != want.want || exact != want.exact {
			t.Errorf("normalizeStage(%q) = (%q,%v), want (%q,%v)", in, got, exact, want.want, want.exact)
		}
	}
}

func TestHeadToHeadRejectsSameClub(t *testing.T) {
	g := LoadTestGraph(t)

	if _, err := g.HeadToHead("Flamengo", "Flamengo-RJ", "", 0, 0, 5); err == nil {
		t.Error("expected an error when both sides resolve to the same club")
	}
}

func TestHeadToHeadWithNoMeetings(t *testing.T) {
	g := LoadTestGraph(t)

	// Two lower-division clubs from opposite ends of the country that never
	// met in any of the loaded competitions.
	res, err := g.HeadToHead("Flamengo", "Boca Juniors", "copa-do-brasil", 0, 0, 5)
	if err != nil {
		t.Fatalf("HeadToHead: %v", err)
	}
	if res.Summary.Played != 0 {
		t.Fatalf("expected no Copa do Brasil meetings, got %d", res.Summary.Played)
	}
	if res.Note == "" {
		t.Error("expected a note explaining the empty result")
	}
}

func TestTeamStatsEmptyScope(t *testing.T) {
	g := LoadTestGraph(t)

	res, err := g.TeamStats("Flamengo", "serie-c", 0, 0, 0, "")
	if err != nil {
		t.Fatalf("TeamStats: %v", err)
	}
	if res.Overall.Played != 0 {
		t.Errorf("Flamengo should have no Série C matches, got %d", res.Overall.Played)
	}
	if res.Note == "" {
		t.Error("expected a note explaining the empty scope")
	}
}

func TestStandingsRequiresSeason(t *testing.T) {
	g := LoadTestGraph(t)

	if _, err := g.Standings("serie-a", 0); err == nil {
		t.Error("expected standings to require a season")
	}
	if _, err := g.Standings("serie-a", 1950); err == nil {
		t.Error("expected an error for a season that is not in the data")
	}
}

func TestBracketRejectsLeague(t *testing.T) {
	g := LoadTestGraph(t)

	_, err := g.Bracket("serie-a", 2019)
	if err == nil || !strings.Contains(err.Error(), "standings") {
		t.Errorf("error = %v, want a pointer to standings", err)
	}
}

func TestAggregateStatsScopedToTeam(t *testing.T) {
	g := LoadTestGraph(t)

	res, err := g.AggregateStats(StatsScope{Team: "Flamengo", Competition: "serie-a", Season: 2019})
	if err != nil {
		t.Fatalf("AggregateStats: %v", err)
	}
	if res.Matches != 38 {
		t.Errorf("Flamengo played %d Série A matches in 2019, want 38", res.Matches)
	}
	if !strings.Contains(res.Scope, "Flamengo") {
		t.Errorf("scope should name the club: %q", res.Scope)
	}
}

func TestPlayerProfileByID(t *testing.T) {
	g := LoadTestGraph(t)

	byName, err := g.PlayerProfile("Neymar", 0)
	if err != nil {
		t.Fatalf("PlayerProfile by name: %v", err)
	}
	byID, err := g.PlayerProfile("", byName.ID)
	if err != nil {
		t.Fatalf("PlayerProfile by id: %v", err)
	}
	if byID.Name != byName.Name {
		t.Errorf("lookup by id returned %q, want %q", byID.Name, byName.Name)
	}
	if _, err := g.PlayerProfile("", 999999999); err == nil {
		t.Error("expected an error for an unknown FIFA id")
	}
	if _, err := g.PlayerProfile("", 0); err == nil {
		t.Error("expected an error when neither name nor id is given")
	}
}

func TestSearchPlayersRatingAndAgeFilters(t *testing.T) {
	g := LoadTestGraph(t)

	res, err := g.SearchPlayers(PlayerFilter{MinOverall: 88, MaxAge: 27, Limit: 50})
	if err != nil {
		t.Fatalf("SearchPlayers: %v", err)
	}
	if res.Total == 0 {
		t.Fatal("no highly-rated young players found")
	}
	for _, p := range res.Players {
		if p.Overall < 88 || p.Age > 27 {
			t.Errorf("filter leaked: %+v", p)
		}
	}
}

func TestRivalryLookupIsSymmetric(t *testing.T) {
	a, ok := RivalryFor("flamengo-rj", "fluminense-rj")
	if !ok {
		t.Fatal("Fla-Flu not found")
	}
	b, ok := RivalryFor("fluminense-rj", "flamengo-rj")
	if !ok {
		t.Fatal("Fla-Flu not found in the reverse direction")
	}
	if a.Name != b.Name || a.Name != "Fla-Flu" {
		t.Errorf("rivalry lookup is not symmetric: %q vs %q", a.Name, b.Name)
	}
	if _, ok := RivalryFor("flamengo-rj", "cuiaba-mt"); ok {
		t.Error("Flamengo vs Cuiabá is not a traditional derby")
	}
}

func TestRecordArithmetic(t *testing.T) {
	var r Record
	r.add(2, 1) // win
	r.add(0, 0) // draw
	r.add(1, 3) // loss
	r.finalize()

	if r.Played != 3 || r.Wins != 1 || r.Draws != 1 || r.Losses != 1 {
		t.Fatalf("record = %+v", r)
	}
	if r.GoalsFor != 3 || r.GoalsAgainst != 4 || r.GoalDiff != -1 {
		t.Fatalf("goals = %+v", r)
	}
	if r.Points != 4 {
		t.Fatalf("points = %d, want 4", r.Points)
	}
	if r.WinRate < 33.2 || r.WinRate > 33.4 {
		t.Fatalf("win rate = %.1f, want ~33.3", r.WinRate)
	}
}
