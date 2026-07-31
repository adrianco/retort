// soccer_test.go holds the BDD (Given / When / Then) scenarios for the query
// layer, run against the real Kaggle datasets in data/kaggle. Each scenario is
// written as a Go subtest whose steps mirror the Gherkin wording in the
// specification.
package soccer

import (
	"os"
	"path/filepath"
	"sync"
	"testing"
	"time"
)

var (
	loadOnce  sync.Once
	testStore *Store
	loadErr   error
	loadTime  time.Duration
)

// DataDir locates the dataset directory relative to the package.
func DataDir() string { return filepath.Join("..", "data", "kaggle") }

// store loads the datasets once for the whole test binary.
func store(t testing.TB) *Store {
	t.Helper()
	loadOnce.Do(func() {
		if _, err := os.Stat(DataDir()); err != nil {
			loadErr = err
			return
		}
		start := time.Now()
		testStore, loadErr = Load(DataDir())
		loadTime = time.Since(start)
	})
	if loadErr != nil {
		t.Skipf("datasets not available: %v", loadErr)
	}
	return testStore
}

// --- Feature: data loading ------------------------------------------------

func TestFeatureDataLoading(t *testing.T) {
	t.Run("Scenario: all six datasets load", func(t *testing.T) {
		// Given the data directory
		s := store(t)
		// Then every file loads without error
		if errs := s.LoadErrors(); len(errs) > 0 {
			t.Fatalf("load errors: %v", errs)
		}
		// And matches and players are available
		if len(s.Matches) < 15000 {
			t.Errorf("expected >15000 unique matches, got %d", len(s.Matches))
		}
		if len(s.Players) != 18207 {
			t.Errorf("expected 18207 players, got %d", len(s.Players))
		}
		// And every competition named in the spec is present
		want := []string{CompSerieA, CompSerieB, CompSerieC, CompCopaBrasil, CompLibertadores}
		have := map[string]bool{}
		for _, c := range s.Competitions() {
			have[c] = true
		}
		for _, c := range want {
			if !have[c] {
				t.Errorf("competition %q missing from loaded data", c)
			}
		}
	})

	t.Run("Scenario: loading is fast enough for interactive use", func(t *testing.T) {
		store(t)
		if loadTime > 5*time.Second {
			t.Errorf("load took %s, expected under 5s", loadTime)
		}
	})

	t.Run("Scenario: every match is internally consistent", func(t *testing.T) {
		s := store(t)
		for _, m := range s.Matches[:1000] {
			if m.HomeKey == "" || m.AwayKey == "" {
				t.Fatalf("match with empty team key: %+v", m)
			}
			if m.HomeGoals < 0 || m.AwayGoals < 0 {
				t.Fatalf("negative score: %s", FormatMatch(m))
			}
			if m.Date.IsZero() {
				t.Fatalf("zero date: %s", FormatMatch(m))
			}
			if len(m.Sources) == 0 {
				t.Fatalf("match without source: %s", FormatMatch(m))
			}
		}
	})
}

// --- Feature: match queries ------------------------------------------------

