/*
 * ============================================================================
 * Context
 * ----------------------------------------------------------------------------
 * Test:    tests/matches.test.ts
 * Purpose: BDD tests for match queries and head-to-head (features/matches.feature).
 * ============================================================================
 */

import { describe, it, expect } from "vitest";
import { givenDataLoaded } from "./helpers.js";
import { findMatches, headToHead } from "../src/queries/matches.js";
import { normalizeTeam, teamsMatch } from "../src/data/normalize.js";

const ds = givenDataLoaded();

describe("Feature: Match Queries", () => {
  describe("Scenario: Find matches between two teams", () => {
    const matches = findMatches(ds, { team: "Flamengo", team2: "Fluminense" });

    it("Then I should receive a list of matches", () => {
      expect(matches.length).toBeGreaterThan(0);
    });

    it("And each match should have date, scores, and competition", () => {
      for (const m of matches) {
        expect(m.competition).toBeTruthy();
        expect(m.homeGoals).not.toBeNull();
        expect(m.awayGoals).not.toBeNull();
        // Each match really is a Fla x Flu fixture.
        const k1 = normalizeTeam("Flamengo");
        const k2 = normalizeTeam("Fluminense");
        const ok =
          (teamsMatch(m.homeKey, k1) && teamsMatch(m.awayKey, k2)) ||
          (teamsMatch(m.homeKey, k2) && teamsMatch(m.awayKey, k1));
        expect(ok).toBe(true);
      }
    });

    it("And results are sorted most-recent first", () => {
      const dated = matches.filter((m) => m.date).map((m) => m.date!);
      const sorted = [...dated].sort().reverse();
      expect(dated).toEqual(sorted);
    });
  });

  describe("Scenario: Find matches for a team in a season", () => {
    const matches = findMatches(ds, { team: "Palmeiras", season: 2019 });

    it("Then every match involves Palmeiras", () => {
      const key = normalizeTeam("Palmeiras");
      for (const m of matches) {
        expect(teamsMatch(m.homeKey, key) || teamsMatch(m.awayKey, key)).toBe(
          true,
        );
      }
    });

    it("And every match is from season 2019", () => {
      for (const m of matches) expect(m.season).toBe(2019);
    });
  });

  describe("Scenario: Team name variations are handled", () => {
    it("When searching 'Palmeiras' Then 'Palmeiras-SP' rows are included", () => {
      const matches = findMatches(ds, { team: "Palmeiras", season: 2019 });
      const fromSuffixed = matches.some((m) =>
        [m.homeTeam, m.awayTeam].some((t) => /Palmeiras/i.test(t)),
      );
      expect(fromSuffixed).toBe(true);
      expect(matches.length).toBeGreaterThan(30);
    });
  });

  describe("Scenario: Compute a head-to-head record", () => {
    const h = headToHead(ds, "Flamengo", "Fluminense");

    it("Then totals are internally consistent", () => {
      expect(h.team1Wins + h.team2Wins + h.draws).toBe(h.totalMatches);
      expect(h.totalMatches).toBeGreaterThan(0);
    });

    it("And goals are non-negative", () => {
      expect(h.team1Goals).toBeGreaterThanOrEqual(0);
      expect(h.team2Goals).toBeGreaterThanOrEqual(0);
    });
  });

  describe("Scenario: Most recent meeting lookup", () => {
    it("When did Flamengo last play Corinthians Then a dated match returns", () => {
      const matches = findMatches(ds, {
        team: "Flamengo",
        team2: "Corinthians",
        limit: 1,
      });
      expect(matches.length).toBe(1);
      expect(matches[0].date).toBeTruthy();
    });
  });
});
