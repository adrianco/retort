// Package app_test contains the executable acceptance specification for the
// Brazilian Soccer MCP server.
//
// These tests are written from the perspective of an external MCP client. They
// exercise the System Under Test *only* through the public MCP protocol
// (initialize -> tools/list -> tools/call over JSON-RPC 2.0). There is no
// back-door access to internal data structures.
//
// Each scenario is atomic and independent: it seeds its own controlled set of
// fixture CSV files into a fresh temporary directory, starts a brand new server
// instance pointed at that directory, and asserts on WHAT the system reports in
// the language of the problem domain (matches, head-to-head records, standings,
// players, statistics) rather than HOW it computes them.
package app_test

import (
	"bufio"
	"context"
	"encoding/json"
	"io"
	"os"
	"path/filepath"
	"testing"
	"time"

	app "brazilian-soccer-mcp"
)

// ----------------------------------------------------------------------------
// MCP client harness: drives the server through the real JSON-RPC/MCP protocol.
// ----------------------------------------------------------------------------

type mcpSession struct {
	t      *testing.T
	enc    *json.Encoder
	dec    *json.Decoder
	cancel context.CancelFunc
	nextID int
}

type rpcError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

type rpcResponse struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id"`
	Result  json.RawMessage `json:"result"`
	Error   *rpcError       `json:"error"`
}

// startSession boots a fresh MCP server over in-memory pipes and performs the
// MCP initialize handshake, returning a ready-to-use session.
func startSession(t *testing.T, dataDir string) *mcpSession {
	t.Helper()

	srv, err := app.NewMCPServer(dataDir)
	if err != nil {
		t.Fatalf("failed to create MCP server: %v", err)
	}

	clientReader, serverWriter := io.Pipe() // server -> client
	serverReader, clientWriter := io.Pipe() // client -> server

	ctx, cancel := context.WithCancel(context.Background())
	go func() {
		_ = srv.Serve(ctx, serverReader, serverWriter)
		_ = serverWriter.Close()
	}()

	s := &mcpSession{
		t:      t,
		enc:    json.NewEncoder(clientWriter),
		dec:    json.NewDecoder(bufio.NewReader(clientReader)),
		cancel: cancel,
		nextID: 1,
	}
	t.Cleanup(func() {
		cancel()
		_ = clientWriter.Close()
	})

	// MCP handshake.
	s.call("initialize", map[string]any{
		"protocolVersion": "2024-11-05",
		"capabilities":    map[string]any{},
		"clientInfo":      map[string]any{"name": "acceptance-test", "version": "1.0"},
	})
	s.notify("notifications/initialized", map[string]any{})

	return s
}

func (s *mcpSession) call(method string, params any) rpcResponse {
	s.t.Helper()
	id := s.nextID
	s.nextID++
	req := map[string]any{
		"jsonrpc": "2.0",
		"id":      id,
		"method":  method,
		"params":  params,
	}
	if err := s.enc.Encode(req); err != nil {
		s.t.Fatalf("failed to send %q: %v", method, err)
	}
	var resp rpcResponse
	done := make(chan error, 1)
	go func() { done <- s.dec.Decode(&resp) }()
	select {
	case err := <-done:
		if err != nil {
			s.t.Fatalf("failed to read response to %q: %v", method, err)
		}
	case <-time.After(10 * time.Second):
		s.t.Fatalf("timed out waiting for response to %q", method)
	}
	return resp
}

func (s *mcpSession) notify(method string, params any) {
	s.t.Helper()
	req := map[string]any{"jsonrpc": "2.0", "method": method, "params": params}
	if err := s.enc.Encode(req); err != nil {
		s.t.Fatalf("failed to send notification %q: %v", method, err)
	}
}

// callTool invokes an MCP tool and decodes its JSON text result into out.
func (s *mcpSession) callTool(name string, args map[string]any, out any) {
	s.t.Helper()
	resp := s.call("tools/call", map[string]any{"name": name, "arguments": args})
	if resp.Error != nil {
		s.t.Fatalf("tool %q returned protocol error: %s", name, resp.Error.Message)
	}
	var result struct {
		Content []struct {
			Type string `json:"type"`
			Text string `json:"text"`
		} `json:"content"`
		IsError bool `json:"isError"`
	}
	if err := json.Unmarshal(resp.Result, &result); err != nil {
		s.t.Fatalf("tool %q result not valid MCP content: %v", name, err)
	}
	if result.IsError {
		text := ""
		if len(result.Content) > 0 {
			text = result.Content[0].Text
		}
		s.t.Fatalf("tool %q reported an error: %s", name, text)
	}
	if len(result.Content) == 0 {
		s.t.Fatalf("tool %q returned no content", name)
	}
	if out != nil {
		if err := json.Unmarshal([]byte(result.Content[0].Text), out); err != nil {
			s.t.Fatalf("tool %q text payload not valid JSON: %v\npayload: %s", name, err, result.Content[0].Text)
		}
	}
}

