/**
 * Context
 * -------
 * Feature: Statistical Analysis (spec section 5).
 * Average goals per match, home win rate, biggest victories and top scoring
 * teams — the aggregate queries that must respond in < 5s.
 */

import { describe, it, expect } from "vitest";
import { givenDataLoaded } from "./support/world.js";
import { biggestWins, competitionStats, topScoringTeams } from "../src/queries.js";

describe("Feature: Statistical Analysis", () => {
  it("Scenario: Average goals per match for the Brasileirão is realistic", () => {
    // Given the match data is loaded
    const store = givenDataLoaded();
    // When I compute Brasileirão aggregate stats
    const s = competitionStats(store, { competition: "Brasileirão" });
    // Then the average goals per match is in a plausible football range
    expect(s.averageGoalsPerMatch).toBeGreaterThan(2);
    expect(s.averageGoalsPerMatch).toBeLessThan(3.5);
    // And the home/away/draw split accounts for every scored match
    expect(s.homeWins + s.awayWins + s.draws).toBe(s.matchesWithScores);
    expect(s.homeWinRate).toBeGreaterThan(40);
    expect(s.homeWinRate).toBeLessThan(60);
  });

  it("Scenario: Biggest wins are ordered by margin", () => {
    const store = givenDataLoaded();
    const wins = biggestWins(store, { competition: "Brasileirão", limit: 10 });
    expect(wins.length).toBe(10);
    for (let i = 1; i < wins.length; i++) {
      expect(wins[i - 1].margin).toBeGreaterThanOrEqual(wins[i].margin);
    }
    // The very biggest win has a large margin.
    expect(wins[0].margin).toBeGreaterThanOrEqual(5);
  });

  it("Scenario: Top scoring teams in a season are ranked descending", () => {
    const store = givenDataLoaded();
    const teams = topScoringTeams(store, { competition: "Brasileirão", season: 2019, limit: 5 });
    expect(teams.length).toBe(5);
    for (let i = 1; i < teams.length; i++) {
      expect(teams[i - 1].goals).toBeGreaterThanOrEqual(teams[i].goals);
    }
  });

  it("Scenario: Aggregate query performance is under the 5s budget", () => {
    const store = givenDataLoaded();
    const start = performance.now();
    competitionStats(store, {});
    biggestWins(store, { limit: 20 });
    topScoringTeams(store, { limit: 20 });
    const elapsed = performance.now() - start;
    expect(elapsed).toBeLessThan(5000);
  });
});
