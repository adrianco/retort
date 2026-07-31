package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"runtime"
	"strings"
	"testing"
)

var integrationData *DataStore

func TestMain(m *testing.M) {
	_, file, _, ok := runtime.Caller(0)
	if !ok {
		panic("cannot locate test file")
	}
	dataDir := filepath.Join(filepath.Dir(file), "data", "kaggle")
	var err error
	integrationData, err = LoadData(dataDir)
	if err != nil {
		panic(err)
	}
	os.Exit(m.Run())
}

func sourceCount(file string) int {
	for _, source := range integrationData.Sources {
		if source.File == file {
			return source.RecordCount
		}
	}
	return 0
}

func TestFeatureDataCoverage_GivenAllCSVs_WhenLoaded_ThenEverySourceIsQueryable(t *testing.T) {
	// Given all six supplied files are loaded by TestMain.
	if got, want := len(integrationData.Sources), 6; got != want {
		t.Fatalf("loaded %d sources, want %d", got, want)
	}
	for file, want := range map[string]int{
		brasileiraoFile:  4180,
		cupFile:          1337,
		libertadoresFile: 1255,
		extendedFile:     10296,
		historicalFile:   6886,
		fifaFile:         18207,
	} {
		if got := sourceCount(file); got != want {
			t.Errorf("%s loaded %d rows, want %d", file, got, want)
		}
	}

	// When each match source is addressed explicitly, it is not hidden by the
	// default duplicate-collapse behavior.
	for _, source := range []string{"brasileirao", "cup", "libertadores", "extended", "historical"} {
		matches := integrationData.SearchMatches(MatchFilter{Source: source})
		if len(matches) == 0 {
			t.Errorf("source %q was not queryable", source)
		}
	}
	extended := integrationData.SearchMatches(MatchFilter{Source: "extended", Limit: 1})
	if len(extended) != 1 || extended[0].Statistics == nil {
		t.Errorf("extended match statistics were not retained: %+v", extended)
	}
	historical := integrationData.SearchMatches(MatchFilter{Source: "historical", Limit: 1})
	if len(historical) != 1 || historical[0].Venue == "" {
		t.Errorf("historical venue data was not retained: %+v", historical)
	}
	players := integrationData.SearchPlayers(PlayerFilter{Limit: 1})
	if players.Total != 18207 {
		t.Errorf("player dataset has %d records, want 18207", players.Total)
	}
}

func TestFeatureMatchQueries_GivenLoadedMatches_WhenSearchingNormalizedTeams_ThenResultsHaveCoreFields(t *testing.T) {
	// Given the match data is loaded. When Flamengo's state suffix and
	// Fluminense are used as criteria, then each result has date, score, and
	// competition as required by the BDD scenario in the specification.
	matches := integrationData.SearchMatches(MatchFilter{
		Team: "Flamengo-RJ", Opponent: "Fluminense", Season: 2023, Descending: true,
	})
	if len(matches) == 0 {
		t.Fatal("expected Flamengo vs Fluminense matches in 2023")
	}
	for _, match := range matches {
		if match.DateText == "" || match.Competition == "" || !match.HasScore {
			t.Fatalf("incomplete match returned: %+v", match)
		}
		if !teamNameMatches(match.HomeKey, "Flamengo") && !teamNameMatches(match.AwayKey, "Flamengo") {
			t.Fatalf("unexpected non-Flamengo match: %+v", match)
		}
		if !teamNameMatches(match.HomeKey, "Fluminense") && !teamNameMatches(match.AwayKey, "Fluminense") {
			t.Fatalf("unexpected non-Fluminense match: %+v", match)
		}
	}
}

