package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"
)

func TestGivenAllCSVFiles_WhenStoreLoads_ThenEveryRequiredSourceIsQueryable(t *testing.T) {
	store := loadFixtureStore(t)
	wantRows := map[string]int{
		brasileiraoFile:  5,
		cupFile:          2,
		libertadoresFile: 2,
		extendedFile:     2,
		historicalFile:   2,
		playersFile:      3,
	}
	for source, want := range wantRows {
		if got := store.SourceRows[source]; got != want {
			t.Fatalf("%s: loaded %d rows, want %d", source, got, want)
		}
	}
	if got, want := len(store.Matches), 13; got != want {
		t.Fatalf("loaded %d match rows, want %d", got, want)
	}
	if got, want := len(store.Players), 3; got != want {
		t.Fatalf("loaded %d player rows, want %d", got, want)
	}
	if _, err := store.SearchMatches(MatchFilter{Source: "historical", Team: "Flamengo"}); err != nil {
		t.Fatalf("historical source should be queryable: %v", err)
	}
	if _, err := store.SearchPlayers(PlayerFilter{Name: "Gabriel"}); err != nil {
		t.Fatalf("FIFA source should be queryable: %v", err)
	}
}

func TestGivenTeamAliasesAndDates_WhenSearchingMatches_ThenVariantsAndBoundariesMatch(t *testing.T) {
	store := loadFixtureStore(t)
	result, err := store.SearchMatches(MatchFilter{
		Team: "São Paulo FC", Source: "brasileirao", Season: 2022,
		DateFrom: "2022-10-20", DateTo: "2022-10-20",
	})
	if err != nil {
		t.Fatal(err)
	}
	if result.Total != 1 {
		t.Fatalf("got %d São Paulo rows, want 1", result.Total)
	}
	match := result.Matches[0]
	if match.HomeTeam != "Sao Paulo" || match.HomeGoals != nil || match.AwayGoals != nil {
		t.Fatalf("unexpected normalized unknown-score match: %#v", match)
	}
	if match.Date[:10] != "2022-10-20" {
		t.Fatalf("got date %q", match.Date)
	}

	historical, err := store.SearchMatches(MatchFilter{Team: "Flamengo", Source: "historical", Season: 2003})
	if err != nil {
		t.Fatal(err)
	}
	if historical.Total != 2 || historical.Matches[0].Date[:10] != "2003-04-05" {
		t.Fatalf("Brazilian date parsing or sort failed: %#v", historical.Matches)
	}
	if _, err := store.SearchMatches(MatchFilter{Venue: "neutral"}); err == nil {
		t.Fatal("invalid venue should return a validation error")
	}
}

func TestGivenCompletedLeagueRows_WhenComputingTeamStatsHeadToHeadAndStandings_ThenTotalsReconcile(t *testing.T) {
	store := loadFixtureStore(t)
	stats, err := store.TeamStatistics(TeamStatsQuery{Team: "Flamengo", Competition: "Brasileirão", Source: "brasileirao", Season: 2022})
	if err != nil {
		t.Fatal(err)
	}
	if stats.Matches != 3 || stats.Wins != 1 || stats.Losses != 1 || stats.Draws != 1 || stats.GoalsFor != 3 || stats.GoalsAgainst != 5 || stats.Points != 4 {
		t.Fatalf("unexpected Flamengo statistics: %#v", stats)
	}

	head, err := store.HeadToHead("Flamengo", "Fluminense", "Brasileirão", "brasileirao", 2022)
	if err != nil {
		t.Fatal(err)
	}
	if head.Matches != 2 || head.TeamAWins != 1 || head.TeamBWins != 0 || head.Draws != 1 || head.TeamAGoals != 3 || head.TeamBGoals != 2 {
		t.Fatalf("unexpected head-to-head: %#v", head)
	}

	standings, err := store.Standings("Brasileirão", 2022, "brasileirao")
	if err != nil {
		t.Fatal(err)
	}
	if len(standings.Standings) != 3 {
		t.Fatalf("standings teams = %d, want 3", len(standings.Standings))
	}
	if got := standings.Standings[0]; got.Team != "Corinthians" || got.Points != 4 || got.Played != 2 {
		t.Fatalf("unexpected top row: %#v", got)
	}
	if _, err := store.Standings("Copa do Brasil", 2022, ""); err == nil {
		t.Fatal("cup standings should be explicitly unsupported")
	}
}

