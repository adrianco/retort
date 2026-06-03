/**
 * tests/matches.test.ts
 * -----------------------------------------------------------------------------
 * CONTEXT
 *   BDD specs for the match-query service: finding matches by team / opponent /
 *   competition / season / date range, and computing head-to-head tallies.
 * -----------------------------------------------------------------------------
 */

import { describe, it, expect } from "vitest";
import { givenDataset } from "./fixture.js";
import { findMatches, headToHead } from "../src/services/matches.js";

describe("Feature: Match Queries", () => {
  describe("Scenario: Find matches between two teams", () => {
    it("Given the match data, When I search Flamengo vs Fluminense, Then I get a list with scores and competition", () => {
      const ds = givenDataset();
      const matches = findMatches(ds, { teamA: "Flamengo", teamB: "Fluminense" });
      expect(matches.length).toBeGreaterThan(10);
      for (const m of matches) {
        const teams = [m.homeTeam, m.awayTeam].join(" ");
        expect(teams).toMatch(/Flamengo/);
        expect(teams).toMatch(/Fluminense/);
        expect(m.competition).toBeTruthy();
      }
    });

    it("Given results, Then they are ordered most-recent first", () => {
      const ds = givenDataset();
      const matches = findMatches(ds, { teamA: "Palmeiras", teamB: "Santos" });
      const dated = matches.filter((m) => m.date).map((m) => m.date!);
      const sorted = [...dated].sort((a, b) => b.localeCompare(a));
      expect(dated).toEqual(sorted);
    });
  });

  describe("Scenario: Filter matches by team and season", () => {
    it("Given Palmeiras in 2019, When I search, Then every result is Palmeiras in 2019", () => {
      const ds = givenDataset();
      const matches = findMatches(ds, { team: "Palmeiras", season: 2019 });
      expect(matches.length).toBeGreaterThan(0);
      for (const m of matches) {
        expect(m.season).toBe(2019);
        expect([m.homeTeam, m.awayTeam].join(" ")).toMatch(/Palmeiras/);
      }
    });
  });

  describe("Scenario: Filter matches by competition", () => {
    it("Given a Libertadores filter, Then only Libertadores matches return", () => {
      const ds = givenDataset();
      const matches = findMatches(ds, { competition: "Libertadores", limit: 50 });
      expect(matches.length).toBeGreaterThan(0);
      for (const m of matches) expect(m.competition).toBe("Libertadores");
    });
  });

  describe("Scenario: Filter matches by venue", () => {
    it("Given Corinthians home matches, Then Corinthians is always the home team", () => {
      const ds = givenDataset();
      const matches = findMatches(ds, { team: "Corinthians", venue: "home", limit: 30 });
      expect(matches.length).toBeGreaterThan(0);
      for (const m of matches) expect(m.homeTeam).toMatch(/Corinthians/);
    });
  });

  describe("Scenario: Head-to-head between two teams", () => {
    it("Given Flamengo vs Fluminense, Then wins + draws + losses equal scored matches", () => {
      const ds = givenDataset();
      const h = headToHead(ds, "Flamengo", "Fluminense");
      const scored = h.matches.filter(
        (m) => m.homeGoals !== null && m.awayGoals !== null,
      ).length;
      expect(h.teamAWins + h.teamBWins + h.draws).toBe(scored);
      expect(h.totalMatches).toBe(h.matches.length);
    });

    it("Given a head-to-head, Then it is symmetric when teams are swapped", () => {
      const ds = givenDataset();
      const ab = headToHead(ds, "Flamengo", "Fluminense");
      const ba = headToHead(ds, "Fluminense", "Flamengo");
      expect(ab.teamAWins).toBe(ba.teamBWins);
      expect(ab.teamBWins).toBe(ba.teamAWins);
      expect(ab.draws).toBe(ba.draws);
    });
  });
});
