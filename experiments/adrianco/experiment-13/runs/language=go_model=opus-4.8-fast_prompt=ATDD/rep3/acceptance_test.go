// Context: Executable acceptance specification for the Brazilian Soccer MCP
// server. Each scenario is written from the perspective of an external MCP
// client (an LLM), drives the System Under Test only through the MCP
// tools/protocol (via mcpclient_test.go), and asserts on WHAT the system does
// in the language of the problem domain — finding matches between two teams,
// a team's home record, head-to-head tallies, player search, competition
// standings and aggregate statistics. Every scenario starts from a freshly
// booted server loaded with its own small fixture dataset written to a temp
// directory, so tests are atomic and share no data. A separate group of
// scenarios runs against the real bundled Kaggle datasets to prove coverage of
// all six CSV files.
package main

import (
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// --- fixture helpers -------------------------------------------------------

func writeFixture(t *testing.T, dir, name, content string) {
	t.Helper()
	if err := os.WriteFile(filepath.Join(dir, name), []byte(content), 0o644); err != nil {
		t.Fatalf("writing fixture %s: %v", name, err)
	}
}

func mustContain(t *testing.T, haystack, needle string) {
	t.Helper()
	if !strings.Contains(haystack, needle) {
		t.Fatalf("expected output to contain %q\n--- got ---\n%s", needle, haystack)
	}
}

func mustNotContain(t *testing.T, haystack, needle string) {
	t.Helper()
	if strings.Contains(haystack, needle) {
		t.Fatalf("expected output NOT to contain %q\n--- got ---\n%s", needle, haystack)
	}
}

const brasileiraoHeader = `"datetime","home_team","home_team_state","away_team","away_team_state","home_goal","away_goal","season","round"` + "\n"

func brasileiraoFixture(rows ...string) string {
	return brasileiraoHeader + strings.Join(rows, "\n") + "\n"
}

const fifaHeader = `,ID,Name,Age,Nationality,Overall,Potential,Club,Position` + "\n"

func fifaFixture(rows ...string) string {
	return fifaHeader + strings.Join(rows, "\n") + "\n"
}

// --- Match queries ---------------------------------------------------------

func TestFindMatchesBetweenTwoTeams(t *testing.T) {
	dir := t.TempDir()
	// Flamengo and Fluminense play twice (the Fla-Flu derby), plus an unrelated
	// match that must not leak into the result. Team names carry state suffixes
	// to exercise normalization against the bare names used in the query.
	writeFixture(t, dir, "Brasileirao_Matches.csv", brasileiraoFixture(
		`2023-09-03 16:00:00,"Flamengo-RJ","RJ","Fluminense-RJ","RJ",2,1,2023,22`,
		`2023-05-28 16:00:00,"Fluminense-RJ","RJ","Flamengo-RJ","RJ",1,0,2023,8`,
		`2023-07-01 16:00:00,"Palmeiras-SP","SP","Santos-SP","SP",3,0,2023,15`,
	))
	c := startServer(t, dir)

	out, isErr := c.callTool("find_matches", map[string]any{
		"team":     "Flamengo",
		"opponent": "Fluminense",
	})
	if isErr {
		t.Fatalf("find_matches reported error: %s", out)
	}
	mustContain(t, out, "Flamengo 2-1 Fluminense")
	mustContain(t, out, "Fluminense 1-0 Flamengo")
	mustNotContain(t, out, "Palmeiras")
	// Head-to-head between exactly these two teams: one win each, no draws.
	mustContain(t, out, "Flamengo 1 win")
	mustContain(t, out, "Fluminense 1 win")
}

func TestFindMatchesByTeamAndSeason(t *testing.T) {
	dir := t.TempDir()
	writeFixture(t, dir, "Brasileirao_Matches.csv", brasileiraoFixture(
		`2023-07-01 16:00:00,"Palmeiras-SP","SP","Santos-SP","SP",3,0,2023,15`,
		`2022-07-01 16:00:00,"Palmeiras-SP","SP","Corinthians-SP","SP",1,1,2022,15`,
	))
	c := startServer(t, dir)

	out, _ := c.callTool("find_matches", map[string]any{
		"team":   "Palmeiras",
		"season": 2023,
	})
	mustContain(t, out, "Palmeiras 3-0 Santos")
	mustNotContain(t, out, "Corinthians")
}

func TestFindMatchesByCompetition(t *testing.T) {
	dir := t.TempDir()
	writeFixture(t, dir, "Brasileirao_Matches.csv", brasileiraoFixture(
		`2023-07-01 16:00:00,"Flamengo-RJ","RJ","Santos-SP","SP",2,0,2023,15`,
	))
	writeFixture(t, dir, "Libertadores_Matches.csv",
		`"datetime","home_team","away_team","home_goal","away_goal","season","stage"`+"\n"+
			`2023-04-01 20:15:00,"Flamengo","Nacional (URU)",4,1,2023,"group stage"`+"\n")
	c := startServer(t, dir)

	out, _ := c.callTool("find_matches", map[string]any{
		"team":        "Flamengo",
		"competition": "Libertadores",
	})
	mustContain(t, out, "Flamengo 4-1 Nacional")
	mustContain(t, out, "Libertadores")
	mustNotContain(t, out, "Santos")
}

// --- Team queries ----------------------------------------------------------

func TestTeamHomeRecord(t *testing.T) {
	dir := t.TempDir()
	// Corinthians at home in 2022: 2 wins, 1 draw, 1 loss; GF 5, GA 3.
	writeFixture(t, dir, "Brasileirao_Matches.csv", brasileiraoFixture(
		`2022-05-01 16:00:00,"Corinthians-SP","SP","Santos-SP","SP",2,0,2022,1`,
		`2022-05-08 16:00:00,"Corinthians-SP","SP","Palmeiras-SP","SP",1,1,2022,2`,
		`2022-05-15 16:00:00,"Corinthians-SP","SP","Flamengo-RJ","RJ",1,2,2022,3`,
		`2022-05-22 16:00:00,"Corinthians-SP","SP","Gremio-RS","RS",1,0,2022,4`,
		// An away match that must be excluded from the home record:
		`2022-05-29 16:00:00,"Santos-SP","SP","Corinthians-SP","SP",4,0,2022,5`,
	))
	c := startServer(t, dir)

	out, isErr := c.callTool("team_record", map[string]any{
		"team":   "Corinthians",
		"season": 2022,
		"venue":  "home",
	})
	if isErr {
		t.Fatalf("team_record error: %s", out)
	}
	mustContain(t, out, "Matches: 4")
	mustContain(t, out, "Wins: 2")
	mustContain(t, out, "Draws: 1")
	mustContain(t, out, "Losses: 1")
	mustContain(t, out, "Goals For: 5")
	mustContain(t, out, "Goals Against: 3")
	mustContain(t, out, "Win rate: 50.0%")
}

func TestHeadToHead(t *testing.T) {
	dir := t.TempDir()
	writeFixture(t, dir, "Brasileirao_Matches.csv", brasileiraoFixture(
		`2021-05-01 16:00:00,"Palmeiras-SP","SP","Santos-SP","SP",2,0,2021,1`,
		`2021-09-01 16:00:00,"Santos-SP","SP","Palmeiras-SP","SP",1,1,2021,20`,
		`2022-05-01 16:00:00,"Palmeiras-SP","SP","Santos-SP","SP",0,1,2022,1`,
	))
	c := startServer(t, dir)

	out, isErr := c.callTool("head_to_head", map[string]any{
		"team_a": "Palmeiras",
		"team_b": "Santos",
	})
	if isErr {
		t.Fatalf("head_to_head error: %s", out)
	}
	mustContain(t, out, "Total matches: 3")
	mustContain(t, out, "Palmeiras wins: 1")
	mustContain(t, out, "Santos wins: 1")
	mustContain(t, out, "Draws: 1")
}

// Clubs that share a base name but differ by state (Atlético-MG vs Atlético-PR)
// are distinct teams and must not be conflated in a team's record.
func TestSameBaseNameDifferentStateAreDistinct(t *testing.T) {
	dir := t.TempDir()
	writeFixture(t, dir, "Brasileirao_Matches.csv", brasileiraoFixture(
		`2020-05-01 16:00:00,"Atlético-MG","MG","Santos-SP","SP",3,0,2020,1`,
		`2020-05-08 16:00:00,"Atlético-PR","PR","Santos-SP","SP",0,2,2020,2`,
	))
	c := startServer(t, dir)

	out, isErr := c.callTool("team_record", map[string]any{
		"team":   "Atlético-MG",
		"season": 2020,
	})
	if isErr {
		t.Fatalf("team_record error: %s", out)
	}
	// Only Atlético-MG's single win must count, not Atlético-PR's loss.
	mustContain(t, out, "Matches: 1")
	mustContain(t, out, "Wins: 1")
	mustContain(t, out, "Losses: 0")
}

// --- Player queries --------------------------------------------------------

func TestSearchBrazilianPlayersSorted(t *testing.T) {
	dir := t.TempDir()
	writeFixture(t, dir, "fifa_data.csv", fifaFixture(
		`0,158023,Neymar Jr,27,Brazil,92,93,Paris Saint-Germain,LW`,
		`1,20801,Casemiro,27,Brazil,89,90,Real Madrid,CDM`,
		`2,1,L. Messi,31,Argentina,94,94,FC Barcelona,RF`,
		`3,2,Gabriel Barbosa,22,Brazil,80,86,Flamengo,ST`,
	))
	c := startServer(t, dir)

	out, isErr := c.callTool("search_players", map[string]any{
		"nationality": "Brazil",
	})
	if isErr {
		t.Fatalf("search_players error: %s", out)
	}
	// Brazilians only, sorted by overall rating descending: Neymar first.
	mustContain(t, out, "Neymar Jr")
	mustContain(t, out, "Gabriel Barbosa")
	mustNotContain(t, out, "Messi")
	if i, j := strings.Index(out, "Neymar"), strings.Index(out, "Casemiro"); i < 0 || j < 0 || i > j {
		t.Fatalf("expected Neymar listed before Casemiro\n%s", out)
	}
}

func TestSearchPlayersByClub(t *testing.T) {
	dir := t.TempDir()
	writeFixture(t, dir, "fifa_data.csv", fifaFixture(
		`0,1,Gabriel Barbosa,22,Brazil,80,86,Flamengo,ST`,
		`1,2,Bruno Henrique,28,Brazil,79,80,Flamengo,LW`,
		`2,3,Neymar Jr,27,Brazil,92,93,Paris Saint-Germain,LW`,
	))
	c := startServer(t, dir)

	out, _ := c.callTool("search_players", map[string]any{"club": "Flamengo"})
	mustContain(t, out, "Gabriel Barbosa")
	mustContain(t, out, "Bruno Henrique")
	mustNotContain(t, out, "Neymar")
}

func TestSearchPlayerByName(t *testing.T) {
	dir := t.TempDir()
	writeFixture(t, dir, "fifa_data.csv", fifaFixture(
		`0,1,Gabriel Barbosa,22,Brazil,80,86,Flamengo,ST`,
		`1,2,Neymar Jr,27,Brazil,92,93,Paris Saint-Germain,LW`,
	))
	c := startServer(t, dir)

	out, _ := c.callTool("search_players", map[string]any{"name": "Gabriel"})
	mustContain(t, out, "Gabriel Barbosa")
	mustNotContain(t, out, "Neymar")
}

// --- Competition queries ---------------------------------------------------

func TestCompetitionStandings(t *testing.T) {
	dir := t.TempDir()
	// A tiny 3-team round robin. Expected points:
	//  A: beat B (2-0) and beat C (1-0) => 6 pts
	//  C: lost to A, beat B (3-1)       => 3 pts
	//  B: lost both                     => 0 pts
	writeFixture(t, dir, "Brasileirao_Matches.csv", brasileiraoFixture(
		`2020-05-01 16:00:00,"Team A-SP","SP","Team B-SP","SP",2,0,2020,1`,
		`2020-05-08 16:00:00,"Team A-SP","SP","Team C-SP","SP",1,0,2020,2`,
		`2020-05-15 16:00:00,"Team C-SP","SP","Team B-SP","SP",3,1,2020,3`,
	))
	c := startServer(t, dir)

	out, isErr := c.callTool("competition_standings", map[string]any{
		"competition": "Brasileirão",
		"season":      2020,
	})
	if isErr {
		t.Fatalf("competition_standings error: %s", out)
	}
	mustContain(t, out, "1. Team A")
	mustContain(t, out, "6 pts")
	// Champion (A) must be listed before the runner-up (C).
	if i, j := strings.Index(out, "Team A"), strings.Index(out, "Team C"); i < 0 || j < 0 || i > j {
		t.Fatalf("expected Team A listed before Team C\n%s", out)
	}
}

// Standings must count each real match once even when the same fixtures appear
// in two overlapping source files (Brasileirao_Matches and the historical
// novo_campeonato_brasileiro both carry Brasileirão results).
func TestStandingsDeduplicatesOverlappingSources(t *testing.T) {
	dir := t.TempDir()
	writeFixture(t, dir, "Brasileirao_Matches.csv", brasileiraoFixture(
		`2019-05-01 16:00:00,"Flamengo-RJ","RJ","Vasco-RJ","RJ",3,0,2019,1`,
	))
	writeFixture(t, dir, "novo_campeonato_brasileiro.csv",
		`ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena,OBS`+"\n"+
			`2019.01.0001,01/05/2019,2019,1,Flamengo,Vasco,3,0,RJ,RJ,Mandante,Maracanã,`+"\n")
	c := startServer(t, dir)

	out, _ := c.callTool("competition_standings", map[string]any{
		"competition": "Brasileirão",
		"season":      2019,
	})
	// One win => 3 points, not 6 (which would indicate double counting).
	mustContain(t, out, "3 pts")
	mustNotContain(t, out, "6 pts")
}

// --- Statistical analysis --------------------------------------------------

func TestMatchStatistics(t *testing.T) {
	dir := t.TempDir()
	// 3 matches, total goals 2+0 + 1+1 + 5+0 = 9 over 3 => avg 3.00.
	// Home wins: match1 (Flamengo) and match3 (Palmeiras) => 2 of 3 => 66.7%.
	writeFixture(t, dir, "Brasileirao_Matches.csv", brasileiraoFixture(
		`2019-05-01 16:00:00,"Flamengo-RJ","RJ","Gremio-RS","RS",2,0,2019,1`,
		`2019-05-08 16:00:00,"Santos-SP","SP","Palmeiras-SP","SP",1,1,2019,2`,
		`2019-05-15 16:00:00,"Palmeiras-SP","SP","Sao Paulo-SP","SP",5,0,2019,3`,
	))
	c := startServer(t, dir)

	out, isErr := c.callTool("match_statistics", map[string]any{
		"competition": "Brasileirão",
		"season":      2019,
	})
	if isErr {
		t.Fatalf("match_statistics error: %s", out)
	}
	mustContain(t, out, "Average goals per match: 3.00")
	mustContain(t, out, "Home win rate: 66.7%")
	// The biggest victory in the set is Palmeiras 5-0.
	mustContain(t, out, "Biggest")
	mustContain(t, out, "Palmeiras 5-0 Sao Paulo")
}

// --- Protocol-level scenarios ----------------------------------------------

func TestListToolsExposesCapabilities(t *testing.T) {
	dir := t.TempDir()
	writeFixture(t, dir, "Brasileirao_Matches.csv", brasileiraoFixture(
		`2019-05-01 16:00:00,"Flamengo-RJ","RJ","Gremio-RS","RS",2,0,2019,1`,
	))
	c := startServer(t, dir)

	tools := c.listTools()
	got := map[string]bool{}
	for _, tl := range tools {
		got[tl.Name] = true
		if tl.Description == "" {
			t.Errorf("tool %s missing description", tl.Name)
		}
		if len(tl.InputSchema) == 0 {
			t.Errorf("tool %s missing inputSchema", tl.Name)
		}
	}
	for _, want := range []string{
		"find_matches", "team_record", "head_to_head",
		"search_players", "competition_standings", "match_statistics",
	} {
		if !got[want] {
			t.Errorf("expected tool %q to be advertised", want)
		}
	}
}

func TestUnknownToolReturnsError(t *testing.T) {
	dir := t.TempDir()
	writeFixture(t, dir, "Brasileirao_Matches.csv", brasileiraoFixture(
		`2019-05-01 16:00:00,"Flamengo-RJ","RJ","Gremio-RS","RS",2,0,2019,1`,
	))
	c := startServer(t, dir)

	out, isErr := c.callTool("does_not_exist", map[string]any{})
	if !isErr {
		t.Fatalf("expected error result for unknown tool, got: %s", out)
	}
}

func TestUnknownMethodReturnsProtocolError(t *testing.T) {
	dir := t.TempDir()
	writeFixture(t, dir, "Brasileirao_Matches.csv", brasileiraoFixture(
		`2019-05-01 16:00:00,"Flamengo-RJ","RJ","Gremio-RS","RS",2,0,2019,1`,
	))
	c := startServer(t, dir)

	resp := c.rawRequest("totally/unknown", map[string]any{})
	if resp.Error == nil {
		t.Fatalf("expected protocol error for unknown method")
	}
	if resp.Error.Code != -32601 {
		t.Errorf("expected method-not-found code -32601, got %d", resp.Error.Code)
	}
}

// --- Real bundled dataset coverage -----------------------------------------

func realDataDir(t *testing.T) string {
	t.Helper()
	dir := filepath.Join("data", "kaggle")
	if _, err := os.Stat(filepath.Join(dir, "Brasileirao_Matches.csv")); err != nil {
		t.Skipf("real dataset not present at %s: %v", dir, err)
	}
	return dir
}

func TestRealDataLoadsAllCompetitions(t *testing.T) {
	c := startServer(t, realDataDir(t))

	out, isErr := c.callTool("find_matches", map[string]any{
		"team":  "Flamengo",
		"limit": 5,
	})
	if isErr {
		t.Fatalf("find_matches error: %s", out)
	}
	mustContain(t, out, "Flamengo")

	// Each provided competition file should be queryable.
	for _, comp := range []string{"Brasileirão", "Copa do Brasil", "Libertadores"} {
		out, isErr := c.callTool("find_matches", map[string]any{
			"competition": comp,
			"limit":       3,
		})
		if isErr {
			t.Fatalf("find_matches for %s error: %s", comp, out)
		}
		mustContain(t, out, "match")
	}
}

func TestRealData2019BrasileiraoChampion(t *testing.T) {
	c := startServer(t, realDataDir(t))

	out, isErr := c.callTool("competition_standings", map[string]any{
		"competition": "Brasileirão",
		"season":      2019,
	})
	if isErr {
		t.Fatalf("competition_standings error: %s", out)
	}
	// Flamengo were the 2019 Brasileirão champions.
	champ := strings.Index(out, "1. Flamengo")
	if champ < 0 {
		t.Fatalf("expected Flamengo as 2019 champion\n%s", firstLines(out, 5))
	}
}

func TestRealDataTopBrazilianPlayer(t *testing.T) {
	c := startServer(t, realDataDir(t))

	out, isErr := c.callTool("search_players", map[string]any{
		"nationality": "Brazil",
		"limit":       5,
	})
	if isErr {
		t.Fatalf("search_players error: %s", out)
	}
	// Neymar Jr is the highest-rated Brazilian in this FIFA dataset.
	if !strings.Contains(firstLines(out, 2), "Neymar") {
		t.Fatalf("expected Neymar as top Brazilian player\n%s", firstLines(out, 6))
	}
}

func firstLines(s string, n int) string {
	lines := strings.SplitN(s, "\n", n+1)
	if len(lines) > n {
		lines = lines[:n]
	}
	return strings.Join(lines, "\n")
}