// callToolExpectingError invokes a tool and asserts it reports a domain error.
func (s *mcpSession) callToolExpectingError(name string, args map[string]any) string {
	s.t.Helper()
	resp := s.call("tools/call", map[string]any{"name": name, "arguments": args})
	if resp.Error != nil {
		return resp.Error.Message
	}
	var result struct {
		Content []struct {
			Text string `json:"text"`
		} `json:"content"`
		IsError bool `json:"isError"`
	}
	if err := json.Unmarshal(resp.Result, &result); err != nil {
		s.t.Fatalf("tool %q result not valid MCP content: %v", name, err)
	}
	if !result.IsError {
		s.t.Fatalf("expected tool %q to report an error, but it succeeded", name)
	}
	if len(result.Content) > 0 {
		return result.Content[0].Text
	}
	return ""
}

// ----------------------------------------------------------------------------
// Fixture helpers: seed a fresh, empty system with controlled data.
// ----------------------------------------------------------------------------

func newDataDir(t *testing.T) string {
	t.Helper()
	dir := t.TempDir()
	kaggle := filepath.Join(dir, "kaggle")
	if err := os.MkdirAll(kaggle, 0o755); err != nil {
		t.Fatalf("mkdir: %v", err)
	}
	return dir
}

func writeFile(t *testing.T, dataDir, name, content string) {
	t.Helper()
	path := filepath.Join(dataDir, "kaggle", name)
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatalf("write %s: %v", name, err)
	}
}

// Convenience seeders for each provided dataset schema.

func seedBrasileirao(t *testing.T, dataDir, rows string) {
	header := `"datetime","home_team","home_team_state","away_team","away_team_state","home_goal","away_goal","season","round"` + "\n"
	writeFile(t, dataDir, "Brasileirao_Matches.csv", header+rows)
}

func seedCopaDoBrasil(t *testing.T, dataDir, rows string) {
	header := `"round","datetime","home_team","away_team","home_goal","away_goal","season"` + "\n"
	writeFile(t, dataDir, "Brazilian_Cup_Matches.csv", header+rows)
}

func seedLibertadores(t *testing.T, dataDir, rows string) {
	header := `"datetime","home_team","away_team","home_goal","away_goal","season","stage"` + "\n"
	writeFile(t, dataDir, "Libertadores_Matches.csv", header+rows)
}

func seedHistorical(t *testing.T, dataDir, rows string) {
	header := "ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena,OBS\n"
	writeFile(t, dataDir, "novo_campeonato_brasileiro.csv", header+rows)
}

func seedExtended(t *testing.T, dataDir, rows string) {
	header := "tournament,home,home_goal,away_goal,away,home_corner,away_corner,home_attack,away_attack,home_shots,away_shots,time,date,ht_diff,at_diff,ht_result,at_result,total_corners\n"
	writeFile(t, dataDir, "BR-Football-Dataset.csv", header+rows)
}

func seedPlayers(t *testing.T, dataDir, rows string) {
	header := ",ID,Name,Age,Photo,Nationality,Flag,Overall,Potential,Club,Club Logo,Value,Wage,Special,Preferred Foot,International Reputation,Weak Foot,Skill Moves,Work Rate,Body Type,Real Face,Position,Jersey Number,Joined,Loaned From,Contract Valid Until,Height,Weight\n"
	writeFile(t, dataDir, "fifa_data.csv", header+rows)
}

// playerRow builds a fifa_data.csv row from the most relevant fields.
func playerRow(idx int, id, name, age, nationality, overall, potential, club, position string) string {
	return join([]string{
		itoa(idx), id, name, age, "photo", nationality, "flag", overall, potential, club,
		"logo", "€1M", "€1K", "1000", "Right", "1", "1", "1", "Medium/ Medium", "Normal",
		"No", position, "10", "Jul 1, 2018", "", "2021", "5'9", "150lbs",
	}) + "\n"
}

func join(fields []string) string {
	out := ""
	for i, f := range fields {
		if i > 0 {
			out += ","
		}
		out += f
	}
	return out
}

func itoa(i int) string {
	return string(rune('0' + i%10)) // sufficient for tiny fixtures (idx 0-9)
}

// ----------------------------------------------------------------------------
// MCP protocol-level acceptance tests.
// ----------------------------------------------------------------------------

func TestInitializeHandshakeReportsServerAndTools(t *testing.T) {
	dir := newDataDir(t)
	srv, err := app.NewMCPServer(dir)
	if err != nil {
		t.Fatalf("create server: %v", err)
	}
	clientReader, serverWriter := io.Pipe()
	serverReader, clientWriter := io.Pipe()
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	go func() { _ = srv.Serve(ctx, serverReader, serverWriter) }()
	enc := json.NewEncoder(clientWriter)
	dec := json.NewDecoder(clientReader)

	_ = enc.Encode(map[string]any{
		"jsonrpc": "2.0", "id": 1, "method": "initialize",
		"params": map[string]any{"protocolVersion": "2024-11-05"},
	})
	var resp rpcResponse
	if err := dec.Decode(&resp); err != nil {
		t.Fatalf("decode initialize response: %v", err)
	}
	if resp.Error != nil {
		t.Fatalf("initialize failed: %s", resp.Error.Message)
	}
	var init struct {
		ProtocolVersion string `json:"protocolVersion"`
		ServerInfo      struct {
			Name string `json:"name"`
		} `json:"serverInfo"`
		Capabilities struct {
			Tools map[string]any `json:"tools"`
		} `json:"capabilities"`
	}
	if err := json.Unmarshal(resp.Result, &init); err != nil {
		t.Fatalf("bad initialize result: %v", err)
	}
	if init.ServerInfo.Name == "" {
		t.Errorf("expected server to identify itself by name")
	}
	if init.Capabilities.Tools == nil {
		t.Errorf("expected server to advertise tools capability")
	}
}

