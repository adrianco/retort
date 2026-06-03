/**
 * tests/competitions.test.ts
 * -----------------------------------------------------------------------------
 * CONTEXT
 *   BDD specs for the competition service: league tables reconstructed from
 *   match results, champions, relegation and available seasons. Anchored on the
 *   2019 Brasileirão, whose real result (Flamengo, 90 pts, 28W-6D-4L) is the
 *   ground truth quoted in the spec.
 * -----------------------------------------------------------------------------
 */

import { describe, it, expect } from "vitest";
import { givenDataset } from "./fixture.js";
import {
  standings,
  champion,
  relegated,
  listSeasons,
} from "../src/services/competitions.js";

describe("Feature: Competition Queries", () => {
  describe("Scenario: Reconstruct the 2019 Brasileirão table", () => {
    it("Given 2019 match results, Then Flamengo are champions with 90 points", () => {
      const ds = givenDataset();
      const c = champion(ds, "Brasileirão", 2019);
      expect(c).not.toBeNull();
      expect(c!.team).toBe("Flamengo");
      expect(c!.points).toBe(90);
      expect(c!.wins).toBe(28);
      expect(c!.draws).toBe(6);
      expect(c!.losses).toBe(4);
    });

    it("Given the table, Then it is ranked by points descending", () => {
      const ds = givenDataset();
      const table = standings(ds, "Brasileirão", 2019);
      expect(table.length).toBe(20);
      for (let i = 1; i < table.length; i++) {
        expect(table[i - 1].points).toBeGreaterThanOrEqual(table[i].points);
        expect(table[i].position).toBe(i + 1);
      }
    });

    it("Given the table, Then the top three are Flamengo, Palmeiras, Santos", () => {
      const ds = givenDataset();
      const table = standings(ds, "Brasileirão", 2019);
      expect(table.slice(0, 3).map((r) => r.team)).toEqual([
        "Flamengo",
        "Palmeiras",
        "Santos",
      ]);
    });
  });

  describe("Scenario: Relegation places", () => {
    it("Given the 2019 Brasileirão, Then four teams fill the bottom places", () => {
      const ds = givenDataset();
      const down = relegated(ds, "Brasileirão", 2019, 4);
      expect(down.length).toBe(4);
      expect(down[down.length - 1].position).toBe(20);
    });
  });

  describe("Scenario: List available seasons", () => {
    it("Given the Brasileirão data, Then seasons span 2003 to 2022", () => {
      const ds = givenDataset();
      const seasons = listSeasons(ds, "Brasileirão");
      expect(seasons[0]).toBe(2003);
      expect(seasons[seasons.length - 1]).toBe(2022);
      // Contiguous, no gaps across two decades of data.
      expect(seasons.length).toBe(2022 - 2003 + 1);
    });
  });
});
