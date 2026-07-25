/**
 * Feature: Query performance
 *
 * Spec: simple lookups < 2s, aggregate queries < 5s, no timeouts.
 */
import { describe, expect, it } from "vitest";
import {
  competitionStats,
  filterMatches,
  headToHead,
  searchPlayers,
  standings,
} from "../src/queries.js";
import { loadDataset } from "../src/loader.js";
import { DATA_DIR, dataset } from "./helpers.js";

describe("Feature: Query performance", () => {
  describe("Scenario: Dataset loads quickly enough for interactive use", () => {
    it("Given all six CSV files, When loaded from scratch, Then loading completes in under 5 seconds", () => {
      const t0 = performance.now();
      const ds = loadDataset(DATA_DIR);
      const elapsed = performance.now() - t0;
      expect(ds.matches.length).toBeGreaterThan(10000);
      expect(elapsed).toBeLessThan(5000);
    });
  });

  describe("Scenario: Simple lookups respond in under 2 seconds", () => {
    it("Match search, head-to-head and player search each finish well under the limit", () => {
      const ds = dataset();
      const t0 = performance.now();
      filterMatches(ds, { team: "Flamengo", opponent: "Fluminense" });
      headToHead(ds, "Palmeiras", "Corinthians");
      searchPlayers(ds, { name: "Neymar" });
      const elapsed = performance.now() - t0;
      expect(elapsed).toBeLessThan(2000);
    });
  });

  describe("Scenario: Aggregate queries respond in under 5 seconds", () => {
    it("Standings and competition statistics finish under the limit", () => {
      const ds = dataset();
      const t0 = performance.now();
      standings(ds, 2019);
      standings(ds, 2003);
      competitionStats(ds, { competition: "Brasileirão" });
      competitionStats(ds, {});
      const elapsed = performance.now() - t0;
      expect(elapsed).toBeLessThan(5000);
    });
  });
});
