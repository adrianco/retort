package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"path/filepath"
	"strings"
	"sync"
	"testing"
	"time"
)

var testData = sync.OnceValues(func() (*Store, error) { return loadStore(filepath.Join("data", "kaggle")) })

func givenDatasets(t *testing.T) *Store {
	t.Helper()
	store, err := testData()
	if err != nil {
		t.Fatal(err)
	}
	return store
}

func TestAllProvidedFilesAreQueryable(t *testing.T) {
	store := givenDatasets(t)
	for file, count := range map[string]int{
		leagueFile: 4180, cupFile: 1337, libertadoresFile: 1255, extendedFile: 10296, historyFile: 6886,
	} {
		t.Run(file, func(t *testing.T) {
			rows, err := store.findMatches(Filter{Source: file})
			if err != nil || len(rows) != count {
				t.Fatalf("got %d raw fixtures, want %d: %v", len(rows), count, err)
			}
		})
	}
	if got := len(store.findPlayers(PlayerFilter{})); got != 18207 {
		t.Errorf("got %d FIFA players, want 18207", got)
	}
}

func TestSoccerQuestions(t *testing.T) {
	store := givenDatasets(t)
	cases := []struct {
		question, tool, args string
		check                func(object) bool
	}{
		{"When did Flamengo last play Corinthians and what was the score?", "search_matches",
			`{"team":"Flamengo","opponent":"Corinthians","status":"played","limit":1}`,
			func(r object) bool {
				m := r["matches"].([]Match)[0]
				return m.Date == "2023-10-08" && *m.HomeGoals == 1 && *m.AwayGoals == 1
			}},
		{"Find all Flamengo vs Fluminense matches", "search_matches",
			`{"team":"Flamengo-RJ","opponent":"Fluminense","limit":500}`, func(r object) bool {
				rows := r["matches"].([]Match)
				if len(rows) < 40 || len(rows) != r["total"] {
					return false
				}
				for _, m := range rows {
					if m.Date == "" || !m.played() || m.Competition == "" ||
						(m.Home != "Flamengo" && m.Away != "Flamengo") || (m.Home != "Fluminense" && m.Away != "Fluminense") {
						return false
					}
				}
				return true
			}},
		{"Find Palmeiras fixtures in 2023", "search_matches",
			`{"team":"Sociedade Esportiva Palmeiras","season":2023,"limit":500}`,
			func(r object) bool { return r["total"] == 43 }},
		{"Find Copa do Brasil finals", "search_matches",
			`{"competition":"Copa do Brasil","stage":"finals"}`, func(r object) bool {
				rows := r["matches"].([]Match)
				return len(rows) == 24 && rows[0].Home == "São Paulo" && rows[0].Stage == "final"
			}},
		{"Find a match on a Brazilian-format date", "search_matches",
			`{"team":"Guarani","date_from":"29/03/2003","date_to":"2003-03-29"}`,
			func(r object) bool {
				m := r["matches"].([]Match)[0]
				return m.Stadium == "Brinco de Ouro" && *m.HomeGoals == 4
			}},
		{"Show 2023 derbies", "search_matches", `{"season":2023,"derby":true}`,
			func(r object) bool { return r["total"].(int) > 30 && derby(r["matches"].([]Match)[0]) }},
		{"Find fixtures with no recorded score", "search_matches",
			`{"source":"Libertadores_Matches.csv","status":"unscored"}`,
			func(r object) bool { return r["total"] == 2 && r["matches"].([]Match)[1].HomeGoals == nil }},
		{"What is Corinthians' 2022 home record?", "team_stats",
			`{"team":"Sport Club Corinthians Paulista","venue":"home"}`, nil},
		{"What is Corinthians' Série A home record in 2022?", "team_stats",
			`{"team":"Sport Club Corinthians Paulista","side":"home","season":2022,"competition":"Serie A"}`, func(r object) bool {
				row := r["record"].(TeamRecord)
				return row.Played == 19 && row.Wins == 12 && row.Draws == 4 && row.Losses == 3 && row.GoalsFor == 24 && row.GoalsAgainst == 11 && row.Away.Played == 0
			}},
		{"What is Palmeiras' 2023 record?", "team_stats",
			`{"team":"Palmeiras","season":2023}`, func(r object) bool {
				row := r["record"].(TeamRecord)
				return row.Played == 43 && row.Played == row.Wins+row.Draws+row.Losses && row.GoalsFor > 0
			}},
		{"Which competitions has Palmeiras played in?", "team_stats",
			`{"team":"Palmeiras"}`, func(r object) bool {
				rows := r["by_competition"].(map[string]TeamRecord)
				return rows[serieA].Played > 100 && rows[libertadores].Played > 0 && rows[cup].Played > 0
			}},
		{"Compare Palmeiras and Santos head-to-head", "team_stats",
			`{"team":"Palmeiras","opponent":"Santos"}`, func(r object) bool {
				row := r["record"].(TeamRecord)
				return row.Played > 40 && row.Home.Played > 0 && row.Away.Played > 0 && r["latest_played_match"].(Match).played()
			}},
		{"Who is Neymar Jr?", "search_players", `{"name":"Neymar","include_attributes":true}`,
			func(r object) bool {
				p := r["players"].([]Player)[0]
				return p.Name == "Neymar Jr" && p.Overall == 92 && p.Attributes["Dribbling"] != "" && p.Attributes["Height"] != ""
			}},
		{"Is Gabriel Barbosa in the FIFA snapshot?", "search_players", `{"name":"Gabriel Barbosa"}`,
			func(r object) bool { return r["total"] == 0 }},
		{"Who are the highest-rated Brazilian players?", "search_players", `{"nationality":"Brazilian","limit":3}`,
			func(r object) bool {
				p := r["players"].([]Player)
				return len(p) == 3 && p[0].Name == "Neymar Jr" && p[0].Overall >= p[1].Overall && p[1].Overall >= p[2].Overall && r["next_offset"] == 3
			}},
		{"Which forwards play for Grêmio?", "search_players", `{"club":"Gremio","position":"forwards"}`,
			func(r object) bool {
				p := r["players"].([]Player)
				return len(p) > 0 && p[0].Club == "Grêmio" && positionMatches(p[0].Position, "FORWARDS")
			}},
		{"Which players are at Flamengo in FIFA?", "search_players", `{"club":"Flamengo"}`,
			func(r object) bool { return r["total"] == 0 }},
		{"Group Brazilians at Brazilian clubs by rating", "search_players",
			`{"nationality":"Brazil","brazilian_clubs":true,"group_by_club":true}`, func(r object) bool {
				for _, row := range r["clubs"].([]ClubRating) {
					if row.Club == "Grêmio" && row.Players == 20 && row.AverageOverall > 60 {
						return true
					}
				}
				return false
			}},
		{"Who won the 2019 Brasileirão?", "competition_standings", `{"season":2019}`, func(r object) bool {
			table := r["standings"].([]Standing)
			return len(table) == 20 && r["complete_round_robin"] == true && table[0].Team == "Flamengo" &&
				table[0].Status == "champion" && table[0].Points == 90 && table[0].Wins == 28 && table[0].Played == 38 &&
				table[1].Team == "Santos" && table[2].Team == "Palmeiras"
		}},
		{"Which teams occupied the 2020 relegation places?", "competition_standings", `{"season":2020}`, func(r object) bool {
			table := r["standings"].([]Standing)
			names := map[string]bool{"Vasco da Gama": true, "Goiás": true, "Coritiba": true, "Botafogo-RJ": true}
			for _, row := range table[16:] {
				if row.Status != "relegation places" || !names[row.Team] {
					return false
				}
			}
			return true
		}},
		{"How complete are the 2023 standings?", "competition_standings", `{"season":2023}`,
			func(r object) bool {
				return r["complete_round_robin"] == false && len(r["standings"].([]Standing)) == 20
			}},
		{"Show the 2018 Copa Libertadores bracket", "search_matches",
			`{"competition":"Libertadores","season":2018,"stage":"knockout","limit":40}`,
			func(r object) bool {
				rows := r["matches"].([]Match)
				return len(rows) == 30 && rows[0].Stage == "final" && rows[0].Home == "River Plate"
			}},
		{"What was the average goals per match in 2019 Série A?", "analyze_matches",
			`{"competition":"Brasileirao","season":2019}`, func(r object) bool {
				total := r["summary"].(Summary)
				return total.Played == 380 && total.Goals == 876 && total.GoalsPerMatch == 876.0/380 && total.HomeWins+total.AwayWins+total.Draws == 380
			}},
		{"Which Série A club scored most goals in 2023?", "analyze_matches",
			`{"competition":"Serie A","season":2023,"metric":"goals_for","limit":1}`,
			func(r object) bool { row := r["teams"].([]TeamRecord)[0]; return row.GoalsFor >= 60 }},
		{"Which club had the best away record in Série A 2019?", "analyze_matches",
			`{"competition":"Serie A","season":2019,"metric":"win_rate","side":"away","minimum_matches":19,"limit":1}`,
			func(r object) bool {
				row := r["teams"].([]TeamRecord)[0]
				return row.Team == "Flamengo" && row.Played == 19 && row.Home.Played == 0
			}},
		{"What were the biggest wins?", "analyze_matches", `{"metric":"biggest_wins","limit":3}`,
			func(r object) bool {
				rows := r["victories"].([]Victory)
				return len(rows) == 3 && rows[0].Margin >= 8 && rows[0].Margin >= rows[1].Margin
			}},
		{"Compare the 2018 and 2019 Série A seasons", "analyze_matches",
			`{"competition":"Serie A","season_from":2018,"season_to":2019}`, func(r object) bool {
				rows := r["by_season"].(map[int]Summary)
				return len(rows) == 2 && rows[2018].Played == 380 && rows[2019].Played == 380 && rows[2018].Goals != rows[2019].Goals
			}},
		{"Join the Grêmio roster to its 2019 league record", "club_profile",
			`{"team":"Gremio-RS","season":2019,"competition":"Serie A","limit":1}`, func(r object) bool {
				return r["fifa_roster"].(object)["total"] == 20 && r["matches"].(map[string]any)["record"].(TeamRecord).Played == 38
			}},
	}

	tools := make(map[string]Tool)
	for _, tool := range soccerTools() {
		tools[tool.Name] = tool
	}
	for _, tt := range cases {
		t.Run(tt.question, func(t *testing.T) {
			start := time.Now()
			result, err := tools[tt.tool].run(store, json.RawMessage(tt.args))
			if tt.check == nil {
				if err == nil {
					t.Fatal("expected invalid input error")
				}
				return
			}
			if err != nil {
				t.Fatal(err)
			}
			if !tt.check(result) {
				t.Fatalf("unexpected response: %v", result)
			}
			budget := 2 * time.Second
			if tt.tool != "search_matches" && tt.tool != "search_players" {
				budget = 5 * time.Second
			}
			if elapsed := time.Since(start); elapsed >= budget {
				t.Errorf("query took %s, budget %s", elapsed, budget)
			}
		})
	}
}

