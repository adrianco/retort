// tools_test.go covers the edges of each tool: bad arguments, ambiguous clubs,
// empty results and the answers that have to explain a gap in the data.
package soccerserver

import (
	"strings"
	"testing"

	"github.com/adriancockcroft/brazilian-soccer-mcp/internal/soccer"
)

func TestSearchMatchesFilters(t *testing.T) {
	data := structured(t, "search_matches", map[string]any{
		"team": "Flamengo", "opponent": "Fluminense", "competition": "brasileirao",
		"season_from": 2015, "season_to": 2019, "limit": 100,
	})
	matches := data["matches"].([]map[string]any)
	if len(matches) == 0 {
		t.Fatal("no Fla-Flu league matches between 2015 and 2019")
	}
	for _, m := range matches {
		if m["competition"] != soccer.CompBrasileirao {
			t.Errorf("competition filter leaked: %v", m["competition"])
		}
		if season := m["season"].(int); season < 2015 || season > 2019 {
			t.Errorf("season filter leaked: %d", season)
		}
	}
}

func TestSearchMatchesByDateRange(t *testing.T) {
	got := answer(t, "search_matches", map[string]any{
		"team": "Santos", "date_from": "2019-05-01", "date_to": "2019-05-31", "limit": 20})
	containsAll(t, got, "2019-05")
	if strings.Contains(got, "2019-06") || strings.Contains(got, "2019-04") {
		t.Errorf("date range leaked:\n%s", got)
	}
}

func TestSearchMatchesEmptyResultExplainsItself(t *testing.T) {
	got := answer(t, "search_matches", map[string]any{"team": "Flamengo", "competition": "serie-c"})
	containsAll(t, got, "No matches found", "Flamengo")
	if !strings.Contains(got, "appears in the data") {
		t.Errorf("an empty answer should say where the club does appear:\n%s", got)
	}
}

func TestAmbiguousTeamIsReported(t *testing.T) {
	got := failure(t, "search_matches", map[string]any{"team": "América"})
	containsAll(t, got, "could mean several clubs", "América-MG", "América-RN")
}

func TestUnknownTeamSuggests(t *testing.T) {
	got := failure(t, "team_stats", map[string]any{"team": "Palmieras"})
	if !strings.Contains(got, "Did you mean") && !strings.Contains(got, "Palmeiras") {
		t.Errorf("an unknown club should suggest alternatives:\n%s", got)
	}
}

func TestUnknownCompetitionIsReported(t *testing.T) {
	got := failure(t, "search_matches", map[string]any{"competition": "Premier League"})
	containsAll(t, got, "unknown competition", "brasileirao")
}

func TestUnknownSeasonIsReported(t *testing.T) {
	got := failure(t, "standings", map[string]any{"competition": "brasileirao", "season": 1975})
	containsAll(t, got, "available seasons", "2003")
}

func TestBadArgumentTypesAreRejected(t *testing.T) {
	cases := []struct {
		tool string
		args map[string]any
		want string
	}{
		{"search_matches", map[string]any{"season": "not a year"}, "integer"},
		{"search_matches", map[string]any{"date_from": "yesterday"}, "not a date"},
		{"search_matches", map[string]any{"team": "Flamengo", "date_from": "2019-12-01", "date_to": "2019-01-01"}, "before"},
		{"search_matches", map[string]any{"season_from": 2020, "season_to": 2010}, "before"},
		{"team_stats", map[string]any{"team": "Flamengo", "venue": "moon"}, "venue"},
		{"compare_seasons", map[string]any{"seasons": []any{2019}}, "at least two"},
	}
	for _, c := range cases {
		got := failure(t, c.tool, c.args)
		if !strings.Contains(strings.ToLower(got), strings.ToLower(c.want)) {
			t.Errorf("%s with %v: message %q does not mention %q", c.tool, c.args, got, c.want)
		}
	}
}

func TestHeadToHeadRejectsOneClubTwice(t *testing.T) {
	got := failure(t, "head_to_head", map[string]any{"team_a": "Flamengo", "team_b": "flamengo-rj"})
	containsAll(t, got, "two different clubs")
}

func TestMatchDetailsCarriesExtendedStats(t *testing.T) {
	got := answer(t, "match_details", map[string]any{
		"team": "Flamengo", "opponent": "Corinthians", "date": "2023-10-08"})
	containsAll(t, got, "2023-10-08", "Shots:", "corners:", "Sources:", "Match id:")
}

func TestMatchDetailsByID(t *testing.T) {
	data := structured(t, "search_matches", map[string]any{"team": "Flamengo", "season": 2019, "limit": 1})
	id := data["matches"].([]map[string]any)[0]["id"].(string)
	got := answer(t, "match_details", map[string]any{"match_id": id})
	containsAll(t, got, id)
	failure(t, "match_details", map[string]any{"match_id": "not-a-match"})
	failure(t, "match_details", map[string]any{"team": "Flamengo"})
}

