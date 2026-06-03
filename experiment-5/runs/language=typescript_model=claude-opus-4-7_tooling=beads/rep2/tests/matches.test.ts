// Feature: Match Queries
//   Scenario: Find matches between two teams
//   Scenario: Filter matches by season and competition
//   Scenario: Head-to-head summary
import { describe, it, expect, beforeAll } from "vitest";
import { DataStore } from "../src/dataStore.js";
import { findMatches, headToHead, lastMatchBetween } from "../src/queries/matches.js";

let ds: DataStore;
beforeAll(() => {
  ds = new DataStore().load();
});

describe("Feature: Match queries", () => {
  describe("Scenario: find matches between two teams", () => {
    it("Given the match data is loaded, When searching Flamengo vs Fluminense, Then matches are returned with score and competition", () => {
      const ms = findMatches(ds.matches, { team: "Flamengo", opponent: "Fluminense" });
      expect(ms.length).toBeGreaterThan(0);
      for (const m of ms) {
        const a = m.homeTeamNormalized;
        const b = m.awayTeamNormalized;
        expect([a, b]).toContain("flamengo");
        expect([a, b]).toContain("fluminense");
        expect(typeof m.competition).toBe("string");
      }
    });
  });

  describe("Scenario: filter by season and competition", () => {
    it("Given a season filter, When querying Brasileirão 2019, Then only that season is returned", () => {
      const ms = findMatches(ds.matches, { competition: "Brasileirão", season: 2019, hasResult: true });
      expect(ms.length).toBeGreaterThan(0);
      for (const m of ms) expect(m.season).toBe(2019);
    });
  });

  describe("Scenario: head-to-head summary", () => {
    it("Given two teams, When computing head-to-head, Then wins+draws+losses equal total matches", () => {
      const { summary } = headToHead(ds.matches, "Palmeiras", "Santos");
      expect(summary.matches).toBeGreaterThan(0);
      expect(summary.teamAWins + summary.teamBWins + summary.draws).toBe(summary.matches);
    });
  });

  describe("Scenario: most recent match between two teams", () => {
    it("Given Flamengo and Corinthians, When asking for last match, Then a non-null match is returned", () => {
      const m = lastMatchBetween(ds.matches, "Flamengo", "Corinthians");
      expect(m).not.toBeNull();
      expect(m!.date).not.toBeNull();
    });
  });

  describe("Scenario: limit results", () => {
    it("Given a limit of 5, When querying, Then at most 5 matches are returned", () => {
      const ms = findMatches(ds.matches, { team: "Palmeiras", limit: 5 });
      expect(ms.length).toBeLessThanOrEqual(5);
    });
  });
});
