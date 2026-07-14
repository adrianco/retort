// Package acceptance contains executable acceptance tests (ATDD) for the
// Brazilian Soccer MCP server. Tests exercise the System Under Test ONLY
// through the public MCP protocol surface (JSON-RPC: initialize, tools/list,
// tools/call) -- no back-door access to internal data structures. Each test
// stands up a fresh server over its own isolated fixture data so scenarios are
// atomic and independent, and asserts on WHAT the system answers in the
// language of the soccer domain.
package acceptance

import (
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"brazilian-soccer-mcp/mcp"
)

// --- JSON-RPC test harness (the only way these tests talk to the server) ---

type rpcRequest struct {
	JSONRPC string         `json:"jsonrpc"`
	ID      int            `json:"id"`
	Method  string         `json:"method"`
	Params  map[string]any `json:"params,omitempty"`
}

type rpcResponse struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      int             `json:"id"`
	Result  json.RawMessage `json:"result,omitempty"`
	Error   *rpcError       `json:"error,omitempty"`
}

type rpcError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

func send(t *testing.T, srv *mcp.Server, method string, params map[string]any) rpcResponse {
	t.Helper()
	reqBytes, err := json.Marshal(rpcRequest{JSONRPC: "2.0", ID: 1, Method: method, Params: params})
	if err != nil {
		t.Fatalf("marshal request: %v", err)
	}
	respBytes := srv.Handle(reqBytes)
	var resp rpcResponse
	if err := json.Unmarshal(respBytes, &resp); err != nil {
		t.Fatalf("unmarshal response %q: %v", respBytes, err)
	}
	return resp
}

// callTool invokes an MCP tool and returns its textual answer, failing on any
// protocol or tool error.
func callTool(t *testing.T, srv *mcp.Server, name string, args map[string]any) string {
	t.Helper()
	resp := send(t, srv, "tools/call", map[string]any{"name": name, "arguments": args})
	if resp.Error != nil {
		t.Fatalf("tool %s returned protocol error: %s", name, resp.Error.Message)
	}
	var result struct {
		IsError bool `json:"isError"`
		Content []struct {
			Type string `json:"type"`
			Text string `json:"text"`
		} `json:"content"`
	}
	if err := json.Unmarshal(resp.Result, &result); err != nil {
		t.Fatalf("decode tool result: %v (%s)", err, resp.Result)
	}
	if len(result.Content) == 0 {
		t.Fatalf("tool %s returned no content", name)
	}
	var sb strings.Builder
	for _, c := range result.Content {
		sb.WriteString(c.Text)
		sb.WriteString("\n")
	}
	if result.IsError {
		t.Fatalf("tool %s reported an error: %s", name, sb.String())
	}
	return sb.String()
}

// newServer writes the given fixture files into a fresh temp data dir and
// returns a running server pointed at it.
func newServer(t *testing.T, fixtures map[string]string) *mcp.Server {
	t.Helper()
	dir := t.TempDir()
	for name, content := range fixtures {
		if err := os.WriteFile(filepath.Join(dir, name), []byte(content), 0o644); err != nil {
			t.Fatalf("write fixture %s: %v", name, err)
		}
	}
	srv, err := mcp.NewServer(dir)
	if err != nil {
		t.Fatalf("start server: %v", err)
	}
	return srv
}

func mustContain(t *testing.T, haystack string, needles ...string) {
	t.Helper()
	for _, n := range needles {
		if !strings.Contains(haystack, n) {
			t.Errorf("expected answer to contain %q\n--- answer ---\n%s", n, haystack)
		}
	}
}

// --- Fixtures expressed in the real CSV formats the loaders must handle ---

const brasileiraoDerby = `"datetime","home_team","home_team_state","away_team","away_team_state","home_goal","away_goal","season","round"
2023-09-03 16:00:00,"Flamengo-RJ","RJ","Fluminense-RJ","RJ",2,1,2023,22
2023-05-28 16:00:00,"Fluminense-RJ","RJ","Flamengo-RJ","RJ",1,0,2023,8
2022-04-10 16:00:00,"Flamengo-RJ","RJ","Fluminense-RJ","RJ",0,0,2022,3
2023-07-10 16:00:00,"Palmeiras-SP","SP","Santos-SP","SP",3,0,2023,15
`

