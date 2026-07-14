/*
 * ============================================================================
 * Context
 * ----------------------------------------------------------------------------
 * Test:    tests/teams.test.ts
 * Purpose: BDD tests for team records and competition history
 *          (features/teams.feature).
 * ============================================================================
 */

import { describe, it, expect } from "vitest";
import { givenDataLoaded } from "./helpers.js";
import {
  teamRecord,
  teamCompetitions,
  winRate,
} from "../src/queries/teams.js";

const ds = givenDataLoaded();

describe("Feature: Team Queries", () => {
  describe("Scenario: Get team statistics for a season", () => {
    const rec = teamRecord(ds, "Palmeiras", { season: 2019 });

    it("Then I receive wins, losses, draws, and goals", () => {
      expect(rec.played).toBeGreaterThan(0);
      expect(rec.wins + rec.draws + rec.losses).toBe(rec.played);
      expect(rec.goalsFor).toBeGreaterThanOrEqual(0);
      expect(rec.goalsAgainst).toBeGreaterThanOrEqual(0);
    });

    it("And points equal wins*3 + draws", () => {
      expect(rec.points).toBe(rec.wins * 3 + rec.draws);
    });
  });

  describe("Scenario: Get a team's home record", () => {
    const rec = teamRecord(ds, "Corinthians", {
      season: 2022,
      venue: "home",
      competition: "Brasileirão Série A",
    });

    it("Then a record is produced with a sane win rate", () => {
      expect(rec.played).toBeGreaterThan(0);
      const wr = winRate(rec);
      expect(wr).toBeGreaterThanOrEqual(0);
      expect(wr).toBeLessThanOrEqual(1);
    });
  });

  describe("Scenario: List the competitions a team has played in", () => {
    const comps = teamCompetitions(ds, "Palmeiras");

    it("Then the list includes Brasileirão Série A", () => {
      const names = comps.map((c) => c.competition);
      expect(names).toContain("Brasileirão Série A");
    });

    it("And each entry has a positive appearance count", () => {
      for (const c of comps) expect(c.appearances).toBeGreaterThan(0);
    });
  });
});
