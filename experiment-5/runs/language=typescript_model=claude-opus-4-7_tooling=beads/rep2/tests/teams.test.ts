// Feature: Team queries
//   Scenario: Aggregate stats for a team
//   Scenario: Filter by competition / season / venue
import { describe, it, expect, beforeAll } from "vitest";
import { DataStore } from "../src/dataStore.js";
import { teamStats, listTeams, teamCompetitions } from "../src/queries/teams.js";

let ds: DataStore;
beforeAll(() => {
  ds = new DataStore().load();
});

describe("Feature: Team queries", () => {
  describe("Scenario: get team statistics for a season", () => {
    it("Given Palmeiras in 2019 Brasileirão, When computing stats, Then totals sum correctly", () => {
      const r = teamStats(ds.matches, { team: "Palmeiras", competition: "Brasileirão", season: 2019 });
      expect(r.matches).toBeGreaterThan(0);
      expect(r.wins + r.draws + r.losses).toBe(r.matches);
      expect(r.points).toBe(r.wins * 3 + r.draws);
    });
  });

  describe("Scenario: home vs away record split", () => {
    it("Given Corinthians 2022 Brasileirão home matches, When asking for home record, Then it has a non-zero count", () => {
      const r = teamStats(ds.matches, {
        team: "Corinthians",
        competition: "Brasileirão",
        season: 2022,
        venue: "home",
      });
      expect(r.matches).toBeGreaterThan(0);
      expect(r.wins + r.draws + r.losses).toBe(r.matches);
    });
  });

  describe("Scenario: list teams contains traditional Brazilian clubs", () => {
    it("Given the data, When listing teams, Then Flamengo and Palmeiras appear", () => {
      const teams = listTeams(ds.matches);
      const norm = teams.map((t) => t.toLowerCase());
      expect(norm.some((t) => t.includes("flamengo"))).toBe(true);
      expect(norm.some((t) => t.includes("palmeiras"))).toBe(true);
    });
  });

  describe("Scenario: team competitions includes major tournaments", () => {
    it("Given Palmeiras, When asking competitions, Then Brasileirão appears", () => {
      const comps = teamCompetitions(ds.matches, "Palmeiras");
      expect(comps.some((c) => c.toLowerCase().includes("brasileirão"))).toBe(true);
    });
  });
});