// A small but complete round-robin so a standings table can be computed.
const brasileiraoMiniLeague = `"datetime","home_team","home_team_state","away_team","away_team_state","home_goal","away_goal","season","round"
2019-05-01 16:00:00,"Flamengo-RJ","RJ","Santos-SP","SP",2,0,2019,1
2019-05-08 16:00:00,"Santos-SP","SP","Flamengo-RJ","RJ",1,1,2019,2
2019-05-01 18:00:00,"Palmeiras-SP","SP","Flamengo-RJ","RJ",0,1,2019,1
2019-05-08 18:00:00,"Flamengo-RJ","RJ","Palmeiras-SP","SP",3,1,2019,2
2019-05-01 20:00:00,"Santos-SP","SP","Palmeiras-SP","SP",1,0,2019,1
2019-05-08 20:00:00,"Palmeiras-SP","SP","Santos-SP","SP",2,2,2019,2
`

// FIFA player data including Brazilians at Brazilian and foreign clubs, plus a
// non-Brazilian to prove nationality filtering. Header mirrors the real file
// (BOM + many columns); only the early columns carry the values under test.
const fifaPlayers = "\ufeff,ID,Name,Age,Photo,Nationality,Flag,Overall,Potential,Club,Club Logo,Value,Wage,Special,Preferred Foot,International Reputation,Weak Foot,Skill Moves,Work Rate,Body Type,Real Face,Position,Jersey Number\n" +
	"0,190871,Neymar Jr,26,x,Brazil,x,92,93,Paris Saint-Germain,x,1,1,1,Left,5,5,5,High,Normal,Yes,LW,10\n" +
	"1,200145,Casemiro,26,x,Brazil,x,88,90,Real Madrid,x,1,1,1,Right,4,3,2,High,Normal,Yes,CDM,14\n" +
	"2,100001,Gabriel Barbosa,26,x,Brazil,x,82,84,Flamengo,x,1,1,1,Right,4,4,4,High,Normal,Yes,ST,9\n" +
	"3,100002,Pedro,25,x,Brazil,x,79,84,Flamengo,x,1,1,1,Right,3,3,3,High,Normal,Yes,ST,21\n" +
	"4,100003,Dudu,27,x,Brazil,x,78,80,Palmeiras,x,1,1,1,Right,3,4,4,High,Normal,Yes,RW,7\n" +
	"5,158023,L. Messi,31,x,Argentina,x,94,94,FC Barcelona,x,1,1,1,Left,5,4,4,Medium,Normal,Yes,RF,10\n"

const libertadores = `"datetime","home_team","away_team","home_goal","away_goal","season","stage"
2021-11-27 17:00:00,"Palmeiras-SP","Flamengo-RJ",2,1,2021,"final"
2021-04-21 19:15:00,"Nacional (URU)","Barcelona-EQU",2,2,2021,"group stage"
`

const copaDoBrasil = `"round","datetime","home_team","away_team","home_goal","away_goal","season"
"final",2022-10-19 21:45:00,"Flamengo-RJ","Corinthians-SP",1,1,2022
"final",2022-10-12 21:45:00,"Corinthians-SP","Flamengo-RJ",0,0,2022
`

// Historical Brasileirão in the Brazilian/Portuguese format (DD/MM/YYYY dates,
// Portuguese column names, accents).
const historicalBR = `ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena,OBS
2003.01.0001,29/03/2003,2003,1,São Paulo,Grêmio,2,1,SP,RS,Mandante,Morumbi,
2003.01.0002,30/03/2003,2003,1,Grêmio,São Paulo,0,0,RS,SP,Empate,Olímpico,
`

// Extended stats file: tournament-keyed, float goals, ISO dates.
const extendedStats = `tournament,home,home_goal,away_goal,away,home_corner,away_corner,home_attack,away_attack,home_shots,away_shots,time,date,ht_diff,at_diff,ht_result,at_result,total_corners
Copa do Brasil,Sao Paulo,1.0,1.0,Flamengo,2.0,4.0,75.0,104.0,8.0,13.0,20:00:00,2023-09-24,0.0,0.0,DRAW,DRAW,6.0
`

// === Protocol-level acceptance tests ===