func TestToolsListAdvertisesAllRequiredCapabilities(t *testing.T) {
	dir := newDataDir(t)
	s := startSession(t, dir)
	resp := s.call("tools/list", map[string]any{})
	if resp.Error != nil {
		t.Fatalf("tools/list failed: %s", resp.Error.Message)
	}
	var list struct {
		Tools []struct {
			Name        string         `json:"name"`
			Description string         `json:"description"`
			InputSchema map[string]any `json:"inputSchema"`
		} `json:"tools"`
	}
	if err := json.Unmarshal(resp.Result, &list); err != nil {
		t.Fatalf("bad tools/list result: %v", err)
	}
	got := map[string]bool{}
	for _, tool := range list.Tools {
		if tool.Description == "" {
			t.Errorf("tool %q is missing a description", tool.Name)
		}
		if tool.InputSchema == nil {
			t.Errorf("tool %q is missing an input schema", tool.Name)
		}
		got[tool.Name] = true
	}
	// One tool per required capability category from the specification.
	for _, want := range []string{
		"find_matches",   // 1. Match Queries
		"get_team_stats", // 2. Team Queries
		"head_to_head",   // 2. Team Queries (comparison)
		"search_players", // 3. Player Queries
		"get_standings",  // 4. Competition Queries
		"league_stats",   // 5. Statistical Analysis
		"team_rankings",  // 5. Statistical Analysis (best home/away record)
	} {
		if !got[want] {
			t.Errorf("expected tool %q to be advertised", want)
		}
	}
}

func TestUnknownToolReportsError(t *testing.T) {
	dir := newDataDir(t)
	s := startSession(t, dir)
	msg := s.callToolExpectingError("no_such_tool", map[string]any{})
	if msg == "" {
		t.Errorf("expected a helpful error message for unknown tool")
	}
}

// ----------------------------------------------------------------------------
// 1. Match Queries
// ----------------------------------------------------------------------------

type matchDTO struct {
	Date        string `json:"date"`
	Competition string `json:"competition"`
	HomeTeam    string `json:"home_team"`
	AwayTeam    string `json:"away_team"`
	HomeGoal    int    `json:"home_goal"`
	AwayGoal    int    `json:"away_goal"`
	Season      int    `json:"season"`
}

type findMatchesResult struct {
	Count      int        `json:"count"`
	Matches    []matchDTO `json:"matches"`
	HeadToHead *struct {
		Team         string `json:"team"`
		Opponent     string `json:"opponent"`
		TeamWins     int    `json:"team_wins"`
		OpponentWins int    `json:"opponent_wins"`
		Draws        int    `json:"draws"`
	} `json:"head_to_head"`
}

func TestFindMatchesBetweenTwoTeamsReturnsHeadToHead(t *testing.T) {
	dir := newDataDir(t)
	// A classic derby across two seasons, with state suffixes that must be normalized.
	seedBrasileirao(t, dir, `
2023-09-03 16:00:00,"Flamengo-RJ","RJ","Fluminense-RJ","RJ",2,1,2023,22
2023-05-28 16:00:00,"Fluminense-RJ","RJ","Flamengo-RJ","RJ",1,0,2023,8
2022-07-10 16:00:00,"Flamengo-RJ","RJ","Fluminense-RJ","RJ",0,0,2022,15
2023-09-03 18:00:00,"Palmeiras-SP","SP","Santos-SP","SP",3,0,2023,22
`)
	s := startSession(t, dir)

	var res findMatchesResult
	s.callTool("find_matches", map[string]any{"team": "Flamengo", "opponent": "Fluminense"}, &res)

	if res.Count != 3 {
		t.Fatalf("expected 3 Fla-Flu matches, got %d", res.Count)
	}
	for _, m := range res.Matches {
		if m.Competition != "Brasileirao" {
			t.Errorf("expected Brasileirao competition, got %q", m.Competition)
		}
	}
	if res.HeadToHead == nil {
		t.Fatalf("expected a head-to-head summary when two teams are given")
	}
	// Flamengo: won 2-1 (home), lost 0-1 (away), drew 0-0 => 1 win, 1 loss, 1 draw.
	if res.HeadToHead.TeamWins != 1 || res.HeadToHead.OpponentWins != 1 || res.HeadToHead.Draws != 1 {
		t.Errorf("unexpected head-to-head: %+v", res.HeadToHead)
	}
}

