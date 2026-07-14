// Feature: Competition standings calculated from matches
//   Scenario: 2019 Brasileirão final standings — Flamengo at top
//   Scenario: Standings rows sum correctly
import { describe, it, expect, beforeAll } from "vitest";
import { DataStore } from "../src/dataStore.js";
import { standings, champion, listCompetitions, listSeasons } from "../src/queries/competitions.js";

let ds: DataStore;
beforeAll(() => {
  ds = new DataStore().load();
});

describe("Feature: Competition queries", () => {
  describe("Scenario: 2019 Brasileirão standings", () => {
    it("Given match data, When computing 2019 standings, Then Flamengo is champion", () => {
      const c = champion(ds.matches, { competition: "Brasileirão", season: 2019 });
      expect(c).not.toBeNull();
      expect(c!.team.toLowerCase()).toContain("flamengo");
      expect(c!.points).toBeGreaterThan(80);
    });

    it("Given any computed standings row, Then wins+draws+losses equals matches played", () => {
      const rows = standings(ds.matches, { competition: "Brasileirão", season: 2019 });
      expect(rows.length).toBeGreaterThan(15);
      for (const r of rows) {
        expect(r.wins + r.draws + r.losses).toBe(r.matches);
        expect(r.points).toBe(r.wins * 3 + r.draws);
      }
    });
  });

  describe("Scenario: list competitions and seasons", () => {
    it("Given data is loaded, When listing competitions, Then key tournaments appear", () => {
      const comps = listCompetitions(ds.matches);
      expect(comps.some((c) => c.includes("Brasileirão"))).toBe(true);
      expect(comps.some((c) => c.includes("Copa do Brasil"))).toBe(true);
      expect(comps.some((c) => c.includes("Libertadores"))).toBe(true);
    });

    it("Given data is loaded, When listing seasons, Then 2019 appears", () => {
      const seasons = listSeasons(ds.matches, "Brasileirão");
      expect(seasons).toContain(2019);
    });
  });
});