func TestGivenOverlappingSources_WhenAggregating_ThenDuplicateRowsAreCountedOnceWithProvenance(t *testing.T) {
	store := loadFixtureStore(t)
	stats, err := store.TeamStatistics(TeamStatsQuery{Team: "Flamengo", Competition: "Brasileirão", Season: 2022})
	if err != nil {
		t.Fatal(err)
	}
	if stats.Matches != 3 || stats.Scheduled != 0 {
		t.Fatalf("overlapping extended row was not deduplicated: %#v", stats)
	}
	summaryRaw, err := store.Analyze(StatisticsQuery{Metric: "summary", Competition: "Brasileirão", Season: 2022})
	if err != nil {
		t.Fatal(err)
	}
	summary := summaryRaw.(SummaryStatistics)
	if summary.Matches != 4 || summary.TotalGoals != 10 || summary.AverageGoalsPerMatch != 2.5 {
		t.Fatalf("unexpected deduplicated summary: %#v", summary)
	}
	biggestRaw, err := store.Analyze(StatisticsQuery{Metric: "biggest_wins", Competition: "Brasileirão", Season: 2022, Limit: 1})
	if err != nil {
		t.Fatal(err)
	}
	biggest := biggestRaw.([]BiggestWin)
	if len(biggest) != 1 || biggest[0].GoalDifference != 3 || biggest[0].Match.HomeTeam != "Corinthians" {
		t.Fatalf("unexpected biggest win: %#v", biggest)
	}
	topRaw, err := store.Analyze(StatisticsQuery{Metric: "top_scoring_teams", Competition: "Brasileirão", Season: 2022, Limit: 1})
	if err != nil {
		t.Fatal(err)
	}
	top := topRaw.([]TeamGoals)
	if len(top) != 1 || top[0].Team != "Corinthians" || top[0].Goals != 4 {
		t.Fatalf("unexpected top-scoring team: %#v", top)
	}
}

func TestGivenFIFABOMAndCrossFileData_WhenSearchingPlayersAndCompetitions_ThenRecordsAreReturned(t *testing.T) {
	store := loadFixtureStore(t)
	players, err := store.SearchPlayers(PlayerFilter{Club: "Flamengo", Sort: "overall_desc"})
	if err != nil {
		t.Fatal(err)
	}
	if players.Total != 2 || players.Players[0].Name != "Gabriel Barbosa" || players.Players[0].Attributes["finishing"] != 86 {
		t.Fatalf("unexpected FIFA result: %#v", players)
	}
	brazilian, err := store.SearchPlayers(PlayerFilter{Nationality: "Brazil", Position: "ST"})
	if err != nil || brazilian.Total != 1 {
		t.Fatalf("nationality/position filter failed: %#v, %v", brazilian, err)
	}
	forwards, err := store.SearchPlayers(PlayerFilter{Club: "Flamengo", PositionGroup: "forwards"})
	if err != nil || forwards.Total != 2 {
		t.Fatalf("position group filter failed: %#v, %v", forwards, err)
	}
	competitions, err := store.TeamCompetitions("Flamengo")
	if err != nil {
		t.Fatal(err)
	}
	if len(competitions) < 3 {
		t.Fatalf("expected cross-file competitions, got %#v", competitions)
	}
}