func TestFindMatchesByTeamAndSeason(t *testing.T) {
	dir := newDataDir(t)
	seedBrasileirao(t, dir, `
2023-04-16 16:00:00,"Palmeiras-SP","SP","Cuiaba-MT","MT",2,1,2023,1
2022-04-10 16:00:00,"Palmeiras-SP","SP","Ceara-CE","CE",1,0,2022,1
2023-05-01 16:00:00,"Santos-SP","SP","Palmeiras-SP","SP",0,2,2023,5
`)
	s := startSession(t, dir)

	var res findMatchesResult
	s.callTool("find_matches", map[string]any{"team": "Palmeiras", "season": 2023}, &res)

	if res.Count != 2 {
		t.Fatalf("expected Palmeiras to have 2 matches in 2023, got %d", res.Count)
	}
	for _, m := range res.Matches {
		if m.Season != 2023 {
			t.Errorf("expected only 2023 matches, got season %d", m.Season)
		}
	}
}

func TestFindMatchesByCompetitionSearchesAllFiles(t *testing.T) {
	dir := newDataDir(t)
	seedBrasileirao(t, dir, `
2023-04-16 16:00:00,"Flamengo-RJ","RJ","Palmeiras-SP","SP",1,1,2023,1
`)
	seedCopaDoBrasil(t, dir, `
"3",2023-05-17 21:30:00,"Flamengo","Athletico Paranaense",1,0,2023
`)
	seedLibertadores(t, dir, `
2023-04-05 21:00:00,"Flamengo","Aucas",2,1,2023,"group stage"
`)
	s := startSession(t, dir)

	var cup findMatchesResult
	s.callTool("find_matches", map[string]any{"team": "Flamengo", "competition": "Copa do Brasil"}, &cup)
	if cup.Count != 1 || cup.Matches[0].Competition != "Copa do Brasil" {
		t.Fatalf("expected exactly the Copa do Brasil match, got %+v", cup)
	}

	var liber findMatchesResult
	s.callTool("find_matches", map[string]any{"team": "Flamengo", "competition": "Libertadores"}, &liber)
	if liber.Count != 1 || liber.Matches[0].Competition != "Libertadores" {
		t.Fatalf("expected exactly the Libertadores match, got %+v", liber)
	}

	// Across all competitions Flamengo appears in three different matches.
	var all findMatchesResult
	s.callTool("find_matches", map[string]any{"team": "Flamengo"}, &all)
	if all.Count != 3 {
		t.Fatalf("expected Flamengo in 3 matches across competitions, got %d", all.Count)
	}
}

func TestFindMatchesByVenueHomeOnly(t *testing.T) {
	dir := newDataDir(t)
	seedBrasileirao(t, dir, `
2022-04-10 16:00:00,"Corinthians-SP","SP","Santos-SP","SP",2,0,2022,1
2022-05-10 16:00:00,"Santos-SP","SP","Corinthians-SP","SP",1,1,2022,5
`)
	s := startSession(t, dir)

	var home findMatchesResult
	s.callTool("find_matches", map[string]any{"team": "Corinthians", "venue": "home"}, &home)
	if home.Count != 1 || home.Matches[0].HomeTeam != "Corinthians" {
		t.Fatalf("expected only Corinthians home match, got %+v", home)
	}
}

func TestFindMatchesByDateRange(t *testing.T) {
	dir := newDataDir(t)
	seedBrasileirao(t, dir, `
2023-01-15 16:00:00,"Gremio-RS","RS","Internacional-RS","RS",1,0,2023,1
2023-06-15 16:00:00,"Gremio-RS","RS","Internacional-RS","RS",2,2,2023,15
2023-11-15 16:00:00,"Gremio-RS","RS","Internacional-RS","RS",0,1,2023,30
`)
	s := startSession(t, dir)

	var res findMatchesResult
	s.callTool("find_matches", map[string]any{
		"team":       "Gremio",
		"start_date": "2023-03-01",
		"end_date":   "2023-09-01",
	}, &res)
	if res.Count != 1 {
		t.Fatalf("expected 1 match in the date window, got %d", res.Count)
	}
	if res.Matches[0].Date != "2023-06-15" {
		t.Errorf("expected the June match, got %q", res.Matches[0].Date)
	}
}

// ----------------------------------------------------------------------------
// 2. Team Queries
// ----------------------------------------------------------------------------

type teamStatsResult struct {
	Team           string  `json:"team"`
	Matches        int     `json:"matches"`
	Wins           int     `json:"wins"`
	Draws          int     `json:"draws"`
	Losses         int     `json:"losses"`
	GoalsFor       int     `json:"goals_for"`
	GoalsAgainst   int     `json:"goals_against"`
	GoalDifference int     `json:"goal_difference"`
	Points         int     `json:"points"`
	WinRate        float64 `json:"win_rate"`
}