func TestServerInitializesAndAdvertisesItsTools(t *testing.T) {
	srv := newServer(t, map[string]string{"Brasileirao_Matches.csv": brasileiraoDerby})

	initResp := send(t, srv, "initialize", nil)
	if initResp.Error != nil {
		t.Fatalf("initialize failed: %s", initResp.Error.Message)
	}
	var initResult struct {
		ProtocolVersion string `json:"protocolVersion"`
		ServerInfo      struct {
			Name string `json:"name"`
		} `json:"serverInfo"`
	}
	if err := json.Unmarshal(initResult2(t, initResp), &initResult); err != nil {
		t.Fatalf("decode initialize: %v", err)
	}
	if initResult.ProtocolVersion == "" {
		t.Errorf("expected a protocol version from initialize")
	}
	if initResult.ServerInfo.Name == "" {
		t.Errorf("expected the server to identify itself")
	}

	listResp := send(t, srv, "tools/list", nil)
	if listResp.Error != nil {
		t.Fatalf("tools/list failed: %s", listResp.Error.Message)
	}
	var listResult struct {
		Tools []struct {
			Name        string          `json:"name"`
			Description string          `json:"description"`
			InputSchema json.RawMessage `json:"inputSchema"`
		} `json:"tools"`
	}
	if err := json.Unmarshal(listResp.Result, &listResult); err != nil {
		t.Fatalf("decode tools/list: %v", err)
	}
	got := map[string]bool{}
	for _, tool := range listResult.Tools {
		if tool.Description == "" || len(tool.InputSchema) == 0 {
			t.Errorf("tool %q must advertise a description and input schema", tool.Name)
		}
		got[tool.Name] = true
	}
	for _, want := range []string{"find_matches", "get_team_stats", "compare_teams", "search_players", "get_standings", "league_statistics"} {
		if !got[want] {
			t.Errorf("expected tool %q to be advertised; got %v", want, keys(got))
		}
	}
}

func initResult2(t *testing.T, r rpcResponse) []byte {
	t.Helper()
	return r.Result
}

func keys(m map[string]bool) []string {
	out := make([]string, 0, len(m))
	for k := range m {
		out = append(out, k)
	}
	return out
}

func TestUnknownToolReportsError(t *testing.T) {
	srv := newServer(t, map[string]string{"Brasileirao_Matches.csv": brasileiraoDerby})
	resp := send(t, srv, "tools/call", map[string]any{"name": "no_such_tool", "arguments": map[string]any{}})
	// Either a JSON-RPC error or a tool-level isError is acceptable; silence is not.
	if resp.Error == nil {
		var result struct {
			IsError bool `json:"isError"`
		}
		_ = json.Unmarshal(resp.Result, &result)
		if !result.IsError {
			t.Fatalf("expected an error for an unknown tool, got %s", resp.Result)
		}
	}
}

// === Match queries ===

func TestFindMatchesBetweenTwoTeamsReportsHeadToHead(t *testing.T) {
	srv := newServer(t, map[string]string{"Brasileirao_Matches.csv": brasileiraoDerby})

	answer := callTool(t, srv, "find_matches", map[string]any{
		"team":     "Flamengo",
		"opponent": "Fluminense",
	})

	// Both Fla-Flu matches, but not the unrelated Palmeiras vs Santos game.
	mustContain(t, answer, "Flamengo", "Fluminense", "2023-09-03", "2023-05-28")
	if strings.Contains(answer, "Santos") {
		t.Errorf("Fla-Flu query should not return the Palmeiras vs Santos match:\n%s", answer)
	}
	// Head-to-head from the matches in the dataset: 1 Flamengo win, 1 Fluminense win.
	mustContain(t, answer, "head-to-head")
	if !strings.Contains(strings.ToLower(answer), "flamengo: 1") && !strings.Contains(answer, "1 win") {
		t.Errorf("expected a head-to-head record (Flamengo 1, Fluminense 1):\n%s", answer)
	}
}

func TestFindMatchesByTeamAndSeason(t *testing.T) {
	srv := newServer(t, map[string]string{"Brasileirao_Matches.csv": brasileiraoDerby})

	answer := callTool(t, srv, "find_matches", map[string]any{
		"team":   "Flamengo",
		"season": 2023,
	})
	mustContain(t, answer, "2023-09-03", "2023-05-28")
	if strings.Contains(answer, "2022") {
		t.Errorf("season filter should exclude the 2022 match:\n%s", answer)
	}
}

