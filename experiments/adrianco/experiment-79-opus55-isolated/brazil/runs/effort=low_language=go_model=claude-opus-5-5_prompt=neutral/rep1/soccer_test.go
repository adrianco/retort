package main

// BDD-style scenarios (Given / When / Then) for the Brazilian soccer MCP
// server, run against the real datasets in data/kaggle.

import (
	"bytes"
	"encoding/json"
	"strings"
	"sync"
	"testing"
	"time"
)

var (
	storeOnce sync.Once
	testStore *Store
	storeErr  error
	loadTime  time.Duration
)

// givenTheDataIsLoaded is the shared "Given the match data is loaded" step.
func givenTheDataIsLoaded(t *testing.T) *Store {
	t.Helper()
	storeOnce.Do(func() {
		start := time.Now()
		testStore, storeErr = LoadStore("data/kaggle")
		loadTime = time.Since(start)
	})
	if storeErr != nil {
		t.Fatalf("loading data: %v", storeErr)
	}
	return testStore
}

func team(t *testing.T, s *Store, name string) string {
	t.Helper()
	tm, ok := s.Reg.Find(name)
	if !ok {
		t.Fatalf("team %q not found", name)
	}
	return tm.Key
}

func call(t *testing.T, s *Store, tool string, a Args) string {
	t.Helper()
	out, err := NewServer(s).CallTool(tool, a)
	if err != nil {
		t.Fatalf("%s(%v): %v", tool, a, err)
	}
	return out
}

func mustContain(t *testing.T, out string, wants ...string) {
	t.Helper()
	for _, w := range wants {
		if !strings.Contains(out, w) {
			t.Errorf("output does not contain %q:\n%s", w, out)
		}
	}
}

// ---- Feature: data loading ----

func TestFeature_DataLoading(t *testing.T) {
	s := givenTheDataIsLoaded(t)

	t.Run("Scenario: all six CSV files are loaded completely", func(t *testing.T) {
		want := map[string]int{
			FileBrasileirao: 4180, FileCup: 1337, FileLibertadores: 1255,
			FileExtended: 10296, FileHistorical: 6886, FileFIFA: 18207,
		}
		for file, rows := range want {
			fi := s.Files[file]
			if fi == nil || fi.Rows != rows {
				t.Errorf("%s: got %+v, want %d rows", file, fi, rows)
			}
			if fi != nil && fi.Loaded == 0 {
				t.Errorf("%s: no usable rows", file)
			}
		}
		if len(s.Players) != 18207 {
			t.Errorf("players = %d, want 18207", len(s.Players))
		}
	})

	t.Run("Scenario: every match file is queryable", func(t *testing.T) {
		seen := map[string]bool{}
		for _, m := range s.Matches {
			for _, src := range m.Sources {
				seen[src] = true
			}
			if m.Date.IsZero() || m.Season == 0 || m.HomeKey == "" || m.AwayKey == "" || m.Competition == "" {
				t.Fatalf("incomplete match: %+v", m)
			}
		}
		for _, f := range []string{FileBrasileirao, FileCup, FileLibertadores, FileExtended, FileHistorical} {
			if !seen[f] {
				t.Errorf("no match sourced from %s", f)
			}
		}
	})

	t.Run("Scenario: overlapping sources are merged, not double counted", func(t *testing.T) {
		for season := 2006; season <= 2022; season++ {
			n := len(s.FindMatches(Filter{Competition: CompSerieA, Season: season}))
			if n < 378 || n > 381 {
				t.Errorf("Série A %d has %d matches, want ~380", season, n)
			}
		}
		// 2019 is covered by three files; merged matches keep all provenance.
		ms := s.FindMatches(Filter{Competition: CompSerieA, Season: 2019})
		if len(ms) != 380 {
			t.Fatalf("Série A 2019 = %d matches, want 380", len(ms))
		}
		for _, m := range ms {
			if len(m.Sources) != 3 || m.Arena == "" || m.Ext == nil {
				t.Fatalf("match not merged from all three sources: %s %v", s.matchLine(m), m.Sources)
			}
		}
	})

	t.Run("Scenario: unplayed fixtures are skipped", func(t *testing.T) {
		if s.Files[FileBrasileirao].Unplayed == 0 || s.Files[FileLibertadores].Unplayed == 0 {
			t.Errorf("expected NA / '-' scores to be counted as unplayed")
		}
	})

	t.Run("Scenario: loading is fast", func(t *testing.T) {
		if loadTime > 5*time.Second {
			t.Errorf("load took %v", loadTime)
		}
	})
}

func TestFeature_DateFormats(t *testing.T) {
	cases := map[string]string{
		"2023-09-24":          "2023-09-24",
		"29/03/2003":          "2003-03-29",
		"2012-05-19 18:30:00": "2012-05-19",
		" 2019-12-08 ":        "2019-12-08",
	}
	for in, want := range cases {
		d, ok := parseDate(in)
		if !ok || d.Format("2006-01-02") != want {
			t.Errorf("parseDate(%q) = %v, %v; want %s", in, d, ok, want)
		}
	}
	for _, bad := range []string{"NA", "", "yesterday", "32/13/2020"} {
		if _, ok := parseDate(bad); ok {
			t.Errorf("parseDate(%q) should fail", bad)
		}
	}
	for in, want := range map[string]int{"2": 2, "2.0": 2, "0": 0} {
		if g, ok := parseGoals(in); !ok || g != want {
			t.Errorf("parseGoals(%q) = %d, %v", in, g, ok)
		}
	}
	for _, bad := range []string{"NA", "-", ""} {
		if _, ok := parseGoals(bad); ok {
			t.Errorf("parseGoals(%q) should fail", bad)
		}
	}
}

