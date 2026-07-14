/**
 * Context
 * -------
 * Feature: Match Queries (spec section 1).
 * Covers finding matches between two teams, by single team + season, by
 * competition, and the head-to-head record — directly mirroring the Gherkin
 * scenarios in the spec's Testing Approach.
 */

import { describe, it, expect } from "vitest";
import { givenDataLoaded } from "./support/world.js";
import { findMatches, headToHead } from "../src/queries.js";

describe("Feature: Match Queries", () => {
  it("Scenario: Find matches between two teams", () => {
    // Given the match data is loaded
    const store = givenDataLoaded();
    // When I search for matches between Flamengo and Fluminense
    const matches = findMatches(store, { team: "Flamengo", opponent: "Fluminense" });
    // Then I should receive a list of matches
    expect(matches.length).toBeGreaterThan(0);
    // And each match should have date, scores, and competition
    for (const m of matches) {
      expect(m.competition).toBeTruthy();
      expect(m.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      const involvesBoth =
        (/flamengo|fluminense/i.test(m.homeTeam) && /flamengo|fluminense/i.test(m.awayTeam));
      expect(involvesBoth).toBe(true);
    }
  });

  it("Scenario: Matches are sorted most-recent first", () => {
    const store = givenDataLoaded();
    const matches = findMatches(store, { team: "Palmeiras", limit: 50 });
    const dates = matches.map((m) => m.date).filter(Boolean) as string[];
    const sorted = [...dates].sort().reverse();
    expect(dates).toEqual(sorted);
  });

  it("Scenario: Find matches for a team in a given season", () => {
    // When I ask what matches Palmeiras played in 2019
    const store = givenDataLoaded();
    const matches = findMatches(store, { team: "Palmeiras", season: 2019 });
    // Then every result is from 2019 and involves Palmeiras
    expect(matches.length).toBeGreaterThan(0);
    for (const m of matches) {
      expect(m.season).toBe(2019);
      expect(/palmeiras/i.test(m.homeTeam) || /palmeiras/i.test(m.awayTeam)).toBe(true);
    }
  });

  it("Scenario: Filter matches by competition", () => {
    const store = givenDataLoaded();
    const matches = findMatches(store, { competition: "Libertadores", limit: 100 });
    expect(matches.length).toBeGreaterThan(0);
    for (const m of matches) expect(m.competition).toBe("Copa Libertadores");
  });

  it("Scenario: Head-to-head record between two rivals", () => {
    // When I request the Fla-Flu head-to-head
    const store = givenDataLoaded();
    const h = headToHead(store, "Flamengo", "Fluminense");
    // Then wins + draws sum to the number of matches
    expect(h.matches.length).toBeGreaterThan(0);
    expect(h.teamAWins + h.teamBWins + h.draws).toBe(h.matches.length);
    expect(h.teamAGoals).toBeGreaterThanOrEqual(0);
    expect(h.teamBGoals).toBeGreaterThanOrEqual(0);
  });

  it("Scenario: Most recent meeting of two teams", () => {
    // When did Flamengo last play Corinthians
    const store = givenDataLoaded();
    const matches = findMatches(store, { team: "Flamengo", opponent: "Corinthians" });
    expect(matches.length).toBeGreaterThan(0);
    // The first result is the most recent (sorted desc)
    expect(matches[0].date).toBe(
      [...matches].map((m) => m.date).sort().reverse()[0],
    );
  });
});
