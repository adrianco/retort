package mcpserver

import (
	"context"
	"strings"
	"testing"

	"brazilian-soccer-mcp/internal/soccer"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

func testStore(t *testing.T) *soccer.Store {
	t.Helper()
	parse := func(s string) soccer.Match {
		d, err := soccer.ParseDate(s)
		if err != nil {
			t.Fatal(err)
		}
		return soccer.Match{Date: d}
	}
	mk := func(date, competition string, season int, home, away string, hg, ag int) soccer.Match {
		m := parse(date)
		m.Competition = competition
		m.Season = season
		m.HomeTeam = home
		m.AwayTeam = away
		m.HomeKey = soccer.NormalizeTeamKey(home)
		m.AwayKey = soccer.NormalizeTeamKey(away)
		m.HomeGoals = hg
		m.AwayGoals = ag
		return m
	}
	matches := []soccer.Match{
		mk("2023-05-28", "Brasileirao", 2023, "Fluminense", "Flamengo", 1, 0),
		mk("2023-09-03", "Brasileirao", 2023, "Flamengo", "Fluminense", 2, 1),
		mk("2022-11-06", "Brasileirao", 2022, "Flamengo", "Palmeiras", 3, 0),
	}
	players := []soccer.Player{
		{Name: "Neymar Jr", Nationality: "Brazil", Overall: 92, Club: "Paris Saint-Germain", Position: "LW"},
		{Name: "Gabriel Barbosa", Nationality: "Brazil", Overall: 77, Club: "Flamengo", Position: "ST"},
	}
	return soccer.NewStore(matches, players)
}

func connectTestServer(ctx context.Context, t *testing.T, store *soccer.Store) *mcp.ClientSession {
	t.Helper()
	server := New(store)
	t1, t2 := mcp.NewInMemoryTransports()
	if _, err := server.Connect(ctx, t1, nil); err != nil {
		t.Fatalf("server.Connect: %v", err)
	}
	client := mcp.NewClient(&mcp.Implementation{Name: "test-client", Version: "v0.0.1"}, nil)
	session, err := client.Connect(ctx, t2, nil)
	if err != nil {
		t.Fatalf("client.Connect: %v", err)
	}
	t.Cleanup(func() { session.Close() })
	return session
}

func callTool(ctx context.Context, t *testing.T, session *mcp.ClientSession, name string, args map[string]any) string {
	t.Helper()
	res, err := session.CallTool(ctx, &mcp.CallToolParams{Name: name, Arguments: args})
	if err != nil {
		t.Fatalf("CallTool(%s): %v", name, err)
	}
	if res.IsError {
		t.Fatalf("CallTool(%s) returned tool error: %+v", name, res.Content)
	}
	if len(res.Content) == 0 {
		t.Fatalf("CallTool(%s) returned no content", name)
	}
	tc, ok := res.Content[0].(*mcp.TextContent)
	if !ok {
		t.Fatalf("CallTool(%s) content[0] is not text: %T", name, res.Content[0])
	}
	return tc.Text
}

func TestServerTools(t *testing.T) {
	ctx := context.Background()
	store := testStore(t)
	session := connectTestServer(ctx, t, store)

	cases := []struct {
		tool string
		args map[string]any
		want string
	}{
		{"find_matches", map[string]any{"team": "Flamengo"}, "Flamengo"},
		{"head_to_head", map[string]any{"team_a": "Flamengo", "team_b": "Fluminense"}, "Head-to-head"},
		{"team_record", map[string]any{"team": "Flamengo"}, "record"},
		{"standings", map[string]any{"competition": "Brasileirao", "season": float64(2023)}, "Standings"},
		{"biggest_wins", map[string]any{}, "Fluminense"},
		{"stats_summary", map[string]any{"competition": "Brasileirao"}, "Average goals per match"},
		{"search_players", map[string]any{"nationality": "Brazil"}, "Neymar Jr"},
	}
	for _, tc := range cases {
		t.Run(tc.tool, func(t *testing.T) {
			got := callTool(ctx, t, session, tc.tool, tc.args)
			if !strings.Contains(got, tc.want) {
				t.Errorf("tool %s response = %q, want substring %q", tc.tool, got, tc.want)
			}
		})
	}
}