// ---- Feature: team name normalisation ----

func TestFeature_TeamNameNormalisation(t *testing.T) {
	s := givenTheDataIsLoaded(t)

	t.Run("Scenario: spelling variations resolve to the same team", func(t *testing.T) {
		groups := map[string][]string{
			"Palmeiras":    {"Palmeiras", "Palmeiras-SP", "Palmeiras - SP", "palmeiras", "PALMEIRAS", "Sociedade Esportiva Palmeiras"},
			"Flamengo":     {"Flamengo", "Flamengo-RJ", "Flamengo - RJ", "flamengo rj"},
			"São Paulo":    {"São Paulo", "Sao Paulo", "Sao Paulo-SP", "São Paulo FC", "sao paulo"},
			"Grêmio":       {"Grêmio", "Gremio", "Gremio-RS", "Grêmio - RS", "Gremio RS"},
			"Corinthians":  {"Corinthians", "Corinthians-SP", "Sport Club Corinthians Paulista"},
			"Atlético-MG":  {"Atlético-MG", "Atletico-MG", "Atlético Mineiro", "Atletico Mineiro", "Atlético - MG", "Atlético Mineiro - MG"},
			"Athletico-PR": {"Athletico-PR", "Atletico-PR", "Atlético Paranaense", "Athletico Paranaense", "Athletico", "Atlético - PR"},
			"Atlético-GO":  {"Atlético-GO", "Atletico Goianiense", "Atlético - GO"},
			"América-MG":   {"América-MG", "America MG", "America-MG", "América - MG", "América FC (Minas Gerais)"},
			"Vasco":        {"Vasco", "Vasco da Gama-RJ", "Vasco Da Gama RJ", "Vasco da Gama - RJ"},
			"Sport":        {"Sport", "Sport-PE", "Sport Recife", "Sport Club do Recife"},
			"Avaí":         {"Avaí", "Avai", "Avai-SC", "Avaí - SC"},
			"Fortaleza":    {"Fortaleza", "Fortaleza-CE", "Fortaleza EC", "Fortaleza FC", "Fortaleza Esporte Clube"},
			"Bragantino":   {"Bragantino", "Red Bull Bragantino-SP", "Red Bull Bragantino"},
			"CSA":          {"CSA", "Csa-AL", "C.s.a. - AL", "CS Alagoano"},
		}
		for want, names := range groups {
			for _, n := range names {
				tm, ok := s.Reg.Find(n)
				if !ok || tm.Name != want {
					got := "<not found>"
					if ok {
						got = tm.Name
					}
					t.Errorf("Find(%q) = %s, want %s", n, got, want)
				}
			}
		}
	})

	t.Run("Scenario: different clubs with similar names stay separate", func(t *testing.T) {
		distinct := []string{"Atlético-MG", "Athletico-PR", "Atlético-GO", "América-MG", "América-RN", "Botafogo", "Botafogo-PB", "Botafogo-SP",
			"Flamengo", "Flamengo-PI", "River Plate", "River Plate-URU", "Nacional (URU)", "Nacional (PAR)", "Guarani", "Guaraní (PAR)"}
		seen := map[string]string{}
		for _, n := range distinct {
			k := team(t, s, n)
			if other, dup := seen[k]; dup {
				t.Errorf("%q and %q resolve to the same team %s", n, other, k)
			}
			seen[k] = n
		}
	})

	t.Run("Scenario: accents are preserved in display names", func(t *testing.T) {
		for _, n := range []string{"São Paulo", "Grêmio", "Avaí", "Goiás", "Ceará", "Vitória", "Criciúma", "Náutico"} {
			if got := s.TeamName(team(t, s, fold(n))); got != n {
				t.Errorf("display name for %q = %q", fold(n), got)
			}
		}
	})

	t.Run("Scenario: an unknown team is reported, not guessed", func(t *testing.T) {
		if tm, ok := s.Reg.Find("Real Madrid"); ok {
			t.Errorf("Real Madrid resolved to %s", tm.Name)
		}
		if _, err := NewServer(s).CallTool("team_stats", Args{"team": "Real Madrid"}); err == nil {
			t.Error("expected an error for an unknown team")
		}
	})
}

// ---- Feature: match queries ----

