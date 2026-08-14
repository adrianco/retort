package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
)

func TestLoadData_GivenAllSixSchemas_WhenLoaded_ThenEveryDatasetIsAvailable(t *testing.T) {
	dataDir := writeFixtureData(t)

	store, err := LoadData(dataDir)
	if err != nil {
		t.Fatalf("LoadData() error = %v", err)
	}
	if len(store.Datasets) != 6 {
		t.Fatalf("loaded datasets = %d, want 6", len(store.Datasets))
	}
	if len(store.Matches) != 6 {
		t.Fatalf("loaded matches = %d, want 6", len(store.Matches))
	}
	if len(store.Players) != 1 {
		t.Fatalf("loaded players = %d, want 1", len(store.Players))
	}

	if store.Matches[1].Played() {
		t.Fatal("Given NA scores, incomplete fixture must not be marked played")
	}
	if store.Matches[4].HomeGoals == nil || *store.Matches[4].HomeGoals != 3 {
		t.Fatalf("Given decimal extended score, HomeGoals = %v, want 3", store.Matches[4].HomeGoals)
	}
	if got := store.Matches[5].DateText; got != "2019-05-04" {
		t.Fatalf("Given DD/MM/YYYY historical date, DateText = %q, want 2019-05-04", got)
	}
	if got := store.Players[0].Name; got != "Neymar Jr" {
		t.Fatalf("Given BOM-prefixed FIFA header, player Name = %q, want Neymar Jr", got)
	}
}

