// BDD-style (Given/When/Then) tests run against the real CSV files in data/kaggle.
package main

import (
	"bytes"
	"encoding/json"
	"strings"
	"sync"
	"testing"
	"time"
)

var (
	loadOnce sync.Once
	testDB   *DB
	loadErr  error
)

// givenData is the shared "Given the match and player data is loaded" step.
func givenData(t *testing.T) *DB {
	t.Helper()
	loadOnce.Do(func() {
		var dir string
		if dir, loadErr = FindDataDir(""); loadErr == nil {
			testDB, loadErr = LoadDB(dir)
		}
	})
	if loadErr != nil {
		t.Fatalf("loading data: %v", loadErr)
	}
	return testDB
}

func call(t *testing.T, db *DB, tool string, args Args) string {
	t.Helper()
	out, err := CallTool(db, tool, args)
	if err != nil {
		t.Fatalf("%s(%v): %v", tool, args, err)
	}
	return out
}

func mustContain(t *testing.T, out string, wants ...string) {
	t.Helper()
	for _, w := range wants {
		if !strings.Contains(out, w) {
			t.Errorf("expected output to contain %q, got:\n%s", w, out)
		}
	}
}

// ---------- Feature: data loading ----------

func TestFeature_DataLoading(t *testing.T) {
	db := givenData(t)
	t.Run("Scenario: all six CSV files are loaded with the documented row counts", func(t *testing.T) {
		want := map[string]int{SrcBrasileirao: 4180, SrcCup: 1337, SrcLibertadores: 1255, SrcExtended: 10296, SrcHistorical: 6886, "fifa": 18207}
		for src, n := range want {
			if db.Counts[src] != n {
				t.Errorf("%s: loaded %d rows, want %d", src, db.Counts[src], n)
			}
		}
		if len(db.Players) != 18207 {
			t.Errorf("players = %d", len(db.Players))
		}
	})
	t.Run("Scenario: every file is queryable on its own", func(t *testing.T) {
		for _, ds := range []string{SrcBrasileirao, SrcCup, SrcLibertadores, SrcExtended, SrcHistorical} {
			ms, err := db.FindMatches(MatchFilter{Team: "Flamengo", Dataset: ds})
			if err != nil || len(ms) == 0 {
				t.Errorf("dataset %s: %d Flamengo matches, err %v", ds, len(ms), err)
			}
			for _, m := range ms {
				if m.Source != ds {
					t.Fatalf("dataset filter leaked %s into %s", m.Source, ds)
				}
			}
		}
	})
	t.Run("Scenario: unplayed fixtures are kept but not counted as results", func(t *testing.T) {
		ms, _ := db.FindMatches(MatchFilter{Dataset: SrcBrasileirao, Season: 2022, Round: "38"})
		if len(ms) != 10 {
			t.Fatalf("round 38 of 2022: %d matches, want 10", len(ms))
		}
		for _, m := range ms {
			if m.Played {
				t.Errorf("match with NA goals reported as played: %s", formatMatch(m))
			}
		}
	})
	t.Run("Scenario: UTF-8 names survive loading", func(t *testing.T) {
		for _, k := range []string{"gremio", "sao paulo", "avai", "goias"} {
			if db.Teams[k] == nil {
				t.Fatalf("team %q missing", k)
			}
		}
		if n := db.Teams["gremio"].Name; n != "Grêmio" {
			t.Errorf("display name = %q, want Grêmio", n)
		}
		if n := db.Teams["sao paulo"].Name; n != "São Paulo" {
			t.Errorf("display name = %q, want São Paulo", n)
		}
	})
}

// ---------- Feature: normalization ----------

