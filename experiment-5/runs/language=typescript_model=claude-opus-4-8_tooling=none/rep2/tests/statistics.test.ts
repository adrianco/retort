/**
 * ============================================================================
 * File: tests/statistics.test.ts
 * Feature: Statistical Analysis (spec capability 5)
 * ----------------------------------------------------------------------------
 * Context:
 *   GWT scenarios for aggregated statistics: average goals per match, home/
 *   away/draw rates, and the biggest victories — mirroring the spec's
 *   "average goals per match" and "biggest wins" examples.
 * ============================================================================
 */

import { describe, it, expect, beforeAll } from "vitest";
import { KnowledgeGraph } from "../src/knowledgeGraph.js";
import { graph } from "./helpers.js";

let g: KnowledgeGraph;
beforeAll(() => {
  g = graph();
});

describe("Feature: Statistical Analysis", () => {
  it("Scenario: average goals per match is in a plausible football range", () => {
    const stats = g.competitionStats("Brasileirão Série A");
    expect(stats.averageGoalsPerMatch).toBeGreaterThan(2);
    expect(stats.averageGoalsPerMatch).toBeLessThan(4);
  });

  it("Scenario: outcome rates sum to ~100%", () => {
    const s = g.competitionStats("Brasileirão Série A");
    const sum = s.homeWinRate + s.awayWinRate + s.drawRate;
    expect(sum).toBeGreaterThan(0.99);
    expect(sum).toBeLessThan(1.01);
  });

  it("Scenario: home advantage exists (home win rate beats away)", () => {
    const s = g.competitionStats("Brasileirão Série A");
    expect(s.homeWinRate).toBeGreaterThan(s.awayWinRate);
  });

  it("Scenario: biggest wins are sorted by margin", () => {
    const wins = g.biggestWins({ limit: 10 });
    expect(wins.length).toBe(10);
    for (let i = 1; i < wins.length; i++) {
      const prev = Math.abs(wins[i - 1].homeGoals! - wins[i - 1].awayGoals!);
      const cur = Math.abs(wins[i].homeGoals! - wins[i].awayGoals!);
      expect(prev).toBeGreaterThanOrEqual(cur);
    }
    // The very biggest margin should be a thrashing
    expect(Math.abs(wins[0].homeGoals! - wins[0].awayGoals!)).toBeGreaterThanOrEqual(6);
  });

  it("Scenario: all-data stats aggregate across every competition", () => {
    const all = g.competitionStats();
    expect(all.matches).toBeGreaterThan(g.competitionStats("Brasileirão Série A").matches);
  });
});

describe("Feature: Performance budget", () => {
  it("Scenario: simple lookups respond in < 2s", () => {
    const start = performance.now();
    g.findMatches({ team: "Flamengo", opponent: "Fluminense" });
    expect(performance.now() - start).toBeLessThan(2000);
  });

  it("Scenario: aggregate queries respond in < 5s", () => {
    const start = performance.now();
    g.standings("Brasileirão Série A", 2019);
    g.competitionStats("Brasileirão Série A");
    expect(performance.now() - start).toBeLessThan(5000);
  });
});