func TestReconciledFixtureCarriesAvailableSourceFields(t *testing.T) {
	store := givenDatasets(t)
	rows, err := store.findMatches(Filter{Team: "Flamengo", Opponent: "Santos", Side: "home", Competition: serieA, Season: 2019})
	if err != nil || len(rows) != 1 {
		t.Fatalf("want one reconciled match, got %d: %v", len(rows), err)
	}
	m := rows[0]
	if len(m.Sources) != 3 || m.Round == "" || m.Stadium == "" || m.HistoricalID == "" || m.HomeState != "RJ" || m.AwayState != "SP" || len(m.Stats) == 0 || !m.played() {
		t.Fatalf("missing source data: %+v", m)
	}
}

func TestMCPStdio(t *testing.T) {
	store := givenDatasets(t)
	input := strings.Join([]string{
		`{"jsonrpc":"2.0","id":"init","method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}`,
		`{"jsonrpc":"2.0","method":"notifications/initialized"}`,
		`{"jsonrpc":"2.0","id":2,"method":"tools/list"}`,
		`{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"search_matches","arguments":{"team":"São Paulo","limit":1}}}`,
		`{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"search_matches","arguments":{"date_from":"today"}}}`,
		`{"jsonrpc":"2.0","id":5,"method":"tools/call","params":{"name":"missing"}}`,
		`not JSON`,
		`{"jsonrpc":"2.0","id":6,"method":"ping"}`,
	}, "\n")
	var output bytes.Buffer
	if err := serve(store, strings.NewReader(input), &output); err != nil {
		t.Fatal(err)
	}
	var messages []Response
	scan := bufio.NewScanner(&output)
	for scan.Scan() {
		var response Response
		if err := json.Unmarshal(scan.Bytes(), &response); err != nil {
			t.Fatal(err)
		}
		messages = append(messages, response)
	}
	if err := scan.Err(); err != nil {
		t.Fatal(err)
	}
	if len(messages) != 7 {
		t.Fatalf("got %d messages, want 7", len(messages))
	}
	if string(messages[0].ID) != `"init"` || (*messages[0].Result)["protocolVersion"] != protocolVersion {
		t.Fatalf("bad handshake: %+v", messages[0])
	}
	if listed := (*messages[1].Result)["tools"].([]any); len(listed) != len(soccerTools()) {
		t.Fatalf("listed %d tools", len(listed))
	}
	content := (*messages[2].Result)["content"].([]any)[0].(map[string]any)
	var result struct {
		Matches []Match
		Total   int
	}
	if content["type"] != "text" {
		t.Fatalf("unexpected content: %v", content)
	}
	if err := json.Unmarshal([]byte(fmt.Sprint(content["text"])), &result); err != nil || len(result.Matches) != 1 || result.Total < 1 {
		t.Fatalf("bad tool result: %+v %v", result, err)
	}
	if (*messages[3].Result)["isError"] != true || messages[4].Error.Code != -32602 || messages[5].Error.Code != -32700 ||
		string(messages[6].ID) != "6" || messages[6].Result == nil {
		t.Fatalf("bad error handling or ping: %+v", messages[3:])
	}
}