func TestStandingsThroughRound(t *testing.T) {
	got := answer(t, "standings", map[string]any{"season": 2019, "through_round": 5, "limit": 5})
	containsAll(t, got, "2019 Brasileirão standings")
	if strings.Contains(got, "Champion") {
		t.Errorf("a five round table must not crown anybody:\n%s", got)
	}
}

func TestSeasonSummaryLeagueAndCup(t *testing.T) {
	league := answer(t, "season_summary", map[string]any{"competition": "brasileirao", "season": 2019})
	containsAll(t, league, "Campeonato Brasileiro Série A 2019", "Champion: Flamengo", "Season statistics", "Most goals scored")

	cup := answer(t, "season_summary", map[string]any{"competition": "copa-do-brasil", "season": 2019})
	containsAll(t, cup, "Bracket", "Final", "Winner")
}

func TestBiggestWinsOrdering(t *testing.T) {
	data := structured(t, "biggest_wins", map[string]any{"competition": "brasileirao", "limit": 5})
	matches := data["matches"].([]map[string]any)
	prev := 99
	for _, m := range matches {
		margin := m["home_goals"].(int) - m["away_goals"].(int)
		if margin < 0 {
			margin = -margin
		}
		if margin > prev {
			t.Error("biggest wins are not ordered by margin")
		}
		prev = margin
	}
	byGoals := answer(t, "biggest_wins", map[string]any{"order_by": "total_goals", "limit": 3})
	containsAll(t, byGoals, "Highest scoring matches")
}

func TestBestRecordsMetrics(t *testing.T) {
	for _, metric := range []string{"points", "win_rate", "wins", "goals_for", "goals_against", "goal_diff", "points_per_match"} {
		got := answer(t, "best_records", map[string]any{
			"competition": "brasileirao", "season": 2019, "metric": metric, "limit": 3})
		containsAll(t, got, strings.ReplaceAll(metric, "_", " "))
	}
}

func TestFindDerbies(t *testing.T) {
	got := answer(t, "find_derbies", map[string]any{"season": 2019, "competition": "brasileirao", "limit": 50})
	containsAll(t, got, "Derbies", "Fla-Flu")
	filtered := structured(t, "find_derbies", map[string]any{"rivalry": "Grenal", "limit": 10})
	for _, m := range filtered["matches"].([]map[string]any) {
		if m["rivalry"] != "Grenal" {
			t.Errorf("rivalry filter leaked: %v", m["rivalry"])
		}
	}
	none := answer(t, "find_derbies", map[string]any{"rivalry": "Not A Derby"})
	containsAll(t, none, "Known derbies")
}

func TestSearchPlayersMissingClubExplained(t *testing.T) {
	got := answer(t, "search_players", map[string]any{"club": "Flamengo"})
	containsAll(t, got, "No players match", "no squad for", "Grêmio")
}

func TestSearchPlayersByClubUsesTheCanonicalName(t *testing.T) {
	for _, club := range []string{"Gremio", "Grêmio", "gremio-rs"} {
		data := structured(t, "search_players", map[string]any{"club": club, "limit": 5})
		if data["total"].(int) == 0 {
			t.Errorf("no squad found for %q", club)
		}
	}
}

func TestClubSquadsFilters(t *testing.T) {
	all := structured(t, "club_squads", map[string]any{"brazilian_only": false, "limit": 200})
	brazilian := structured(t, "club_squads", map[string]any{"brazilian_only": true, "limit": 200})
	if brazilian["total"].(int) >= all["total"].(int) {
		t.Error("the Brazilian filter did not narrow the list")
	}
	named := answer(t, "club_squads", map[string]any{"clubs": []any{"Cruzeiro"}})
	containsAll(t, named, "Cruzeiro")
}

func TestGraphTools(t *testing.T) {
	got := answer(t, "graph_neighbors", map[string]any{"entity": "Flamengo", "type": "team", "limit": 10})
	containsAll(t, got, "team:flamengo-rj", "relationships")

	byID := answer(t, "graph_neighbors", map[string]any{
		"entity": "competition:brasileirao", "node_types": []any{"season"}, "limit": 5})
	containsAll(t, byID, "season")

	path := answer(t, "graph_path", map[string]any{
		"from": "Neymar", "from_type": "player", "to": "country:brazil", "max_depth": 3})
	containsAll(t, path, "Path from", "nationality")

	failure(t, "graph_neighbors", map[string]any{"entity": "not an entity at all"})

	disconnected := answer(t, "graph_path", map[string]any{
		"from": "team:flamengo-rj", "to": "competition:brasileirao", "max_depth": 1})
	containsAll(t, disconnected, "No path")
}