func TestFeature_MatchQueries(t *testing.T) {
	s := givenTheDataIsLoaded(t)
	fla, flu := team(t, s, "Flamengo"), team(t, s, "Fluminense")

	t.Run("Scenario: find matches between two teams", func(t *testing.T) {
		ms := s.FindMatches(Filter{Team: fla, Opponent: flu})
		if len(ms) < 30 {
			t.Fatalf("only %d Fla-Flu matches", len(ms))
		}
		for _, m := range ms {
			if !(m.HomeKey == fla && m.AwayKey == flu) && !(m.HomeKey == flu && m.AwayKey == fla) {
				t.Fatalf("wrong teams: %s", s.matchLine(m))
			}
			if m.Date.IsZero() || m.Competition == "" {
				t.Fatalf("match lacks date/competition: %+v", m)
			}
		}
		out := call(t, s, "search_matches", Args{"team": "Flamengo", "opponent": "Fluminense", "limit": 5})
		mustContain(t, out, "Flamengo vs Fluminense (Fla-Flu)", "Head-to-head in dataset", "more matches in dataset")
	})

	t.Run("Scenario: filter by season, competition, venue and date range", func(t *testing.T) {
		pal := team(t, s, "Palmeiras")
		ms := s.FindMatches(Filter{Team: pal, Season: 2019, Competition: CompSerieA})
		if len(ms) != 38 {
			t.Errorf("Palmeiras Série A 2019 = %d matches, want 38", len(ms))
		}
		if n := len(s.FindMatches(Filter{Team: pal, Season: 2019, Competition: CompSerieA, Venue: "home"})); n != 19 {
			t.Errorf("home matches = %d, want 19", n)
		}
		from, _ := parseDate("2019-05-01")
		to, _ := parseDate("31/05/2019")
		for _, m := range s.FindMatches(Filter{Team: pal, From: from, To: to}) {
			if m.Date.Before(from) || m.Date.After(to.AddDate(0, 0, 1)) {
				t.Errorf("match outside range: %s", s.matchLine(m))
			}
		}
		if len(s.FindMatches(Filter{Team: pal, From: from, To: to})) == 0 {
			t.Error("no matches in May 2019")
		}
	})

	t.Run("Scenario: a known result is returned with the right score", func(t *testing.T) {
		// novo_campeonato_brasileiro.csv, first row: 29/03/2003 Guarani 4-2 Vasco
		out := call(t, s, "search_matches", Args{"team": "Guarani", "opponent": "Vasco", "season": 2003, "venue": "home"})
		mustContain(t, out, "2003-03-29: Guarani 4-2 Vasco", "Brinco de Ouro")
		// Libertadores 2019 final
		out = call(t, s, "search_matches", Args{"competition": "Libertadores", "stage": "final", "season": 2019})
		mustContain(t, out, "2019-11-23: Flamengo 2-1 River Plate")
	})

	t.Run("Scenario: find all Copa do Brasil finals", func(t *testing.T) {
		out := call(t, s, "search_matches", Args{"competition": "Copa do Brasil", "stage": "final", "limit": 50})
		mustContain(t, out, "Cruzeiro 1-0 Corinthians", "Athletico-PR 1-0 Internacional", "Palmeiras 2-0 Grêmio")
		for _, m := range s.FindMatches(Filter{Competition: CompCup, Stage: "final"}) {
			if m.Stage != "final" {
				t.Errorf("not a final: %s", s.matchLine(m))
			}
		}
	})

	t.Run("Scenario: most recent meeting of two teams", func(t *testing.T) {
		ms := s.FindMatches(Filter{Team: fla, Opponent: team(t, s, "Corinthians")})
		last := ms[len(ms)-1]
		out := call(t, s, "head_to_head", Args{"team_a": "Flamengo", "team_b": "Corinthians"})
		mustContain(t, out, "Most recent meeting: "+last.Date.Format("2006-01-02"))
	})

	t.Run("Scenario: invalid arguments are rejected", func(t *testing.T) {
		srv := NewServer(s)
		for _, a := range []Args{
			{"team": "Flamengo", "date_from": "not a date"},
			{"team": "Flamengo", "competition": "Premier League"},
			{"team": "Flamengo", "venue": "neutral"},
			{"opponent": "Flamengo"},
			{"team": "Flamengo", "season": "twenty"},
		} {
			if _, err := srv.CallTool("search_matches", a); err == nil {
				t.Errorf("expected error for %v", a)
			}
		}
	})
}

// ---- Feature: team queries ----

