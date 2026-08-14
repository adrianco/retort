package main

import (
	"bytes"
	"encoding/json"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func fixtureDatabase() *Database {
	date := func(value string) time.Time {
		parsed, err := parseDate(value)
		if err != nil {
			panic(err)
		}
		return parsed
	}
	matches := []Match{
		{Source: "historical_brasileirao", Competition: "Brasileirão (Historical 2003-2019)", Date: date("2019-05-01"), Season: 2019, HomeTeam: "São Paulo-SP", AwayTeam: "Flamengo-RJ", HomeGoals: 1, AwayGoals: 2, ScoreKnown: true},
		{Source: "historical_brasileirao", Competition: "Brasileirão (Historical 2003-2019)", Date: date("2019-05-08"), Season: 2019, HomeTeam: "Flamengo-RJ", AwayTeam: "São Paulo-SP", HomeGoals: 3, AwayGoals: 0, ScoreKnown: true},
		{Source: "brasileirao", Competition: "Brasileirão Série A", Date: date("2019-05-08"), Season: 2019, HomeTeam: "Flamengo-RJ", AwayTeam: "São Paulo-SP", HomeGoals: 3, AwayGoals: 0, ScoreKnown: true}, // overlapping raw record
		{Source: "historical_brasileirao", Competition: "Brasileirão (Historical 2003-2019)", Date: date("2019-05-15"), Season: 2019, HomeTeam: "São Paulo-SP", AwayTeam: "Palmeiras-SP", HomeGoals: 0, AwayGoals: 0, ScoreKnown: true},
		{Source: "historical_brasileirao", Competition: "Brasileirão (Historical 2003-2019)", Date: date("2019-05-22"), Season: 2019, HomeTeam: "Palmeiras-SP", AwayTeam: "Flamengo-RJ", HomeGoals: 1, AwayGoals: 0, ScoreKnown: true},
		{Source: "brasileirao", Competition: "Brasileirão Série A", Date: date("2022-10-01"), Season: 2022, HomeTeam: "Flamengo-RJ", AwayTeam: "Corinthians-SP", ScoreKnown: false},
		{Source: "brazilian_cup", Competition: "Copa do Brasil", Date: date("2012-07-11"), Season: 2012, Round: "6", HomeTeam: "Palmeiras-SP", AwayTeam: "Coritiba-PR", HomeGoals: 2, AwayGoals: 0, ScoreKnown: true},
	}
	players := []Player{{ID: "158023", Name: "Neymar Jr", Nationality: "Brazil", Overall: 92, Potential: 92, Club: "Paris Saint-Germain", Position: "LW"}}
	return NewDatabase(matches, players)
}

func TestNormalization_GivenTeamVariants_WhenNormalized_ThenAliasesAndStatesAreSafe(t *testing.T) {
	if got, want := normalizeTeam("São Paulo-SP"), normalizeTeam("Sao Paulo FC"); got != want {
		t.Fatalf("São Paulo variants differ: %q vs %q", got, want)
	}
	if got, want := normalizeTeam("Athletico-PR"), normalizeTeam("Atlético Paranaense"); got != want {
		t.Fatalf("Athletico aliases differ: %q vs %q", got, want)
	}
	if normalizeTeam("Atlético-MG") == normalizeTeam("Atlético-GO") {
		t.Fatal("distinct Atlético state teams must not collapse")
	}
	if normalizeTeam("América-MG") == normalizeTeam("América-RN") {
		t.Fatal("distinct América state teams must not collapse")
	}
	if normalizeTeam("Flamengo-PI") == normalizeTeam("Flamengo-RJ") {
		t.Fatal("Flamengo-PI must not collapse into Flamengo-RJ")
	}
	if got, want := normalizeTeam("Flamengo"), normalizeTeam("Flamengo-RJ"); got != want {
		t.Fatalf("bare Flamengo should resolve to Rio club: %q vs %q", got, want)
	}
	if normalizeTeam("Santos-AP") == normalizeTeam("Santos-SP") {
		t.Fatal("Santos-AP must not collapse into Santos-SP")
	}
	if !strings.Contains(normalizeText(displayTeam("Flamengo - PI")), "pi") {
		t.Fatalf("explicit state identity was hidden in display: %q", displayTeam("Flamengo - PI"))
	}
}

func TestQueries_GivenNormalizedGraph_WhenFilteringAndAggregating_ThenResultsAreSourceAware(t *testing.T) {
	database := fixtureDatabase()

	// Given overlapping source rows, when canonical matches are requested, then one authoritative row remains.
	canonical := database.SearchMatches(MatchFilter{Competition: "Brasileirão", Season: 2019, IncludeUnplayed: true, Limit: 100})
	if canonical.Total != 4 {
		t.Fatalf("canonical matches = %d, want 4", canonical.Total)
	}
	raw := database.SearchMatches(MatchFilter{Competition: "Brasileirão", Season: 2019, Source: "all", IncludeUnplayed: true, Limit: 100})
	if raw.Total != 5 {
		t.Fatalf("raw matches = %d, want 5", raw.Total)
	}

	// Given accent/state variation, when a team is searched, then either home/away orientation matches.
	matchResult := database.SearchMatches(MatchFilter{Team: "Sao Paulo", Opponent: "Flamengo", Season: 2019, IncludeUnplayed: true, Limit: 20})
	if matchResult.Total != 2 {
		t.Fatalf("São Paulo vs Flamengo = %d, want 2", matchResult.Total)
	}

	// Given an unknown-score fixture, when a home record is calculated, then it is not counted as 0-0.
	stats, err := database.TeamStatistics("Flamengo", MatchFilter{Season: 2022, Source: "brasileirao"}, "home")
	if err != nil {
		t.Fatal(err)
	}
	if stats.Matches != 0 {
		t.Fatalf("unknown fixture counted in stats: %+v", stats)
	}
	if stats.UnknownFixturesExcluded != 1 {
		t.Fatalf("unknown fixture exclusion count = %d, want 1", stats.UnknownFixturesExcluded)
	}
	if err := func() error {
		_, err := database.TeamStatistics("Flamengo", MatchFilter{Source: "all"}, "all")
		return err
	}(); err == nil {
		t.Fatal("source=all must be rejected for aggregates to prevent double counting")
	}

	// Given completed results, when head-to-head is calculated, then wins are assigned from each team's perspective.
	headToHead, matches, err := database.CompareTeams("Flamengo", "São Paulo", MatchFilter{Season: 2019})
	if err != nil {
		t.Fatal(err)
	}
	if headToHead.TeamAWins != 2 || headToHead.TeamBWins != 0 || headToHead.Matches != 2 || len(matches) != 2 {
		t.Fatalf("unexpected head-to-head: %+v, matches=%d", headToHead, len(matches))
	}

	// Given a season, when standings are calculated, then source duplicates do not affect points.
	standings, err := database.CompetitionStandings("brasileirao", 2019, "")
	if err != nil {
		t.Fatal(err)
	}
	if len(standings) != 3 || standings[0].Team != "Flamengo" || standings[0].Points != 6 {
		t.Fatalf("unexpected standings: %+v", standings)
	}

	// Given a player nationality, when natural-language Brazilian is used, then it maps to the source value Brazil.
	players, total, _ := database.SearchPlayers(PlayerFilter{Nationality: "Brazilian", Limit: 20})
	if total != 1 || len(players) != 1 || players[0].Name != "Neymar Jr" {
		t.Fatalf("Brazilian player filter failed: total=%d players=%+v", total, players)
	}

	// Given completed matches, when goals-per-match is requested, then a deterministic aggregate is returned.
	analysis, err := database.AnalyzeMatches(MatchFilter{Competition: "brasileirao", Season: 2019}, "goals_per_match")
	if err != nil {
		t.Fatal(err)
	}
	value := analysis.Value.(map[string]interface{})
	if value["averageGoalsPerMatch"] != 1.75 {
		t.Fatalf("average = %#v, want 1.75", value["averageGoalsPerMatch"])
	}
	if _, err := database.CompetitionStandings("Copa do Brasil", 2019, ""); err == nil {
		t.Fatal("knockout competitions must not receive fabricated league standings")
	}
	if _, err := database.AnalyzeMatches(MatchFilter{Source: "all"}, "summary"); err == nil {
		t.Fatal("source=all must be rejected for aggregate analysis")
	}
}

func TestSearchMatches_GivenCupRounds_WhenFinalRequested_ThenHighestRoundIsRecognized(t *testing.T) {
	database := fixtureDatabase()
	result := database.SearchMatches(MatchFilter{Competition: "Copa do Brasil", Season: 2012, Stage: "final", IncludeUnplayed: true, Limit: 20})
	if result.Total != 1 || result.Matches[0].Round != "6" {
		t.Fatalf("final lookup = %+v", result)
	}
}

func TestMCPStdio_GivenProtocolTranscript_WhenServed_ThenOnlyJSONResponsesAreEmitted(t *testing.T) {
	server := NewMCPServer(fixtureDatabase())
	input := strings.Join([]string{
		`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}`,
		`{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}`,
		`{"jsonrpc":"2.0","id":"tools","method":"tools/list"}`,
		`{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"search_matches","arguments":{"team":"Sao Paulo","season":2019}}}`,
	}, "\n")
	var output bytes.Buffer
	if err := server.Serve(strings.NewReader(input), &output); err != nil {
		t.Fatal(err)
	}
	lines := strings.Split(strings.TrimSpace(output.String()), "\n")
	if len(lines) != 3 {
		t.Fatalf("response count = %d, want 3: %q", len(lines), output.String())
	}
	for _, line := range lines {
		var response map[string]interface{}
		if err := json.Unmarshal([]byte(line), &response); err != nil {
			t.Fatalf("invalid JSON response %q: %v", line, err)
		}
		if response["jsonrpc"] != "2.0" {
			t.Fatalf("not JSON-RPC: %#v", response)
		}
	}
	if !strings.Contains(lines[1], `"tools"`) || !strings.Contains(lines[2], `"matches"`) {
		t.Fatalf("unexpected MCP output: %s", output.String())
	}
}

func TestMCPValidation_GivenMalformedRequests_WhenHandled_ThenProtocolErrorsAreClear(t *testing.T) {
	server := NewMCPServer(fixtureDatabase())
	tests := []struct {
		name    string
		request string
		code    int
	}{
		{
			name:    "initialize requires client metadata",
			request: `{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":{}}}`,
			code:    -32602,
		},
		{
			name:    "initialize capabilities must be object",
			request: `{"jsonrpc":"2.0","id":2,"method":"initialize","params":{"protocolVersion":"2025-11-25","capabilities":null,"clientInfo":{"name":"test","version":"1"}}}`,
			code:    -32602,
		},
		{
			name:    "wrong argument type",
			request: `{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"search_matches","arguments":{"competition":123}}}`,
			code:    -32602,
		},
		{
			name:    "unknown argument",
			request: `{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"search_matches","arguments":{"not_a_filter":"value"}}}`,
			code:    -32602,
		},
		{
			name:    "oversize page",
			request: `{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"search_matches","arguments":{"limit":101}}}`,
			code:    -32602,
		},
		{
			name:    "identified notification is a request",
			request: `{"jsonrpc":"2.0","id":6,"method":"notifications/initialized","params":{}}`,
			code:    -32601,
		},
	}
	for _, test := range tests {
		t.Run(test.name, func(t *testing.T) {
			response, respond := server.HandleJSON([]byte(test.request))
			if !respond || response.Error == nil || response.Error.Code != test.code {
				t.Fatalf("response = %+v, respond=%v; want error code %d", response, respond, test.code)
			}
		})
	}

	response, respond := server.HandleJSON([]byte(`{"jsonrpc":"2.0","id":7,"method":"initialize","params":{"protocolVersion":"future-version","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}`))
	if !respond || response.Error != nil {
		t.Fatalf("unsupported protocol version should negotiate, got %+v", response)
	}
	result, ok := response.Result.(map[string]interface{})
	if !ok || result["protocolVersion"] != "2025-11-25" {
		t.Fatalf("unexpected negotiated initialization result: %#v", response.Result)
	}
}

func TestMCPTools_GivenUnknownFixturesAndSourcePolicy_WhenCalled_ThenResultsExposeBoth(t *testing.T) {
	server := NewMCPServer(fixtureDatabase())
	result, err := server.callTool(toolCall{Name: "get_team_stats", Arguments: map[string]interface{}{"team": "Flamengo", "season": 2022, "source": "brasileirao", "venue": "home"}})
	if err != nil || result.IsError {
		t.Fatalf("team stats tool failed: result=%+v err=%v", result, err)
	}
	stats, ok := result.StructuredContent.(TeamStats)
	if !ok || stats.UnknownFixturesExcluded != 1 || len(stats.DataSources) != 1 || stats.DataSources[0] != "brasileirao" {
		t.Fatalf("team stats provenance/completeness missing: %#v", result.StructuredContent)
	}

	standingsResult, err := server.callTool(toolCall{Name: "get_standings", Arguments: map[string]interface{}{"season": 2022, "source": "brasileirao"}})
	if err != nil || standingsResult.IsError {
		t.Fatalf("standings tool failed: result=%+v err=%v", standingsResult, err)
	}
	standingData, ok := standingsResult.StructuredContent.(map[string]interface{})
	if !ok || standingData["unplayedExcluded"] != 1 {
		t.Fatalf("standings completeness missing: %#v", standingsResult.StructuredContent)
	}

	raw, err := server.callTool(toolCall{Name: "get_competition_stats", Arguments: map[string]interface{}{"source": "all"}})
	if err != nil || !raw.IsError {
		t.Fatalf("raw aggregate should return a tool error: result=%+v err=%v", raw, err)
	}
}

func TestLoadDatabase_GivenSuppliedCSVs_WhenLoaded_ThenAllSixSourcesAndDataFormatsWork(t *testing.T) {
	database, err := LoadDatabase(filepath.Join("data", "kaggle"))
	if err != nil {
		t.Fatal(err)
	}
	want := map[string]int{"brasileirao": 4180, "brazilian_cup": 1337, "libertadores": 1255, "extended_statistics": 10296, "historical_brasileirao": 6886, "fifa_players": 18207}
	for source, expected := range want {
		if got := database.Report.Sources[source].Loaded; got != expected {
			t.Errorf("%s loaded %d, want %d", source, got, expected)
		}
	}
	if len(database.Matches) != 23954 || len(database.Players) != 18207 {
		t.Fatalf("loaded matches=%d players=%d", len(database.Matches), len(database.Players))
	}
	if database.Players[0].ID != "158023" || database.Players[0].Name != "L. Messi" {
		t.Fatalf("FIFA BOM/index handling failed: %+v", database.Players[0])
	}
	if _, ok := database.Players[0].Attributes["finishing"]; !ok {
		t.Fatalf("FIFA skill attributes were not retained: %+v", database.Players[0])
	}
	brazilianPlayers, brazilianTotal, _ := database.SearchPlayers(PlayerFilter{Nationality: "Brazil", Limit: 100})
	if brazilianTotal != 827 || len(brazilianPlayers) == 0 || brazilianPlayers[0].Name != "Neymar Jr" || brazilianPlayers[0].Overall != 92 {
		t.Fatalf("Brazilian FIFA filter returned unexpected data: total=%d first=%+v", brazilianTotal, brazilianPlayers[:min(1, len(brazilianPlayers))])
	}
	if players, total, _ := database.SearchPlayers(PlayerFilter{Name: "Gabriel Barbosa", Limit: 20}); total != 0 || len(players) != 0 {
		t.Fatalf("missing FIFA player must remain a truthful empty result: total=%d players=%+v", total, players)
	}
	if players, total, _ := database.SearchPlayers(PlayerFilter{Club: "Flamengo", Limit: 20}); total != 0 || len(players) != 0 {
		t.Fatalf("missing Flamengo club rows must remain a truthful empty result: total=%d players=%+v", total, players)
	}
	var extended Match
	for _, match := range database.Matches {
		if match.ID == "" || match.SourceRow <= 0 {
			t.Fatalf("match provenance is incomplete: %+v", match)
		}
		if match.Source == "extended_statistics" && match.Season != 0 {
			t.Fatalf("extended source invented an official season for %+v", match)
		}
		if match.Source == "extended_statistics" && extended.Source == "" {
			extended = match
		}
	}
	if extended.Source == "" || extended.Kickoff == "" || extended.HomeAttacks == nil || extended.AwayAttacks == nil || extended.TotalCorners == nil || extended.HomeGoalDifference == nil || extended.HomeResult == "" {
		t.Fatalf("extended statistics were not preserved: %+v", extended)
	}

	// Given authoritative historical records, when 2019 table is calculated, then the documented champion and tie ordering appear.
	standings, err := database.CompetitionStandings("brasileirao", 2019, "historical_brasileirao")
	if err != nil {
		t.Fatal(err)
	}
	if len(standings) < 3 || standings[0].Team != "Flamengo" || standings[0].Points != 90 || standings[1].Team != "Santos" || standings[2].Team != "Palmeiras" {
		t.Fatalf("unexpected 2019 standings: %+v", standings[:min(3, len(standings))])
	}

	// Given a 2022 unknown-score fixture, when searched, then status is preserved rather than becoming a 0-0 result.
	unknowns := database.SearchMatches(MatchFilter{Competition: "brasileirao", Season: 2022, Source: "brasileirao", IncludeUnplayed: true, Limit: 100})
	foundUnknown := false
	for _, match := range unknowns.Matches {
		if !match.ScoreKnown {
			foundUnknown = match.ResultStatus == "unplayed_or_unknown"
			break
		}
	}
	if !foundUnknown {
		t.Fatal("expected an unknown 2022 Brasileirão score in the first result page")
	}
	for _, match := range unknowns.Matches {
		if !match.ScoreKnown {
			encoded, err := json.Marshal(match)
			if err != nil {
				t.Fatal(err)
			}
			if !strings.Contains(string(encoded), `"homeGoals":null`) || !strings.Contains(string(encoded), `"awayGoals":null`) {
				t.Fatalf("unknown score was not nullable in JSON: %s", encoded)
			}
			break
		}
	}
	corinthians2021, err := database.TeamStatistics("Corinthians", MatchFilter{Competition: "brasileirao", Season: 2021, Source: "brasileirao"}, "home")
	if err != nil {
		t.Fatal(err)
	}
	if got := []int{corinthians2021.Matches, corinthians2021.Wins, corinthians2021.Draws, corinthians2021.Losses, corinthians2021.GoalsFor, corinthians2021.GoalsAgainst}; !sameInts(got, []int{19, 10, 5, 4, 26, 18}) {
		t.Fatalf("unexpected 2021 Corinthians home record: %+v", corinthians2021)
	}
	corinthians2022, err := database.TeamStatistics("Corinthians", MatchFilter{Competition: "brasileirao", Season: 2022, Source: "brasileirao"}, "home")
	if err != nil {
		t.Fatal(err)
	}
	if corinthians2022.Matches != 15 || corinthians2022.UnknownFixturesExcluded != 4 {
		t.Fatalf("2022 completeness was not reported: %+v", corinthians2022)
	}

	libertadoresFinal := database.SearchMatches(MatchFilter{Competition: "libertadores", Season: 2019, Source: "libertadores", Stage: "final", IncludeUnplayed: true, Limit: 20})
	if libertadoresFinal.Total != 1 || canonicalStage(libertadoresFinal.Matches[0].Stage) != "final" || libertadoresFinal.Matches[0].HomeTeam != "Flamengo" {
		t.Fatalf("Libertadores final filtering leaked non-finals: %+v", libertadoresFinal)
	}
	cup2021Final := database.SearchMatches(MatchFilter{Competition: "copa do brasil", Season: 2021, Source: "brazilian_cup", Stage: "final", IncludeUnplayed: true, Limit: 20})
	if cup2021Final.Total != 0 {
		t.Fatalf("incomplete 2021 Cup round must not be called a final: %+v", cup2021Final)
	}
	cup2019Final := database.SearchMatches(MatchFilter{Competition: "copa do brasil", Season: 2019, Source: "brazilian_cup", Stage: "final", IncludeUnplayed: true, Limit: 20})
	if cup2019Final.Total != 2 {
		t.Fatalf("expected two 2019 Cup final legs, got %+v", cup2019Final)
	}
	roundOne := database.SearchMatches(MatchFilter{Competition: "brasileirao", Season: 2019, Source: "brasileirao", Round: "1", IncludeUnplayed: true, Limit: 100})
	if roundOne.Total != 10 {
		t.Fatalf("round=1 must match only round 1, got %d", roundOne.Total)
	}
	flamengoPI := database.SearchMatches(MatchFilter{Team: "Flamengo-PI", Competition: "copa do brasil", Source: "brazilian_cup", IncludeUnplayed: true, Limit: 100})
	if flamengoPI.Total != 2 {
		t.Fatalf("state-qualified Flamengo-PI lookup leaked other clubs: %+v", flamengoPI)
	}
	for _, match := range flamengoPI.Matches {
		if match.HomeKey != "flamengo pi" && match.AwayKey != "flamengo pi" {
			t.Fatalf("Flamengo-PI result lost its identity: %+v", match)
		}
	}

	server := NewMCPServer(database)
	structured, _, naturalErr := server.answerQuestion("Compare Atlético Mineiro and Cruzeiro head-to-head")
	if naturalErr != nil {
		t.Fatalf("natural alias query failed: %v", naturalErr)
	}
	naturalResult, ok := structured.(map[string]interface{})
	if !ok {
		t.Fatalf("unexpected natural result: %#v", structured)
	}
	head, ok := naturalResult["headToHead"].(HeadToHead)
	if !ok || head.Matches == 0 || head.TeamA != "Atlético-MG" {
		t.Fatalf("natural alias query lost team identity: %#v", structured)
	}

	historicalDate, dateErr := parseDate("2003-03-29")
	if dateErr != nil {
		t.Fatal(dateErr)
	}
	dateMatches := database.SearchMatches(MatchFilter{Competition: "brasileirao", Source: "historical_brasileirao", DateFrom: &historicalDate, DateTo: &historicalDate, IncludeUnplayed: true, Limit: 100})
	guaraniVasco := false
	for _, match := range dateMatches.Matches {
		if match.HomeKey == normalizeTeam("Guarani") && match.AwayKey == normalizeTeam("Vasco") && match.HomeGoals == 4 && match.AwayGoals == 2 {
			guaraniVasco = true
		}
	}
	if !guaraniVasco {
		t.Fatalf("Brazilian DD/MM/YYYY date was not queryable through ISO bounds: %+v", dateMatches)
	}

	for _, question := range []string{
		"When did Flamengo last play Corinthians?",
		"Show me all Flamengo vs Fluminense matches",
		"What matches did Palmeiras play in 2023?",
		"Find all Copa do Brasil finals",
		"What is Corinthians home record in 2021?",
		"Which team scored the most goals in Serie A 2023?",
		"Compare Palmeiras and Santos head-to-head",
		"Find all Brazilian players in the dataset",
		"Who are the highest rated Brazilian players?",
		"Who is Neymar Jr?",
		"Which players play for Flamengo?",
		"Who won the 2019 Brasileirão?",
		"Which teams were relegated in 2020?",
		"What's the average goals per match in Brasileirão?",
		"Which team has the best away record in 2019?",
		"Show the biggest wins in the dataset",
		"Show all derbies in 2023",
		"What competitions has Palmeiras played in?",
		"Compare the 2018 and 2019 seasons",
	} {
		if _, _, questionErr := server.answerQuestion(question); questionErr != nil {
			t.Fatalf("natural question %q failed: %v", question, questionErr)
		}
	}
	for _, unavailable := range []string{"Who are the top scorers?", "Show the 2018 Copa Libertadores bracket"} {
		_, _, questionErr := server.answerQuestion(unavailable)
		if questionErr == nil || questionErr.Code != "DATA_UNAVAILABLE" {
			t.Fatalf("natural question %q should explain unavailable source data, got %v", unavailable, questionErr)
		}
	}
	calendarYear2023 := database.SearchMatches(MatchFilter{Competition: "brasileirao", Season: 2023, Limit: 1, IncludeUnplayed: true})
	if calendarYear2023.Total == 0 || calendarYear2023.Matches[0].Source != "extended_statistics" {
		t.Fatalf("expected 2023 calendar-year fallback from extended source: %+v", calendarYear2023)
	}
}

func sameInts(left, right []int) bool {
	if len(left) != len(right) {
		return false
	}
	for i := range left {
		if left[i] != right[i] {
			return false
		}
	}
	return true
}

func TestPerformance_GivenLoadedCorpus_WhenQuerying_ThenTargetsAreMet(t *testing.T) {
	database, err := LoadDatabase(filepath.Join("data", "kaggle"))
	if err != nil {
		t.Fatal(err)
	}

	lookupStarted := time.Now()
	lookup := database.SearchMatches(MatchFilter{Team: "Palmeiras", Season: 2019, Limit: 20, IncludeUnplayed: true})
	if lookup.Total == 0 {
		t.Fatal("expected a Palmeiras lookup result")
	}
	if elapsed := time.Since(lookupStarted); elapsed >= 2*time.Second {
		t.Fatalf("simple lookup took %s; target is under 2s", elapsed)
	}

	aggregateStarted := time.Now()
	statistics, err := database.AnalyzeMatches(MatchFilter{Competition: "brasileirao", Season: 2019}, "summary")
	if err != nil {
		t.Fatal(err)
	}
	if statistics.Matches == 0 {
		t.Fatal("expected completed aggregate matches")
	}
	if elapsed := time.Since(aggregateStarted); elapsed >= 5*time.Second {
		t.Fatalf("aggregate took %s; target is under 5s", elapsed)
	}
}
