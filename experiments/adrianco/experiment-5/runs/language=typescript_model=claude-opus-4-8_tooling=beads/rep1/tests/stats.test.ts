/**
 * ============================================================================
 * Context
 * ----------------------------------------------------------------------------
 * Feature: Statistical Analysis
 * Covers average goals per match, home/away win rates, biggest victories and
 * top-scoring teams — the examples in TASK.md "Statistical Analysis".
 * ============================================================================
 */

import { describe, it, expect } from "vitest";
import { dataset } from "./helpers.js";
import {
  aggregateStats,
  biggestWins,
  topScoringTeams,
} from "../src/queries/stats.js";

describe("Feature: Statistical Analysis", () => {
  it("Scenario: Average goals per match in the Brasileirão", () => {
    const ds = dataset();
    const s = aggregateStats(ds, { competition: "Brasileirão Série A" });
    // Then the average sits in a realistic football range
    expect(s.avgGoalsPerMatch).toBeGreaterThan(1.5);
    expect(s.avgGoalsPerMatch).toBeLessThan(4);
  });

  it("Scenario: win/draw rates partition all matches", () => {
    const ds = dataset();
    const s = aggregateStats(ds, { competition: "Brasileirão Série A", season: 2019 });
    expect(s.homeWins + s.awayWins + s.draws).toBe(s.matches);
    const totalRate = s.homeWinRate + s.awayWinRate + s.drawRate;
    expect(totalRate).toBeCloseTo(100, 5);
  });

  it("Scenario: home advantage shows in the win rate", () => {
    const ds = dataset();
    const s = aggregateStats(ds, { competition: "Brasileirão Série A" });
    // Home win rate is typically the largest outcome share.
    expect(s.homeWinRate).toBeGreaterThan(s.awayWinRate);
  });

  it("Scenario: Biggest victories are sorted by margin", () => {
    const ds = dataset();
    const res = biggestWins(ds, { competition: "Brasileirão Série A" }, 10);
    const margins = res.matches.map((m) => Math.abs(m.homeGoal! - m.awayGoal!));
    expect(margins).toEqual([...margins].sort((a, b) => b - a));
    expect(margins[0]).toBeGreaterThanOrEqual(5);
  });

  it("Scenario: Rank teams by goals scored", () => {
    const ds = dataset();
    const res = topScoringTeams(ds, { competition: "Brasileirão Série A", season: 2019 }, 5);
    expect(res.rows.length).toBe(5);
    const goals = res.rows.map((r) => r.goals);
    expect(goals).toEqual([...goals].sort((a, b) => b - a));
  });
});
