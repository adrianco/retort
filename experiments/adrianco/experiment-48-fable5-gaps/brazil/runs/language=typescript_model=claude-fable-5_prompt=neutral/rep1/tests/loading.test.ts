/**
 * Feature: Data loading
 *
 * All six provided Kaggle CSV files must load and be queryable, with
 * cross-file duplicates merged rather than double-counted.
 */
import { describe, expect, it } from "vitest";
import { dataset } from "./helpers.js";

describe("Feature: Data loading", () => {
  describe("Scenario: All six CSV files are loadable", () => {
    it("Given the data directory, When the dataset is loaded, Then every file contributes its expected row count", () => {
      const ds = dataset();
      expect(ds.fileCounts["Brasileirao_Matches.csv"]).toBe(4180);
      expect(ds.fileCounts["Brazilian_Cup_Matches.csv"]).toBe(1337);
      expect(ds.fileCounts["Libertadores_Matches.csv"]).toBe(1255);
      expect(ds.fileCounts["BR-Football-Dataset.csv"]).toBe(10296);
      expect(ds.fileCounts["novo_campeonato_brasileiro.csv"]).toBe(6886);
      expect(ds.fileCounts["fifa_data.csv"]).toBe(18207);
    });

    it("Then all 18,207 FIFA players are loaded", () => {
      expect(dataset().players.length).toBe(18207);
    });

    it("Then matches from every competition are present", () => {
      const comps = new Set(dataset().matches.map((m) => m.competition));
      expect(comps).toContain("Brasileirão Série A");
      expect(comps).toContain("Brasileirão Série B");
      expect(comps).toContain("Brasileirão Série C");
      expect(comps).toContain("Copa do Brasil");
      expect(comps).toContain("Copa Libertadores");
    });
  });

  describe("Scenario: Cross-file duplicates are merged", () => {
    it("Given the same fixture appears in multiple files, When loaded, Then duplicates are merged instead of double-counted", () => {
      const ds = dataset();
      expect(ds.duplicatesMerged).toBeGreaterThan(5000);
      // Unique matches must be fewer than the raw sum of match rows.
      const rawMatchRows =
        ds.fileCounts["Brasileirao_Matches.csv"] +
        ds.fileCounts["Brazilian_Cup_Matches.csv"] +
        ds.fileCounts["Libertadores_Matches.csv"] +
        ds.fileCounts["BR-Football-Dataset.csv"] +
        ds.fileCounts["novo_campeonato_brasileiro.csv"];
      expect(ds.matches.length).toBeLessThan(rawMatchRows);
      expect(ds.matches.length).toBeGreaterThan(10000);
    });

    it("Then a merged match carries extended statistics from the stats file", () => {
      const ds = dataset();
      const merged = ds.matches.find((m) => m.sources.length > 1 && m.stats);
      expect(merged).toBeDefined();
      expect(merged!.stats!.homeCorners ?? merged!.stats!.homeShots).toBeDefined();
    });
  });

  describe("Scenario: Multiple date formats are handled", () => {
    it("Given ISO and Brazilian date formats, When loaded, Then all dates are normalized to ISO", () => {
      const ds = dataset();
      // Historical file uses DD/MM/YYYY — a 2003 match must parse correctly.
      const m2003 = ds.matches.filter((m) => m.date?.startsWith("2003"));
      expect(m2003.length).toBeGreaterThan(300);
      for (const m of ds.matches) {
        if (m.date) expect(m.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      }
    });
  });

  describe("Scenario: UTF-8 team names survive loading", () => {
    it("Given accented Portuguese names, When loaded, Then they are preserved in display names", () => {
      const ds = dataset();
      const raws = new Set(ds.matches.flatMap((m) => [m.home.raw, m.away.raw]));
      const joined = [...raws].join("|");
      expect(joined).toContain("São Paulo");
      expect(joined).toContain("Grêmio");
      expect(joined).toContain("Avaí");
    });
  });
});