func TestGivenTraditionalRivalsAndNaturalLanguage_WhenQuestionIsAsked_ThenDeterministicAnswersUseData(t *testing.T) {
	store := loadFixtureStore(t)
	service := NewSoccerService(store)
	answer, err := service.Ask("When did Flamengo last play Fluminense?")
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(answer.Answer, "2022-01-08") || !strings.Contains(answer.Answer, "1–1") {
		t.Fatalf("unexpected last-match answer: %#v", answer)
	}
	followUp, err := service.Ask("What was the score?")
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(followUp.Answer, "1–1") {
		t.Fatalf("score follow-up lost context: %#v", followUp)
	}
	derbies, err := service.Ask("Show me all derbies in 2022")
	if err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(derbies.Answer, "2 known") {
		t.Fatalf("unexpected derby answer: %#v", derbies)
	}
	players, err := service.Ask("Which players play for Flamengo?")
	if err != nil || !strings.Contains(players.Answer, "2 players") {
		t.Fatalf("unexpected player question: %#v, %v", players, err)
	}
	unsupported, err := service.Ask("Who are the top scorers?")
	if err != nil || !strings.Contains(unsupported.Answer, "cannot") {
		t.Fatalf("top scorer response should be honest: %#v, %v", unsupported, err)
	}
}

func TestGivenMCPServer_WhenClientInitializesListsAndCallsTools_ThenValidJSONRPCResponsesAreReturned(t *testing.T) {
	server := NewMCPServer(loadFixtureStore(t))
	input := strings.Join([]string{
		`{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{}}}`,
		`{"jsonrpc":"2.0","method":"notifications/initialized","params":{}}`,
		`{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}`,
		`{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"search_matches","arguments":{"team":"Flamengo","season":2022,"limit":2}}}`,
		`{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"get_competition_standings","arguments":{"competition":"Brasileirão","season":2022,"source":"brasileirao"}}}`,
		`{"jsonrpc":"2.0","id":5,"method":"resources/list","params":{}}`,
		`{"jsonrpc":"2.0","id":6,"method":"resources/read","params":{"uri":"soccer://datasets"}}`,
		`{"jsonrpc":"2.0","id":7,"method":"does/not/exist","params":{}}`,
	}, "\n") + "\n"
	var output bytes.Buffer
	if err := server.Serve(strings.NewReader(input), &output); err != nil {
		t.Fatal(err)
	}
	decoder := json.NewDecoder(&output)
	var responses []map[string]any
	for decoder.More() {
		var response map[string]any
		if err := decoder.Decode(&response); err != nil {
			t.Fatal(err)
		}
		responses = append(responses, response)
	}
	if len(responses) != 7 {
		t.Fatalf("notification should not receive a response: got %d", len(responses))
	}
	initialize := responses[0]["result"].(map[string]any)
	if initialize["protocolVersion"] != "2025-06-18" {
		t.Fatalf("unexpected initialize response: %#v", initialize)
	}
	tools := responses[1]["result"].(map[string]any)["tools"].([]any)
	if len(tools) < 8 {
		t.Fatalf("tools/list incomplete: %#v", tools)
	}
	if _, ok := responses[2]["result"].(map[string]any)["structuredContent"]; !ok {
		t.Fatalf("tools/call lacks structured content: %#v", responses[2])
	}
	resources := responses[4]["result"].(map[string]any)["resources"].([]any)
	if len(resources) != 2 {
		t.Fatalf("resources/list incomplete: %#v", resources)
	}
	if _, ok := responses[5]["result"].(map[string]any)["contents"]; !ok {
		t.Fatalf("resources/read missing contents: %#v", responses[5])
	}
	if responses[6]["error"].(map[string]any)["code"].(float64) != -32601 {
		t.Fatalf("unknown method response: %#v", responses[6])
	}
}