func TestTeamHomeRecordForSeason(t *testing.T) {
	dir := newDataDir(t)
	// Corinthians home games in 2022: 2W, 1D, 1L (plus an away game that must be excluded).
	seedBrasileirao(t, dir, `
2022-04-10 16:00:00,"Corinthians-SP","SP","Santos-SP","SP",2,0,2022,1
2022-04-20 16:00:00,"Corinthians-SP","SP","Palmeiras-SP","SP",3,1,2022,2
2022-05-01 16:00:00,"Corinthians-SP","SP","Flamengo-RJ","RJ",1,1,2022,3
2022-05-10 16:00:00,"Corinthians-SP","SP","Gremio-RS","RS",0,2,2022,4
2022-06-01 16:00:00,"Santos-SP","SP","Corinthians-SP","SP",4,0,2022,5
`)
	s := startSession(t, dir)

	var res teamStatsResult
	s.callTool("get_team_stats", map[string]any{
		"team":   "Corinthians",
		"season": 2022,
		"venue":  "home",
	}, &res)

	if res.Matches != 4 {
		t.Fatalf("expected 4 home matches, got %d", res.Matches)
	}
	if res.Wins != 2 || res.Draws != 1 || res.Losses != 1 {
		t.Errorf("expected 2W 1D 1L, got %dW %dD %dL", res.Wins, res.Draws, res.Losses)
	}
	if res.GoalsFor != 6 || res.GoalsAgainst != 4 {
		t.Errorf("expected GF=6 GA=4, got GF=%d GA=%d", res.GoalsFor, res.GoalsAgainst)
	}
	if res.Points != 7 {
		t.Errorf("expected 7 points (2*3+1), got %d", res.Points)
	}
	if res.WinRate < 0.49 || res.WinRate > 0.51 {
		t.Errorf("expected win rate ~0.50, got %.3f", res.WinRate)
	}
}

type headToHeadResult struct {
	TeamA      string `json:"team_a"`
	TeamB      string `json:"team_b"`
	Matches    int    `json:"matches"`
	TeamAWins  int    `json:"team_a_wins"`
	TeamBWins  int    `json:"team_b_wins"`
	Draws      int    `json:"draws"`
	TeamAGoals int    `json:"team_a_goals"`
	TeamBGoals int    `json:"team_b_goals"`
}

func TestCompareTwoTeamsHeadToHead(t *testing.T) {
	dir := newDataDir(t)
	seedBrasileirao(t, dir, `
2021-04-10 16:00:00,"Palmeiras-SP","SP","Santos-SP","SP",2,0,2021,1
2021-08-10 16:00:00,"Santos-SP","SP","Palmeiras-SP","SP",1,1,2021,20
2022-04-10 16:00:00,"Palmeiras-SP","SP","Santos-SP","SP",0,1,2022,1
`)
	s := startSession(t, dir)

	var res headToHeadResult
	s.callTool("head_to_head", map[string]any{"team_a": "Palmeiras", "team_b": "Santos"}, &res)

	if res.Matches != 3 {
		t.Fatalf("expected 3 meetings, got %d", res.Matches)
	}
	if res.TeamAWins != 1 || res.TeamBWins != 1 || res.Draws != 1 {
		t.Errorf("expected 1-1-1, got A=%d B=%d D=%d", res.TeamAWins, res.TeamBWins, res.Draws)
	}
	if res.TeamAGoals != 3 || res.TeamBGoals != 2 {
		t.Errorf("expected Palmeiras 3 goals, Santos 2; got %d / %d", res.TeamAGoals, res.TeamBGoals)
	}
}

// ----------------------------------------------------------------------------
// 3. Player Queries
// ----------------------------------------------------------------------------

type playerDTO struct {
	Name        string `json:"name"`
	Nationality string `json:"nationality"`
	Overall     int    `json:"overall"`
	Club        string `json:"club"`
	Position    string `json:"position"`
}

type searchPlayersResult struct {
	Count   int         `json:"count"`
	Players []playerDTO `json:"players"`
}

func TestSearchPlayersByNationalitySortedByRating(t *testing.T) {
	dir := newDataDir(t)
	seedPlayers(t, dir,
		playerRow(0, "1", "Neymar Jr", "31", "Brazil", "89", "89", "Al Hilal", "LW")+
			playerRow(1, "2", "Alisson", "30", "Brazil", "89", "90", "Liverpool", "GK")+
			playerRow(2, "3", "Lionel Messi", "36", "Argentina", "90", "90", "Inter Miami", "RW")+
			playerRow(3, "4", "Gabriel Barbosa", "27", "Brazil", "82", "84", "Flamengo", "ST"),
	)
	s := startSession(t, dir)

	var res searchPlayersResult
	s.callTool("search_players", map[string]any{"nationality": "Brazil"}, &res)

	if res.Count != 3 {
		t.Fatalf("expected 3 Brazilian players, got %d", res.Count)
	}
	for _, p := range res.Players {
		if p.Nationality != "Brazil" {
			t.Errorf("got non-Brazilian player %q (%s)", p.Name, p.Nationality)
		}
	}
	// Results must be sorted by overall rating, highest first.
	if res.Players[0].Overall < res.Players[len(res.Players)-1].Overall {
		t.Errorf("expected players sorted by rating descending, got %+v", res.Players)
	}
}

func TestSearchPlayersByClub(t *testing.T) {
	dir := newDataDir(t)
	seedPlayers(t, dir,
		playerRow(0, "1", "Gabriel Barbosa", "27", "Brazil", "82", "84", "Flamengo", "ST")+
			playerRow(1, "2", "Bruno Henrique", "32", "Brazil", "80", "80", "Flamengo", "LW")+
			playerRow(2, "3", "Dudu", "31", "Brazil", "80", "80", "Palmeiras", "RW"),
	)
	s := startSession(t, dir)

	var res searchPlayersResult
	s.callTool("search_players", map[string]any{"club": "Flamengo"}, &res)
	if res.Count != 2 {
		t.Fatalf("expected 2 Flamengo players, got %d", res.Count)
	}
}