func TestFeatureTeamQueries_Given2019Brasileirao_WhenCalculatingTable_ThenFlamengoIsChampion(t *testing.T) {
	// Given the match data is loaded, when a final league table is calculated,
	// then its known 2019 champion and totals demonstrate non-duplicated stats.
	standings, err := integrationData.Standings("Brasileirão", 2019, "")
	if err != nil {
		t.Fatal(err)
	}
	if got, want := len(standings), 20; got != want {
		t.Fatalf("standings has %d teams, want %d", got, want)
	}
	champion := standings[0]
	if normalizeTeam(champion.Team) != "flamengo" || champion.Points != 90 || champion.Played != 38 {
		t.Fatalf("unexpected calculated champion: %+v", champion)
	}

	stats := integrationData.TeamStatistics("Palmeiras-SP", MatchFilter{Competition: "Brasileirão", Season: 2019}, "all")
	if stats.Matches != 38 || stats.Wins != 21 || stats.Points != 74 {
		t.Fatalf("state-suffixed Palmeiras statistics were not normalized correctly: %+v", stats)
	}
}

func TestFeaturePlayerQueries_GivenFIFAData_WhenFilteringBrazilianPlayers_ThenHighestRatedIsReturned(t *testing.T) {
	// Given the FIFA data is loaded, when Brazilian players are requested, then
	// rating order and player information are returned.
	result := integrationData.SearchPlayers(PlayerFilter{Nationality: "Brazilian", Limit: 5})
	if result.Total == 0 || len(result.Players) == 0 {
		t.Fatal("expected Brazilian FIFA players")
	}
	if result.Players[0].Name != "Neymar Jr" || result.Players[0].Overall != 92 {
		t.Fatalf("unexpected top Brazilian player: %+v", result.Players[0])
	}
	for _, player := range result.Players {
		if player.Nationality != "Brazil" || player.Position == "" || player.Club == "" {
			t.Fatalf("incomplete player result: %+v", player)
		}
	}
}

func TestFeatureCompetitionQueries_GivenFinalFilters_WhenSearching_ThenOnlyActualFinalsAreReturned(t *testing.T) {
	// Libertadores stages are explicit. A stage=final filter must not match the
	// substring in "semifinals" or "quarterfinals".
	libertadoresFinals := integrationData.SearchMatches(MatchFilter{Competition: "Libertadores", Stage: "final"})
	if len(libertadoresFinals) == 0 {
		t.Fatal("expected Libertadores final matches")
	}
	for _, match := range libertadoresFinals {
		if normalizeStage(match.Stage) != "final" {
			t.Fatalf("non-final stage leaked into final search: %+v", match)
		}
	}

	// Copa do Brasil encodes rounds numerically; terminal complete rounds are
	// classified as finals, while incomplete 2021 round-four rows are excluded.
	cupFinals := integrationData.SearchMatches(MatchFilter{Competition: "Copa do Brasil", FinalsOnly: true})
	if len(cupFinals) != 18 {
		t.Fatalf("got %d Copa do Brasil final legs, want 18", len(cupFinals))
	}
	for _, match := range cupFinals {
		if !integrationData.isFinalMatch(match) || !match.HasScore {
			t.Fatalf("non-final or incomplete match returned: %+v", match)
		}
	}

	bracketServer := NewMCPServer(integrationData)
	bracket := bracketServer.CallTool("competition_bracket", map[string]any{"season": 2018})
	if bracket.IsError || len(bracket.Content) != 1 || !strings.Contains(bracket.Content[0].Text, "Round of 16") || !strings.Contains(bracket.Content[0].Text, "Final") {
		t.Fatalf("unexpected Libertadores bracket result: %#v", bracket)
	}
}

func TestFeatureStatisticalAnalysis_Given2023SerieA_WhenFindingMostGoals_ThenGremioLeads(t *testing.T) {
	// Given scored Serie A rows, when the most goals statistic is requested,
	// then the result is calculated from match scores rather than hard-coded.
	leader, ok := integrationData.MostGoalsScorer(MatchFilter{Competition: "Serie A", Season: 2023})
	if !ok {
		t.Fatal("expected a goals leader")
	}
	if normalizeTeam(leader.Team) != "gremio" || leader.GoalsFor != 63 || leader.Matches != 38 {
		t.Fatalf("unexpected 2023 goals leader: %+v", leader)
	}

	summary, biggest := integrationData.CompetitionStatistics(MatchFilter{Competition: "Brasileirão", Season: 2023})
	if summary.Matches < 370 || summary.AverageGoals <= 2 || len(biggest) == 0 || biggest[0].Margin <= 0 {
		t.Fatalf("unexpected aggregate statistics: summary=%+v biggest=%+v", summary, biggest)
	}
}