func TestListTeamsFilters(t *testing.T) {
	data := structured(t, "list_teams", map[string]any{"state": "RJ", "limit": 100})
	teams := data["teams"].([]map[string]any)
	if len(teams) < 5 {
		t.Fatalf("only %d clubs from Rio", len(teams))
	}
	for _, team := range teams {
		if team["state"] != "RJ" {
			t.Errorf("%v is not from RJ", team["name"])
		}
	}
	byComp := structured(t, "list_teams", map[string]any{"competition": "libertadores", "limit": 200})
	for _, team := range byComp["teams"].([]map[string]any) {
		found := false
		for _, comp := range team["competitions"].([]string) {
			if comp == soccer.CompLibertadores {
				found = true
			}
		}
		if !found {
			t.Errorf("%v never played the Libertadores", team["name"])
		}
	}
	bySeason := structured(t, "list_teams", map[string]any{"competition": "brasileirao", "season": 2019, "limit": 100})
	if n := len(bySeason["teams"].([]map[string]any)); n != 20 {
		t.Errorf("the 2019 Brasileirão had %d clubs", n)
	}
	byQuery := answer(t, "list_teams", map[string]any{"query": "atletico"})
	containsAll(t, byQuery, "Atlético-MG", "Atlético-GO")
}

func TestLimitsAreBounded(t *testing.T) {
	data := structured(t, "search_matches", map[string]any{"team": "Flamengo", "limit": 5000})
	if len(data["matches"].([]map[string]any)) > 200 {
		t.Error("limit is not capped")
	}
}

func TestDatasetInventory(t *testing.T) {
	got := answer(t, "list_datasets", map[string]any{})
	containsAll(t, got,
		"Brasileirao_Matches.csv", "novo_campeonato_brasileiro.csv", "Brazilian_Cup_Matches.csv",
		"Libertadores_Matches.csv", "BR-Football-Dataset.csv", "fifa_data.csv",
		"CC BY 4.0", "CC0 Public Domain", "Apache 2.0", "Known gaps")
}

func TestServerMetadata(t *testing.T) {
	srv := testServer(t)
	if srv.Name != ServerName || srv.Version != ServerVersion {
		t.Errorf("server identity = %s %s", srv.Name, srv.Version)
	}
	if !strings.Contains(srv.Instructions, "Coverage:") {
		t.Errorf("instructions should describe the coverage:\n%s", srv.Instructions)
	}
	if !strings.Contains(srv.Instructions, "Limitations") {
		t.Error("instructions should state the limitations")
	}
}

func TestVenueAndResultNeedAClub(t *testing.T) {
	containsAll(t, failure(t, "search_matches", map[string]any{"result": "win", "season": 2019}), "needs a `team`")
	containsAll(t, failure(t, "search_matches", map[string]any{"venue": "home", "season": 2019}), "needs a `team`")
}

func TestCompareSeasonsHandlesOverlappingArguments(t *testing.T) {
	got := answer(t, "compare_seasons", map[string]any{
		"competition": "brasileirao", "seasons": []any{2018, 2019},
		"season_from": 2018, "season_to": 2019,
	})
	if strings.Count(got, "\n2018 ") > 1 || strings.Count(got, "\n2019 ") > 1 {
		t.Errorf("a season is listed twice:\n%s", got)
	}
}

func TestClubSquadsDeduplicatesOverlappingPatterns(t *testing.T) {
	got := answer(t, "club_squads", map[string]any{"clubs": []any{"Gremio", "Gr"}})
	if strings.Count(got, "- Grêmio:") > 1 {
		t.Errorf("Grêmio is listed twice:\n%s", got)
	}
}

// A plain date_to means the whole of that day: fixtures carry a kick-off time.
func TestDateRangeIncludesTheLastDay(t *testing.T) {
	data := structured(t, "search_matches", map[string]any{
		"competition": "brasileirao", "date_from": "2019-05-26", "date_to": "2019-05-26", "limit": 20})
	matches := data["matches"].([]map[string]any)
	if len(matches) == 0 {
		t.Fatal("a single day range returned nothing, although fixtures were played that day")
	}
	for _, m := range matches {
		if m["date"] != "2019-05-26" {
			t.Errorf("date range leaked: %v", m["date"])
		}
	}
}

// Paging must be honest in the prose as well as in the structured payload.
func TestPagingProseMatchesTheData(t *testing.T) {
	all := structured(t, "search_matches", map[string]any{"team": "Flamengo", "season": 2019, "limit": 200})
	total := all["total"].(int)

	last := answer(t, "search_matches", map[string]any{
		"team": "Flamengo", "season": 2019, "limit": 3, "offset": total - 2})
	if strings.Contains(last, "more matches match these filters") {
		t.Errorf("the last page claims there is more to come:\n%s", last)
	}

	beyond := answer(t, "search_matches", map[string]any{
		"team": "Flamengo", "season": 2019, "limit": 3, "offset": total + 5})
	if strings.Contains(beyond, "No matches found") {
		t.Errorf("paging past the end must not read as an empty result set:\n%s", beyond)
	}
	containsAll(t, beyond, "past the end")

	players := answer(t, "search_players", map[string]any{"nationality": "Brazil", "limit": 2, "offset": 900})
	if strings.Contains(players, "No players match") {
		t.Errorf("paging past the end of the player list must explain itself:\n%s", players)
	}
}