func TestFeatureMatchQueries(t *testing.T) {
	s := store(t)

	t.Run("Scenario: find matches between two teams", func(t *testing.T) {
		// Given the match data is loaded
		// When I search for matches between "Flamengo" and "Fluminense"
		got := s.SearchMatches(MatchFilter{Team: "Flamengo", Opponent: "Fluminense"})
		// Then I should receive a list of matches
		if len(got) < 20 {
			t.Fatalf("expected many Fla-Flu meetings, got %d", len(got))
		}
		// And each match should have date, scores and competition
		fla := CanonicalTeam("Flamengo")
		flu := CanonicalTeam("Fluminense")
		for _, m := range got {
			if !m.Involves(fla) || !m.Involves(flu) {
				t.Fatalf("match does not involve both clubs: %s", FormatMatch(m))
			}
			if m.DateString == "" || m.Competition == "" {
				t.Fatalf("incomplete match record: %+v", m)
			}
		}
		// And results are returned most recent first
		for i := 1; i < len(got); i++ {
			if got[i].Date.After(got[i-1].Date) {
				t.Fatalf("results not sorted by date descending")
			}
		}
	})

	t.Run("Scenario: filter matches by team and season", func(t *testing.T) {
		got := s.SearchMatches(MatchFilter{Team: "Palmeiras", Season: 2019, Competition: "Brasileirão"})
		if len(got) != 38 {
			t.Fatalf("expected 38 Palmeiras Série A matches in 2019, got %d", len(got))
		}
		for _, m := range got {
			if m.Season != 2019 || m.Competition != CompSerieA {
				t.Fatalf("filter leaked: %s", FormatMatch(m))
			}
		}
	})

	t.Run("Scenario: filter by date range", func(t *testing.T) {
		got := s.SearchMatches(MatchFilter{Competition: "Serie A", From: "2019-05-01", To: "2019-05-31"})
		if len(got) == 0 {
			t.Fatal("expected matches in May 2019")
		}
		for _, m := range got {
			if m.DateString < "2019-05-01" || m.DateString > "2019-05-31" {
				t.Fatalf("match outside range: %s", FormatMatch(m))
			}
		}
	})

	t.Run("Scenario: find Copa do Brasil finals", func(t *testing.T) {
		got := s.SearchMatches(MatchFilter{Competition: "Copa do Brasil", Stage: "final"})
		if len(got) < 10 {
			t.Fatalf("expected several cup finals, got %d", len(got))
		}
	})

	t.Run("Scenario: restrict a team to its home matches", func(t *testing.T) {
		key, ok := s.ResolveTeam("Corinthians")
		if !ok {
			t.Fatal("Corinthians not found")
		}
		got := s.SearchMatches(MatchFilter{Team: "Corinthians", Season: 2022, Competition: "Serie A", Venue: "home"})
		if len(got) != 19 {
			t.Fatalf("expected 19 home matches in a 20 team league, got %d", len(got))
		}
		for _, m := range got {
			if m.HomeKey != key {
				t.Fatalf("away match returned: %s", FormatMatch(m))
			}
		}
	})

	t.Run("Scenario: an unknown team yields no matches", func(t *testing.T) {
		if got := s.SearchMatches(MatchFilter{Team: "Manchester Rovers United"}); len(got) != 0 {
			t.Fatalf("expected no matches, got %d", len(got))
		}
	})

	t.Run("Scenario: simple lookups are fast", func(t *testing.T) {
		start := time.Now()
		s.SearchMatches(MatchFilter{Team: "Flamengo", Opponent: "Corinthians", Limit: 1})
		if d := time.Since(start); d > 2*time.Second {
			t.Errorf("lookup took %s, budget is 2s", d)
		}
	})
}

// --- Feature: team queries -------------------------------------------------

