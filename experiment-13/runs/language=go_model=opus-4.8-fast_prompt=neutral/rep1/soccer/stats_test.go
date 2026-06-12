package soccer

import "testing"

// mk builds a minimal match for tests.
func mk(home, away string, hg, ag int) Match {
	return Match{
		Competition: CompSerieA,
		HomeTeam:    home, AwayTeam: away,
		HomeKey: NormalizeName(home), AwayKey: NormalizeName(away),
		HomeGoals: hg, AwayGoals: ag,
	}
}

func sampleMatches() []Match {
	// a: 2 wins, 1 draw, 1 loss; gf=2+3+1+0=6, ga=0+1+1+2=4
	return []Match{
		mk("A", "B", 2, 0), // A win (home)
		mk("C", "A", 1, 3), // A win (away)
		mk("A", "C", 1, 1), // draw
		mk("B", "A", 2, 0), // A loss (away)
	}
}

func TestTeamRecord(t *testing.T) {
	ms := sampleMatches()
	r := TeamRecord(ms, "a", "A", VenueAll)
	if r.Matches != 4 || r.Wins != 2 || r.Draws != 1 || r.Losses != 1 {
		t.Errorf("record = %+v", r)
	}
	if r.GoalsFor != 6 || r.GoalsAgainst != 4 {
		t.Errorf("goals = %d-%d, want 6-4", r.GoalsFor, r.GoalsAgainst)
	}
	if r.Points() != 7 {
		t.Errorf("points = %d, want 7", r.Points())
	}
	if r.GoalDiff() != 2 {
		t.Errorf("gd = %d, want 2", r.GoalDiff())
	}

	home := TeamRecord(ms, "a", "A", VenueHome)
	if home.Matches != 2 || home.Wins != 1 || home.Draws != 1 {
		t.Errorf("home record = %+v", home)
	}
	away := TeamRecord(ms, "a", "A", VenueAway)
	if away.Matches != 2 || away.Wins != 1 || away.Losses != 1 {
		t.Errorf("away record = %+v", away)
	}
}

func TestHeadToHead(t *testing.T) {
	ms := sampleMatches()
	h := HeadToHead(ms, "a", "c", "A", "C")
	// A vs C: C-A 1-3 (A win), A-C 1-1 (draw)
	if h.Matches != 2 || h.WinsA != 1 || h.WinsB != 0 || h.Draws != 1 {
		t.Errorf("h2h = %+v", h)
	}
	if h.GoalsA != 4 || h.GoalsB != 2 {
		t.Errorf("h2h goals = %d-%d, want 4-2", h.GoalsA, h.GoalsB)
	}
}

func TestStandings(t *testing.T) {
	ms := sampleMatches()
	disp := func(k string) string { return k }
	table := Standings(ms, disp)
	if len(table) != 3 {
		t.Fatalf("want 3 teams, got %d", len(table))
	}
	// A: 7 pts. B: B-A 2-0 win + A-B 2-0 loss => 1W1L = 3pts. C: A 1-1 draw, C-A loss => 1pt.
	if table[0].Key != "a" || table[0].Points() != 7 {
		t.Errorf("leader = %+v", table[0])
	}
}

func TestSummarizeAndBiggestWins(t *testing.T) {
	ms := sampleMatches()
	c := Summarize(ms)
	if c.Matches != 4 {
		t.Errorf("matches = %d", c.Matches)
	}
	if c.TotalGoals != 2+1+3+1+1+2 {
		t.Errorf("total goals = %d, want 10", c.TotalGoals)
	}
	if got := c.GoalsPerMatch(); got != 2.5 {
		t.Errorf("gpm = %v, want 2.5", got)
	}
	top := BiggestWins(ms, 1)
	if len(top) != 1 || top[0].Margin() != 2 {
		t.Errorf("biggest = %+v", top)
	}
}

func TestCleanBySource(t *testing.T) {
	// Same fixture in two sources with different counts for one season.
	matches := []Match{
		{Competition: CompSerieA, Season: 2019, Source: "primary.csv"},
		{Competition: CompSerieA, Season: 2019, Source: "primary.csv"},
		{Competition: CompSerieA, Season: 2019, Source: "secondary.csv"},
		// A season only the secondary source covers.
		{Competition: CompSerieA, Season: 2023, Source: "secondary.csv"},
	}
	out := CleanBySource(matches)
	// 2019 -> primary (2 rows); 2023 -> secondary (1 row) => 3 total.
	if len(out) != 3 {
		t.Fatalf("want 3 matches, got %d", len(out))
	}
	for _, m := range out {
		if m.Season == 2019 && m.Source != "primary.csv" {
			t.Errorf("2019 should come from primary, got %s", m.Source)
		}
	}
}
