/**
 * tests/teams.test.ts
 * -----------------------------------------------------------------------------
 * CONTEXT
 *   BDD specs for the team-query service: win/draw/loss records, goals, points
 *   and win rate, filtered by season / competition / venue.
 * -----------------------------------------------------------------------------
 */

import { describe, it, expect } from "vitest";
import { givenDataset } from "./fixture.js";
import { teamRecord } from "../src/services/teams.js";

describe("Feature: Team Queries", () => {
  describe("Scenario: Get team statistics for a season", () => {
    it("Given Palmeiras in 2019, Then I receive wins, draws, losses and goals", () => {
      const ds = givenDataset();
      const r = teamRecord(ds, "Palmeiras", { season: 2019, competition: "Brasileirão" });
      expect(r.matchesWithScores).toBeGreaterThan(0);
      expect(r.wins + r.draws + r.losses).toBe(r.matchesWithScores);
      expect(r.points).toBe(r.wins * 3 + r.draws);
      expect(r.goalDifference).toBe(r.goalsFor - r.goalsAgainst);
    });
  });

  describe("Scenario: Home record for a season", () => {
    it("Given Corinthians' 2022 home Brasileirão record, Then it covers one home season", () => {
      const ds = givenDataset();
      const r = teamRecord(ds, "Corinthians", {
        season: 2022,
        competition: "Brasileirão",
        venue: "home",
      });
      // A 20-team league season is 19 home fixtures. The source CSV was
      // captured before the final 4 home games were played, so those rows have
      // no recorded score and are excluded from the tally.
      expect(r.matches).toBe(19);
      expect(r.matchesWithScores).toBe(15);
      expect(r.wins + r.draws + r.losses).toBe(r.matchesWithScores);
      expect(r.winRate).toBeGreaterThanOrEqual(0);
      expect(r.winRate).toBeLessThanOrEqual(1);
    });
  });

  describe("Scenario: Win rate is consistent with wins", () => {
    it("Given any record, Then win rate equals wins / matches-with-scores", () => {
      const ds = givenDataset();
      const r = teamRecord(ds, "Santos", { competition: "Brasileirão" });
      const expected = r.wins / r.matchesWithScores;
      expect(r.winRate).toBeCloseTo(expected, 6);
    });
  });
});