func TestFeatureTeamQueries(t *testing.T) {
	s := store(t)

	t.Run("Scenario: get team statistics", func(t *testing.T) {
		// When I request statistics for "Palmeiras" in season 2019
		rep, err := s.TeamStats(MatchFilter{Team: "Palmeiras", Season: 2019, Competition: "Serie A"})
		if err != nil {
			t.Fatal(err)
		}
		// Then I should receive wins, losses, draws and goals
		if rep.Overall.Matches != 38 {
			t.Fatalf("expected 38 matches, got %d", rep.Overall.Matches)
		}
		if rep.Overall.Wins+rep.Overall.Draws+rep.Overall.Losses != rep.Overall.Matches {
			t.Fatal("W+D+L does not equal matches played")
		}
		if rep.Overall.Points != rep.Overall.Wins*3+rep.Overall.Draws {
			t.Fatal("points do not follow the 3-1-0 rule")
		}
		if rep.Home.Matches+rep.Away.Matches != rep.Overall.Matches {
			t.Fatal("home and away splits do not add up")
		}
		if rep.Overall.GoalsFor != rep.Home.GoalsFor+rep.Away.GoalsFor {
			t.Fatal("goal totals do not add up")
		}
	})

	t.Run("Scenario: home record for a season", func(t *testing.T) {
		rep, err := s.TeamStats(MatchFilter{Team: "Corinthians", Season: 2022, Competition: "Serie A", Venue: "home"})
		if err != nil {
			t.Fatal(err)
		}
		if rep.Overall.Matches != 19 || rep.Away.Matches != 0 {
			t.Fatalf("venue filter not applied: %d matches, %d away", rep.Overall.Matches, rep.Away.Matches)
		}
	})

	t.Run("Scenario: compare two teams head to head", func(t *testing.T) {
		h, err := s.HeadToHead("Palmeiras", "Santos", MatchFilter{})
		if err != nil {
			t.Fatal(err)
		}
		if h.Matches != h.WinsA+h.WinsB+h.Draws {
			t.Fatal("head-to-head results do not add up")
		}
		if h.Matches < 20 {
			t.Fatalf("expected a long rivalry, got %d matches", h.Matches)
		}
		if h.FirstMeeting > h.LastMeeting {
			t.Fatal("first meeting is after the last meeting")
		}
	})

	t.Run("Scenario: head to head is symmetric", func(t *testing.T) {
		ab, err := s.HeadToHead("Flamengo", "Corinthians", MatchFilter{})
		if err != nil {
			t.Fatal(err)
		}
		ba, err := s.HeadToHead("Corinthians", "Flamengo", MatchFilter{})
		if err != nil {
			t.Fatal(err)
		}
		if ab.Matches != ba.Matches || ab.WinsA != ba.WinsB || ab.Draws != ba.Draws {
			t.Fatalf("asymmetric head-to-head: %+v vs %+v", ab, ba)
		}
	})

	t.Run("Scenario: unknown teams are reported clearly", func(t *testing.T) {
		if _, err := s.TeamStats(MatchFilter{Team: "Nowhere FC"}); err == nil {
			t.Fatal("expected an error for an unknown club")
		}
		if _, err := s.HeadToHead("Flamengo", "Flamengo-RJ", MatchFilter{}); err == nil {
			t.Fatal("expected an error when both sides are the same club")
		}
	})

	t.Run("Scenario: rank teams by home record", func(t *testing.T) {
		rows, err := s.RankTeams(MatchFilter{Competition: "Serie A", Season: 2019}, "win_rate", 10)
		if err != nil {
			t.Fatal(err)
		}
		if len(rows) != 20 {
			t.Fatalf("expected 20 clubs in the 2019 Série A, got %d", len(rows))
		}
		for i := 1; i < len(rows); i++ {
			if rows[i].WinRate > rows[i-1].WinRate {
				t.Fatal("rankings not sorted by the requested metric")
			}
		}
	})
}

// --- Feature: competition queries -----------------------------------------

func TestFeatureCompetitionQueries(t *testing.T) {
	s := store(t)

	t.Run("Scenario: who won the 2019 Brasileirao", func(t *testing.T) {
		rows, err := s.Standings("Brasileirão", 2019)
		if err != nil {
			t.Fatal(err)
		}
		if len(rows) != 20 {
			t.Fatalf("expected a 20 team table, got %d", len(rows))
		}
		// Flamengo won the 2019 Brasileirão with 90 points.
		if rows[0].Team != "Flamengo" {
			t.Errorf("expected Flamengo as champion, got %s", rows[0].Team)
		}
		if rows[0].Points != 90 {
			t.Errorf("expected 90 points, got %d", rows[0].Points)
		}
		if rows[0].Matches != 38 {
			t.Errorf("expected 38 matches played, got %d", rows[0].Matches)
		}
		for i := 1; i < len(rows); i++ {
			if rows[i].Points > rows[i-1].Points {
				t.Fatal("table is not sorted by points")
			}
			if rows[i].Position != i+1 {
				t.Fatal("positions are not sequential")
			}
		}
	})

	t.Run("Scenario: relegation zone", func(t *testing.T) {
		rows, err := s.Standings("Serie A", 2020)
		if err != nil {
			t.Fatal(err)
		}
		if len(rows) != 20 {
			t.Fatalf("expected 20 clubs, got %d", len(rows))
		}
		bottom := rows[len(rows)-4:]
		if len(bottom) != 4 {
			t.Fatal("expected four relegated clubs")
		}
		for _, r := range bottom {
			if r.Position <= 16 {
				t.Fatal("relegation slice is wrong")
			}
		}
	})

	t.Run("Scenario: standings for an unplayed season fail cleanly", func(t *testing.T) {
		if _, err := s.Standings("Serie A", 1899); err == nil {
			t.Fatal("expected an error for a season with no data")
		}
	})

	t.Run("Scenario: list competitions", func(t *testing.T) {
		comps := s.ListCompetitions()
		if len(comps) < 5 {
			t.Fatalf("expected at least five competitions, got %d", len(comps))
		}
		for _, c := range comps {
			if c.Matches == 0 || c.Teams == 0 {
				t.Fatalf("empty competition summary: %+v", c)
			}
		}
	})
}

