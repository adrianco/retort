import { beforeAll, describe, expect, it } from "vitest";
import type { SoccerDataStore } from "../src/data/store.js";
import { biggestWins, calculateGoalStats } from "../src/queries/stats.js";
import { loadTestStore } from "./support/testStore.js";

describe("calculateGoalStats", () => {
  let store: SoccerDataStore;

  beforeAll(async () => {
    store = await loadTestStore();
  });

  it("test_given_brasileirao_matches_when_goal_stats_are_calculated_then_average_goals_is_plausible", () => {
    // Given every Brasileirão match with a known score
    // When calculating goal statistics
    const stats = calculateGoalStats(store, { competition: "Brasileirao" });
    // Then the average goals per match falls in the range typical of Brazilian top-flight football (2-3)
    expect(stats.averageGoalsPerMatch).toBeGreaterThan(2);
    expect(stats.averageGoalsPerMatch).toBeLessThan(3);
  });

  it("test_given_outcome_rates_when_calculated_then_they_sum_to_one", () => {
    // Given every Brasileirão match with a known score
    // When calculating home win / away win / draw rates
    const stats = calculateGoalStats(store, { competition: "Brasileirao" });
    // Then the three mutually exclusive outcome rates sum to 1 (within floating point rounding)
    const total = stats.homeWinRate + stats.awayWinRate + stats.drawRate;
    expect(total).toBeCloseTo(1, 1);
  });

  it("test_given_no_matches_for_the_criteria_when_calculating_goal_stats_then_a_zeroed_result_is_returned", () => {
    // Given a season with no data at all
    // When calculating goal statistics
    const stats = calculateGoalStats(store, { competition: "Brasileirao", season: 1899 });
    // Then a zeroed result is returned instead of NaN or a division-by-zero error
    expect(stats.matchesConsidered).toBe(0);
    expect(stats.averageGoalsPerMatch).toBe(0);
  });
});

describe("biggestWins", () => {
  let store: SoccerDataStore;

  beforeAll(async () => {
    store = await loadTestStore();
  });

  it("test_given_the_full_dataset_when_finding_biggest_wins_then_results_are_sorted_by_descending_margin", () => {
    // Given every match with a known score
    // When finding the biggest wins
    const wins = biggestWins(store, { limit: 10 });
    // Then each entry's goal margin is greater than or equal to the next
    const margin = (m: (typeof wins)[number]) => Math.abs((m.homeGoals as number) - (m.awayGoals as number));
    expect(wins.length).toBe(10);
    for (let i = 1; i < wins.length; i += 1) {
      expect(margin(wins[i - 1]!)).toBeGreaterThanOrEqual(margin(wins[i]!));
    }
  });

  it("test_given_a_limit_when_finding_biggest_wins_then_result_count_matches_the_limit", () => {
    // Given a request for the top 3 biggest wins
    // When finding them
    const wins = biggestWins(store, { limit: 3 });
    // Then exactly 3 matches are returned
    expect(wins.length).toBe(3);
  });
});