func TestFeature_TeamNameNormalization(t *testing.T) {
	db := givenData(t)
	groups := map[string][]string{
		"palmeiras":   {"Palmeiras", "Palmeiras-SP", "Palmeiras - SP", "palmeiras", "  PALMEIRAS  ", "Sociedade Esportiva Palmeiras"},
		"flamengo":    {"Flamengo", "Flamengo-RJ", "Flamengo - RJ", "Flamengo RJ"},
		"sao paulo":   {"São Paulo", "Sao Paulo", "Sao Paulo-SP", "São Paulo FC", "sao paulo fc"},
		"gremio":      {"Grêmio", "Gremio", "Gremio-RS", "Grêmio - RS", "Gremio RS"},
		"atletico":    {"Atlético-MG", "Atletico-MG", "Atlético Mineiro", "Atletico Mineiro", "Atlético - MG"},
		"atletico-go": {"Atlético-GO", "Atletico Goianiense", "Atlético - GO"},
		"athletico":   {"Athletico-PR", "Atletico-PR", "Atlético Paranaense", "Athletico Paranaense", "Athletico"},
		"corinthians": {"Corinthians", "Corinthians-SP", "Sport Club Corinthians Paulista"},
		"vasco":       {"Vasco", "Vasco da Gama-RJ", "Vasco Da Gama RJ", "Vasco da Gama - RJ"},
		"america":     {"América-MG", "America MG", "America - MG"},
		"america-rn":  {"América-RN", "America RN", "America FC Natal"},
		"bahia":       {"Bahia", "EC Bahia", "Bahia-BA"},
		"fortaleza":   {"Fortaleza", "Fortaleza EC", "Fortaleza Esporte Clube", "Fortaleza-CE"},
		"sport":       {"Sport", "Sport-PE", "Sport Recife"},
		"bragantino":  {"Red Bull Bragantino-SP", "Bragantino", "Bragantino - SP"},
	}
	for key, names := range groups {
		for _, n := range names {
			ts := db.ResolveTeam(n)
			if len(ts) != 1 || ts[0].Key != key {
				got := "nothing"
				if len(ts) > 0 {
					got = ts[0].Key
				}
				t.Errorf("ResolveTeam(%q) = %s (%d teams), want %s", n, got, len(ts), key)
			}
		}
	}
	t.Run("Scenario: clubs sharing a name in different states stay separate", func(t *testing.T) {
		pairs := [][2]string{{"Flamengo - RJ", "Flamengo - PI"}, {"Santos-SP", "Santos AP"}, {"Atlético-MG", "Atlético-GO"}, {"Botafogo-RJ", "Botafogo PB"}, {"Nacional (URU)", "Nacional (PAR)"}}
		for _, p := range pairs {
			a, b := db.ResolveTeam(p[0]), db.ResolveTeam(p[1])
			if len(a) != 1 || len(b) != 1 || a[0] == b[0] {
				t.Errorf("%q and %q should resolve to two distinct teams", p[0], p[1])
			}
		}
	})
	t.Run("Scenario: unknown team gives a clear error", func(t *testing.T) {
		if _, err := db.FindMatches(MatchFilter{Team: "Real Madrid CF Zzz"}); err == nil {
			t.Error("expected an error for an unknown team")
		}
	})
}

func TestFeature_DateFormats(t *testing.T) {
	cases := map[string]string{
		"2023-09-24": "2023-09-24", "29/03/2003": "2003-03-29", "2012-05-19 18:30:00": "2012-05-19", " 2019-12-08 ": "2019-12-08",
	}
	for in, want := range cases {
		d, ok := parseDate(in)
		if !ok || d.Format("2006-01-02") != want {
			t.Errorf("parseDate(%q) = %v, %v; want %s", in, d, ok, want)
		}
	}
	for _, bad := range []string{"", "NA", "31/31/2020", "yesterday"} {
		if _, ok := parseDate(bad); ok {
			t.Errorf("parseDate(%q) should fail", bad)
		}
	}
	db := givenData(t)
	iso, _ := db.FindMatches(MatchFilter{Team: "Flamengo", From: "2019-01-01", To: "2019-12-31"})
	br, _ := db.FindMatches(MatchFilter{Team: "Flamengo", From: "01/01/2019", To: "31/12/2019"})
	if len(iso) == 0 || len(iso) != len(br) {
		t.Errorf("ISO range gave %d matches, Brazilian-format range %d", len(iso), len(br))
	}
	for _, m := range iso {
		if m.Date.Year() != 2019 {
			t.Errorf("match outside date range: %s", formatMatch(m))
		}
	}
	if _, err := db.FindMatches(MatchFilter{From: "not a date"}); err == nil {
		t.Error("expected error for bad date")
	}
}

// ---------- Feature: match queries ----------