// --- Feature: player queries ----------------------------------------------

func TestFeaturePlayerQueries(t *testing.T) {
	s := store(t)

	t.Run("Scenario: look up a player by name", func(t *testing.T) {
		got := s.SearchPlayers(PlayerFilter{Name: "Neymar", Limit: 5})
		if len(got) == 0 {
			t.Fatal("Neymar not found")
		}
		if got[0].Nationality != "Brazil" || got[0].Overall < 85 {
			t.Fatalf("unexpected profile: %s", FormatPlayer(got[0]))
		}
	})

	t.Run("Scenario: accent insensitive player search", func(t *testing.T) {
		if len(s.SearchPlayers(PlayerFilter{Name: "Coutinho"})) == 0 {
			t.Fatal("expected to find Coutinho")
		}
	})

	t.Run("Scenario: find all Brazilian players", func(t *testing.T) {
		got := s.SearchPlayers(PlayerFilter{Nationality: "Brazil"})
		if len(got) < 500 {
			t.Fatalf("expected hundreds of Brazilian players, got %d", len(got))
		}
		for i := 1; i < len(got); i++ {
			if got[i].Overall > got[i-1].Overall {
				t.Fatal("players are not sorted by rating")
			}
		}
	})

	// The FIFA 19 dataset only carries licensed Brazilian clubs, so Grêmio is
	// used here: Flamengo, Palmeiras and Corinthians are absent from it.
	t.Run("Scenario: highest rated players at a Brazilian club", func(t *testing.T) {
		got := s.SearchPlayers(PlayerFilter{Club: "Gremio", Limit: 10})
		if len(got) == 0 {
			t.Fatal("expected Gremio players in the FIFA data")
		}
		for _, p := range got {
			if !NameMatches("Gremio", p.Club) && !NameMatches("Grêmio", p.Club) {
				t.Fatalf("wrong club: %s", FormatPlayer(p))
			}
		}
	})

	t.Run("Scenario: filter players by position group", func(t *testing.T) {
		got := s.SearchPlayers(PlayerFilter{Position: "goalkeeper", Limit: 20})
		if len(got) == 0 {
			t.Fatal("expected goalkeepers")
		}
		for _, p := range got {
			if p.Position != "GK" {
				t.Fatalf("non goalkeeper returned: %s", FormatPlayer(p))
			}
		}
	})

	t.Run("Scenario: combine filters", func(t *testing.T) {
		got := s.SearchPlayers(PlayerFilter{Nationality: "Brazil", Position: "forward", MinOverall: 80, MaxAge: 30})
		if len(got) == 0 {
			t.Fatal("expected young high rated Brazilian forwards")
		}
		for _, p := range got {
			if !p.IsBrazilian() || p.Overall < 80 || p.Age > 30 {
				t.Fatalf("filter leaked: %s", FormatPlayer(p))
			}
		}
	})

	t.Run("Scenario: cross dataset join of players and clubs", func(t *testing.T) {
		squads := s.ClubSquads("Brazil", 10)
		if len(squads) == 0 {
			t.Fatal("expected Brazilian clubs with FIFA squads")
		}
		for _, sq := range squads {
			if sq.Players == 0 || sq.AvgOverall <= 0 {
				t.Fatalf("bad squad summary: %+v", sq)
			}
			// The club must also exist in the match data.
			if _, ok := s.ResolveTeam(sq.Club); !ok {
				t.Fatalf("club %q is not in the match data", sq.Club)
			}
		}
	})
}

