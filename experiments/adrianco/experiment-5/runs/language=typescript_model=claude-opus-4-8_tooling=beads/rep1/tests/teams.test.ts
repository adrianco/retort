/**
 * ============================================================================
 * Context
 * ----------------------------------------------------------------------------
 * Feature: Team Queries  (mirrors the Gherkin in TASK.md "Testing Approach")
 * Covers win/draw/loss records, goal tallies and home/away splits.
 * ============================================================================
 */

import { describe, it, expect } from "vitest";
import { dataset, given, when } from "./helpers.js";
import { teamStats } from "../src/queries/teams.js";

describe("Feature: Team Queries", () => {
  it("Scenario: Get team statistics for a season", () => {
    const ds = given("the match data is loaded", () => dataset());
    const stats = when("I request statistics for Palmeiras in 2019", () =>
      teamStats(ds, "Palmeiras", {
        competition: "Brasileirão Série A",
        season: 2019,
      })
    );
    // Then I should receive wins, losses, draws, and goals
    expect(stats.overall.matches).toBeGreaterThan(0);
    expect(
      stats.overall.wins + stats.overall.draws + stats.overall.losses
    ).toBe(stats.overall.matches);
    expect(stats.overall.goalsFor).toBeGreaterThanOrEqual(0);
  });

  it("Scenario: home and away splits sum to the overall record", () => {
    const ds = dataset();
    const s = teamStats(ds, "Corinthians", {
      competition: "Brasileirão Série A",
      season: 2022,
    });
    expect(s.home.matches + s.away.matches).toBe(s.overall.matches);
    expect(s.home.wins + s.away.wins).toBe(s.overall.wins);
    expect(s.home.goalsFor + s.away.goalsFor).toBe(s.overall.goalsFor);
  });

  it("Scenario: win rate is a valid percentage", () => {
    const ds = dataset();
    const s = teamStats(ds, "Flamengo", { season: 2019 });
    expect(s.overall.winRate).toBeGreaterThanOrEqual(0);
    expect(s.overall.winRate).toBeLessThanOrEqual(100);
  });

  it("Scenario: a full Série A season has ~38 rounds of matches", () => {
    const ds = dataset();
    // The 20-team round-robin Brasileirão plays 38 games per team.
    const s = teamStats(ds, "Flamengo", {
      competition: "Brasileirão Série A",
      season: 2019,
    });
    expect(s.overall.matches).toBe(38);
    expect(s.home.matches).toBe(19);
    expect(s.away.matches).toBe(19);
  });
});
