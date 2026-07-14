import { beforeAll, describe, expect, it } from "vitest";
import type { SoccerDataStore } from "../src/data/store.js";
import { competitionsForTeam, getTeamRecord, rankTeamsByRecord } from "../src/queries/teams.js";
import { loadTestStore } from "./support/testStore.js";

describe("getTeamRecord", () => {
  let store: SoccerDataStore;

  beforeAll(async () => {
    store = await loadTestStore();
  });

  it("test_given_a_teams_full_record_when_computed_then_wins_draws_and_losses_sum_to_matches_played", () => {
    // Given Corinthians' full record across all competitions and seasons
    // When computing the record
    const record = getTeamRecord(store, "Corinthians");
    // Then wins + draws + losses accounts for every match counted
    expect(record.matches).toBeGreaterThan(0);
    expect(record.wins + record.draws + record.losses).toBe(record.matches);
  });

  it("test_given_a_season_and_home_venue_filter_when_computing_record_then_every_counted_match_is_a_home_fixture", () => {
    // Given Corinthians' 2021 Brasileirão home record (a fully-played, un-truncated season in the dataset)
    // When computing it with venue scoped to home
    const record = getTeamRecord(store, "Corinthians", { competition: "Brasileirao", season: 2021, venue: "home" });
    // Then a full single round-robin home slate is 19 matches (38-round season)
    expect(record.matches).toBe(19);
  });

  it("test_given_fixtures_with_unrecorded_scores_when_computing_record_then_only_scored_matches_are_counted", () => {
    // Given Corinthians' 2022 season, where Brasileirao_Matches.csv has 4 home fixtures recorded as "NA" scores
    // (the source dataset was captured before the season finished)
    const record = getTeamRecord(store, "Corinthians", { competition: "Brasileirao", season: 2022, venue: "home" });
    // When computing the home record
    // Then only the 15 fixtures with a known result are counted, not all 19 scheduled fixtures
    expect(record.matches).toBe(15);
  });

  it("test_given_home_and_away_records_when_summed_then_they_equal_the_combined_season_record", () => {
    // Given Palmeiras' 2023 Brasileirão season split into home and away records
    const home = getTeamRecord(store, "Palmeiras", { competition: "Brasileirao", season: 2023, venue: "home" });
    const away = getTeamRecord(store, "Palmeiras", { competition: "Brasileirao", season: 2023, venue: "away" });
    const combined = getTeamRecord(store, "Palmeiras", { competition: "Brasileirao", season: 2023, venue: "all" });
    // When summing the home and away splits
    // Then the totals reconcile with the combined record
    expect(home.matches + away.matches).toBe(combined.matches);
    expect(home.wins + away.wins).toBe(combined.wins);
    expect(home.goalsFor + away.goalsFor).toBe(combined.goalsFor);
  });

  it("test_given_a_team_with_no_matches_when_computing_record_then_zeroed_record_is_returned_without_error", () => {
    // Given a team name that appears nowhere in the dataset
    // When computing its record
    const record = getTeamRecord(store, "Not A Real Football Club");
    // Then a zeroed record is returned rather than throwing
    expect(record.matches).toBe(0);
    expect(record.winRate).toBe(0);
  });
});

describe("competitionsForTeam", () => {
  let store: SoccerDataStore;

  beforeAll(async () => {
    store = await loadTestStore();
  });

  it("test_given_a_team_that_played_in_multiple_competitions_when_listed_then_all_of_them_are_returned", () => {
    // Given Palmeiras, who play in the Brasileirão, Copa do Brasil, and Libertadores
    // When listing the competitions they've appeared in
    const labels = competitionsForTeam(store, "Palmeiras");
    // Then more than one distinct competition is found
    expect(labels.length).toBeGreaterThan(1);
  });
});

describe("rankTeamsByRecord", () => {
  let store: SoccerDataStore;

  beforeAll(async () => {
    store = await loadTestStore();
  });

  it("test_given_teams_ranked_by_win_rate_when_computed_then_the_list_is_sorted_descending", () => {
    // Given all Brasileirão teams with at least 20 matches
    // When ranking them by win rate
    const ranked = rankTeamsByRecord(store, { competition: "Brasileirao", minMatches: 20, limit: 15 });
    // Then each entry's win rate is greater than or equal to the next
    expect(ranked.length).toBeGreaterThan(1);
    for (let i = 1; i < ranked.length; i += 1) {
      expect(ranked[i - 1]!.winRate).toBeGreaterThanOrEqual(ranked[i]!.winRate);
    }
  });

  it("test_given_a_minimum_matches_threshold_when_ranking_then_teams_below_it_are_excluded", () => {
    // Given a high minimum-matches threshold
    // When ranking teams by record
    const ranked = rankTeamsByRecord(store, { competition: "Brasileirao", minMatches: 50 });
    // Then every returned team meets the threshold
    expect(ranked.every((r) => r.matches >= 50)).toBe(true);
  });
});
