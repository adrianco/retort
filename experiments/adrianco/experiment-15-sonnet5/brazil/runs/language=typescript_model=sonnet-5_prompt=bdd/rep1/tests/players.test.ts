import { beforeAll, describe, expect, it } from "vitest";
import type { SoccerDataStore } from "../src/data/store.js";
import { brazilianPlayersAtBrazilianClubs, searchPlayers, topBrazilianPlayers } from "../src/queries/players.js";
import { loadTestStore } from "./support/testStore.js";

describe("searchPlayers", () => {
  let store: SoccerDataStore;

  beforeAll(async () => {
    store = await loadTestStore();
  });

  it("test_given_a_partial_name_when_searching_players_then_matching_names_are_returned", () => {
    // Given a partial player name
    // When searching by name
    const results = searchPlayers(store, { name: "Neymar" });
    // Then a matching player is found
    expect(results.length).toBeGreaterThan(0);
    expect(results[0]!.name).toContain("Neymar");
  });

  it("test_given_a_nationality_filter_when_searching_then_every_result_has_that_nationality", () => {
    // Given a request for Brazilian players
    // When searching by nationality
    const results = searchPlayers(store, { nationality: "Brazil", limit: 100 });
    // Then every returned player is Brazilian
    expect(results.length).toBeGreaterThan(0);
    expect(results.every((p) => p.nationality === "Brazil")).toBe(true);
  });

  it("test_given_a_club_filter_when_searching_then_every_result_plays_for_that_club", () => {
    // Given a request for Grêmio's players (spelled without an accent, as some datasets do)
    // When searching by club
    const results = searchPlayers(store, { club: "Gremio", limit: 100 });
    // Then every returned player's club normalizes to Grêmio
    expect(results.length).toBeGreaterThan(0);
    expect(results.every((p) => p.club === "Grêmio")).toBe(true);
  });

  it("test_given_sort_by_overall_when_searching_then_results_are_sorted_descending", () => {
    // Given a search across all Brazilian players
    // When sorting by FIFA overall rating
    const results = searchPlayers(store, { nationality: "Brazil", sortBy: "overall", limit: 20 });
    // Then each entry's rating is greater than or equal to the next
    for (let i = 1; i < results.length; i += 1) {
      expect(results[i - 1]!.overall ?? 0).toBeGreaterThanOrEqual(results[i]!.overall ?? 0);
    }
  });

  it("test_given_a_limit_when_searching_then_result_count_does_not_exceed_it", () => {
    // Given a request for Brazilian players with a limit of 3
    // When searching
    const results = searchPlayers(store, { nationality: "Brazil", limit: 3 });
    // Then no more than 3 players are returned
    expect(results.length).toBe(3);
  });
});

describe("topBrazilianPlayers", () => {
  let store: SoccerDataStore;

  beforeAll(async () => {
    store = await loadTestStore();
  });

  it("test_given_the_dataset_when_finding_top_brazilian_players_then_the_highest_rated_is_first", () => {
    // Given the full FIFA dataset
    // When finding the top-rated Brazilian players
    const top = topBrazilianPlayers(store, 5);
    // Then the list is non-empty and sorted with the best player first
    expect(top.length).toBe(5);
    expect(top[0]!.overall ?? 0).toBeGreaterThanOrEqual(top[4]!.overall ?? 0);
  });
});

describe("brazilianPlayersAtBrazilianClubs", () => {
  let store: SoccerDataStore;

  beforeAll(async () => {
    store = await loadTestStore();
  });

  it("test_given_brazilian_players_grouped_by_club_when_computed_then_every_group_has_at_least_one_player", () => {
    // Given Brazilian players grouped by the Brazilian clubs they play for
    // When computing the summary
    const summaries = brazilianPlayersAtBrazilianClubs(store);
    // Then every group has a positive player count and a plausible average rating
    expect(summaries.length).toBeGreaterThan(0);
    expect(summaries.every((s) => s.playerCount > 0 && s.averageOverall > 0)).toBe(true);
  });
});