func TestFeature_TeamQueries(t *testing.T) {
	s := givenTheDataIsLoaded(t)

	t.Run("Scenario: get team statistics for a season", func(t *testing.T) {
		fla := team(t, s, "Flamengo")
		r := RecordFor(fla, s.FindMatches(Filter{Team: fla, Season: 2019, Competition: CompSerieA}))
		want := Record{Played: 38, Wins: 28, Draws: 6, Losses: 4, GoalsFor: 86, GoalsAgainst: 37}
		if r != want {
			t.Errorf("Flamengo 2019 = %+v, want %+v", r, want)
		}
		if r.Wins+r.Draws+r.Losses != r.Played {
			t.Error("W+D+L != played")
		}
		out := call(t, s, "team_stats", Args{"team": "Palmeiras", "season": 2023})
		mustContain(t, out, "Wins:", "Draws:", "Losses:", "Goals For:", "Goals Against:", "Win rate:")
	})

	t.Run("Scenario: home record in a season", func(t *testing.T) {
		out := call(t, s, "team_stats", Args{"team": "Corinthians", "season": 2022, "venue": "home", "competition": "Brasileirão"})
		mustContain(t, out, "Corinthians home record (Brasileirão Série A 2022)", "- Matches: 19", "Win rate:")
	})

	t.Run("Scenario: compare two teams head-to-head", func(t *testing.T) {
		pal, san := team(t, s, "Palmeiras"), team(t, s, "Santos")
		ms := s.FindMatches(Filter{Team: pal, Opponent: san})
		rp, rs := RecordFor(pal, ms), RecordFor(san, ms)
		if rp.Wins != rs.Losses || rp.Losses != rs.Wins || rp.Draws != rs.Draws || rp.GoalsFor != rs.GoalsAgainst {
			t.Errorf("asymmetric head-to-head: %+v vs %+v", rp, rs)
		}
		out := call(t, s, "head_to_head", Args{"team_a": "Palmeiras", "team_b": "Santos-SP"})
		mustContain(t, out, "Palmeiras vs Santos", "By competition:", CompSerieA, "Recent matches:")
		if _, err := NewServer(s).CallTool("head_to_head", Args{"team_a": "Palmeiras", "team_b": "Palmeiras-SP"}); err == nil {
			t.Error("expected error when both teams are the same")
		}
	})

	t.Run("Scenario: competitions a team has played in (cross-file)", func(t *testing.T) {
		out := call(t, s, "team_profile", Args{"team": "Palmeiras"})
		mustContain(t, out, CompSerieA, CompCup, CompLibertadores, "Traditional rivals", "Corinthians (Derby Paulista)")
	})

	t.Run("Scenario: which team scored the most goals in a season", func(t *testing.T) {
		rows, err := s.Rankings(Filter{Competition: CompSerieA, Season: 2019}, "", "goals_for", 5)
		if err != nil || len(rows) != 20 {
			t.Fatalf("rankings: %v, %d rows", err, len(rows))
		}
		if s.TeamName(rows[0].Team) != "Flamengo" || rows[0].GoalsFor != 86 {
			t.Errorf("top scorers = %s (%d)", s.TeamName(rows[0].Team), rows[0].GoalsFor)
		}
	})
}

// ---- Feature: competition queries ----

func TestFeature_CompetitionQueries(t *testing.T) {
	s := givenTheDataIsLoaded(t)

	t.Run("Scenario: who won the 2019 Brasileirão", func(t *testing.T) {
		rows := s.Standings(CompSerieA, 2019)
		if len(rows) != 20 {
			t.Fatalf("%d teams", len(rows))
		}
		type line struct {
			name         string
			pts, w, d, l int
		}
		want := []line{{"Flamengo", 90, 28, 6, 4}, {"Santos", 74, 22, 8, 8}, {"Palmeiras", 74, 21, 11, 6}}
		for i, w := range want {
			r := rows[i]
			got := line{s.TeamName(r.Team), r.Points(), r.Wins, r.Draws, r.Losses}
			if got != w {
				t.Errorf("position %d = %+v, want %+v", i+1, got, w)
			}
		}
		out := call(t, s, "standings", Args{"season": 2019})
		mustContain(t, out, "1. Flamengo - 90 pts (28W, 6D, 4L)", "Champion: Flamengo")
	})

	t.Run("Scenario: which teams were relegated in 2020", func(t *testing.T) {
		out := call(t, s, "standings", Args{"season": 2020, "competition": "Serie A"})
		mustContain(t, out, "Relegated (bottom four): Vasco, Goiás, Coritiba, Botafogo")
	})

	t.Run("Scenario: champions of earlier seasons from the historical file", func(t *testing.T) {
		for season, champ := range map[int]string{2003: "Cruzeiro", 2006: "São Paulo", 2011: "Corinthians", 2015: "Corinthians", 2018: "Palmeiras", 2021: "Atlético-MG", 2022: "Palmeiras"} {
			rows := s.Standings(CompSerieA, season)
			if got := s.TeamName(rows[0].Team); got != champ {
				t.Errorf("%d champion = %s, want %s", season, got, champ)
			}
		}
	})

	t.Run("Scenario: stray mislabelled rows do not enter the table", func(t *testing.T) {
		if n := len(s.Standings(CompSerieA, 2016)); n != 20 {
			t.Errorf("2016 table has %d teams", n)
		}
	})

	t.Run("Scenario: an incomplete season is flagged", func(t *testing.T) {
		out := call(t, s, "standings", Args{"season": 2023})
		mustContain(t, out, "partial")
		if strings.Contains(out, "Champion:") {
			t.Errorf("champion declared for incomplete season:\n%s", out)
		}
	})

	t.Run("Scenario: show the 2018 Copa Libertadores bracket", func(t *testing.T) {
		out := call(t, s, "competition_bracket", Args{"competition": "Libertadores", "season": 2018})
		mustContain(t, out, "Round Of 16 (16 matches)", "Quarterfinals (8 matches)", "Semifinals (4 matches)", "Final (2 matches)", "Winner: River Plate (5-3 on aggregate)")
		out = call(t, s, "competition_bracket", Args{"competition": "Copa do Brasil", "season": 2019})
		mustContain(t, out, "Final", "Winner: Athletico-PR (3-1 on aggregate)")
	})

	t.Run("Scenario: a drawn final is not given a made-up winner", func(t *testing.T) {
		out := call(t, s, "competition_bracket", Args{"competition": "Copa do Brasil", "season": 2017})
		mustContain(t, out, "Winner: undetermined")
	})

	t.Run("Scenario: compare the 2018 and 2019 seasons", func(t *testing.T) {
		out := call(t, s, "compare_seasons", Args{"season_a": 2018, "season_b": 2019})
		mustContain(t, out, "Champion: Palmeiras (80 pts)", "Champion: Flamengo (90 pts)", "Matches: 380", "average 2.31 per match")
	})
}