func TestFindMatchesByDateRange(t *testing.T) {
	srv := newServer(t, map[string]string{"Brasileirao_Matches.csv": brasileiraoDerby})

	answer := callTool(t, srv, "find_matches", map[string]any{
		"team":       "Flamengo",
		"start_date": "2023-01-01",
		"end_date":   "2023-06-30",
	})
	mustContain(t, answer, "2023-05-28")
	if strings.Contains(answer, "2023-09-03") || strings.Contains(answer, "2022") {
		t.Errorf("date range should only include the May 2023 match:\n%s", answer)
	}
}

func TestFindMatchesByCompetitionAcrossFiles(t *testing.T) {
	srv := newServer(t, map[string]string{
		"Brasileirao_Matches.csv":  brasileiraoDerby,
		"Libertadores_Matches.csv": libertadores,
	})

	answer := callTool(t, srv, "find_matches", map[string]any{
		"team":        "Flamengo",
		"competition": "Libertadores",
	})
	mustContain(t, answer, "Palmeiras", "Flamengo", "2021")
	if strings.Contains(answer, "Fluminense") {
		t.Errorf("Libertadores filter should not surface Brasileirão Fla-Flu matches:\n%s", answer)
	}
}

// === Team queries ===

func TestTeamStatisticsWinLossDrawAndGoals(t *testing.T) {
	srv := newServer(t, map[string]string{"Brasileirao_Matches.csv": brasileiraoMiniLeague})

	answer := callTool(t, srv, "get_team_stats", map[string]any{
		"team":   "Flamengo",
		"season": 2019,
	})
	// Flamengo 2019 mini-league: vs Santos (W 2-0, D 1-1), vs Palmeiras (W away 0-1, W 3-1).
	// Played 4, Wins 3, Draws 1, Losses 0, GF 7, GA 2.
	mustContain(t, answer, "Flamengo")
	mustContain(t, answer, "Wins", "Draws", "Losses")
	mustContain(t, answer, "3", "1", "0", "7", "2")
}

func TestTeamHomeRecordOnly(t *testing.T) {
	srv := newServer(t, map[string]string{"Brasileirao_Matches.csv": brasileiraoMiniLeague})

	answer := callTool(t, srv, "get_team_stats", map[string]any{
		"team":   "Flamengo",
		"season": 2019,
		"venue":  "home",
	})
	// Flamengo home in 2019: vs Santos 2-0 (W), vs Palmeiras 3-1 (W) => 2 matches, 2 wins.
	mustContain(t, answer, "home")
	mustContain(t, answer, "Flamengo", "2")
	if strings.Contains(answer, "Matches: 4") {
		t.Errorf("home filter should report 2 home matches, not 4:\n%s", answer)
	}
}

func TestCompareTeamsHeadToHead(t *testing.T) {
	srv := newServer(t, map[string]string{"Brasileirao_Matches.csv": brasileiraoDerby})

	answer := callTool(t, srv, "compare_teams", map[string]any{
		"team1": "Flamengo",
		"team2": "Fluminense",
	})
	// 3 Fla-Flu matches in the derby fixture: Fla 2-1, Flu 1-0, 0-0 draw => 1 win each, 1 draw.
	mustContain(t, answer, "Flamengo", "Fluminense")
	mustContain(t, answer, "draw")
}

// === Player queries ===

func TestSearchPlayerByName(t *testing.T) {
	srv := newServer(t, map[string]string{"fifa_data.csv": fifaPlayers})

	answer := callTool(t, srv, "search_players", map[string]any{"name": "Gabriel Barbosa"})
	mustContain(t, answer, "Gabriel Barbosa", "Flamengo", "82")
	if strings.Contains(answer, "Messi") {
		t.Errorf("name search for Gabriel Barbosa should not return Messi:\n%s", answer)
	}
}

func TestSearchPlayersByNationalityAreSortedByRating(t *testing.T) {
	srv := newServer(t, map[string]string{"fifa_data.csv": fifaPlayers})

	answer := callTool(t, srv, "search_players", map[string]any{"nationality": "Brazil"})
	// Only Brazilians, and Argentina's Messi excluded.
	mustContain(t, answer, "Neymar", "Casemiro", "Gabriel Barbosa")
	if strings.Contains(answer, "Messi") {
		t.Errorf("nationality=Brazil must exclude the Argentine player:\n%s", answer)
	}
	// Highest-rated Brazilian (Neymar, 92) must appear before a lower-rated one (Dudu, 78).
	if strings.Index(answer, "Neymar") > strings.Index(answer, "Dudu") {
		t.Errorf("expected players sorted by rating (Neymar before Dudu):\n%s", answer)
	}
}

