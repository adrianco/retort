/**
 * tests/players.test.ts
 * -----------------------------------------------------------------------------
 * CONTEXT
 *   BDD specs for the player-query service: search by name / nationality / club
 *   / position / rating, and the per-club breakdown of Brazilian players.
 * -----------------------------------------------------------------------------
 */

import { describe, it, expect } from "vitest";
import { givenDataset } from "./fixture.js";
import { findPlayers, clubBreakdown } from "../src/services/players.js";

describe("Feature: Player Queries", () => {
  describe("Scenario: Search a player by name", () => {
    it("Given the name 'Neymar', Then a matching player is returned", () => {
      const ds = givenDataset();
      const players = findPlayers(ds, { name: "Neymar" });
      expect(players.length).toBeGreaterThan(0);
      expect(players[0].name.toLowerCase()).toContain("neymar");
      expect(players[0].nationality).toBe("Brazil");
    });
  });

  describe("Scenario: Filter players by nationality", () => {
    it("Given nationality 'Brazil', Then all results are Brazilian and sorted by rating", () => {
      const ds = givenDataset();
      const players = findPlayers(ds, { nationality: "Brazil", limit: 50 });
      expect(players.length).toBe(50);
      for (const p of players) expect(p.nationality).toBe("Brazil");
      // Top of the list is the highest-rated Brazilian.
      expect(players[0].overall).toBeGreaterThanOrEqual(players[49].overall ?? 0);
      expect(players[0].name).toMatch(/Neymar/);
    });
  });

  describe("Scenario: Filter players by club and position", () => {
    it("Given a Brazilian club, Then its players are returned", () => {
      const ds = givenDataset();
      const players = findPlayers(ds, { club: "Santos" });
      expect(players.length).toBeGreaterThan(0);
      for (const p of players) expect(p.club.toLowerCase()).toContain("santos");
    });

    it("Given a position filter, Then only that position returns", () => {
      const ds = givenDataset();
      const gks = findPlayers(ds, { nationality: "Brazil", position: "GK", limit: 20 });
      expect(gks.length).toBeGreaterThan(0);
      for (const p of gks) expect(p.position).toBe("GK");
    });
  });

  describe("Scenario: Filter by minimum rating", () => {
    it("Given minOverall 85, Then every result is rated >= 85", () => {
      const ds = givenDataset();
      const players = findPlayers(ds, { nationality: "Brazil", minOverall: 85 });
      expect(players.length).toBeGreaterThan(0);
      for (const p of players) expect(p.overall ?? 0).toBeGreaterThanOrEqual(85);
    });
  });

  describe("Scenario: Brazilian players grouped by club", () => {
    it("Given Brazilian players, Then a per-club breakdown with counts and averages is produced", () => {
      const ds = givenDataset();
      const rows = clubBreakdown(ds, { nationality: "Brazil" }, 5);
      expect(rows.length).toBe(5);
      // Sorted by player count, descending.
      for (let i = 1; i < rows.length; i++) {
        expect(rows[i - 1].count).toBeGreaterThanOrEqual(rows[i].count);
      }
      for (const r of rows) {
        expect(r.averageOverall).toBeGreaterThan(0);
        expect(r.topPlayer).toBeTruthy();
      }
    });
  });
});