func TestFeature_MatchQueries(t *testing.T) {
	db := givenData(t)
	t.Run("Scenario: Find matches between two teams", func(t *testing.T) {
		// When I search for matches between "Flamengo" and "Fluminense"
		ms, err := db.FindMatches(MatchFilter{Team: "Flamengo", Opponent: "Fluminense"})
		if err != nil {
			t.Fatal(err)
		}
		// Then I should receive a list of matches
		if len(ms) < 20 {
			t.Fatalf("only %d Fla-Flu matches", len(ms))
		}
		// And each match should have date, scores and competition
		for _, m := range ms {
			keys := map[string]bool{m.Home.Key: true, m.Away.Key: true}
			if !keys["flamengo"] || !keys["fluminense"] {
				t.Fatalf("wrong teams: %s", formatMatch(m))
			}
			if !m.HasDate || m.Competition == "" || m.Season == 0 {
				t.Errorf("incomplete match: %+v", m)
			}
		}
		out := call(t, db, "find_matches", Args{"team": "Flamengo", "opponent": "Fluminense", "limit": 5.0})
		mustContain(t, out, "Flamengo vs Fluminense", "Head-to-head in dataset: Flamengo", "more matches in dataset")
	})
	t.Run("Scenario: matches are not double counted across files", func(t *testing.T) {
		ms, _ := db.FindMatches(MatchFilter{Competition: "Brasileirão", Season: 2015})
		if len(ms) != 380 {
			t.Errorf("2015 Serie A has %d matches in the default view, want 380", len(ms))
		}
	})
	t.Run("Scenario: filter by venue, season and competition", func(t *testing.T) {
		ms, _ := db.FindMatches(MatchFilter{Team: "Palmeiras", Venue: "home", Season: 2019, Competition: "Serie A"})
		if len(ms) != 19 {
			t.Fatalf("Palmeiras 2019 home league matches = %d, want 19", len(ms))
		}
		for _, m := range ms {
			if m.Home.Key != "palmeiras" {
				t.Errorf("not a home match: %s", formatMatch(m))
			}
		}
		away, _ := db.FindMatches(MatchFilter{Team: "Palmeiras", Venue: "away", Season: 2019, Competition: "Serie A"})
		if len(away) != 19 {
			t.Errorf("away = %d", len(away))
		}
	})
	t.Run("Scenario: Copa do Brasil finals are found", func(t *testing.T) {
		ms, _ := db.FindMatches(MatchFilter{Competition: "Copa do Brasil", Stage: "final"})
		seasons := map[int]int{}
		for _, m := range ms {
			seasons[m.Season]++
		}
		for y := 2012; y <= 2023; y++ {
			if seasons[y] != 2 {
				t.Errorf("season %d: %d final legs, want 2", y, seasons[y])
			}
		}
		out := call(t, db, "find_matches", Args{"competition": "Copa do Brasil", "stage": "finals", "season": 2019.0})
		mustContain(t, out, "Athletico-PR 1-0 Internacional", "Internacional 1-2 Athletico-PR")
	})
	t.Run("Scenario: extended statistics are exposed", func(t *testing.T) {
		out := call(t, db, "find_matches", Args{"team": "Sao Paulo", "opponent": "Flamengo", "dataset": "extended", "date_from": "2023-09-24", "date_to": "2023-09-24"})
		mustContain(t, out, "2023-09-24: São Paulo 1-1 Flamengo", "corners 2-4", "shots 8-13")
	})
	t.Run("Scenario: historical file carries the stadium", func(t *testing.T) {
		out := call(t, db, "find_matches", Args{"team": "Guarani", "opponent": "Vasco", "season": 2003.0, "venue": "home"})
		mustContain(t, out, "2003-03-29: Guarani 4-2 Vasco da Gama", "Brinco de Ouro")
	})
}

// ---------- Feature: team queries ----------

func TestFeature_TeamQueries(t *testing.T) {
	db := givenData(t)
	t.Run("Scenario: Get team statistics", func(t *testing.T) {
		// When I request statistics for "Palmeiras" in season "2023"
		r, byComp, _, err := db.TeamRecord(MatchFilter{Team: "Palmeiras", Season: 2023})
		if err != nil {
			t.Fatal(err)
		}
		// Then I should receive wins, losses, draws and goals
		if r.Played == 0 || r.Wins+r.Draws+r.Losses != r.Played || r.GoalsFor == 0 {
			t.Errorf("bad record %+v", r)
		}
		sum := 0
		for _, c := range byComp {
			sum += c.Played
		}
		if sum != r.Played {
			t.Errorf("per-competition breakdown sums to %d, total %d", sum, r.Played)
		}
		mustContain(t, call(t, db, "team_stats", Args{"team": "Palmeiras", "season": "2023"}), "Wins:", "Draws:", "Losses:", "Goals For:", "Win rate:")
	})
	t.Run("Scenario: home record in a league season", func(t *testing.T) {
		r, _, _, _ := db.TeamRecord(MatchFilter{Team: "Flamengo", Season: 2019, Competition: "Brasileirão", Venue: "home"})
		if r.Played != 19 || r.Wins != 17 || r.Draws != 2 || r.Losses != 0 {
			t.Errorf("Flamengo 2019 home record = %+v, want 19 played 17W 2D 0L", r)
		}
		out := call(t, db, "team_stats", Args{"team": "Corinthians", "season": 2022.0, "venue": "home", "competition": "Brasileirão"})
		mustContain(t, out, "Corinthians home record (Brasileirão Série A, 2022)", "Matches: 19")
	})
	t.Run("Scenario: home and away records add up to the total", func(t *testing.T) {
		f := MatchFilter{Team: "Santos", Competition: "Serie A"}
		all, _, _, _ := db.TeamRecord(f)
		f.Venue = "home"
		h, _, _, _ := db.TeamRecord(f)
		f.Venue = "away"
		a, _, _, _ := db.TeamRecord(f)
		if h.Played+a.Played != all.Played || h.GoalsFor+a.GoalsFor != all.GoalsFor || h.Wins+a.Wins != all.Wins {
			t.Errorf("home %+v + away %+v != total %+v", h, a, all)
		}
	})
	t.Run("Scenario: head-to-head comparison is symmetric", func(t *testing.T) {
		ab, err := db.HeadToHead("Palmeiras", "Santos", MatchFilter{})
		if err != nil {
			t.Fatal(err)
		}
		ba, _ := db.HeadToHead("Santos-SP", "Palmeiras - SP", MatchFilter{})
		if len(ab.Matches) == 0 || ab.AWins != ba.BWins || ab.BWins != ba.AWins || ab.Draws != ba.Draws || ab.AGoals != ba.BGoals {
			t.Errorf("asymmetric h2h: %+v vs %+v", ab, ba)
		}
		played := 0
		for _, m := range ab.Matches {
			if m.Played {
				played++
			}
		}
		if ab.AWins+ab.BWins+ab.Draws != played {
			t.Errorf("W+W+D = %d, played %d", ab.AWins+ab.BWins+ab.Draws, played)
		}
		out := call(t, db, "head_to_head", Args{"team_a": "Palmeiras", "team_b": "Santos"})
		mustContain(t, out, "Palmeiras vs Santos (Clássico da Saudade)", "Head-to-head in dataset", "Most recent meeting")
	})
	t.Run("Scenario: cross-file team profile", func(t *testing.T) {
		out := call(t, db, "team_profile", Args{"team": "Grêmio"})
		mustContain(t, out, "Brasileirão Série A", "Copa do Brasil", "Copa Libertadores", "Internacional (Grenal)", "FIFA squad (Grêmio): 20 players")
	})
}

