/**
 * ============================================================================
 * File: tests/matchQueries.test.ts
 * Feature: Match Queries (spec capability 1)
 * ----------------------------------------------------------------------------
 * Context:
 *   GWT scenarios for finding matches by team, opponent, competition, season
 *   and date range, plus head-to-head records — mirroring the spec's
 *   "Match Queries" examples (e.g. the Fla-Flu derby).
 * ============================================================================
 */

import { describe, it, expect, beforeAll } from "vitest";
import { KnowledgeGraph } from "../src/knowledgeGraph.js";
import { graph } from "./helpers.js";

let g: KnowledgeGraph;
beforeAll(() => {
  g = graph();
});

describe("Feature: Match Queries", () => {
  it("Scenario: find matches between two teams", () => {
    // Given the match data is loaded
    // When I search for matches between Flamengo and Fluminense
    const matches = g.findMatches({ team: "Flamengo", opponent: "Fluminense" });
    // Then I should receive a list of matches
    expect(matches.length).toBeGreaterThan(10);
    // And each match should involve exactly those two teams, with date and scores
    for (const m of matches) {
      const keys = [m.homeTeamKey, m.awayTeamKey].sort();
      expect(keys).toEqual(["flamengo", "fluminense"]);
      expect(m.competition).toBeTruthy();
    }
  });

  it("Scenario: results are sorted most-recent first", () => {
    const matches = g.findMatches({ team: "Palmeiras", limit: 50 });
    const dated = matches.filter((m) => m.date);
    for (let i = 1; i < dated.length; i++) {
      expect(dated[i - 1].date! >= dated[i].date!).toBe(true);
    }
  });

  it("Scenario: filter by season", () => {
    // When I request Palmeiras matches in 2022
    const matches = g.findMatches({ team: "Palmeiras", season: 2022 });
    expect(matches.length).toBeGreaterThan(0);
    // Then every returned match is from 2022
    for (const m of matches) expect(m.season).toBe(2022);
  });

  it("Scenario: filter by competition", () => {
    const matches = g.findMatches({ team: "Flamengo", competition: "Copa Libertadores" });
    expect(matches.length).toBeGreaterThan(0);
    for (const m of matches) expect(m.competition).toBe("Copa Libertadores");
  });

  it("Scenario: filter by date range", () => {
    const matches = g.findMatches({ team: "Santos", from: "2015-01-01", to: "2015-12-31" });
    expect(matches.length).toBeGreaterThan(0);
    for (const m of matches) {
      expect(m.date! >= "2015-01-01").toBe(true);
      expect(m.date! <= "2015-12-31").toBe(true);
    }
  });

  it("Scenario: restrict to home matches only", () => {
    const matches = g.findMatches({ team: "Corinthians", venue: "home", season: 2022, competition: "Brasileirão Série A" });
    expect(matches.length).toBe(19); // a full Série A season has 19 home games
    for (const m of matches) expect(m.homeTeamKey).toBe("corinthians");
  });

  it("Scenario: head-to-head tallies are internally consistent", () => {
    const h = g.headToHead("Flamengo", "Fluminense");
    expect(h.totalMatches).toBeGreaterThan(0);
    // wins + draws + losses never exceeds the number of matches with scores
    expect(h.teamAWins + h.teamBWins + h.draws).toBeLessThanOrEqual(h.totalMatches);
    expect(h.matches.length).toBe(h.totalMatches);
  });

  it("Scenario: unknown team yields no matches (no crash)", () => {
    expect(g.findMatches({ team: "Nonexistent United" })).toEqual([]);
  });
});
