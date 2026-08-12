package main

import (
	"testing"
	"time"
)

func TestLoadAllProvidedDatasetsAndKnownResults(t *testing.T) {
	started := time.Now()
	db, err := LoadDatabase("data/kaggle")
	if err != nil {
		t.Fatal(err)
	}
	if len(db.Matches) < 20000 {
		t.Fatalf("expected all five match files, got %d loaded matches", len(db.Matches))
	}
	if len(db.Players) != 18207 {
		t.Fatalf("expected 18,207 FIFA players, got %d", len(db.Players))
	}
	sources := map[string]bool{}
	for _, m := range db.Matches {
		sources[m.Source] = true
	}
	for _, name := range []string{"Brasileirao_Matches.csv", "Brazilian_Cup_Matches.csv", "Libertadores_Matches.csv", "BR-Football-Dataset.csv", "novo_campeonato_brasileiro.csv"} {
		if !sources[name] {
			t.Errorf("source %s was not loaded", name)
		}
	}
	table := db.Standings("Brasileirao", 2019)
	if len(table) == 0 || table[0].Team != "Flamengo" || table[0].Points != 90 {
		t.Fatalf("unexpected calculated 2019 champion: %+v", table)
	}
	brazilians := db.SearchPlayers(PlayerFilter{Nationality: "Brazil", Limit: 1})
	if len(brazilians) != 1 || brazilians[0].Name != "Neymar Jr" || brazilians[0].Overall != 92 {
		t.Fatalf("unexpected top Brazilian player: %+v", brazilians)
	}
	if elapsed := time.Since(started); elapsed > 5*time.Second {
		t.Fatalf("load and aggregate query took %s; expected under five seconds", elapsed)
	}
}

func TestTwentyNaturalLanguageBehaviors(t *testing.T) {
	db, err := LoadDatabase("data/kaggle")
	if err != nil {
		t.Fatal(err)
	}
	questions := []string{
		"Show me all Flamengo vs Fluminense matches",
		"What matches did Palmeiras play in 2023?",
		"Find all Copa do Brasil finals",
		"What is Corinthians' home record in 2022?",
		"Which team scored the most goals in Serie A 2023?",
		"Compare Palmeiras and Santos head-to-head",
		"Find all Brazilian players in the dataset",
		"Who are the highest-rated Brazilian players?",
		"Show me all forwards from São Paulo FC",
		"Who won the 2019 Brasileirão?",
		"Show the 2018 Copa Libertadores bracket",
		"Which teams were relegated in 2020?",
		"What's the average goals per match in the Brasileirão?",
		"Which team has the best away record in 2022?",
		"Show me the biggest wins in the dataset",
		"When did Flamengo last play Corinthians?",
		"What competitions has Palmeiras played in?",
		"Show me all derbies in 2023",
		"Compare the 2018 and 2019 seasons",
		"Who are the top scorers in 2019?",
		"Who is Neymar Jr?",
	}
	for _, q := range questions {
		answer := db.Answer(q)
		if answer == "" || answer == "I could not map that question to the provided data. Try naming a team, player, competition, or season, or use the specialized MCP tools for exact filters." {
			t.Errorf("question was not answered: %q => %q", q, answer)
		}
	}
}