// ---- Feature: statistical analysis ----

func TestFeature_StatisticalAnalysis(t *testing.T) {
	s := givenTheDataIsLoaded(t)

	t.Run("Scenario: average goals per match in the Brasileirão", func(t *testing.T) {
		ms := s.FindMatches(Filter{Competition: CompSerieA})
		sm := Summarize(ms)
		goals := 0
		for _, m := range ms {
			goals += m.HomeGoals + m.AwayGoals
		}
		if sm.Goals != goals || sm.HomeWins+sm.Draws+sm.AwayWins != sm.Matches {
			t.Errorf("inconsistent summary %+v", sm)
		}
		if avg := sm.AvgGoals(); avg < 2.2 || avg > 3.0 {
			t.Errorf("average goals %.2f out of plausible range", avg)
		}
		if hw := sm.pct(sm.HomeWins); hw < 40 || hw > 60 {
			t.Errorf("home win rate %.1f out of plausible range", hw)
		}
		out := call(t, s, "competition_stats", Args{"competition": "Brasileirão"})
		mustContain(t, out, "average", "Home win rate")
	})

	t.Run("Scenario: best home and away records", func(t *testing.T) {
		for _, venue := range []string{"home", "away"} {
			rows, err := s.Rankings(Filter{Competition: CompSerieA}, venue, "win_rate", 100)
			if err != nil || len(rows) < 10 {
				t.Fatalf("rankings: %v (%d rows)", err, len(rows))
			}
			for i := 1; i < len(rows); i++ {
				if rows[i].WinRate() > rows[i-1].WinRate() {
					t.Fatalf("%s ranking not sorted at %d", venue, i)
				}
			}
			out := call(t, s, "team_rankings", Args{"venue": venue, "competition": "Serie A", "min_matches": 100})
			mustContain(t, out, "1. "+s.TeamName(rows[0].Team))
		}
		if _, err := s.Rankings(Filter{}, "", "bogus", 1); err == nil {
			t.Error("expected error for unknown metric")
		}
	})

	t.Run("Scenario: biggest wins in the dataset", func(t *testing.T) {
		ms := s.BiggestWins(Filter{}, 10)
		if len(ms) != 10 {
			t.Fatalf("%d matches", len(ms))
		}
		margin := func(m *Match) int {
			d := m.HomeGoals - m.AwayGoals
			if d < 0 {
				d = -d
			}
			return d
		}
		best := 0
		for _, m := range s.Matches {
			best = max(best, margin(m))
		}
		if margin(ms[0]) != best {
			t.Errorf("top margin %d, want %d", margin(ms[0]), best)
		}
		for i := 1; i < len(ms); i++ {
			if margin(ms[i]) > margin(ms[i-1]) {
				t.Errorf("not sorted by margin at %d", i)
			}
		}
		mustContain(t, call(t, s, "biggest_wins", Args{"competition": "Brasileirão", "limit": 3}), "1. ", "Average goals per match")
	})

	t.Run("Scenario: derbies in a season", func(t *testing.T) {
		ms := s.Derbies(Filter{Season: 2023})
		if len(ms) == 0 {
			t.Fatal("no derbies in 2023")
		}
		for _, m := range ms {
			if m.Season != 2023 || s.DerbyName(m.HomeKey, m.AwayKey) == "" {
				t.Errorf("not a 2023 derby: %s", s.matchLine(m))
			}
		}
		mustContain(t, call(t, s, "derbies", Args{"season": 2023}), "[Fla-Flu]", "[Grenal]")
	})

	t.Run("Scenario: extended statistics come from BR-Football-Dataset", func(t *testing.T) {
		out := call(t, s, "team_stats", Args{"team": "Flamengo", "season": 2022, "competition": "Serie A"})
		mustContain(t, out, "corners per match", "shots per match")
	})
}

// ---- Feature: player queries ----