// ---------- Feature: competition queries ----------

func TestFeature_CompetitionQueries(t *testing.T) {
	db := givenData(t)
	t.Run("Scenario: Who won the 2019 Brasileirão", func(t *testing.T) {
		rows, complete, err := db.Standings("Brasileirão", 2019)
		if err != nil {
			t.Fatal(err)
		}
		if !complete || len(rows) != 20 {
			t.Fatalf("complete=%v teams=%d", complete, len(rows))
		}
		f := rows[0]
		if f.Team.Name != "Flamengo" || f.Points() != 90 || f.Wins != 28 || f.Draws != 6 || f.Losses != 4 {
			t.Errorf("champion row = %s %+v", f.Team.Name, *f)
		}
		if rows[1].Team.Name != "Santos" || rows[1].Points() != 74 || rows[2].Team.Name != "Palmeiras" || rows[2].Points() != 74 {
			t.Errorf("2nd/3rd = %s, %s", rows[1].Team.Name, rows[2].Team.Name)
		}
		out := call(t, db, "standings", Args{"season": 2019.0})
		mustContain(t, out, "1. Flamengo - 90 pts (28W, 6D, 4L)", "- Champion", "2. Santos - 74 pts (22W, 8D, 8L)")
	})
	t.Run("Scenario: champions across files and eras", func(t *testing.T) {
		want := map[int]string{2003: "Cruzeiro", 2006: "São Paulo", 2009: "Flamengo", 2012: "Fluminense", 2015: "Corinthians", 2017: "Corinthians", 2018: "Palmeiras", 2020: "Flamengo", 2021: "Atlético-MG"}
		for season, champ := range want {
			rows, _, err := db.Standings("", season)
			if err != nil {
				t.Errorf("%d: %v", season, err)
				continue
			}
			if rows[0].Team.Name != champ {
				t.Errorf("%d champion = %s, want %s", season, rows[0].Team.Name, champ)
			}
		}
	})
	t.Run("Scenario: Which teams were relegated in 2020", func(t *testing.T) {
		out := call(t, db, "standings", Args{"season": 2020.0, "limit": 1.0})
		for _, team := range []string{"Vasco da Gama", "Goiás", "Coritiba", "Botafogo"} {
			found := false
			for _, line := range strings.Split(out, "\n") {
				if strings.Contains(line, team) && strings.HasSuffix(line, "- Relegated") {
					found = true
				}
			}
			if !found {
				t.Errorf("%s should be marked relegated:\n%s", team, out)
			}
		}
	})
	t.Run("Scenario: standings are internally consistent", func(t *testing.T) {
		rows, _, _ := db.Standings("Serie A", 2016)
		gf, ga, w, l := 0, 0, 0, 0
		for i, r := range rows {
			gf, ga, w, l = gf+r.GoalsFor, ga+r.GoalsAgainst, w+r.Wins, l+r.Losses
			if i > 0 && rows[i-1].Points() < r.Points() {
				t.Error("table not sorted by points")
			}
		}
		if gf != ga || w != l {
			t.Errorf("GF %d != GA %d or W %d != L %d", gf, ga, w, l)
		}
	})
	t.Run("Scenario: Show the 2018 Copa Libertadores bracket", func(t *testing.T) {
		ties, err := db.Bracket("Libertadores", 2018)
		if err != nil {
			t.Fatal(err)
		}
		n := map[string]int{}
		for _, tie := range ties {
			n[tie.Stage]++
		}
		if n["round of 16"] != 8 || n["quarterfinals"] != 4 || n["semifinals"] != 2 || n["final"] != 1 {
			t.Errorf("ties per stage = %v", n)
		}
		out := call(t, db, "knockout_bracket", Args{"season": 2018.0, "competition": "Libertadores"})
		mustContain(t, out, "Final:", "Boca Juniors 2-2 River Plate", "Champion: River Plate")
	})
	t.Run("Scenario: errors for seasons outside the data", func(t *testing.T) {
		if _, _, err := db.Standings("Serie A", 1990); err == nil || !strings.Contains(err.Error(), "2003-2023") {
			t.Errorf("want error naming the available seasons, got %v", err)
		}
		if _, err := CallTool(db, "standings", Args{}); err == nil {
			t.Error("standings without season should fail")
		}
	})
}