func TestGivenTwentySupportedQuestions_WhenAsked_ThenEachProducesADataBoundAnswer(t *testing.T) {
	service := NewSoccerService(loadFixtureStore(t))
	cases := []struct{ question, contains string }{
		{"When did Flamengo last play Fluminense?", "2022-01-08"},
		{"What was the score?", "1–1"},
		{"Who is Gabriel Barbosa?", "Found 1 FIFA"},
		{"Which players play for Flamengo?", "Found 2 players"},
		{"Show all derbies in 2022", "Found 2 known"},
		{"What competitions has Flamengo played in?", "appears in"},
		{"What is Flamengo's home record in 2022?", "home record"},
		{"Which team scored the most goals in Serie A 2022?", "ranked"},
		{"Compare Flamengo and Fluminense head-to-head", "Compared"},
		{"Find all Brazilian players", "Found 2 Brazilian"},
		{"Who are the top Brazilian players?", "Found 2 Brazilian"},
		{"Show all forwards from Flamengo", "Found 2 forward"},
		{"Who won the 2022 Brasileirão?", "Corinthians leads"},
		{"Show 2022 Copa Libertadores bracket", "stage-labelled"},
		{"Which teams were relegated in 2022?", "bottom four"},
		{"What's the average goals per match in Brasileirão?", "Calculated"},
		{"Which team has the best away record?", "ranked"},
		{"Show me the biggest wins in the Brasileirão", "ordered"},
		{"What matches did Flamengo play in 2022?", "Found"},
		{"Find all Copa do Brasil finals", "cannot reliably"},
	}
	for _, test := range cases {
		t.Run(test.question, func(t *testing.T) {
			answer, err := service.Ask(test.question)
			if err != nil {
				t.Fatal(err)
			}
			if !strings.Contains(answer.Answer, test.contains) {
				t.Fatalf("answer %q does not contain %q", answer.Answer, test.contains)
			}
		})
	}
}

func TestGivenConcurrentMCPQueries_WhenStoreIsReadInParallel_ThenResultsRemainValid(t *testing.T) {
	store := loadFixtureStore(t)
	var wait sync.WaitGroup
	errs := make(chan error, 40)
	for i := 0; i < 40; i++ {
		wait.Add(1)
		go func() {
			defer wait.Done()
			if _, err := store.SearchMatches(MatchFilter{Team: "Flamengo", Season: 2022}); err != nil {
				errs <- err
				return
			}
			if _, err := store.Analyze(StatisticsQuery{Metric: "summary", Competition: "Brasileirão", Season: 2022}); err != nil {
				errs <- err
			}
		}()
	}
	wait.Wait()
	close(errs)
	for err := range errs {
		t.Fatal(err)
	}
}

func TestGivenScoreStrings_WhenParsed_ThenUnknownAndFractionalScoresAreHandledSafely(t *testing.T) {
	value, err := optionalInt("1.0")
	if err != nil || value == nil || *value != 1 {
		t.Fatalf("float-form integer parse failed: %v, %v", value, err)
	}
	unknown, err := optionalInt("NA")
	if err != nil || unknown != nil {
		t.Fatalf("NA should remain unknown: %v, %v", unknown, err)
	}
	if _, err := optionalInt("1.5"); err == nil {
		t.Fatal("fractional score should be rejected")
	}
}

func TestSimpleLookupAndAggregateQueriesMeetSpecifiedLatency(t *testing.T) {
	if _, err := os.Stat(filepath.Join("data", "kaggle", brasileiraoFile)); err != nil {
		t.Skip("repository data is unavailable")
	}
	store, err := LoadStore(filepath.Join("data", "kaggle"))
	if err != nil {
		t.Fatal(err)
	}
	start := time.Now()
	if _, err := store.SearchMatches(MatchFilter{Team: "Flamengo", Limit: 50}); err != nil {
		t.Fatal(err)
	}
	if elapsed := time.Since(start); elapsed >= 2*time.Second {
		t.Fatalf("simple lookup took %s, want < 2s", elapsed)
	}
	start = time.Now()
	if _, err := store.Analyze(StatisticsQuery{Metric: "summary", Competition: "Brasileirão"}); err != nil {
		t.Fatal(err)
	}
	if elapsed := time.Since(start); elapsed >= 5*time.Second {
		t.Fatalf("aggregate query took %s, want < 5s", elapsed)
	}
}