func TestLoadData_GivenHeaderOnlyDatasetWithMissingColumns_WhenLoaded_ThenItFailsClearly(t *testing.T) {
	dataDir := writeFixtureData(t)
	if err := os.WriteFile(filepath.Join(dataDir, brasileiraoFile), []byte("datetime\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	_, err := LoadData(dataDir)
	if err == nil || !strings.Contains(err.Error(), "missing required column") {
		t.Fatalf("LoadData() error = %v, want missing-header validation error", err)
	}
}

func TestScoreAndSeasonParsing_GivenInvalidNumericValues_WhenParsed_ThenTheyDoNotBecomeInventedResults(t *testing.T) {
	if score := parseScore("1.0"); score == nil || *score != 1 {
		t.Fatalf("parseScore(1.0) = %v, want 1", score)
	}
	for _, value := range []string{"1.5", "-1", "NA", "-"} {
		if score := parseScore(value); score != nil {
			t.Fatalf("parseScore(%q) = %v, want nil", value, *score)
		}
	}
	if season := parseInt("2023.5"); season != 0 {
		t.Fatalf("parseInt(2023.5) = %d, want 0", season)
	}
}

func TestTeamMatching_GivenAccentAndStateVariations_WhenCompared_ThenOnlyCompatibleTeamsMatch(t *testing.T) {
	tests := []struct {
		candidate string
		query     string
		want      bool
	}{
		{"São Paulo - SP", "Sao Paulo-SP", true},
		{"Flamengo-RJ", "flamengo", true},
		{"Flamengo-PI", "Flamengo-RJ", false},
		{"Athletico Paranaense", "Atlético-PR", true},
		{"Atletico Mineiro", "Atletico-MG", true},
		{"Atletico Mineiro", "Atletico-PR", false},
		{"America MG", "America-MG", true},
		{"EC Bahia", "Bahia-BA", true},
		{"Sport Recife", "Sport-PE", true},
	}
	for _, test := range tests {
		t.Run(test.candidate+"/"+test.query, func(t *testing.T) {
			if got := teamMatches(test.candidate, test.query); got != test.want {
				t.Fatalf("teamMatches(%q, %q) = %v, want %v", test.candidate, test.query, got, test.want)
			}
		})
	}
}

func TestStatistics_GivenOverlappingAndIncompleteFixtures_WhenCalculated_ThenCanonicalSourceAndPlayedOnlyResultsAreUsed(t *testing.T) {
	store, err := LoadData(writeFixtureData(t))
	if err != nil {
		t.Fatal(err)
	}

	stats, err := store.TeamStatistics("Sao Paulo-SP", MatchFilter{Competition: "Brasileirão", Season: 2023}, "all")
	if err != nil {
		t.Fatal(err)
	}
	if stats.Matches != 1 || stats.Wins != 1 || stats.GoalsFor != 2 || stats.GoalsAgainst != 1 {
		t.Fatalf("canonical team stats = %+v, want one 2-1 win", stats)
	}
	if stats.UnplayedMatches != 1 {
		t.Fatalf("unplayed fixtures = %d, want 1", stats.UnplayedMatches)
	}

	allSources := store.Statistics(MatchFilter{Competition: "Brasileirão", Season: 2023, IncludeAllSources: true})
	if allSources.PlayedMatches != 2 || allSources.UnplayedMatches != 1 {
		t.Fatalf("all-source stats = %+v, want two played and one incomplete fixture", allSources)
	}
	if allSources.TotalGoals != 6 {
		t.Fatalf("all-source total goals = %d, want 6", allSources.TotalGoals)
	}
}

func TestSearchAndHeadToHead_GivenStructuredFilters_WhenQueried_ThenMatchesRemainSourceAware(t *testing.T) {
	store, err := LoadData(writeFixtureData(t))
	if err != nil {
		t.Fatal(err)
	}

	matches := store.SearchMatches(MatchFilter{Team: "São Paulo-SP", Competition: "Brasileirão", Season: 2023, Limit: 10})
	if len(matches) != 2 {
		t.Fatalf("SearchMatches() = %d records, want 2 canonical-source records", len(matches))
	}
	if matches[0].Source != brasileiraoFile {
		t.Fatalf("SearchMatches() source = %q, want %q", matches[0].Source, brasileiraoFile)
	}

	headToHead, err := store.HeadToHead("São Paulo-SP", "Flamengo-RJ", MatchFilter{Competition: "Brasileirão", Season: 2023, Limit: 10})
	if err != nil {
		t.Fatal(err)
	}
	if headToHead.Played != 1 || headToHead.Unplayed != 1 || headToHead.TeamAWins != 1 || headToHead.Total != 2 {
		t.Fatalf("HeadToHead() = %+v, want one Sao Paulo win and one incomplete match", headToHead)
	}
	if len(headToHead.Matches) != 2 {
		t.Fatalf("head-to-head fixture list = %d, want 2 including the incomplete fixture", len(headToHead.Matches))
	}
}

func TestTeamProfile_GivenMatchAndPlayerData_WhenQueried_ThenItJoinsBothDatasetsWithoutInventingRosterHistory(t *testing.T) {
	dataDir := writeFixtureData(t)
	if err := os.WriteFile(filepath.Join(dataDir, fifaFile), []byte("\ufeff,ID,Name,Age,Nationality,Overall,Potential,Club,Position,Jersey Number,Height,Weight\n0,10,Fixture Player,27,Brazil,92,95,Sao Paulo,LW,10,5'9,150lbs\n"), 0o600); err != nil {
		t.Fatal(err)
	}
	store, err := LoadData(dataDir)
	if err != nil {
		t.Fatal(err)
	}
	profile, err := store.TeamProfile("Sao Paulo-SP", MatchFilter{Competition: "Brasileirão", Season: 2023, Limit: 10}, 10)
	if err != nil {
		t.Fatal(err)
	}
	if profile["match_count"] != 2 {
		t.Fatalf("team profile match count = %#v, want 2", profile["match_count"])
	}
	players, ok := profile["players"].([]Player)
	if !ok || len(players) != 1 || players[0].Name != "Fixture Player" {
		t.Fatalf("team profile players = %#v, want matching FIFA snapshot player", profile["players"])
	}
}

func TestStatistics_GivenOnlyDraws_WhenFindingBiggestWins_ThenNoDrawIsCalledAWin(t *testing.T) {
	store, err := LoadData(writeFixtureData(t))
	if err != nil {
		t.Fatal(err)
	}
	stats := store.Statistics(MatchFilter{Competition: "Copa Libertadores", Season: 2022})
	if len(stats.BiggestWins) != 0 {
		t.Fatalf("biggest wins = %+v, want no draw fixtures", stats.BiggestWins)
	}
}

func TestMCPServer_GivenJSONRPCSession_WhenClientListsAndCallsTools_ThenResponsesStayOnProtocol(t *testing.T) {
	store, err := LoadData(writeFixtureData(t))
	if err != nil {
		t.Fatal(err)
	}
	input := strings.Join([]string{
		`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}`,
		`{"jsonrpc":"2.0","method":"notifications/initialized"}`,
		`{"jsonrpc":"2.0","id":2,"method":"tools/list"}`,
		`{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"team_statistics","arguments":{"team":"Sao Paulo-SP","competition":"Brasileirão","season":2023}}}`,
		`{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"team_statistics","arguments":{}}}`,
		`{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"team_statistics","arguments":{"team":false}}}`,
		`{"jsonrpc":"2.0","id":[],"method":"ping"}`,
	}, "\n") + "\n"
	var output bytes.Buffer
	if err := NewMCPServer(store).Serve(strings.NewReader(input), &output); err != nil {
		t.Fatalf("Serve() error = %v", err)
	}

	responses := decodeProtocolLines(t, output.String())
	if len(responses) != 6 {
		t.Fatalf("protocol response count = %d, want 6; output=%q", len(responses), output.String())
	}
	if got := nestedString(t, responses[0].Result, "protocolVersion"); got != "2025-11-25" {
		t.Fatalf("initialize protocolVersion = %q, want 2025-11-25", got)
	}
	var toolList struct {
		Tools []listedTool `json:"tools"`
	}
	if err := json.Unmarshal(responses[1].Result, &toolList); err != nil {
		t.Fatal(err)
	}
	if !hasTool(toolList.Tools, "search_matches") || !hasTool(toolList.Tools, "team_profile") || !hasTool(toolList.Tools, "soccer_query") {
		t.Fatalf("tool list does not expose expected tools: %+v", toolList.Tools)
	}
	for _, tool := range toolList.Tools {
		if tool.InputSchema["type"] != "object" {
			t.Fatalf("tool %q input schema = %#v, want root object schema", tool.Name, tool.InputSchema)
		}
	}
	var success toolResult
	if err := json.Unmarshal(responses[2].Result, &success); err != nil {
		t.Fatal(err)
	}
	if success.IsError || len(success.Content) != 1 || !strings.Contains(success.Content[0].Text, `"wins": 1`) {
		t.Fatalf("team_statistics MCP result = %+v", success)
	}
	var failure toolResult
	if err := json.Unmarshal(responses[3].Result, &failure); err != nil {
		t.Fatal(err)
	}
	if !failure.IsError || !strings.Contains(failure.Content[0].Text, "team is required") {
		t.Fatalf("missing-argument MCP result = %+v", failure)
	}
	var wrongType toolResult
	if err := json.Unmarshal(responses[4].Result, &wrongType); err != nil {
		t.Fatal(err)
	}
	if !wrongType.IsError || !strings.Contains(wrongType.Content[0].Text, "team must be a string") {
		t.Fatalf("wrong-type MCP result = %+v", wrongType)
	}
	if responses[5].Error == nil || responses[5].Error.Code != -32600 || string(responses[5].ID) != "null" {
		t.Fatalf("invalid-id response = %+v, want JSON-RPC invalid request with null id", responses[5])
	}
}

func TestMCPServer_GivenCallsBeforeInitialization_WhenServed_ThenTheyAreRejectedWithoutExecutingNotifications(t *testing.T) {
	store, err := LoadData(writeFixtureData(t))
	if err != nil {
		t.Fatal(err)
	}
	input := strings.Join([]string{
		`{"jsonrpc":"2.0","id":"before","method":"tools/list"}`,
		`{"jsonrpc":"2.0","method":"tools/call","params":{"name":"dataset_summary","arguments":{}}}`,
		`[]`,
	}, "\n") + "\n"
	var output bytes.Buffer
	if err := NewMCPServer(store).Serve(strings.NewReader(input), &output); err != nil {
		t.Fatal(err)
	}
	responses := decodeProtocolLines(t, output.String())
	if len(responses) != 2 {
		t.Fatalf("response count = %d, want 2", len(responses))
	}
	if responses[0].Error == nil || responses[0].Error.Code != -32002 {
		t.Fatalf("pre-initialize response = %+v, want not-initialized error", responses[0])
	}
	if responses[1].Error == nil || responses[1].Error.Code != -32600 {
		t.Fatalf("array request response = %+v, want invalid request", responses[1])
	}
}

func TestMCPToolResults_GivenNaturalQueryReturningAList_WhenEncoded_ThenStructuredContentIsOmitted(t *testing.T) {
	store, err := LoadData(writeFixtureData(t))
	if err != nil {
		t.Fatal(err)
	}
	result, known := NewMCPServer(store).callTool("soccer_query", map[string]any{"query": "Who is Neymar?"})
	if !known || result.IsError {
		t.Fatalf("soccer_query result = %+v, known=%v", result, known)
	}
	if result.StructuredContent != nil {
		t.Fatalf("array result structuredContent = %#v, want omitted", result.StructuredContent)
	}
}

func TestSuppliedData_GivenFullDatasets_WhenLoadedAndQueried_ThenCoverageAnd2019StandingsAreCorrect(t *testing.T) {
	store := suppliedDataStore(t)
	if len(store.Matches) != 23954 || len(store.Players) != 18207 {
		t.Fatalf("full dataset coverage: matches=%d players=%d, want 23954 and 18207", len(store.Matches), len(store.Players))
	}

	standings, err := store.Standings("Brasileirão", 2019, "", false)
	if err != nil {
		t.Fatal(err)
	}
	if len(standings.Standings) != 20 {
		t.Fatalf("2019 standings length = %d, want 20", len(standings.Standings))
	}
	champion := standings.Standings[0]
	if champion.Team != "Flamengo-RJ" || champion.Points != 90 || champion.Wins != 28 || champion.Draws != 6 || champion.Losses != 4 {
		t.Fatalf("2019 champion = %+v, want Flamengo-RJ with 90 points (28W 6D 4L)", champion)
	}
	if !teamMatches(standings.Standings[1].Team, "Santos-SP") || standings.Standings[1].Wins != 22 || !teamMatches(standings.Standings[2].Team, "Palmeiras-SP") || standings.Standings[2].Wins != 21 {
		t.Fatalf("2019 tied-points ordering = %+v, want Santos (22 wins) before Palmeiras (21 wins)", standings.Standings[:3])
	}

	historical, err := store.Standings("Brasileirão", 2003, "historical", false)
	if err != nil {
		t.Fatal(err)
	}
	if len(historical.Standings) != 24 {
		t.Fatalf("2003 historical standings teams = %d, want 24 without splitting inconsistent UF values", len(historical.Standings))
	}

	serieB := store.SearchMatches(MatchFilter{Competition: "Campeonato Brasileiro Serie B", Season: 2019, Source: "extended", Limit: 500})
	if len(serieB) == 0 || normalizedCompetition(serieB[0].Competition) != "serie b" {
		t.Fatalf("Serie B full-name query = %+v, want extended Serie B matches", serieB)
	}
	if count := len(store.SearchMatches(MatchFilter{Competition: "Brasileirão", Season: 2019, Round: "1", Limit: 500})); count != 10 {
		t.Fatalf("round 1 match count = %d, want 10 without matching rounds 10-19", count)
	}
	atleticoPR, err := store.TeamStatistics("Atletico-PR", MatchFilter{Competition: "Serie A", Season: 2023, Source: "extended"}, "all")
	if err != nil {
		t.Fatal(err)
	}
	if atleticoPR.Matches != 38 {
		t.Fatalf("Atletico-PR 2023 extended matches = %d, want 38 without Atletico Mineiro", atleticoPR.Matches)
	}

	players := store.SearchPlayers(PlayerFilter{Nationality: "Brazil", MinOverall: 85, Limit: 50})
	if !containsPlayer(players, "Neymar") {
		t.Fatalf("Brazilian players rated 85+ = %+v, want Neymar", players)
	}
}

func TestNaturalQuery_GivenACommonQuestion_WhenAnswered_ThenItUsesTheStructuredCalculation(t *testing.T) {
	store, err := LoadData(writeFixtureData(t))
	if err != nil {
		t.Fatal(err)
	}
	answer, err := store.AnswerNaturalQuery("Who won the Brasileirão in 2019?", 10)
	if err != nil {
		t.Fatal(err)
	}
	standings, ok := answer.(StandingsResult)
	if !ok {
		t.Fatalf("natural answer type = %T, want StandingsResult", answer)
	}
	if standings.Season != 2019 || len(standings.Standings) == 0 {
		t.Fatalf("natural standings answer = %+v", standings)
	}
}

func TestNaturalQuery_GivenSpecifiedQuestionPatterns_WhenAnswered_ThenItFindsHeadToHeadAndPlayers(t *testing.T) {
	store := suppliedDataStore(t)
	for _, test := range []struct {
		question string
		check    func(testing.TB, any)
	}{
		{
			question: "Compare Palmeiras and Santos head-to-head in 2019",
			check: func(t testing.TB, answer any) {
				t.Helper()
				result, ok := answer.(HeadToHead)
				if !ok || result.Played == 0 {
					t.Fatalf("comparison answer = %#v, want non-empty HeadToHead", answer)
				}
			},
		},
		{
			question: "Atletico-MG vs Atletico-PR in 2019",
			check: func(t testing.TB, answer any) {
				t.Helper()
				result, ok := answer.(HeadToHead)
				if !ok || !teamMatches(result.TeamA, "Atletico-MG") || !teamMatches(result.TeamB, "Atletico-PR") {
					t.Fatalf("state-qualified answer = %#v, want Atletico-MG vs Atletico-PR", answer)
				}
			},
		},
		{
			question: "Who   is Neymar?",
			check: func(t testing.TB, answer any) {
				t.Helper()
				players, ok := answer.([]Player)
				if !ok || !containsPlayer(players, "Neymar") {
					t.Fatalf("player answer = %#v, want Neymar player result", answer)
				}
			},
		},
	} {
		t.Run(test.question, func(t *testing.T) {
			answer, err := store.AnswerNaturalQuery(test.question, 20)
			if err != nil {
				t.Fatal(err)
			}
			test.check(t, answer)
		})
	}
}

type protocolResponse struct {
	JSONRPC string          `json:"jsonrpc"`
	ID      json.RawMessage `json:"id"`
	Result  json.RawMessage `json:"result"`
	Error   *jsonRPCError   `json:"error"`
}

type listedTool struct {
	Name        string         `json:"name"`
	InputSchema map[string]any `json:"inputSchema"`
}

func decodeProtocolLines(t *testing.T, output string) []protocolResponse {
	t.Helper()
	scanner := bufio.NewScanner(strings.NewReader(output))
	var responses []protocolResponse
	for scanner.Scan() {
		var response protocolResponse
		if err := json.Unmarshal(scanner.Bytes(), &response); err != nil {
			t.Fatalf("stdout contains non-JSON protocol output %q: %v", scanner.Text(), err)
		}
		if response.JSONRPC != "2.0" {
			t.Fatalf("jsonrpc version = %q, want 2.0", response.JSONRPC)
		}
		responses = append(responses, response)
	}
	if err := scanner.Err(); err != nil {
		t.Fatal(err)
	}
	return responses
}

func nestedString(t *testing.T, raw json.RawMessage, key string) string {
	t.Helper()
	var value map[string]any
	if err := json.Unmarshal(raw, &value); err != nil {
		t.Fatal(err)
	}
	text, _ := value[key].(string)
	return text
}

func hasTool(tools []listedTool, name string) bool {
	for _, tool := range tools {
		if tool.Name == name {
			return true
		}
	}
	return false
}

func containsPlayer(players []Player, name string) bool {
	for _, player := range players {
		if strings.Contains(player.Name, name) {
			return true
		}
	}
	return false
}

var (
	fullDataOnce  sync.Once
	fullDataStore *DataStore
	fullDataErr   error
)

func suppliedDataStore(t *testing.T) *DataStore {
	t.Helper()
	fullDataOnce.Do(func() {
		fullDataStore, fullDataErr = LoadData(filepath.Join("data", "kaggle"))
	})
	if fullDataErr != nil {
		t.Fatalf("LoadData(full data): %v", fullDataErr)
	}
	return fullDataStore
}

func writeFixtureData(t *testing.T) string {
	t.Helper()
	directory := t.TempDir()
	files := map[string]string{
		brasileiraoFile: `"datetime","home_team","home_team_state","away_team","away_team_state","home_goal","away_goal","season","round"
2023-05-01 18:30:00,"São Paulo - SP",SP,"Flamengo-RJ",RJ,2,1,2023,1
2023-06-01 18:30:00,"Flamengo-RJ",RJ,"São Paulo-SP",SP,NA,NA,2023,2
`,
		cupFile: `"round","datetime","home_team","away_team","home_goal","away_goal","season"
Final,2022-10-01 16:00:00,"Flamengo-RJ","Corinthians-SP",1,0,2022
`,
		libertadoresFile: `"datetime","home_team","away_team","home_goal","away_goal","season","stage"
2022-08-01 20:00:00,"Palmeiras-SP","Flamengo-RJ",2,2,2022,"group stage"
`,
		extendedFile: `"tournament","home","home_goal","away_goal","away","time","date"
Serie A,"São Paulo",3.0,0.0,Flamengo,20:00:00,2023-11-01
`,
		historicalFile: `ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena
2003.01.0001,04/05/2019,2019,1,Flamengo,Vasco,2,0,RJ,RJ,Mandante,Maracana
`,
		fifaFile: "\ufeff,ID,Name,Age,Nationality,Overall,Potential,Club,Position,Jersey Number,Height,Weight\n0,10,Neymar Jr,27,Brazil,92,95,Paris Saint-Germain,LW,10,5'9,150lbs\n",
	}
	for name, content := range files {
		if err := os.WriteFile(filepath.Join(directory, name), []byte(content), 0o600); err != nil {
			t.Fatalf("write %s: %v", name, err)
		}
	}
	return directory
}
