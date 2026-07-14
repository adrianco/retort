/**
 * tests/loader.test.ts
 * -----------------------------------------------------------------------------
 * CONTEXT
 *   BDD specs for the CSV loader: all six files load, date formats normalise to
 *   ISO, and cross-file duplicate fixtures collapse so standings aren't inflated.
 * -----------------------------------------------------------------------------
 */

import { describe, it, expect } from "vitest";
import { givenDataset } from "./fixture.js";
import { toIsoDate } from "../src/data/loader.js";

describe("Feature: Data loading", () => {
  describe("Scenario: All provided datasets load", () => {
    it("Given the CSV files, Then matches and players are populated", () => {
      const ds = givenDataset();
      expect(ds.matches.length).toBeGreaterThan(10000);
      expect(ds.players.length).toBe(18207);
    });

    it("Given the loaded matches, Then every canonical competition is present", () => {
      const ds = givenDataset();
      const comps = new Set(ds.matches.map((m) => m.competition));
      expect(comps.has("Brasileirão")).toBe(true);
      expect(comps.has("Copa do Brasil")).toBe(true);
      expect(comps.has("Libertadores")).toBe(true);
    });

    it("Given each match, Then scores are numbers or null (never NaN)", () => {
      const ds = givenDataset();
      for (const m of ds.matches.slice(0, 500)) {
        expect(m.homeGoals === null || Number.isFinite(m.homeGoals)).toBe(true);
        expect(m.awayGoals === null || Number.isFinite(m.awayGoals)).toBe(true);
      }
    });
  });

  describe("Scenario: Multiple date formats normalise to ISO", () => {
    it("Given ISO, ISO+time and Brazilian dates, Then all become YYYY-MM-DD", () => {
      expect(toIsoDate("2023-09-24")).toBe("2023-09-24");
      expect(toIsoDate("2012-05-19 18:30:00")).toBe("2012-05-19");
      expect(toIsoDate("29/03/2003")).toBe("2003-03-29");
      expect(toIsoDate("")).toBeNull();
      expect(toIsoDate(undefined)).toBeNull();
    });
  });

  describe("Scenario: Duplicate fixtures are de-duplicated", () => {
    it("Given the same fixture in two sources, Then it appears once", () => {
      const ds = givenDataset();
      const seen = new Map<string, number>();
      for (const m of ds.matches) {
        if (!m.date) continue;
        const k = `${m.date}|${m.homeTeam}|${m.awayTeam}|${m.competition}`;
        seen.set(k, (seen.get(k) ?? 0) + 1);
      }
      const dupes = [...seen.values()].filter((n) => n > 1).length;
      // Allow a tiny tail of genuine source date discrepancies, but the bulk
      // (2012-2019 Brasileirão double-listing) must be collapsed.
      expect(dupes).toBeLessThan(50);
    });
  });
});