func TestSearchPlayersByNameAndPosition(t *testing.T) {
	dir := newDataDir(t)
	seedPlayers(t, dir,
		playerRow(0, "1", "Gabriel Barbosa", "27", "Brazil", "82", "84", "Flamengo", "ST")+
			playerRow(1, "2", "Gabriel Jesus", "26", "Brazil", "84", "86", "Arsenal", "ST")+
			playerRow(2, "3", "Gabriel Magalhaes", "25", "Brazil", "84", "87", "Arsenal", "CB"),
	)
	s := startSession(t, dir)

	var byName searchPlayersResult
	s.callTool("search_players", map[string]any{"name": "Gabriel"}, &byName)
	if byName.Count != 3 {
		t.Fatalf("expected 3 players named Gabriel, got %d", byName.Count)
	}

	var forwards searchPlayersResult
	s.callTool("search_players", map[string]any{"name": "Gabriel", "position": "ST"}, &forwards)
	if forwards.Count != 2 {
		t.Fatalf("expected 2 Gabriel forwards, got %d", forwards.Count)
	}
}

// ----------------------------------------------------------------------------
// 4. Competition Queries
// ----------------------------------------------------------------------------

type standingRow struct {
	Position       int    `json:"position"`
	Team           string `json:"team"`
	Points         int    `json:"points"`
	Played         int    `json:"played"`
	Wins           int    `json:"wins"`
	Draws          int    `json:"draws"`
	Losses         int    `json:"losses"`
	GoalsFor       int    `json:"goals_for"`
	GoalsAgainst   int    `json:"goals_against"`
	GoalDifference int    `json:"goal_difference"`
}

type standingsResult struct {
	Competition string        `json:"competition"`
	Season      int           `json:"season"`
	Standings   []standingRow `json:"standings"`
}

func TestStandingsCalculatedFromMatchResults(t *testing.T) {
	dir := newDataDir(t)
	// A tiny 3-team single round-robin (home and away) for 2019.
	// A beats B and C; B and C draw both meetings; so:
	//   A: 4 games, 4W       => 12 pts
	//   B: 4 games, 1W?(no)  let's compute precisely below.
	seedBrasileirao(t, dir, `
2019-05-01 16:00:00,"Flamengo-RJ","RJ","Santos-SP","SP",2,0,2019,1
2019-05-08 16:00:00,"Santos-SP","SP","Flamengo-RJ","RJ",0,1,2019,2
2019-05-15 16:00:00,"Flamengo-RJ","RJ","Palmeiras-SP","SP",3,1,2019,3
2019-05-22 16:00:00,"Palmeiras-SP","SP","Flamengo-RJ","RJ",0,2,2019,4
2019-06-01 16:00:00,"Santos-SP","SP","Palmeiras-SP","SP",1,1,2019,5
2019-06-08 16:00:00,"Palmeiras-SP","SP","Santos-SP","SP",2,2,2019,6
`)
	s := startSession(t, dir)

	var res standingsResult
	s.callTool("get_standings", map[string]any{"competition": "Brasileirao", "season": 2019}, &res)

	if len(res.Standings) != 3 {
		t.Fatalf("expected 3 teams in the table, got %d", len(res.Standings))
	}
	champ := res.Standings[0]
	if champ.Team != "Flamengo" {
		t.Errorf("expected Flamengo as champion (position 1), got %q", champ.Team)
	}
	if champ.Position != 1 {
		t.Errorf("expected champion at position 1, got %d", champ.Position)
	}
	if champ.Points != 12 || champ.Wins != 4 || champ.Played != 4 {
		t.Errorf("expected champion 12 pts / 4W / 4 played, got %d pts / %dW / %d played",
			champ.Points, champ.Wins, champ.Played)
	}
	// Santos and Palmeiras each: 2 draws + 2 losses to Flamengo => 2 pts each.
	for _, row := range res.Standings[1:] {
		if row.Points != 2 {
			t.Errorf("expected %s to have 2 points, got %d", row.Team, row.Points)
		}
	}
}

// ----------------------------------------------------------------------------
// 5. Statistical Analysis
// ----------------------------------------------------------------------------

type biggestWin struct {
	HomeTeam string `json:"home_team"`
	AwayTeam string `json:"away_team"`
	HomeGoal int    `json:"home_goal"`
	AwayGoal int    `json:"away_goal"`
	Margin   int    `json:"margin"`
}

type leagueStatsResult struct {
	TotalMatches     int          `json:"total_matches"`
	TotalGoals       int          `json:"total_goals"`
	AvgGoalsPerMatch float64      `json:"avg_goals_per_match"`
	HomeWins         int          `json:"home_wins"`
	AwayWins         int          `json:"away_wins"`
	Draws            int          `json:"draws"`
	HomeWinRate      float64      `json:"home_win_rate"`
	BiggestWins      []biggestWin `json:"biggest_wins"`
}