// --- Feature: statistical analysis ----------------------------------------

func TestFeatureStatistics(t *testing.T) {
	s := store(t)

	t.Run("Scenario: average goals per match", func(t *testing.T) {
		st, err := s.Stats(MatchFilter{Competition: "Brasileirão"})
		if err != nil {
			t.Fatal(err)
		}
		if st.GoalsPerMatch < 1.5 || st.GoalsPerMatch > 4 {
			t.Fatalf("implausible goals per match: %v", st.GoalsPerMatch)
		}
		if st.HomeWins+st.AwayWins+st.Draws != st.Matches {
			t.Fatal("result counts do not add up")
		}
		if st.TotalGoals != st.HomeGoals+st.AwayGoals {
			t.Fatal("goal totals do not add up")
		}
		if st.HomeWinRate <= st.AwayWinRate {
			t.Error("expected a home advantage in the Brasileirão")
		}
	})

	t.Run("Scenario: biggest wins", func(t *testing.T) {
		got := s.BiggestWins(MatchFilter{Limit: 10})
		if len(got) != 10 {
			t.Fatalf("expected 10 matches, got %d", len(got))
		}
		for i := 1; i < len(got); i++ {
			if got[i].GoalDiff() > got[i-1].GoalDiff() {
				t.Fatal("not sorted by margin")
			}
		}
		if got[0].GoalDiff() < 5 {
			t.Fatalf("expected a heavy defeat at the top, got %s", FormatMatch(got[0]))
		}
	})

	t.Run("Scenario: aggregate queries stay within the time budget", func(t *testing.T) {
		start := time.Now()
		if _, err := s.Stats(MatchFilter{}); err != nil {
			t.Fatal(err)
		}
		if _, err := s.RankTeams(MatchFilter{}, "points", 10); err != nil {
			t.Fatal(err)
		}
		if d := time.Since(start); d > 5*time.Second {
			t.Errorf("aggregation took %s, budget is 5s", d)
		}
	})

	t.Run("Scenario: compare two seasons", func(t *testing.T) {
		a, err := s.Stats(MatchFilter{Competition: "Serie A", Season: 2018})
		if err != nil {
			t.Fatal(err)
		}
		b, err := s.Stats(MatchFilter{Competition: "Serie A", Season: 2019})
		if err != nil {
			t.Fatal(err)
		}
		if a.Matches != 380 || b.Matches != 380 {
			t.Fatalf("expected 380 matches per season, got %d and %d", a.Matches, b.Matches)
		}
	})
}

// --- Formatting -----------------------------------------------------------

func TestFormattingIncludesTheKeyFacts(t *testing.T) {
	s := store(t)
	h, err := s.HeadToHead("Flamengo", "Fluminense", MatchFilter{Limit: 3})
	if err != nil {
		t.Fatal(err)
	}
	out := FormatH2H(h)
	for _, want := range []string{"Flamengo", "Fluminense", "wins", "draws"} {
		if !contains(out, want) {
			t.Errorf("formatted head-to-head is missing %q:\n%s", want, out)
		}
	}
	m := h.Results[0]
	line := FormatMatch(m)
	if !contains(line, m.DateString) || !contains(line, m.Competition) {
		t.Errorf("match line missing date or competition: %s", line)
	}
}

func contains(haystack, needle string) bool {
	return len(haystack) >= len(needle) && (func() bool {
		for i := 0; i+len(needle) <= len(haystack); i++ {
			if haystack[i:i+len(needle)] == needle {
				return true
			}
		}
		return false
	})()
}
