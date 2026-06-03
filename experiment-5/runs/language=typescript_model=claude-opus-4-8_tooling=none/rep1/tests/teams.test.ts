/**
 * Context
 * -------
 * Feature: Team Queries (spec section 2).
 * Win/draw/loss records, goals for/against, home vs away split, and
 * head-to-head comparison, scoped by competition and season.
 */

import { describe, it, expect } from "vitest";
import { givenDataLoaded } from "./support/world.js";
import { teamStats, teamCompetitions } from "../src/queries.js";

describe("Feature: Team Queries", () => {
  it("Scenario: Get team statistics for a season", () => {
    // Given the match data is loaded
    const store = givenDataLoaded();
    // When I request statistics for Palmeiras in season 2019
    const s = teamStats(store, "Palmeiras", { competition: "Brasileirão", season: 2019 });
    // Then I receive wins, losses, draws and goals that are internally consistent
    expect(s.overall.played).toBeGreaterThan(0);
    expect(s.overall.wins + s.overall.draws + s.overall.losses).toBe(s.overall.played);
    expect(s.overall.goalsFor).toBeGreaterThanOrEqual(0);
    expect(s.winRate).toBeGreaterThanOrEqual(0);
    expect(s.winRate).toBeLessThanOrEqual(100);
  });

  it("Scenario: Home and away records add up to the overall record", () => {
    const store = givenDataLoaded();
    const s = teamStats(store, "Corinthians", { competition: "Brasileirão", season: 2019 });
    expect(s.home.played + s.away.played).toBe(s.overall.played);
    expect(s.home.wins + s.away.wins).toBe(s.overall.wins);
    expect(s.home.goalsFor + s.away.goalsFor).toBe(s.overall.goalsFor);
  });

  it("Scenario: A 20-team league season yields 38 games per team", () => {
    // 2019 Brasileirão had 20 teams => 38 matches each.
    const store = givenDataLoaded();
    const s = teamStats(store, "Flamengo", { competition: "Brasileirão", season: 2019 });
    expect(s.overall.played).toBe(38);
    expect(s.home.played).toBe(19);
    expect(s.away.played).toBe(19);
  });

  it("Scenario: Which competitions a team has played in", () => {
    const store = givenDataLoaded();
    const comps = teamCompetitions(store, "Palmeiras");
    expect(comps.length).toBeGreaterThan(0);
    const names = comps.map((c) => c.competition);
    expect(names).toContain("Brasileirão Série A");
    for (const c of comps) expect(c.matches).toBeGreaterThan(0);
  });
});