// ---------- Feature: statistical analysis ----------

func TestFeature_Statistics(t *testing.T) {
	db := givenData(t)
	t.Run("Scenario: average goals per match in the Brasileirão", func(t *testing.T) {
		s, err := db.Stats(MatchFilter{Competition: "Brasileirão"})
		if err != nil {
			t.Fatal(err)
		}
		if s.Matches < 7500 || s.AvgGoals() < 2.2 || s.AvgGoals() > 2.9 {
			t.Errorf("matches=%d avg=%.2f", s.Matches, s.AvgGoals())
		}
		if s.HomeWins+s.Draws+s.AwayWins != s.Matches || s.HomeWins <= s.AwayWins {
			t.Errorf("inconsistent outcome counts %+v", s)
		}
		mustContain(t, call(t, db, "league_stats", Args{"competition": "Brasileirão"}), "Average goals per match:", "Home win rate:")
	})
	t.Run("Scenario: compare the 2018 and 2019 seasons", func(t *testing.T) {
		out := call(t, db, "league_stats", Args{"competition": "Serie A", "seasons": []any{2018.0, 2019.0}})
		mustContain(t, out, "Brasileirão Série A, 2018", "Matches: 380, Goals: 827", "Champion: Palmeiras (80 pts)",
			"Brasileirão Série A, 2019", "Goals: 876", "Champion: Flamengo (90 pts)")
	})
	t.Run("Scenario: biggest wins are ordered by margin", func(t *testing.T) {
		ms, err := db.BiggestWins(MatchFilter{}, 10)
		if err != nil || len(ms) != 10 {
			t.Fatalf("%d results, err %v", len(ms), err)
		}
		prev := 99
		for _, m := range ms {
			d := m.HomeGoals - m.AwayGoals
			if d < 0 {
				d = -d
			}
			if d > prev {
				t.Errorf("not sorted by margin: %s", formatMatch(m))
			}
			prev = d
		}
		if prev < 6 {
			t.Errorf("10th biggest margin is only %d", prev)
		}
		mustContain(t, call(t, db, "biggest_wins", Args{"limit": 3.0}), "1. 2021-06-08: São Paulo 9-1 4 de Julho")
	})
	t.Run("Scenario: best home and away records", func(t *testing.T) {
		rows, err := db.RankTeams("win_rate", MatchFilter{Competition: "Serie A", Season: 2019}, "home", 10, false)
		if err != nil {
			t.Fatal(err)
		}
		if rows[0].Team.Name != "Flamengo" || rows[0].Played != 19 {
			t.Errorf("best 2019 home record = %s (%d played)", rows[0].Team.Name, rows[0].Played)
		}
		for i := 1; i < len(rows); i++ {
			if rows[i].WinRate() > rows[i-1].WinRate() {
				t.Error("ranking not descending")
			}
		}
		out := call(t, db, "rank_teams", Args{"metric": "win_rate", "venue": "away", "competition": "Serie A"})
		mustContain(t, out, "away matches", "1. ")
	})
	t.Run("Scenario: most goals in a season", func(t *testing.T) {
		rows, _ := db.RankTeams("goals_for", MatchFilter{Competition: "Serie A", Season: 2019}, "", 1, false)
		if rows[0].Team.Name != "Flamengo" || rows[0].GoalsFor != 86 {
			t.Errorf("top scorers 2019 = %s %d", rows[0].Team.Name, rows[0].GoalsFor)
		}
		if _, err := db.RankTeams("vibes", MatchFilter{}, "", 1, false); err == nil {
			t.Error("unknown metric should fail")
		}
	})
	t.Run("Scenario: derbies in a season", func(t *testing.T) {
		ms, _ := db.Derbies(MatchFilter{Season: 2023})
		if len(ms) < 10 {
			t.Fatalf("only %d derbies in 2023", len(ms))
		}
		for _, m := range ms {
			if DerbyName(m.Home, m.Away) == "" || m.Season != 2023 {
				t.Errorf("not a 2023 derby: %s", formatMatch(m))
			}
		}
		mustContain(t, call(t, db, "list_derbies", Args{"season": 2023.0, "limit": 100.0}), "Fla-Flu", "Grenal")
	})
}

// ---------- Feature: player queries ----------

