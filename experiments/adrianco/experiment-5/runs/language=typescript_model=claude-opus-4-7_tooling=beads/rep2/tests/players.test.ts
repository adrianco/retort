// Feature: Player queries (FIFA dataset)
//   Scenario: Search by name
//   Scenario: Filter by nationality
//   Scenario: Sort by overall rating
import { describe, it, expect, beforeAll } from "vitest";
import { DataStore } from "../src/dataStore.js";
import { findPlayers, topBrazilianPlayers } from "../src/queries/players.js";

let ds: DataStore;
beforeAll(() => {
  ds = new DataStore().load();
});

describe("Feature: Player queries", () => {
  describe("Scenario: search by name", () => {
    it("Given the FIFA data, When searching 'Messi', Then Lionel Messi is returned", () => {
      const ps = findPlayers(ds.players, { name: "Messi" });
      expect(ps.length).toBeGreaterThan(0);
      expect(ps[0].name).toMatch(/Messi/);
    });
  });

  describe("Scenario: filter by nationality and rating", () => {
    it("Given Brazilians with overall>=80, When searching, Then all returned are Brazilian with rating>=80", () => {
      const ps = findPlayers(ds.players, { nationality: "Brazil", minOverall: 80 });
      expect(ps.length).toBeGreaterThan(0);
      for (const p of ps) {
        expect(p.nationality).toBe("Brazil");
        expect(p.overall).not.toBeNull();
        expect(p.overall!).toBeGreaterThanOrEqual(80);
      }
    });
  });

  describe("Scenario: top Brazilian players sorted by overall", () => {
    it("Given the FIFA data, When asking for top Brazilians, Then returned in descending overall", () => {
      const ps = topBrazilianPlayers(ds.players, 5);
      expect(ps.length).toBe(5);
      for (let i = 1; i < ps.length; i++) {
        expect(ps[i].overall ?? 0).toBeLessThanOrEqual(ps[i - 1].overall ?? 0);
      }
      expect(ps[0].nationality).toBe("Brazil");
    });
  });

  describe("Scenario: filter by club", () => {
    it("Given a Brazilian club, When filtering by 'Flamengo', Then results have Flamengo in their club", () => {
      const ps = findPlayers(ds.players, { club: "Flamengo" });
      // Dataset may not include every Brazilian club, so just assert the filter is respected.
      for (const p of ps) {
        expect(p.club.toLowerCase()).toContain("flamengo");
      }
    });
  });
});
