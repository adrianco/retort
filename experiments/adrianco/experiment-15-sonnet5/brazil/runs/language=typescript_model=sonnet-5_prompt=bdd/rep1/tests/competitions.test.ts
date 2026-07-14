import { beforeAll, describe, expect, it } from "vitest";
import type { SoccerDataStore } from "../src/data/store.js";
import { bottomOfTable, calculateStandings, seasonsForCompetition } from "../src/queries/competitions.js";
import { loadTestStore } from "./support/testStore.js";

describe("calculateStandings", () => {
  let store: SoccerDataStore;

  beforeAll(async () => {
    store = await loadTestStore();
  });

  it("test_given_the_2019_brasileirao_season_when_standings_are_calculated_then_flamengo_is_champion", () => {
    // Given the 2019 Brasileirão season, which Flamengo famously won
    // When calculating the standings from raw match results
    const standings = calculateStandings(store, "Brasileirao", 2019);
    // Then Flamengo tops the table with 90 points from 28 wins, 6 draws, 4 losses
    expect(standings[0]).toMatchObject({ team: "Flamengo", points: 90, wins: 28, draws: 6, losses: 4, position: 1 });
  });

  it("test_given_a_calculated_table_when_inspected_then_positions_are_sequential_starting_at_one", () => {
    // Given a calculated 2019 Brasileirão table
    const standings = calculateStandings(store, "Brasileirao", 2019);
    // When inspecting the position field of each row
    // Then positions are assigned 1, 2, 3, ... in table order
    standings.forEach((row, index) => {
      expect(row.position).toBe(index + 1);
    });
  });

  it("test_given_a_calculated_table_when_sorted_then_points_never_increase_down_the_table", () => {
    // Given a calculated 2019 Brasileirão table
    const standings = calculateStandings(store, "Brasileirao", 2019);
    // When walking down the table
    // Then each team has no more points than the team above it
    for (let i = 1; i < standings.length; i += 1) {
      expect(standings[i]!.points).toBeLessThanOrEqual(standings[i - 1]!.points);
    }
  });

  it("test_given_a_full_season_when_standings_are_calculated_then_twenty_teams_are_ranked", () => {
    // Given a complete 20-team Brasileirão season (2019)
    // When calculating the standings
    const standings = calculateStandings(store, "Brasileirao", 2019);
    // Then all 20 participating teams appear in the table
    expect(standings.length).toBe(20);
  });
});

describe("bottomOfTable", () => {
  let store: SoccerDataStore;

  beforeAll(async () => {
    store = await loadTestStore();
  });

  it("test_given_a_relegation_proxy_request_when_computed_then_the_requested_count_of_bottom_teams_is_returned", () => {
    // Given the 2019 Brasileirão table
    // When asking for the bottom 4 teams (the standard relegation slot count)
    const bottom = bottomOfTable(store, "Brasileirao", 2019, 4);
    // Then exactly 4 teams are returned, ordered as the last positions in the table
    expect(bottom.length).toBe(4);
    expect(bottom[3]!.position).toBe(20);
  });
});

describe("seasonsForCompetition", () => {
  let store: SoccerDataStore;

  beforeAll(async () => {
    store = await loadTestStore();
  });

  it("test_given_the_brasileirao_competition_when_listing_seasons_then_they_are_returned_in_ascending_order", () => {
    // Given the Brasileirão competition's full season coverage
    // When listing the available seasons
    const seasons = seasonsForCompetition(store, "Brasileirao");
    // Then the seasons are sorted ascending and cover a multi-decade range
    expect(seasons.length).toBeGreaterThan(10);
    for (let i = 1; i < seasons.length; i += 1) {
      expect(seasons[i]!).toBeGreaterThan(seasons[i - 1]!);
    }
  });
});