func TestSearchPlayersByClub(t *testing.T) {
	srv := newServer(t, map[string]string{"fifa_data.csv": fifaPlayers})

	answer := callTool(t, srv, "search_players", map[string]any{"club": "Flamengo"})
	mustContain(t, answer, "Gabriel Barbosa", "Pedro")
	if strings.Contains(answer, "Dudu") || strings.Contains(answer, "Messi") {
		t.Errorf("club=Flamengo should only return Flamengo players:\n%s", answer)
	}
}

// === Competition queries ===

func TestStandingsAreCalculatedFromMatchResults(t *testing.T) {
	srv := newServer(t, map[string]string{"Brasileirao_Matches.csv": brasileiraoMiniLeague})

	answer := callTool(t, srv, "get_standings", map[string]any{
		"competition": "Brasileirão",
		"season":      2019,
	})
	// Points: Flamengo 3W+1D = 10; Santos 1W? Santos: vs Fla D,D? Recompute below in impl.
	// Regardless of exact tail, Flamengo tops the table and all three teams appear.
	mustContain(t, answer, "Flamengo", "Santos", "Palmeiras", "pts")
	flaIdx := strings.Index(answer, "Flamengo")
	if flaIdx == -1 || flaIdx > strings.Index(answer, "Palmeiras") {
		t.Errorf("expected Flamengo to lead the 2019 standings:\n%s", answer)
	}
}

// === Statistical analysis ===

func TestLeagueStatisticsAggregatesGoalsAndHomeAdvantage(t *testing.T) {
	srv := newServer(t, map[string]string{"Brasileirao_Matches.csv": brasileiraoMiniLeague})

	answer := callTool(t, srv, "league_statistics", map[string]any{
		"competition": "Brasileirão",
		"season":      2019,
	})
	mustContain(t, answer, "goals per match", "win rate")
	// 6 matches in the mini league.
	mustContain(t, answer, "6")
}

func TestBiggestWinsAreReported(t *testing.T) {
	srv := newServer(t, map[string]string{"Brasileirao_Matches.csv": brasileiraoDerby})

	answer := callTool(t, srv, "league_statistics", map[string]any{"season": 2023})
	// Largest margin in the 2023 fixture is Palmeiras 3-0 Santos.
	mustContain(t, answer, "Palmeiras", "Santos", "3")
}

// === Data quality handling ===

func TestTeamNameVariationsAreNormalized(t *testing.T) {
	// "São Paulo" (accented, no suffix) in the historical file must match a
	// query of "Sao Paulo" (no accent).
	srv := newServer(t, map[string]string{"novo_campeonato_brasileiro.csv": historicalBR})

	answer := callTool(t, srv, "find_matches", map[string]any{"team": "Sao Paulo"})
	mustContain(t, answer, "Paulo", "Grêmio", "2003")
}

func TestBrazilianDateFormatIsParsed(t *testing.T) {
	srv := newServer(t, map[string]string{"novo_campeonato_brasileiro.csv": historicalBR})

	answer := callTool(t, srv, "find_matches", map[string]any{
		"team":   "São Paulo",
		"season": 2003,
	})
	// DD/MM/YYYY in source should be presented as ISO 2003-03-29 / 2003-03-30.
	mustContain(t, answer, "2003-03-29")
}

func TestExtendedStatsFileIsQueryable(t *testing.T) {
	srv := newServer(t, map[string]string{"BR-Football-Dataset.csv": extendedStats})

	answer := callTool(t, srv, "find_matches", map[string]any{"team": "Flamengo"})
	mustContain(t, answer, "Flamengo", "2023-09-24")
}

func TestCupFinalsAcrossCompetition(t *testing.T) {
	srv := newServer(t, map[string]string{"Brazilian_Cup_Matches.csv": copaDoBrasil})

	answer := callTool(t, srv, "find_matches", map[string]any{
		"competition": "Copa do Brasil",
		"team":        "Corinthians",
	})
	mustContain(t, answer, "Flamengo", "Corinthians", "2022")
}
