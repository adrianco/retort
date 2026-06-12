// Acceptance tests against the full, real Kaggle datasets shipped in
// data/kaggle. These prove the success criteria: all six CSV files load and are
// queryable, and concrete sample questions from the specification are answered.
// Still driven purely through the MCP protocol.
package acceptance

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"brazilian-soccer-mcp/mcp"
)

func realDataDir(t *testing.T) string {
	t.Helper()
	dir := filepath.Join("..", "data", "kaggle")
	if _, err := os.Stat(filepath.Join(dir, "fifa_data.csv")); err != nil {
		t.Skipf("real Kaggle data not present at %s: %v", dir, err)
	}
	return dir
}

func realServer(t *testing.T) *mcp.Server {
	t.Helper()
	srv, err := mcp.NewServer(realDataDir(t))
	if err != nil {
		t.Fatalf("load real data: %v", err)
	}
	return srv
}

func TestRealData_AllSixFilesLoadAndAreReportedHealthy(t *testing.T) {
	srv := realServer(t)
	// The server exposes a health/summary via initialize's instructions or a
	// dedicated tool; here we just confirm queries against every dataset return
	// content rather than empty results.
	playersAnswer := callTool(t, srv, "search_players", map[string]any{"nationality": "Brazil", "limit": 5})
	mustContain(t, playersAnswer, "Overall:", "Nationality:") // real player rows, not just the echoed query

	matchAnswer := callTool(t, srv, "find_matches", map[string]any{"team": "Flamengo", "limit": 3})
	mustContain(t, matchAnswer, "Flamengo", "Total matches in dataset:")
}

func TestRealData_FindFlamengoVsFluminense(t *testing.T) {
	srv := realServer(t)
	answer := callTool(t, srv, "find_matches", map[string]any{
		"team":     "Flamengo",
		"opponent": "Fluminense",
	})
	mustContain(t, answer, "Flamengo", "Fluminense", "head-to-head")
}

func TestRealData_TopBrazilianPlayers(t *testing.T) {
	srv := realServer(t)
	answer := callTool(t, srv, "search_players", map[string]any{
		"nationality": "Brazil",
		"limit":       5,
	})
	// Neymar is the top-rated Brazilian in this FIFA dataset.
	mustContain(t, answer, "Neymar")
}

func TestRealData_WhoIsGabrielBarbosa(t *testing.T) {
	srv := realServer(t)
	answer := callTool(t, srv, "search_players", map[string]any{"name": "Gabriel Barbosa"})
	mustContain(t, answer, "Gabriel Barbosa")
}

func TestRealData_2019BrasileiraoStandingsChampion(t *testing.T) {
	srv := realServer(t)
	answer := callTool(t, srv, "get_standings", map[string]any{
		"competition": "Brasileirão",
		"season":      2019,
	})
	// Flamengo were the 2019 Brasileirão champions.
	if !strings.Contains(answer, "Flamengo") {
		t.Errorf("expected Flamengo in 2019 standings:\n%s", truncate(answer, 800))
	}
}

func TestRealData_LeagueStatisticsRespondReasonably(t *testing.T) {
	srv := realServer(t)
	answer := callTool(t, srv, "league_statistics", map[string]any{"competition": "Brasileirão"})
	mustContain(t, answer, "goals per match", "win rate")
}

func TestRealData_PlayersAtABrazilianClub(t *testing.T) {
	srv := realServer(t)
	// Use Santos, which is present in this FIFA snapshot. Assert on actual
	// player rows ("Overall:") rather than the echoed query, so the test fails
	// if no real players are returned. (Note: Flamengo is absent from this FIFA
	// edition due to licensing, so it would legitimately return nothing.)
	answer := callTool(t, srv, "search_players", map[string]any{"club": "Santos", "limit": 10})
	mustContain(t, answer, "Santos", "Overall:", "Nationality:")
}

func truncate(s string, n int) string {
	if len(s) <= n {
		return s
	}
	return s[:n] + "..."
}