func TestLeagueStatsAggregatesGoalsAndHomeAdvantage(t *testing.T) {
	dir := newDataDir(t)
	// 4 matches, 10 goals total => avg 2.5. Home wins: 2, away wins: 1, draws: 1.
	seedBrasileirao(t, dir, `
2020-08-01 16:00:00,"Flamengo-RJ","RJ","Santos-SP","SP",3,0,2020,1
2020-08-02 16:00:00,"Palmeiras-SP","SP","Gremio-RS","RS",1,1,2020,1
2020-08-03 16:00:00,"Corinthians-SP","SP","Internacional-RS","RS",2,1,2020,1
2020-08-04 16:00:00,"Bahia-BA","BA","Fortaleza-CE","CE",0,2,2020,1
`)
	s := startSession(t, dir)

	var res leagueStatsResult
	s.callTool("league_stats", map[string]any{"competition": "Brasileirao", "season": 2020}, &res)

	if res.TotalMatches != 4 {
		t.Fatalf("expected 4 matches, got %d", res.TotalMatches)
	}
	if res.TotalGoals != 10 {
		t.Errorf("expected 10 total goals, got %d", res.TotalGoals)
	}
	if res.AvgGoalsPerMatch < 2.49 || res.AvgGoalsPerMatch > 2.51 {
		t.Errorf("expected avg 2.5 goals/match, got %.3f", res.AvgGoalsPerMatch)
	}
	if res.HomeWins != 2 || res.AwayWins != 1 || res.Draws != 1 {
		t.Errorf("expected 2 home / 1 away / 1 draw, got %d / %d / %d", res.HomeWins, res.AwayWins, res.Draws)
	}
	if res.HomeWinRate < 0.49 || res.HomeWinRate > 0.51 {
		t.Errorf("expected home win rate ~0.5, got %.3f", res.HomeWinRate)
	}
	if len(res.BiggestWins) == 0 {
		t.Fatalf("expected at least one biggest win to be reported")
	}
	top := res.BiggestWins[0]
	if top.Margin != 3 || top.HomeTeam != "Flamengo" {
		t.Errorf("expected biggest win to be Flamengo 3-0 (margin 3), got %+v", top)
	}
}

type rankingRow struct {
	Team  string  `json:"team"`
	Value float64 `json:"value"`
}

type teamRankingsResult struct {
	Metric   string       `json:"metric"`
	Rankings []rankingRow `json:"rankings"`
}

func TestTeamRankingsByGoalsScored(t *testing.T) {
	dir := newDataDir(t)
	seedBrasileirao(t, dir, `
2021-05-01 16:00:00,"Atletico Mineiro-MG","MG","Bahia-BA","BA",5,0,2021,1
2021-05-02 16:00:00,"Flamengo-RJ","RJ","Bahia-BA","BA",2,1,2021,1
2021-05-08 16:00:00,"Bahia-BA","BA","Atletico Mineiro-MG","MG",0,1,2021,2
`)
	s := startSession(t, dir)

	var res teamRankingsResult
	s.callTool("team_rankings", map[string]any{
		"competition": "Brasileirao",
		"season":      2021,
		"metric":      "goals_for",
	}, &res)

	if len(res.Rankings) == 0 {
		t.Fatalf("expected ranked teams, got none")
	}
	// Atletico Mineiro scored 6, Flamengo 2, Bahia 1 -> Atletico tops.
	if res.Rankings[0].Team != "Atletico Mineiro" {
		t.Errorf("expected Atletico Mineiro to top goals_for, got %q", res.Rankings[0].Team)
	}
	if res.Rankings[0].Value != 6 {
		t.Errorf("expected top scorer to have 6 goals, got %v", res.Rankings[0].Value)
	}
}

func TestTeamRankingsBestHomeRecord(t *testing.T) {
	dir := newDataDir(t)
	seedBrasileirao(t, dir, `
2021-05-01 16:00:00,"Sao Paulo-SP","SP","Santos-SP","SP",3,0,2021,1
2021-05-08 16:00:00,"Sao Paulo-SP","SP","Flamengo-RJ","RJ",2,0,2021,2
2021-05-15 16:00:00,"Santos-SP","SP","Sao Paulo-SP","SP",1,0,2021,3
2021-05-22 16:00:00,"Santos-SP","SP","Flamengo-RJ","RJ",0,2,2021,4
`)
	s := startSession(t, dir)

	var res teamRankingsResult
	s.callTool("team_rankings", map[string]any{
		"competition": "Brasileirao",
		"season":      2021,
		"metric":      "win_rate",
		"venue":       "home",
	}, &res)

	if len(res.Rankings) == 0 {
		t.Fatalf("expected ranked teams, got none")
	}
	// Sao Paulo won both home games (100%); Santos won 1 of 2 home (50%).
	if res.Rankings[0].Team != "Sao Paulo" {
		t.Errorf("expected Sao Paulo to have the best home record, got %q", res.Rankings[0].Team)
	}
}

// ----------------------------------------------------------------------------
// Data quality requirements: name variations, date formats, encoding, dedup.
// ----------------------------------------------------------------------------

