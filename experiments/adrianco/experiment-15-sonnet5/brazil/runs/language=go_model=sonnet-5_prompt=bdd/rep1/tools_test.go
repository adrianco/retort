package main

import (
	"encoding/json"
	"strings"
	"testing"
)

func Test_GivenAKnownRivalry_WhenCallingHeadToHeadTool_ThenResponseContainsTheWinTally(t *testing.T) {
	// Given a store with three Flamengo-vs-Fluminense matches
	store := buildFixtureStore(t)
	args, _ := json.Marshal(map[string]string{"team_a": "Flamengo", "team_b": "Fluminense"})

	// When calling the head_to_head tool
	text, err := handleHeadToHead(store, args)

	// Then the response reports the correct win tally
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !strings.Contains(text, "Flamengo 2 wins") {
		t.Errorf("response %q does not mention the expected win tally", text)
	}
}

func Test_GivenMissingRequiredArgument_WhenCallingHeadToHeadTool_ThenAnErrorIsReturned(t *testing.T) {
	// Given arguments missing the required team_b field
	store := buildFixtureStore(t)
	args, _ := json.Marshal(map[string]string{"team_a": "Flamengo"})

	// When calling the head_to_head tool
	_, err := handleHeadToHead(store, args)

	// Then an error is returned instead of a panic or empty result
	if err == nil {
		t.Error("expected an error for missing team_b, got nil")
	}
}

func Test_GivenASeason_WhenCallingStandingsTool_ThenChampionIsListedFirst(t *testing.T) {
	// Given the fixture's 2023 Brasileirao season, won by Flamengo
	store := buildFixtureStore(t)
	args, _ := json.Marshal(map[string]any{"season": 2023})

	// When calling the standings tool
	text, err := handleStandings(store, args)

	// Then Flamengo is listed as the champion in the first line of results
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !strings.Contains(text, "1. Flamengo") || !strings.Contains(text, "Champion") {
		t.Errorf("response does not show Flamengo as champion:\n%s", text)
	}
}

func Test_GivenNoSeasonArgument_WhenCallingStandingsTool_ThenAnErrorIsReturned(t *testing.T) {
	// Given arguments missing the required season field
	store := buildFixtureStore(t)
	args, _ := json.Marshal(map[string]any{})

	// When calling the standings tool
	_, err := handleStandings(store, args)

	// Then an error is returned
	if err == nil {
		t.Error("expected an error for missing season, got nil")
	}
}

func Test_GivenABrazilianNationalityFilter_WhenCallingTopPlayersTool_ThenOnlyBrazilianPlayersAreListed(t *testing.T) {
	// Given a mix of Brazilian and non-Brazilian players
	store := buildFixtureStore(t)
	args, _ := json.Marshal(map[string]any{"nationality": "Brazil", "limit": 10})

	// When calling the top_players tool
	text, err := handleTopPlayers(store, args)

	// Then no non-Brazilian player (e.g. the fixture's Messi) appears in the response
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if strings.Contains(text, "Messi") {
		t.Errorf("response unexpectedly includes a non-Brazilian player:\n%s", text)
	}
	if !strings.Contains(text, "Neymar Jr") {
		t.Errorf("response missing expected Brazilian player:\n%s", text)
	}
}

func Test_GivenNoMatchingTeam_WhenCallingSearchMatchesTool_ThenAFriendlyNoResultsMessageIsReturned(t *testing.T) {
	// Given a store with no matches for a fictional team
	store := buildFixtureStore(t)
	args, _ := json.Marshal(map[string]string{"team": "Nonexistent FC"})

	// When calling the search_matches tool
	text, err := handleSearchMatches(store, args)

	// Then a friendly "no results" message is returned rather than an error
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !strings.Contains(text, "No matches found") {
		t.Errorf("got %q, want a no-results message", text)
	}
}

func Test_GivenTheBuiltInToolRegistry_WhenListingTools_ThenEveryRequiredCategoryIsCovered(t *testing.T) {
	// Given the full tool registry the server exposes
	registry := BuildToolRegistry()

	// When listing its tools
	tools := registry.List()

	// Then match, player, and standings/statistics tools are all present,
	// covering the match/team/player/competition/statistics categories
	names := make(map[string]bool)
	for _, tool := range tools {
		names[tool.Name] = true
	}
	for _, want := range []string{"search_matches", "head_to_head", "team_record", "standings", "search_players", "top_players", "biggest_wins", "stats_summary"} {
		if !names[want] {
			t.Errorf("tool registry missing expected tool %q", want)
		}
	}
}
