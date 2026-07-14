/*
 * ============================================================================
 * Context
 * ----------------------------------------------------------------------------
 * Test:    tests/players.test.ts
 * Purpose: BDD tests for player search and club summaries
 *          (features/players.feature).
 * ============================================================================
 */

import { describe, it, expect } from "vitest";
import { givenDataLoaded } from "./helpers.js";
import { findPlayers, playersByClub } from "../src/queries/players.js";

const ds = givenDataLoaded();

describe("Feature: Player Queries", () => {
  describe("Scenario: Search a player by name", () => {
    // The bundled FIFA dataset (FIFA 19 vintage) contains Gabriel Jesus but not
    // Gabriel "Gabigol" Barbosa, so we assert on a Brazilian who is present.
    const players = findPlayers(ds, { name: "Gabriel Jesus" });

    it("Then at least one player is returned", () => {
      expect(players.length).toBeGreaterThanOrEqual(1);
    });

    it("And the result includes an overall rating", () => {
      expect(players[0].overall).not.toBeNull();
    });
  });

  describe("Scenario: Find Brazilian players", () => {
    const players = findPlayers(ds, { nationality: "Brazil", limit: 1000 });

    it("Then all returned players are Brazilian", () => {
      for (const p of players) expect(p.nationality).toBe("Brazil");
    });

    it("And the top result is the highest rated (Neymar Jr)", () => {
      expect(players[0].name).toBe("Neymar Jr");
      expect((players[0].overall ?? 0) >= (players[1].overall ?? 0)).toBe(true);
    });
  });

  describe("Scenario: Find players by club", () => {
    // Grêmio is one of the Brazilian clubs present in the FIFA dataset; the
    // accent-insensitive query "Gremio" must still match the stored "Grêmio".
    const players = findPlayers(ds, { club: "Gremio" });

    it("Then players are returned and all belong to Grêmio", () => {
      expect(players.length).toBeGreaterThan(0);
      for (const p of players) expect(/Gr[eê]mio/i.test(p.club)).toBe(true);
    });
  });

  describe("Scenario: Filter by position", () => {
    it("When searching GKs Then all returned players are goalkeepers", () => {
      const gks = findPlayers(ds, { position: "GK", limit: 20 });
      expect(gks.length).toBeGreaterThan(0);
      for (const p of gks) expect(p.position).toBe("GK");
    });
  });

  describe("Scenario: Summarize Brazilian players by club", () => {
    const summaries = playersByClub(ds, { nationality: "Brazil", limit: 10 });

    it("Then each group reports count and average rating", () => {
      expect(summaries.length).toBeGreaterThan(0);
      for (const s of summaries) {
        expect(s.count).toBeGreaterThan(0);
        expect(s.avgOverall).toBeGreaterThan(0);
      }
    });

    it("And groups are ordered by squad size (descending)", () => {
      for (let i = 1; i < summaries.length; i++) {
        expect(summaries[i - 1].count).toBeGreaterThanOrEqual(summaries[i].count);
      }
    });
  });
});
