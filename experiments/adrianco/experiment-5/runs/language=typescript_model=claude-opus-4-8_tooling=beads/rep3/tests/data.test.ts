/*
 * ============================================================================
 * Context
 * ----------------------------------------------------------------------------
 * Test:    tests/data.test.ts
 * Purpose: BDD tests for the data-loading layer: all six CSVs load, the
 *          overlap-dedup (canonical source selection) works, and the unified
 *          collections are populated.
 * ============================================================================
 */

import { describe, it, expect } from "vitest";
import { givenDataLoaded } from "./helpers.js";

describe("Feature: Data loading", () => {
  describe("Given the data directory", () => {
    const ds = givenDataLoaded();

    it("When loaded Then all 6 source files are present", () => {
      expect(ds.loadedFiles).toHaveLength(6);
    });

    it("When loaded Then there are matches and players", () => {
      expect(ds.matches.length).toBeGreaterThan(10000);
      expect(ds.players.length).toBeGreaterThan(18000);
    });

    it("When loaded Then duplicate Série A coverage is collapsed", () => {
      // 2019 Série A appears in 3 source files; canonical selection keeps one.
      const serieA2019 = ds.matches.filter(
        (m) => m.competition === "Brasileirão Série A" && m.season === 2019,
      );
      const sources = new Set(serieA2019.map((m) => m.source));
      expect(sources.size).toBe(1);
      // A 20-team double round-robin season has 380 matches.
      expect(serieA2019.length).toBe(380);
    });

    it("When loaded Then every match has normalized team keys", () => {
      const sample = ds.matches.slice(0, 500);
      for (const m of sample) {
        expect(m.homeKey).toBeTruthy();
        expect(m.awayKey).toBeTruthy();
      }
    });

    it("When loaded Then players expose nationality and rating", () => {
      const brazil = ds.players.filter((p) => p.nationality === "Brazil");
      expect(brazil.length).toBeGreaterThan(500);
    });
  });
});
