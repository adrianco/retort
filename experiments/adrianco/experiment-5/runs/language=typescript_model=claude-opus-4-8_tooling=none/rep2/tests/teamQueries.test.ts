/**
 * ============================================================================
 * File: tests/teamQueries.test.ts
 * Feature: Team Queries (spec capability 2)
 * ----------------------------------------------------------------------------
 * Context:
 *   GWT scenarios for team records (W/D/L, goals), home/away splits and the
 *   set of competitions a team appears in — mirroring the spec's "Corinthians
 *   home record" example.
 * ============================================================================
 */

import { describe, it, expect, beforeAll } from "vitest";
import { KnowledgeGraph } from "../src/knowledgeGraph.js";
import { graph } from "./helpers.js";

let g: KnowledgeGraph;
beforeAll(() => {
  g = graph();
});

describe("Feature: Team Queries", () => {
  it("Scenario: team record is self-consistent", () => {
    // Given match data is loaded
    // When I request Palmeiras' 2022 Série A record
    const rec = g.teamRecord("Palmeiras", { competition: "Brasileirão Série A", season: 2022 });
    // Then wins + draws + losses equals matches, and goal counts are present
    expect(rec.matches).toBeGreaterThan(0);
    expect(rec.wins + rec.draws + rec.losses).toBe(rec.matches);
    expect(rec.goalsFor).toBeGreaterThanOrEqual(0);
    expect(rec.goalsAgainst).toBeGreaterThanOrEqual(0);
  });

  it("Scenario: home + away records sum to the overall record", () => {
    const all = g.teamRecord("Flamengo", { competition: "Brasileirão Série A", season: 2019 });
    const home = g.teamRecord("Flamengo", { competition: "Brasileirão Série A", season: 2019, venue: "home" });
    const away = g.teamRecord("Flamengo", { competition: "Brasileirão Série A", season: 2019, venue: "away" });
    expect(home.matches + away.matches).toBe(all.matches);
    expect(home.wins + away.wins).toBe(all.wins);
    expect(home.goalsFor + away.goalsFor).toBe(all.goalsFor);
  });

  it("Scenario: Corinthians 2022 home record matches the spec example shape", () => {
    const rec = g.teamRecord("Corinthians", { competition: "Brasileirão Série A", season: 2022, venue: "home" });
    expect(rec.matches).toBeGreaterThanOrEqual(15);
    expect(rec.wins).toBeGreaterThan(rec.losses);
  });

  it("Scenario: a club lists the competitions it appears in", () => {
    const comps = g.teamCompetitions("Flamengo");
    expect(comps).toContain("Brasileirão Série A");
    expect(comps).toContain("Copa Libertadores");
  });

  it("Scenario: team name variations resolve to the same club", () => {
    const a = g.teamRecord("Flamengo-RJ", { season: 2019 });
    const b = g.teamRecord("Flamengo", { season: 2019 });
    expect(a.matches).toBe(b.matches);
  });
});