func TestFeature_PlayerQueries(t *testing.T) {
	db := givenData(t)
	t.Run("Scenario: find all Brazilian players, best first", func(t *testing.T) {
		ps, err := db.SearchPlayers(PlayerFilter{Nationality: "Brazilian"})
		if err != nil {
			t.Fatal(err)
		}
		if len(ps) != 827 {
			t.Errorf("%d Brazilian players, want 827", len(ps))
		}
		if ps[0].Name != "Neymar Jr" || ps[0].Overall != 92 || ps[0].Club != "Paris Saint-Germain" || ps[0].Position != "LW" {
			t.Errorf("top Brazilian = %+v", ps[0])
		}
		for i, p := range ps {
			if p.Nationality != "Brazil" || (i > 0 && ps[i-1].Overall < p.Overall) {
				t.Fatalf("bad row %d: %s", i, formatPlayer(p))
			}
		}
		out := call(t, db, "search_players", Args{"nationality": "Brazil", "limit": 3.0})
		mustContain(t, out, "1. Neymar Jr - Overall: 92, Position: LW, Club: Paris Saint-Germain")
	})
	t.Run("Scenario: search by name ignores accents and case", func(t *testing.T) {
		for _, q := range []string{"neymar", "NEYMAR JR", "Neymár"} {
			ps, _ := db.SearchPlayers(PlayerFilter{Name: q})
			if len(ps) == 0 || ps[0].Name != "Neymar Jr" {
				t.Errorf("search %q did not find Neymar Jr", q)
			}
		}
		out := call(t, db, "player_details", Args{"name": "Alisson"})
		mustContain(t, out, "Alisson", "Nationality: Brazil", "Position: GK", "Liverpool", "GKReflexes")
		mustContain(t, call(t, db, "player_details", Args{"name": "Gabriel Barbosa"}), "No player matching")
	})
	t.Run("Scenario: players of a Brazilian club", func(t *testing.T) {
		ps, _ := db.SearchPlayers(PlayerFilter{Club: "Santos"})
		if len(ps) == 0 {
			t.Fatal("no Santos players")
		}
		for _, p := range ps {
			if p.Club != "Santos" { // must not pick up Santos Laguna
				t.Errorf("wrong club %q", p.Club)
			}
		}
		for _, q := range []string{"Atlético-MG", "Atletico Mineiro", "Gremio", "Sport Recife"} {
			if ps, _ := db.SearchPlayers(PlayerFilter{Club: q}); len(ps) != 20 {
				t.Errorf("club %q: %d players, want 20", q, len(ps))
			}
		}
		mustContain(t, call(t, db, "search_players", Args{"club": "Flamengo"}), "0 found", "absent")
	})
	t.Run("Scenario: forwards at a club and attribute sorting", func(t *testing.T) {
		ps, err := db.SearchPlayers(PlayerFilter{Club: "Grêmio", Position: "forwards"})
		if err != nil || len(ps) == 0 {
			t.Fatalf("%d forwards, err %v", len(ps), err)
		}
		fw := map[string]bool{}
		for _, p := range positionGroups["forward"] {
			fw[p] = true
		}
		for _, p := range ps {
			if !fw[p.Position] {
				t.Errorf("%s is not a forward (%s)", p.Name, p.Position)
			}
		}
		ps, err = db.SearchPlayers(PlayerFilter{Nationality: "Brazil", SortBy: "Finishing"})
		if err != nil || ps[0].Attributes["Finishing"] < ps[1].Attributes["Finishing"] || ps[0].Attributes["Finishing"] < 85 {
			t.Errorf("attribute sort failed: %v", err)
		}
		if _, err := db.SearchPlayers(PlayerFilter{Position: "wizard"}); err == nil {
			t.Error("unknown position should fail")
		}
	})
	t.Run("Scenario: Brazilian players grouped by Brazilian club", func(t *testing.T) {
		out := call(t, db, "players_at_brazilian_clubs", Args{"nationality": "Brazil"})
		mustContain(t, out, "Grêmio: 20 players", "Santos: 20 players", "avg rating")
		if strings.Contains(out, "Inter:") || strings.Contains(out, "Boavista FC") || strings.Contains(out, "Santos Laguna") {
			t.Errorf("foreign clubs leaked into Brazilian clubs:\n%s", out)
		}
	})
}

// ---------- Feature: 20+ sample questions ----------