func TestFeature_PlayerQueries(t *testing.T) {
	s := givenTheDataIsLoaded(t)

	t.Run("Scenario: find all Brazilian players, best first", func(t *testing.T) {
		ps := s.SearchPlayers(PlayerFilter{Nationality: "Brazilian"})
		if len(ps) != 827 {
			t.Errorf("%d Brazilian players, want 827", len(ps))
		}
		if ps[0].Name != "Neymar Jr" || ps[0].Overall != 92 || ps[0].Club != "Paris Saint-Germain" || ps[0].Position != "LW" {
			t.Errorf("top Brazilian = %+v", ps[0])
		}
		for i, p := range ps {
			if p.Nationality != "Brazil" || (i > 0 && p.Overall > ps[i-1].Overall) {
				t.Fatalf("bad row %d: %+v", i, p)
			}
		}
		out := call(t, s, "search_players", Args{"nationality": "Brazil", "limit": 3})
		mustContain(t, out, "1. Neymar Jr - Overall: 92", "Position: LW", "Club: Paris Saint-Germain", "more players in dataset")
	})

	t.Run("Scenario: search a player by name, ignoring accents", func(t *testing.T) {
		out := call(t, s, "player_details", Args{"name": "neymar"})
		mustContain(t, out, "Neymar Jr", "Nationality: Brazil", "Overall: 92", "Dribbling 96", "Jersey: 10")
		if ps := s.SearchPlayers(PlayerFilter{Name: "Gabriel Jesus"}); len(ps) != 1 || ps[0].Club != "Manchester City" {
			t.Errorf("Gabriel Jesus: %+v", ps)
		}
		// "Gabriel Barbosa" is not in the FIFA data under that name.
		out = call(t, s, "player_details", Args{"name": "Gabriel Barbosa"})
		mustContain(t, out, "No player with that exact name", "Closest matches", "Gabriel Jesus")
	})

	t.Run("Scenario: players of a Brazilian club", func(t *testing.T) {
		ps := s.SearchPlayers(PlayerFilter{Club: "Gremio"})
		if len(ps) != 20 {
			t.Fatalf("%d Grêmio players", len(ps))
		}
		for _, p := range ps {
			if p.Club != "Grêmio" {
				t.Errorf("wrong club: %+v", p)
			}
		}
		// exact club match: Santos must not include Santos Laguna
		for _, p := range s.SearchPlayers(PlayerFilter{Club: "Santos"}) {
			if p.Club != "Santos" {
				t.Errorf("Santos search returned %s (%s)", p.Name, p.Club)
			}
		}
		// foreign clubs are matched by substring
		if ps := s.SearchPlayers(PlayerFilter{Club: "Barcelona", Nationality: "Brazil"}); len(ps) == 0 || ps[0].Name != "Coutinho" {
			t.Errorf("Brazilian players at Barcelona: %+v", ps)
		}
	})

	t.Run("Scenario: forwards from a club", func(t *testing.T) {
		ps := s.SearchPlayers(PlayerFilter{Club: "Santos", Position: "forwards"})
		if len(ps) == 0 {
			t.Fatal("no forwards")
		}
		fw := positionSet("forward")
		for _, p := range ps {
			if !fw[p.Position] {
				t.Errorf("%s is %s, not a forward", p.Name, p.Position)
			}
		}
		if ps := s.SearchPlayers(PlayerFilter{Nationality: "Brazil", Position: "GK", MinOverall: 85}); len(ps) != 2 || ps[0].Name != "Ederson" || ps[1].Name != "Alisson" {
			t.Errorf("top Brazilian goalkeepers: %+v", ps)
		}
	})

	t.Run("Scenario: a club missing from the FIFA data is explained", func(t *testing.T) {
		out := call(t, s, "search_players", Args{"club": "Flamengo"})
		mustContain(t, out, "0 found", "no club matching", "Santos")
	})

	t.Run("Scenario: Brazilian players at Brazilian clubs", func(t *testing.T) {
		out := call(t, s, "players_by_club", Args{"nationality": "Brazil", "brazilian_clubs_only": true})
		mustContain(t, out, "Grêmio: 20 players (avg rating:", "Santos:", "Cruzeiro:")
		if strings.Contains(out, "Boavista FC") || strings.Contains(out, "Paris") {
			t.Errorf("foreign club listed:\n%s", out)
		}
	})

	t.Run("Scenario: cross-file query joins a player's club with match data", func(t *testing.T) {
		out := call(t, s, "team_profile", Args{"team": "Grêmio"})
		mustContain(t, out, "FIFA dataset squad (Grêmio, 20 players", CompLibertadores, "Internacional (Grenal)")
		ps := s.SearchPlayers(PlayerFilter{Club: "Atlético Mineiro"})
		if len(ps) == 0 || ps[0].ClubKey != team(t, s, "Atlético-MG") {
			t.Errorf("Atlético Mineiro players are not linked to Atlético-MG")
		}
		mustContain(t, call(t, s, "player_details", Args{"id": ps[0].ID}), "Club in match data: Atlético-MG")
	})
}

// ---- Feature: MCP protocol ----

func rpc(t *testing.T, srv *Server, msg string) map[string]any {
	t.Helper()
	resp := srv.HandleMessage([]byte(msg))
	if resp == nil {
		return nil
	}
	data, err := json.Marshal(resp)
	if err != nil {
		t.Fatal(err)
	}
	var out map[string]any
	if err := json.Unmarshal(data, &out); err != nil {
		t.Fatal(err)
	}
	return out
}

