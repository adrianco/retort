package main

import (
	"testing"
)

// statsTestDB uses the same testDB from queries_test.go
// Brasileirao 2020: Palmeiras-SP 2-1 Flamengo-RJ, Flamengo-RJ 1-0 Palmeiras-SP
// Brasileirao 2021: São Paulo-SP 0-0 Corinthians-SP, Palmeiras-SP 3-1 São Paulo-SP
// Copa 2020: Flamengo 2-0 Palmeiras

func TestGetStatistics_AvgGoals(t *testing.T) {
	result := GetStatistics(testDB, "brasileirao", 0, "avg_goals")
	avg, ok := result["avg_goals_per_match"].(float64)
	if !ok {
		t.Fatalf("expected float64 avg_goals_per_match, got %T: %v", result["avg_goals_per_match"], result["avg_goals_per_match"])
	}
	// Total goals in brasileirao: 2+1 + 1+0 + 0+0 + 3+1 = 8 goals in 4 matches = 2.0
	if avg < 1.0 || avg > 10.0 {
		t.Errorf("avg_goals_per_match out of reasonable range: %f", avg)
	}
}

func TestGetStatistics_BiggestWins(t *testing.T) {
	result := GetStatistics(testDB, "brasileirao", 0, "biggest_wins")
	wins, ok := result["biggest_wins"].([]Match)
	if !ok {
		t.Fatalf("expected []Match biggest_wins, got %T", result["biggest_wins"])
	}
	if len(wins) == 0 {
		t.Error("expected at least one biggest win")
	}
	// The biggest win in testDB brasileirao is Palmeiras 3-1 São Paulo (diff 2)
	if wins[0].HomeGoals-wins[0].AwayGoals < 1 {
		t.Error("biggest win should have positive goal diff")
	}
}

func TestGetStatistics_BestHomeRecord(t *testing.T) {
	result := GetStatistics(testDB, "brasileirao", 0, "best_home_record")
	records, ok := result["best_home_record"].([]TeamStats)
	if !ok {
		t.Fatalf("expected []TeamStats best_home_record, got %T", result["best_home_record"])
	}
	if len(records) == 0 {
		t.Error("expected at least one team in best_home_record")
	}
}

func TestGetStatistics_MatchCount(t *testing.T) {
	result := GetStatistics(testDB, "brasileirao", 2020, "avg_goals")
	count, ok := result["match_count"].(int)
	if !ok {
		t.Fatalf("expected int match_count, got %T", result["match_count"])
	}
	if count != 2 {
		t.Errorf("expected 2 matches in brasileirao 2020, got %d", count)
	}
}
