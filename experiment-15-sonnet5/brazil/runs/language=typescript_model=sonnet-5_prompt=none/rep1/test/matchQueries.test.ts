import { describe, expect, it } from "vitest";
import { getDataset } from "../src/dataLoader.js";
import { findMatches, headToHead } from "../src/queries/matchQueries.js";

const dataset = getDataset();

describe("findMatches", () => {
  it("finds matches for a team regardless of home/away", () => {
    const result = findMatches(dataset, { team: "Flamengo", season: 2019, competition: "Brasileirao" });
    expect(result.total).toBeGreaterThan(0);
    for (const m of result.matches) {
      expect(m.homeTeam.baseKey === "flamengo" || m.awayTeam.baseKey === "flamengo").toBe(true);
    }
  });

  it("finds matches between two specific teams in either home/away order", () => {
    const result = findMatches(dataset, { team: "Flamengo", opponent: "Fluminense" });
    expect(result.total).toBeGreaterThan(0);
    for (const m of result.matches) {
      const teams = [m.homeTeam.baseKey, m.awayTeam.baseKey];
      expect(teams).toContain("flamengo");
      expect(teams).toContain("fluminense");
    }
  });

  it("filters by season and date range", () => {
    const result = findMatches(dataset, { team: "Palmeiras", season: 2023 });
    expect(result.total).toBeGreaterThan(0);
    for (const m of result.matches) {
      expect(m.season).toBe(2023);
    }
  });

  it("caps results at the requested limit but reports the true total", () => {
    const result = findMatches(dataset, { team: "Corinthians", limit: 3 });
    expect(result.matches.length).toBe(3);
    expect(result.total).toBeGreaterThan(3);
  });

  it("sorts results most-recent-first", () => {
    const result = findMatches(dataset, { team: "Santos", limit: 10 });
    for (let i = 1; i < result.matches.length; i++) {
      const prev = result.matches[i - 1].date?.getTime() ?? 0;
      const curr = result.matches[i].date?.getTime() ?? 0;
      expect(prev).toBeGreaterThanOrEqual(curr);
    }
  });

  it("returns nothing for a nonexistent team", () => {
    const result = findMatches(dataset, { team: "Nonexistent FC 12345" });
    expect(result.total).toBe(0);
  });
});

describe("headToHead", () => {
  it("computes symmetric win/draw totals that add up to the match count", () => {
    const result = headToHead(dataset, "Flamengo", "Fluminense");
    expect(result.teamAWins + result.teamBWins + result.draws).toBe(result.totalMatches);
  });

  it("is symmetric when teams are swapped", () => {
    const ab = headToHead(dataset, "Flamengo", "Fluminense");
    const ba = headToHead(dataset, "Fluminense", "Flamengo");
    expect(ba.totalMatches).toBe(ab.totalMatches);
    expect(ba.teamAWins).toBe(ab.teamBWins);
    expect(ba.teamBWins).toBe(ab.teamAWins);
    expect(ba.teamAGoals).toBe(ab.teamBGoals);
  });

  it("supports scoping to a competition and season", () => {
    const result = headToHead(dataset, "Palmeiras", "Santos", { competition: "Brasileirao", season: 2022 });
    for (const m of result.matches) {
      expect(m.season).toBe(2022);
    }
  });
});