func loadFixtureStore(t *testing.T) *Store {
	t.Helper()
	dir := filepath.Join(t.TempDir(), "data", "kaggle")
	if err := os.MkdirAll(dir, 0o755); err != nil {
		t.Fatal(err)
	}
	writeFixtureFile(t, dir, brasileiraoFile, `datetime,home_team,home_team_state,away_team,away_team_state,home_goal,away_goal,season,round
2022-01-01 16:00:00,Flamengo-RJ,RJ,Fluminense-RJ,RJ,2,1,2022,1
2022-01-08 16:00:00,Fluminense-RJ,RJ,Flamengo-RJ,RJ,1,1,2022,2
2022-01-15 16:00:00,Fluminense-RJ,RJ,Corinthians-SP,SP,1,1,2022,3
2022-01-22 16:00:00,Corinthians-SP,SP,Flamengo-RJ,RJ,3,0,2022,4
2022-10-20 16:00:00,Sao Paulo-SP,SP,Coritiba-PR,PR,NA,NA,2022,5
`)
	writeFixtureFile(t, dir, cupFile, `round,datetime,home_team,away_team,home_goal,away_goal,season
1,2022-03-01 20:00:00,Flamengo,Atletico-MG,1,0,2022
8,2022-05-01 20:00:00,Sao Paulo,Flamengo,1,1,2022
`)
	writeFixtureFile(t, dir, libertadoresFile, `datetime,home_team,away_team,home_goal,away_goal,season,stage
2022-04-01 20:00:00,Flamengo,Barcelona-EQU,2,0,2022,group stage
NA,Flamengo,Athletico,-,-,NA,final
`)
	writeFixtureFile(t, dir, extendedFile, `tournament,home,home_goal,away_goal,away,time,date,home_corner,away_corner,total_corners
Serie A,Flamengo,2.0,1.0,Fluminense,16:00:00,2022-01-01,3.0,4.0,7.0
Copa do Brasil,Sao Paulo,1.0,1.0,Flamengo,20:00:00,2022-05-01,2.0,2.0,4.0
`)
	writeFixtureFile(t, dir, historicalFile, `ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena,OBS
2003.01.0001,29/03/2003,2003,1,Flamengo,Fluminense,4,2,RJ,RJ,Mandante,Maracana,
2003.01.0002,05/04/2003,2003,2,Fluminense,Flamengo,0,0,RJ,RJ,Empate,Maracana,
`)
	writeFixtureFile(t, dir, playersFile, "\ufeff,ID,Name,Age,Nationality,Overall,Potential,Club,Position,Jersey Number,Preferred Foot,Height,Weight,Crossing,Finishing\n0,10,Gabriel Barbosa,25,Brazil,82,84,Flamengo,ST,9,Right,5'10,170lbs,75,86\n1,11,Bruno Henrique,30,Brazil,80,80,Flamengo,LW,27,Right,5'11,170lbs,77,79\n2,12,Lionel Messi,31,Argentina,94,94,FC Barcelona,RF,10,Left,5'7,159lbs,84,95\n")
	store, err := LoadStore(dir)
	if err != nil {
		t.Fatal(err)
	}
	return store
}

func writeFixtureFile(t *testing.T, dir, name, content string) {
	t.Helper()
	if err := os.WriteFile(filepath.Join(dir, name), []byte(content), 0o644); err != nil {
		t.Fatalf("write %s: %v", name, err)
	}
}

func ExampleMCPServer() {
	// Start with: go run . -data-dir data/kaggle
	// Then send an MCP initialize request followed by tools/list or tools/call.
	fmt.Println("MCP server uses JSON-RPC over stdin/stdout")
	// Output: MCP server uses JSON-RPC over stdin/stdout
}