func TestFeatureNaturalLanguage_GivenSampleQuestions_WhenCalled_ThenTheyRouteToExpectedData(t *testing.T) {
	server := NewMCPServer(integrationData)
	cases := []struct {
		question string
		contains string
	}{
		{"When did Flamengo last play Corinthians?", "Corinthians"},
		{"Who won the 2019 Brasileirão?", "Flamengo won"},
		{"Who are the top Brazilian players?", "Neymar Jr"},
		{"Which team scored the most goals in Serie A 2023?", "Most goals: Gremio"},
		{"Find all Copa do Brasil finals", "Copa do Brasil"},
	}
	for _, test := range cases {
		result := server.CallTool("query_brazilian_soccer", map[string]any{"question": test.question})
		if result.IsError || len(result.Content) != 1 || !strings.Contains(result.Content[0].Text, test.contains) {
			t.Errorf("question %q returned %#v", test.question, result)
		}
	}

	// A short follow-up score question can use the immediately preceding match
	// result in the same MCP server session.
	followUpServer := NewMCPServer(integrationData)
	_ = followUpServer.CallTool("query_brazilian_soccer", map[string]any{"question": "When did Flamengo last play Corinthians?"})
	followUp := followUpServer.CallTool("query_brazilian_soccer", map[string]any{"question": "What was the score?"})
	if followUp.IsError || len(followUp.Content) != 1 || !strings.Contains(followUp.Content[0].Text, "1-1") {
		t.Fatalf("score follow-up did not use previous match: %#v", followUp)
	}
}

func TestFeatureMCPProtocol_GivenStdioRequests_WhenInitializedAndCalled_ThenValidJSONRPCResponsesAreWritten(t *testing.T) {
	server := NewMCPServer(integrationData)
	input := strings.Join([]string{
		`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26"}}`,
		`{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}`,
		`{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"search_matches","arguments":{"team":"Flamengo","opponent":"Fluminense","season":2023,"limit":1}}}`,
	}, "\n") + "\n"
	var output bytes.Buffer
	if err := server.Run(strings.NewReader(input), &output); err != nil {
		t.Fatal(err)
	}
	scanner := bufio.NewScanner(&output)
	responses := make([]map[string]any, 0)
	for scanner.Scan() {
		var response map[string]any
		if err := json.Unmarshal(scanner.Bytes(), &response); err != nil {
			t.Fatalf("invalid JSON-RPC response %q: %v", scanner.Text(), err)
		}
		responses = append(responses, response)
	}
	if err := scanner.Err(); err != nil {
		t.Fatal(err)
	}
	if len(responses) != 2 {
		t.Fatalf("got %d responses, want 2 (notification has no response)", len(responses))
	}
	initialize, ok := responses[0]["result"].(map[string]any)
	if !ok || initialize["protocolVersion"] != "2025-03-26" {
		t.Fatalf("unexpected initialize response: %#v", responses[0])
	}
	call, ok := responses[1]["result"].(map[string]any)
	if !ok {
		t.Fatalf("unexpected tool response: %#v", responses[1])
	}
	content, ok := call["content"].([]any)
	if !ok || len(content) != 1 {
		t.Fatalf("tool response missing content: %#v", call)
	}
}

func TestDateAndTeamNormalization(t *testing.T) {
	for value := range map[string]bool{
		"2023-09-24": true, "2012-05-19 18:30:00": true, "29/03/2003": true,
	} {
		if _, ok := parseDate(value); !ok {
			t.Errorf("did not parse required date format %q", value)
		}
	}
	for input, want := range map[string]string{
		"Palmeiras-SP": "palmeiras", "São Paulo FC": "sao paulo", "Sport Club Corinthians Paulista": "corinthians", "Atlético-MG": "atletico mineiro",
	} {
		if got := normalizeTeam(input); got != want {
			t.Errorf("normalizeTeam(%q) = %q, want %q", input, got, want)
		}
	}
}
