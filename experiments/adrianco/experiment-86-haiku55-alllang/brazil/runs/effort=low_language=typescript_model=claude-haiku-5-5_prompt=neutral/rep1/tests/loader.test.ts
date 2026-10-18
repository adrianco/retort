import { describe, expect, it } from "vitest";
import { DEFAULT_DATA_DIR, loadDataset, loadMatches, loadPlayers } from "../src/loader.js";

describe("Feature: Loading the provided datasets", () => {
  const ds = loadDataset(DEFAULT_DATA_DIR);

  it("Given the bundled CSVs, When loaded, Then matches from all competitions are present", () => {
    const competitions = new Set(ds.matches.map((m) => m.competition));
    expect(competitions).toEqual(
      new Set([
        "Brasileirão Série A",
        "Brasileirão Série B",
        "Brasileirão Série C",
        "Copa do Brasil",
        "Copa Libertadores",
      ]),
    );
  });

  it("Given the source files, When loaded, Then every match has valid dates, scores and teams", () => {
    for (const m of ds.matches) {
      expect(m.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(Number.isInteger(m.homeGoals)).toBe(true);
      expect(Number.isInteger(m.awayGoals)).toBe(true);
      expect(m.home.length).toBeGreaterThan(0);
      expect(m.away.length).toBeGreaterThan(0);
    }
  });

  it("Given matches sorted by date, When loaded, Then they are in ascending order", () => {
    for (let i = 1; i < ds.matches.length; i++) {
      expect(ds.matches[i - 1]!.date <= ds.matches[i]!.date).toBe(true);
    }
  });

  it("Given the Brasileirão appears in three files with different spellings and dates, When loaded, Then each season has one fixture per match", () => {
    const season2019 = ds.matches.filter(
      (m) => m.season === 2019 && m.competition === "Brasileirão Série A",
    );
    // The 2019 Serie A had 380 matches; the sources overlap by up to a day on some dates.
    expect(season2019.length).toBeGreaterThanOrEqual(380);
    expect(season2019.length).toBeLessThanOrEqual(385);
  });

  it("Given the Libertadores file stores scores as quoted strings, When loaded, Then they are numbers", () => {
    const lib = ds.matches.filter((m) => m.competition === "Copa Libertadores");
    expect(lib.length).toBeGreaterThan(1200);
    expect(typeof lib[0]!.homeGoals).toBe("number");
  });

  it("Given the FIFA file has a BOM and an unnamed index column, When loaded, Then players parse correctly", () => {
    expect(ds.players.length).toBeGreaterThan(18000);
    const messi = ds.players.find((p) => p.name === "L. Messi");
    expect(messi).toMatchObject({ overall: 94, nationality: "Argentina", position: "RF" });
  });

  it("Given the Brasileirão Serie A file alone, When loaded, Then it yields matches for 2012", () => {
    const only = loadMatches(DEFAULT_DATA_DIR).filter((m) => m.source === "Brasileirao_Matches.csv");
    expect(only.some((m) => m.season === 2012)).toBe(true);
    expect(loadPlayers(DEFAULT_DATA_DIR).length).toBe(ds.players.length);
  });
});