func TestFeature_SampleQuestions(t *testing.T) {
	db := givenData(t)
	qs := []struct {
		question, tool string
		args           Args
		want           []string
	}{
		{"Show me all Flamengo vs Fluminense matches", "find_matches", Args{"team": "Flamengo", "opponent": "Fluminense"}, []string{"Flamengo vs Fluminense", "Head-to-head"}},
		{"What matches did Palmeiras play in 2023?", "find_matches", Args{"team": "Palmeiras", "season": 2023.0}, []string{"Palmeiras - 2023:", "2023-"}},
		{"Find all Copa do Brasil finals", "find_matches", Args{"competition": "Copa do Brasil", "stage": "final", "limit": 50.0}, []string{"2012-07-11: Coritiba 1-1 Palmeiras", "2023-09-24: São Paulo 1-1 Flamengo"}},
		{"What is Corinthians' home record in 2022?", "team_stats", Args{"team": "Corinthians", "season": 2022.0, "venue": "home"}, []string{"Corinthians home record", "Win rate"}},
		{"Which team scored the most goals in Serie A 2023?", "rank_teams", Args{"metric": "goals_for", "competition": "Serie A", "season": 2023.0}, []string{"1. ", "goals_for"}},
		{"Compare Palmeiras and Santos head-to-head", "head_to_head", Args{"team_a": "Palmeiras", "team_b": "Santos"}, []string{"Palmeiras", "Santos", "draws"}},
		{"Find all Brazilian players in the dataset", "search_players", Args{"nationality": "Brazil"}, []string{"827 found", "Neymar Jr"}},
		{"Who are the highest-rated players at Grêmio?", "search_players", Args{"club": "Grêmio", "limit": 5.0}, []string{"20 found", "Club: Grêmio"}},
		{"Show me all forwards from Santos", "search_players", Args{"club": "Santos", "position": "forward"}, []string{"Position: ST", "Club: Santos"}},
		{"Who won the 2019 Brasileirão?", "standings", Args{"season": 2019.0}, []string{"1. Flamengo - 90 pts", "Champion"}},
		{"Show the 2018 Copa Libertadores bracket", "knockout_bracket", Args{"season": 2018.0}, []string{"Semifinals:", "Champion: River Plate"}},
		{"Which teams were relegated in 2020?", "standings", Args{"season": 2020.0}, []string{"Botafogo", "- Relegated"}},
		{"What's the average goals per match in the Brasileirão?", "league_stats", Args{"competition": "Brasileirão"}, []string{"Average goals per match: 2."}},
		{"Which team has the best away record?", "rank_teams", Args{"venue": "away", "competition": "Serie A"}, []string{"away matches", "win_rate"}},
		{"Show me the biggest wins in the dataset", "biggest_wins", Args{}, []string{"Biggest victories", "9-1"}},
		{"When did Flamengo last play Corinthians?", "find_matches", Args{"team": "Flamengo", "opponent": "Corinthians", "limit": 1.0}, []string{"2023-10-08: Corinthians 1-1 Flamengo"}},
		{"Who is Neymar?", "player_details", Args{"name": "Neymar"}, []string{"Neymar Jr", "Overall: 92", "Dribbling 96"}},
		{"Which players play for Cruzeiro?", "search_players", Args{"club": "Cruzeiro"}, []string{"Club: Cruzeiro"}},
		{"Show me all derbies in 2023", "list_derbies", Args{"season": 2023.0}, []string{"Derbies", "2023-"}},
		{"What competitions has Palmeiras played in?", "team_profile", Args{"team": "Palmeiras"}, []string{"Brasileirão Série A", "Copa Libertadores", "Copa do Brasil"}},
		{"Which team has the best home record?", "rank_teams", Args{"venue": "home", "competition": "Serie A"}, []string{"home matches"}},
		{"Who are the top Brazilian players?", "search_players", Args{"nationality": "Brazil", "limit": 10.0}, []string{"1. Neymar Jr", "10. "}},
		{"Compare the 2018 and 2019 seasons", "league_stats", Args{"competition": "Serie A", "seasons": []any{2018.0, 2019.0}}, []string{"2018", "2019", "Champion: Flamengo"}},
		{"Which Brazilian clubs have players in the FIFA data?", "players_at_brazilian_clubs", Args{}, []string{"Internacional: 20 players"}},
		{"Who won the 2016 Copa do Brasil?", "knockout_bracket", Args{"season": 2016.0, "competition": "Copa do Brasil"}, []string{"Champion: Grêmio"}},
		{"What Serie B data is there for 2019?", "standings", Args{"season": 2019.0, "competition": "Serie B"}, []string{"Brasileirão Série B", "1. Bragantino"}},
		{"What data do you have?", "dataset_info", Args{}, []string{"Brasileirao_Matches.csv", "fifa_data.csv", "18207"}},
		{"Which teams are called Atlético?", "list_teams", Args{"query": "atlético"}, []string{"Atlético-MG", "Atlético-GO"}},
	}
	if len(qs) < 20 {
		t.Fatalf("need at least 20 sample questions, have %d", len(qs))
	}
	for _, q := range qs {
		t.Run(q.question, func(t *testing.T) {
			start := time.Now()
			out := call(t, db, q.tool, q.args)
			if d := time.Since(start); d > 2*time.Second {
				t.Errorf("took %v, want < 2s", d)
			}
			mustContain(t, out, q.want...)
		})
	}
}

// ---------- Feature: MCP protocol ----------

func rpc(t *testing.T, s *Server, lines ...string) []map[string]any {
	t.Helper()
	var out bytes.Buffer
	if err := s.Serve(strings.NewReader(strings.Join(lines, "\n")+"\n"), &out); err != nil {
		t.Fatal(err)
	}
	var resps []map[string]any
	for _, l := range strings.Split(strings.TrimSpace(out.String()), "\n") {
		if l == "" {
			continue
		}
		var m map[string]any
		if err := json.Unmarshal([]byte(l), &m); err != nil {
			t.Fatalf("response is not one JSON object per line: %q", l)
		}
		resps = append(resps, m)
	}
	return resps
}

