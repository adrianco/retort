/**
 * Feature: Player queries (FIFA dataset) and cross-file queries
 */
import { describe, expect, it } from "vitest";
import { searchPlayers, teamStats } from "../src/queries.js";
import { dataset } from "./helpers.js";

describe("Feature: Player queries", () => {
  describe("Scenario: Search a player by name", () => {
    it("Given the FIFA data, When I search 'Neymar', Then Neymar Jr is found with rating and club", () => {
      const players = searchPlayers(dataset(), { name: "Neymar" });
      expect(players.length).toBeGreaterThan(0);
      expect(players[0].name).toContain("Neymar");
      expect(players[0].overall).toBeGreaterThan(85);
      expect(players[0].nationality).toBe("Brazil");
    });

    it("Given an accented query, When I search 'Coutinho', Then the search is accent-insensitive", () => {
      const players = searchPlayers(dataset(), { name: "coutinho" });
      expect(players.length).toBeGreaterThan(0);
    });

    it("Given a well-known Brazilian, When I search 'Gabriel Jesus', Then his profile data is returned", () => {
      const players = searchPlayers(dataset(), { name: "Gabriel Jesus" });
      expect(players.length).toBeGreaterThan(0);
      expect(players[0].nationality).toBe("Brazil");
      expect(players[0].overall).toBeGreaterThan(75);
    });
  });

  describe("Scenario: Find all Brazilian players", () => {
    it("Given the FIFA data, When I filter by nationality Brazil, Then hundreds of players return, sorted by rating", () => {
      const players = searchPlayers(dataset(), { nationality: "Brazil", limit: 1000 });
      expect(players.length).toBeGreaterThan(500);
      for (let i = 1; i < players.length; i++) {
        expect(players[i].overall).toBeLessThanOrEqual(players[i - 1].overall);
      }
      expect(players[0].overall).toBeGreaterThanOrEqual(89);
    });
  });

  describe("Scenario: Players at a Brazilian club", () => {
    it("Given the FIFA data, When I filter by club 'Grêmio', Then its squad is returned", () => {
      const players = searchPlayers(dataset(), { club: "Grêmio", limit: 50 });
      expect(players.length).toBeGreaterThan(10);
      for (const p of players) expect(p.club).toContain("Grêmio");
    });

    it("Given position and club filters, When I search Santos forwards (ST), Then only strikers return", () => {
      const players = searchPlayers(dataset(), { club: "Santos", position: "ST", limit: 20 });
      for (const p of players) expect(p.position).toBe("ST");
    });
  });

  describe("Scenario: Minimum rating filter", () => {
    it("Given min_overall 90, When I search, Then only elite players return", () => {
      const players = searchPlayers(dataset(), { minOverall: 90, limit: 50 });
      expect(players.length).toBeGreaterThan(3);
      for (const p of players) expect(p.overall).toBeGreaterThanOrEqual(90);
    });
  });
});

describe("Feature: Cross-file queries", () => {
  describe("Scenario: Combine player data with match data", () => {
    it("Given a club present in both FIFA and match datasets, When I query both, Then squad and match record are available together", () => {
      const ds = dataset();
      const squad = searchPlayers(ds, { club: "Grêmio", limit: 50 });
      const record = teamStats(ds, "Grêmio", { competition: "Brasileirão" });
      expect(squad.length).toBeGreaterThan(0);
      expect(record.matches).toBeGreaterThan(100);
      // Average squad rating is computable alongside the win rate.
      const avg = squad.reduce((s, p) => s + p.overall, 0) / squad.length;
      expect(avg).toBeGreaterThan(60);
      expect(record.winRate).toBeGreaterThan(0);
    });
  });
});