func TestTeamNameVariationsAreNormalizedAcrossFiles(t *testing.T) {
	dir := newDataDir(t)
	// The same club appears with a state suffix in one file ("Flamengo-RJ") and
	// without one in another ("Flamengo"). Using different seasons keeps both
	// matches in play (overlapping seasons are intentionally de-duplicated).
	seedBrasileirao(t, dir, `
2019-05-01 16:00:00,"Flamengo-RJ","RJ","Palmeiras-SP","SP",2,0,2019,1
`)
	seedHistorical(t, dir, `
2018.01.0002,02/06/2018,2018,2,Flamengo,Vasco,3,1,RJ,RJ,Mandante,Maracana,
`)
	s := startSession(t, dir)

	// Querying "Flamengo" must find both the suffixed and unsuffixed entries.
	var res findMatchesResult
	s.callTool("find_matches", map[string]any{"team": "Flamengo"}, &res)
	if res.Count != 2 {
		t.Fatalf("expected name normalization to unify Flamengo-RJ and Flamengo (2 matches), got %d", res.Count)
	}
}

func TestBrazilianDateFormatIsParsed(t *testing.T) {
	dir := newDataDir(t)
	// Historical file uses DD/MM/YYYY dates.
	seedHistorical(t, dir, `
2003.01.0001,29/03/2003,2003,1,Guarani,Vasco,4,2,SP,RJ,Mandante,Brinco de Ouro,
`)
	s := startSession(t, dir)

	var res findMatchesResult
	s.callTool("find_matches", map[string]any{"team": "Guarani"}, &res)
	if res.Count != 1 {
		t.Fatalf("expected the historical match to load, got %d", res.Count)
	}
	if res.Matches[0].Date != "2003-03-29" {
		t.Errorf("expected DD/MM/YYYY date parsed to 2003-03-29, got %q", res.Matches[0].Date)
	}
}

func TestUTF8AccentedTeamNamesAreSearchable(t *testing.T) {
	dir := newDataDir(t)
	seedHistorical(t, dir, `
2003.01.0002,29/03/2003,2003,1,Grêmio,Avaí,2,0,RS,SC,Mandante,Olimpico,
`)
	s := startSession(t, dir)

	// Search using an unaccented spelling must still match the accented record.
	var res findMatchesResult
	s.callTool("find_matches", map[string]any{"team": "Gremio"}, &res)
	if res.Count != 1 {
		t.Fatalf("expected accent-insensitive search to find Grêmio, got %d", res.Count)
	}
}

func TestDuplicateMatchesAcrossFilesAreNotDoubleCounted(t *testing.T) {
	dir := newDataDir(t)
	// The very same Brasileirao match is present in two overlapping datasets.
	seedBrasileirao(t, dir, `
2019-05-01 16:00:00,"Flamengo-RJ","RJ","Palmeiras-SP","SP",2,0,2019,1
`)
	seedHistorical(t, dir, `
2019.01.0001,01/05/2019,2019,1,Flamengo,Palmeiras,2,0,RJ,SP,Mandante,Maracana,
`)
	s := startSession(t, dir)

	var res findMatchesResult
	s.callTool("find_matches", map[string]any{"team": "Flamengo", "opponent": "Palmeiras"}, &res)
	if res.Count != 1 {
		t.Fatalf("expected duplicate match to be de-duplicated to 1, got %d", res.Count)
	}
}

func TestOverlappingSeasonUsesSingleAuthoritativeSource(t *testing.T) {
	dir := newDataDir(t)
	// Two datasets both cover the 2019 Brasileirao. The higher-priority,
	// suffix-tagged file is authoritative; the overlapping season from the
	// secondary file must not be added on top (which would inflate the table).
	seedBrasileirao(t, dir, `
2019-05-01 16:00:00,"Flamengo-RJ","RJ","Santos-SP","SP",2,0,2019,1
2019-05-08 16:00:00,"Santos-SP","SP","Flamengo-RJ","RJ",0,1,2019,2
`)
	seedHistorical(t, dir, `
2019.01.0001,01/05/2019,2019,1,Flamengo,Santos,2,0,RJ,SP,Mandante,Maracana,
2019.01.0002,08/05/2019,2019,2,Santos,Flamengo,0,1,SP,RJ,Visitante,Vila Belmiro,
2019.01.0003,15/05/2019,2019,3,Flamengo,Santos,3,0,RJ,SP,Mandante,Maracana,
`)
	s := startSession(t, dir)

	var res standingsResult
	s.callTool("get_standings", map[string]any{"competition": "Brasileirao", "season": 2019}, &res)
	if len(res.Standings) != 2 {
		t.Fatalf("expected 2 teams, got %d", len(res.Standings))
	}
	// Only the 2 authoritative matches count: Flamengo 2W => played 2, 6 pts.
	champ := res.Standings[0]
	if champ.Team != "Flamengo" || champ.Played != 2 || champ.Points != 6 {
		t.Errorf("expected Flamengo played 2 / 6 pts from authoritative source, got %+v", champ)
	}
}

func TestEmptySystemReturnsNoResultsGracefully(t *testing.T) {
	dir := newDataDir(t) // no CSV files seeded at all
	s := startSession(t, dir)

	var res findMatchesResult
	s.callTool("find_matches", map[string]any{"team": "Flamengo"}, &res)
	if res.Count != 0 {
		t.Fatalf("expected 0 matches from an empty system, got %d", res.Count)
	}

	var players searchPlayersResult
	s.callTool("search_players", map[string]any{"nationality": "Brazil"}, &players)
	if players.Count != 0 {
		t.Fatalf("expected 0 players from an empty system, got %d", players.Count)
	}
}