func TestFeature_MCPProtocol(t *testing.T) {
	s := NewServer(givenData(t))
	t.Run("Scenario: initialize handshake", func(t *testing.T) {
		r := rpc(t, s,
			`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"0"}}}`,
			`{"jsonrpc":"2.0","method":"notifications/initialized"}`,
			`{"jsonrpc":"2.0","id":"p","method":"ping"}`)
		if len(r) != 2 {
			t.Fatalf("got %d responses, want 2 (notifications get no reply)", len(r))
		}
		res := r[0]["result"].(map[string]any)
		if res["protocolVersion"] != "2024-11-05" || res["serverInfo"].(map[string]any)["name"] != serverName {
			t.Errorf("bad initialize result: %v", res)
		}
		if _, ok := res["capabilities"].(map[string]any)["tools"]; !ok {
			t.Error("tools capability not advertised")
		}
		if r[1]["id"] != "p" || r[1]["result"] == nil {
			t.Errorf("bad ping response: %v", r[1])
		}
	})
	t.Run("Scenario: tools/list returns valid schemas", func(t *testing.T) {
		r := rpc(t, s, `{"jsonrpc":"2.0","id":2,"method":"tools/list"}`)
		tools := r[0]["result"].(map[string]any)["tools"].([]any)
		if len(tools) != len(Tools) || len(tools) < 10 {
			t.Fatalf("%d tools listed", len(tools))
		}
		seen := map[string]bool{}
		for _, x := range tools {
			tool := x.(map[string]any)
			name := tool["name"].(string)
			schema := tool["inputSchema"].(map[string]any)
			if seen[name] || tool["description"] == "" || schema["type"] != "object" {
				t.Errorf("bad tool definition %v", tool)
			}
			seen[name] = true
			props := schema["properties"].(map[string]any)
			if req, ok := schema["required"].([]any); ok {
				for _, k := range req {
					if _, ok := props[k.(string)]; !ok {
						t.Errorf("%s: required %q is not a property", name, k)
					}
				}
			}
		}
	})
	t.Run("Scenario: tools/call returns text content", func(t *testing.T) {
		r := rpc(t, s, `{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"standings","arguments":{"season":2019,"limit":3}}}`)
		res := r[0]["result"].(map[string]any)
		c := res["content"].([]any)[0].(map[string]any)
		if res["isError"] != false || c["type"] != "text" || !strings.Contains(c["text"].(string), "1. Flamengo - 90 pts") {
			t.Errorf("unexpected result: %v", res)
		}
	})
	t.Run("Scenario: errors are reported, not fatal", func(t *testing.T) {
		r := rpc(t, s,
			`{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"team_stats","arguments":{"team":"Nonexistent FC 123"}}}`,
			`{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"no_such_tool","arguments":{}}}`,
			`{"jsonrpc":"2.0","id":6,"method":"bogus/method"}`,
			`this is not json`,
			`{"jsonrpc":"2.0","id":7,"method":"tools/call","params":{"name":"team_stats","arguments":{"team":"Flamengo","season":"abc"}}}`,
			`{"jsonrpc":"2.0","id":8,"method":"tools/call","params":{"name":"team_stats"}}`,
			`{"jsonrpc":"2.0","id":9,"method":"ping"}`)
		if len(r) != 7 {
			t.Fatalf("got %d responses, want 7", len(r))
		}
		if res := r[0]["result"].(map[string]any); res["isError"] != true {
			t.Errorf("unknown team should be a tool error: %v", res)
		}
		code := func(m map[string]any) float64 {
			e, _ := m["error"].(map[string]any)
			c, _ := e["code"].(float64)
			return c
		}
		if code(r[1]) != -32602 || code(r[2]) != -32601 || code(r[3]) != -32700 {
			t.Errorf("error codes = %v %v %v", code(r[1]), code(r[2]), code(r[3]))
		}
		for _, i := range []int{4, 5} {
			if res, _ := r[i]["result"].(map[string]any); res["isError"] != true {
				t.Errorf("response %d should be a tool error: %v", i, r[i])
			}
		}
		if r[6]["result"] == nil {
			t.Error("server stopped answering after errors")
		}
	})
}

// ---------- Feature: performance ----------

func TestFeature_Performance(t *testing.T) {
	dir, err := FindDataDir("")
	if err != nil {
		t.Fatal(err)
	}
	start := time.Now()
	db, err := LoadDB(dir)
	if err != nil {
		t.Fatal(err)
	}
	if d := time.Since(start); d > 5*time.Second {
		t.Errorf("loading took %v", d)
	}
	start = time.Now()
	call(t, db, "find_matches", Args{"team": "Flamengo", "opponent": "Corinthians"})
	call(t, db, "player_details", Args{"name": "Neymar"})
	if d := time.Since(start); d > 2*time.Second {
		t.Errorf("simple lookups took %v, want < 2s", d)
	}
	start = time.Now()
	call(t, db, "rank_teams", Args{"metric": "win_rate"})
	call(t, db, "league_stats", Args{})
	call(t, db, "biggest_wins", Args{})
	call(t, db, "standings", Args{"season": 2019.0})
	if d := time.Since(start); d > 5*time.Second {
		t.Errorf("aggregate queries took %v, want < 5s", d)
	}
}
