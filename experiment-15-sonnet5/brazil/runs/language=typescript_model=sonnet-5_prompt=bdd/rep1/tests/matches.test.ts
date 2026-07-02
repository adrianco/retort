import { beforeAll, describe, expect, it } from "vitest";
import type { SoccerDataStore } from "../src/data/store.js";
import { headToHead, mostRecentMatch, searchMatches } from "../src/queries/matches.js";
import { loadTestStore } from "./support/testStore.js";

describe("searchMatches", () => {
  let store: SoccerDataStore;

  beforeAll(async () => {
    store = await loadTestStore();
  });

  it("test_given_a_team_name_when_searching_matches_then_every_result_involves_that_team", () => {
    // Given the team Palmeiras
    // When searching for its matches
    const result = searchMatches(store, { team: "Palmeiras", limit: 50 });
    // Then every returned match has Palmeiras as home or away
    expect(result.matches.length).toBeGreaterThan(0);
    expect(result.matches.every((m) => m.homeTeamKey === "palmeiras" || m.awayTeamKey === "palmeiras")).toBe(true);
  });

  it("test_given_a_state_suffixed_team_name_when_searching_then_it_matches_the_same_team_as_the_bare_name", () => {
    // Given the same club referred to with and without its state suffix
    const withSuffix = searchMatches(store, { team: "Flamengo-RJ" });
    const withoutSuffix = searchMatches(store, { team: "Flamengo" });
    // When searching matches by each spelling
    // Then both spellings resolve to the same total match count
    expect(withSuffix.totalMatches).toBe(withoutSuffix.totalMatches);
    expect(withSuffix.totalMatches).toBeGreaterThan(0);
  });

  it("test_given_a_season_filter_when_searching_then_only_that_season_is_returned", () => {
    // Given a request scoped to the 2023 season
    // When searching Palmeiras matches in that season
    const result = searchMatches(store, { team: "Palmeiras", season: 2023, limit: 100 });
    // Then every returned match belongs to the 2023 season
    expect(result.matches.length).toBeGreaterThan(0);
    expect(result.matches.every((m) => m.season === 2023)).toBe(true);
  });

  it("test_given_a_competition_filter_when_searching_then_only_that_competition_is_returned", () => {
    // Given a request scoped to Copa do Brasil
    // When searching Palmeiras matches in that competition
    const result = searchMatches(store, { team: "Palmeiras", competition: "CopaDoBrasil", limit: 100 });
    // Then every returned match belongs to the Copa do Brasil competition
    expect(result.matches.length).toBeGreaterThan(0);
    expect(result.matches.every((m) => m.competition === "CopaDoBrasil")).toBe(true);
  });

  it("test_given_a_limit_lower_than_total_matches_when_searching_then_total_count_still_reflects_the_full_set", () => {
    // Given a Flamengo search limited to 2 results, when there are many more matches in the dataset
    const result = searchMatches(store, { team: "Flamengo", limit: 2 });
    // When inspecting the totals
    // Then only 2 matches are returned but totalMatches reflects the full unfiltered count
    expect(result.matches.length).toBe(2);
    expect(result.totalMatches).toBeGreaterThan(2);
  });

  it("test_given_no_matching_team_when_searching_then_an_empty_result_is_returned", () => {
    // Given a team name that does not exist in any dataset
    // When searching for its matches
    const result = searchMatches(store, { team: "Not A Real Football Club" });
    // Then no matches are found and no error is thrown
    expect(result.matches).toHaveLength(0);
    expect(result.totalMatches).toBe(0);
  });
});

describe("headToHead", () => {
  let store: SoccerDataStore;

  beforeAll(async () => {
    store = await loadTestStore();
  });

  it("test_given_two_rival_teams_when_computing_head_to_head_then_win_counts_sum_to_total_matches", () => {
    // Given the Fla-Flu derby (Flamengo vs Fluminense)
    // When computing their head-to-head record
    const result = headToHead(store, "Flamengo", "Fluminense");
    // Then wins for both sides plus draws account for every match
    expect(result.totalMatches).toBeGreaterThan(0);
    expect(result.teamAWins + result.teamBWins + result.draws).toBe(result.totalMatches);
  });

  it("test_given_two_teams_when_computing_head_to_head_then_every_match_involves_both_teams", () => {
    // Given two known rival clubs
    // When computing their head-to-head matches
    const result = headToHead(store, "Corinthians", "Palmeiras");
    // Then every returned match features both clubs, on opposite sides
    expect(result.matches.length).toBeGreaterThan(0);
    for (const match of result.matches) {
      const teamKeys = [match.homeTeamKey, match.awayTeamKey];
      expect(teamKeys).toContain("corinthians");
      expect(teamKeys).toContain("palmeiras");
    }
  });
});

describe("mostRecentMatch", () => {
  let store: SoccerDataStore;

  beforeAll(async () => {
    store = await loadTestStore();
  });

  it("test_given_two_teams_when_finding_most_recent_match_then_it_is_the_latest_by_date", () => {
    // Given all matches between Flamengo and Corinthians
    const all = headToHead(store, "Flamengo", "Corinthians");
    // When asking for only the most recent one
    const recent = mostRecentMatch(store, "Flamengo", "Corinthians");
    // Then it matches the first entry of the date-descending full list
    expect(recent).not.toBeNull();
    expect(recent?.date?.getTime()).toBe(all.matches[0]?.date?.getTime());
  });
});