func TestFeature_MCPProtocol(t *testing.T) {
	s := givenTheDataIsLoaded(t)
	srv := NewServer(s)

	t.Run("Scenario: initialize handshake", func(t *testing.T) {
		r := rpc(t, srv, `{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"0"}}}`)
		res := r["result"].(map[string]any)
		if res["protocolVersion"] != "2025-06-18" {
			t.Errorf("protocolVersion = %v", res["protocolVersion"])
		}
		if res["serverInfo"].(map[string]any)["name"] != serverName {
			t.Errorf("serverInfo = %v", res["serverInfo"])
		}
		if _, ok := res["capabilities"].(map[string]any)["tools"]; !ok {
			t.Error("tools capability missing")
		}
		r = rpc(t, srv, `{"jsonrpc":"2.0","id":2,"method":"initialize","params":{"protocolVersion":"1999-01-01"}}`)
		if v := r["result"].(map[string]any)["protocolVersion"]; v != defaultProtocolVersion {
			t.Errorf("fallback protocolVersion = %v", v)
		}
	})

	t.Run("Scenario: notifications get no response", func(t *testing.T) {
		if r := rpc(t, srv, `{"jsonrpc":"2.0","method":"notifications/initialized"}`); r != nil {
			t.Errorf("unexpected response %v", r)
		}
	})

	t.Run("Scenario: tools/list describes every tool with a schema", func(t *testing.T) {
		r := rpc(t, srv, `{"jsonrpc":"2.0","id":"abc","method":"tools/list"}`)
		if r["id"] != "abc" {
			t.Errorf("id not echoed: %v", r["id"])
		}
		tools := r["result"].(map[string]any)["tools"].([]any)
		if len(tools) != len(srv.tools) || len(tools) < 12 {
			t.Fatalf("%d tools listed", len(tools))
		}
		names := map[string]bool{}
		for _, raw := range tools {
			tool := raw.(map[string]any)
			name := tool["name"].(string)
			if names[name] {
				t.Errorf("duplicate tool %s", name)
			}
			names[name] = true
			sch := tool["inputSchema"].(map[string]any)
			if tool["description"] == "" || sch["type"] != "object" {
				t.Errorf("tool %s badly described", name)
			}
			props := sch["properties"].(map[string]any)
			if req, ok := sch["required"].([]any); ok {
				for _, k := range req {
					if _, ok := props[k.(string)]; !ok {
						t.Errorf("tool %s requires undeclared property %v", name, k)
					}
				}
			}
		}
	})

	t.Run("Scenario: tools/call returns text content", func(t *testing.T) {
		r := rpc(t, srv, `{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"standings","arguments":{"season":2019,"limit":1}}}`)
		res := r["result"].(map[string]any)
		if res["isError"] != false {
			t.Errorf("isError = %v", res["isError"])
		}
		c := res["content"].([]any)[0].(map[string]any)
		if c["type"] != "text" || !strings.Contains(c["text"].(string), "1. Flamengo - 90 pts") {
			t.Errorf("content = %v", c)
		}
	})

	t.Run("Scenario: tool failures are reported as tool errors", func(t *testing.T) {
		r := rpc(t, srv, `{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"team_stats","arguments":{"team":"Nonexistent United"}}}`)
		res := r["result"].(map[string]any)
		if res["isError"] != true || !strings.Contains(res["content"].([]any)[0].(map[string]any)["text"].(string), "not found") {
			t.Errorf("result = %v", res)
		}
	})

	t.Run("Scenario: protocol errors use JSON-RPC error codes", func(t *testing.T) {
		cases := map[string]float64{
			`{"jsonrpc":"2.0","id":5,"method":"no/such"}`:                                -32601,
			`{"jsonrpc":"2.0","id":6,"method":"tools/call","params":{"name":"no_tool"}}`: -32602,
			`{not json`: -32700,
			`{"jsonrpc":"1.0","id":7,"method":"ping"}`: -32600,
		}
		for msg, code := range cases {
			r := rpc(t, srv, msg)
			e, ok := r["error"].(map[string]any)
			if !ok || e["code"] != code {
				t.Errorf("%s -> %v, want code %v", msg, r, code)
			}
		}
		if r := rpc(t, srv, `{"jsonrpc":"2.0","id":8,"method":"ping"}`); r["error"] != nil || r["result"] == nil {
			t.Errorf("ping -> %v", r)
		}
	})

	t.Run("Scenario: a stdio session is served line by line", func(t *testing.T) {
		in := strings.Join([]string{
			`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05"}}`,
			`{"jsonrpc":"2.0","method":"notifications/initialized"}`,
			``,
			`{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"dataset_info","arguments":{}}}`,
		}, "\n") // no trailing newline on the last request
		var out bytes.Buffer
		if err := srv.Serve(strings.NewReader(in), &out); err != nil {
			t.Fatal(err)
		}
		lines := strings.Split(strings.TrimSpace(out.String()), "\n")
		if len(lines) != 2 {
			t.Fatalf("%d response lines, want 2:\n%s", len(lines), out.String())
		}
		for i, l := range lines {
			var r map[string]any
			if err := json.Unmarshal([]byte(l), &r); err != nil || r["id"] != float64(i+1) {
				t.Errorf("line %d: %v %s", i, err, l)
			}
		}
		mustContain(t, lines[1], "fifa_data.csv", "novo_campeonato_brasileiro.csv")
	})
}

// ---- Feature: the sample questions of the specification ----

func TestFeature_SampleQuestions(t *testing.T) {
	s := givenTheDataIsLoaded(t)
	srv := NewServer(s)
	questions := []struct {
		q, tool string
		args    Args
		want    []string
		agg     bool // aggregate query: 5s budget instead of 2s
	}{
		{"Show me all Flamengo vs Fluminense matches", "search_matches", Args{"team": "Flamengo", "opponent": "Fluminense", "limit": 100}, []string{"Fla-Flu", "Head-to-head"}, false},
		{"What matches did Palmeiras play in 2023?", "search_matches", Args{"team": "Palmeiras", "season": 2023, "limit": 100}, []string{"Palmeiras — 2023", "2023-"}, false},
		{"Find all Copa do Brasil finals", "search_matches", Args{"competition": "Copa do Brasil", "stage": "final"}, []string{"final"}, false},
		{"What is Corinthians' home record in 2022?", "team_stats", Args{"team": "Corinthians", "season": 2022, "venue": "home"}, []string{"Corinthians home record", "Win rate"}, false},
		{"Which team scored the most goals in Serie A 2023?", "team_rankings", Args{"metric": "goals_for", "competition": "Serie A", "season": 2023}, []string{"1. "}, true},
		{"Compare Palmeiras and Santos head-to-head", "head_to_head", Args{"team_a": "Palmeiras", "team_b": "Santos"}, []string{"Clássico da Saudade", "wins"}, false},
		{"Find all Brazilian players in the dataset", "search_players", Args{"nationality": "Brazil"}, []string{"827 found", "Neymar Jr"}, false},
		{"Who are the highest-rated players at Flamengo?", "search_players", Args{"club": "Flamengo"}, []string{"no club matching"}, false},
		{"Show me all forwards from São Paulo FC", "search_players", Args{"club": "São Paulo FC", "position": "forwards"}, []string{"no club matching"}, false},
		{"Who are the highest-rated players at Cruzeiro?", "search_players", Args{"club": "Cruzeiro", "limit": 5}, []string{"20 found", "Club: Cruzeiro"}, false},
		{"Who won the 2019 Brasileirão?", "standings", Args{"season": 2019}, []string{"Champion: Flamengo"}, true},
		{"Show the 2018 Copa Libertadores bracket", "competition_bracket", Args{"competition": "Libertadores", "season": 2018}, []string{"Semifinals", "Winner: River Plate"}, true},
		{"Which teams were relegated in 2020?", "standings", Args{"season": 2020}, []string{"Relegated (bottom four)"}, true},
		{"What's the average goals per match in the Brasileirão?", "competition_stats", Args{"competition": "Brasileirão"}, []string{"per match"}, true},
		{"Which team has the best away record?", "team_rankings", Args{"venue": "away", "competition": "Brasileirão"}, []string{"away matches", "1. "}, true},
		{"Show me the biggest wins in the dataset", "biggest_wins", Args{}, []string{"Biggest victories", "1. "}, true},
		{"When did Flamengo last play Corinthians?", "search_matches", Args{"team": "Flamengo", "opponent": "Corinthians", "limit": 1}, []string{"Flamengo vs Corinthians", "- 20"}, false},
		{"Who is Gabriel Barbosa?", "player_details", Args{"name": "Gabriel Barbosa"}, []string{"Closest matches"}, false},
		{"Who is Neymar?", "player_details", Args{"name": "Neymar"}, []string{"Paris Saint-Germain"}, false},
		{"Which players play for Grêmio?", "search_players", Args{"club": "Grêmio", "limit": 30}, []string{"20 found"}, false},
		{"Show me all derbies in 2023", "derbies", Args{"season": 2023}, []string{"traditional rivals", "["}, true},
		{"What competitions has Palmeiras played in?", "team_profile", Args{"team": "Palmeiras"}, []string{"Competitions played", CompLibertadores}, false},
		{"Which team has the best home record?", "team_rankings", Args{"venue": "home"}, []string{"home matches", "1. "}, true},
		{"Who are the top Brazilian players?", "search_players", Args{"nationality": "Brazilian", "limit": 10}, []string{"1. Neymar Jr", "10. "}, false},
		{"Compare the 2018 and 2019 seasons", "compare_seasons", Args{"season_a": 2018, "season_b": 2019}, []string{"2018:", "2019:", "Champion"}, true},
		{"Brazilian players at Brazilian clubs", "players_by_club", Args{"nationality": "Brazil", "brazilian_clubs_only": true}, []string{"avg rating"}, true},
		{"What data is available?", "dataset_info", Args{}, []string{"Unique matches", CompSerieB}, true},
	}
	if len(questions) < 20 {
		t.Fatalf("only %d sample questions", len(questions))
	}
	for _, q := range questions {
		t.Run(q.q, func(t *testing.T) {
			start := time.Now()
			out, err := srv.CallTool(q.tool, q.args)
			elapsed := time.Since(start)
			if err != nil {
				t.Fatalf("%s: %v", q.tool, err)
			}
			if strings.TrimSpace(out) == "" {
				t.Fatal("empty answer")
			}
			mustContain(t, out, q.want...)
			budget := 2 * time.Second
			if q.agg {
				budget = 5 * time.Second
			}
			if elapsed > budget {
				t.Errorf("took %v, budget %v", elapsed, budget)
			}
		})
	}
}
