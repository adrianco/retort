import { describe, it, expect, beforeAll } from "vitest";
import { resolve } from "node:path";
import { loadAll } from "../src/loader.js";
import type { Dataset } from "../src/types.js";
import { findMatches, headToHead } from "../src/queries/matches.js";
import { teamRecord, listTeams, topScoringTeams, computeStandings } from "../src/queries/teams.js";
import { findPlayers, brazilianPlayersByClub } from "../src/queries/players.js";
import { matchStats, biggestWins, compareSeasons } from "../src/queries/stats.js";
import { seasonSummary, listSeasons, listCompetitions } from "../src/queries/competitions.js";

let dataset: Dataset;

beforeAll(() => {
  dataset = loadAll(resolve(process.cwd(), "data/kaggle"));
});

describe("match queries", () => {
  it("finds matches between two teams", () => {
    const matches = findMatches(dataset, { team: "Flamengo", team2: "Fluminense", limit: 0 });
    expect(matches.length).toBeGreaterThan(5);
    for (const m of matches.slice(0, 10)) {
      const teams = `${m.homeTeam} ${m.awayTeam}`;
      expect(teams).toMatch(/flamengo/);
      expect(teams).toMatch(/fluminense/);
    }
  });

  it("filters by season", () => {
    const matches = findMatches(dataset, { team: "Palmeiras", season: 2019, limit: 0 });
    expect(matches.length).toBeGreaterThan(0);
    for (const m of matches) expect(m.season).toBe(2019);
  });

  it("filters by competition", () => {
    const matches = findMatches(dataset, { competition: "Libertadores", limit: 5 });
    expect(matches.length).toBe(5);
    for (const m of matches) expect(m.competition).toBe("Libertadores");
  });

  it("filters by date range", () => {
    const matches = findMatches(dataset, { dateFrom: "2019-01-01", dateTo: "2019-12-31", competition: "Brasileirao", limit: 0 });
    expect(matches.length).toBeGreaterThan(0);
    for (const m of matches) {
      expect(m.date >= "2019-01-01").toBe(true);
      expect(m.date <= "2019-12-31").toBe(true);
    }
  });

  it("computes head-to-head record", () => {
    const h2h = headToHead(dataset, "Flamengo", "Fluminense");
    expect(h2h.matches).toBeGreaterThan(5);
    expect(h2h.teamAWins + h2h.teamBWins + h2h.draws).toBe(h2h.matches);
    expect(h2h.recentMatches.length).toBeGreaterThan(0);
  });
});

describe("team queries", () => {
  it("computes team record including home/away splits", () => {
    const rec = teamRecord(dataset, "Corinthians", { competition: "Brasileirao", season: 2019 });
    expect(rec.overall.matches).toBeGreaterThan(0);
    expect(rec.overall.matches).toBe(rec.home.matches + rec.away.matches);
    expect(rec.overall.points).toBe(rec.overall.wins * 3 + rec.overall.draws);
  });

  it("lists teams", () => {
    const teams = listTeams(dataset, { competition: "Brasileirao", season: 2019 });
    expect(teams.length).toBeGreaterThan(15);
    expect(teams.length).toBeLessThan(40);
  });

  it("returns top scoring teams", () => {
    const top = topScoringTeams(dataset, { competition: "Brasileirao", season: 2019, limit: 5 });
    expect(top.length).toBe(5);
    expect(top[0].goals).toBeGreaterThanOrEqual(top[4].goals);
  });

  it("computes standings ordered by points", () => {
    const standings = computeStandings(dataset, { competition: "Brasileirao", season: 2019 });
    expect(standings.length).toBeGreaterThan(15);
    for (let i = 1; i < standings.length; i++) {
      expect(standings[i - 1].points).toBeGreaterThanOrEqual(standings[i].points);
    }
    expect(standings[0].rank).toBe(1);
  });
});

describe("player queries", () => {
  it("finds Brazilian players", () => {
    const brazilians = findPlayers(dataset, { nationality: "Brazil", limit: 25 });
    expect(brazilians.length).toBe(25);
    for (const p of brazilians) expect(p.nationality.toLowerCase()).toContain("brazil");
  });

  it("filters by overall rating", () => {
    const elite = findPlayers(dataset, { minOverall: 88, limit: 0 });
    expect(elite.length).toBeGreaterThan(0);
    for (const p of elite) expect((p.overall ?? 0)).toBeGreaterThanOrEqual(88);
  });

  it("filters by club", () => {
    const fluminense = findPlayers(dataset, { club: "Fluminense", limit: 0 });
    expect(fluminense.length).toBeGreaterThan(0);
    for (const p of fluminense) expect(p.club.toLowerCase()).toContain("fluminense");
  });

  it("searches by name", () => {
    const result = findPlayers(dataset, { name: "Neymar", limit: 5 });
    expect(result.length).toBeGreaterThan(0);
    expect(result[0].name.toLowerCase()).toContain("neymar");
  });

  it("groups Brazilians by club", () => {
    const groups = brazilianPlayersByClub(dataset);
    expect(groups.length).toBeGreaterThan(0);
    expect(groups[0].players).toBeGreaterThanOrEqual(groups[groups.length - 1].players);
  });
});

describe("competition queries", () => {
  it("summarizes a season", () => {
    const s = seasonSummary(dataset, 2019, "Brasileirao");
    expect(s.champion).not.toBeNull();
    expect(s.topThree.length).toBe(3);
    expect(s.totalTeams).toBeGreaterThan(15);
  });

  it("lists seasons", () => {
    const seasons = listSeasons(dataset, "Brasileirao");
    expect(seasons.length).toBeGreaterThan(3);
    expect(seasons).toEqual([...seasons].sort((a, b) => a - b));
  });

  it("lists competitions", () => {
    const comps = listCompetitions(dataset);
    const keys = comps.map((c) => c.competition);
    expect(keys).toContain("Brasileirao");
    expect(keys).toContain("CopaDoBrasil");
    expect(keys).toContain("Libertadores");
    expect(keys).toContain("BRDataset");
    expect(keys).toContain("BrasileiraoHistorical");
  });
});

describe("stats queries", () => {
  it("computes match stats", () => {
    const s = matchStats(dataset, { competition: "Brasileirao" });
    expect(s.matches).toBeGreaterThan(0);
    expect(s.averageGoalsPerMatch).toBeGreaterThan(1);
    expect(s.averageGoalsPerMatch).toBeLessThan(5);
    expect(s.homeWinRate + s.awayWinRate + s.drawRate).toBeCloseTo(1, 5);
  });

  it("finds biggest wins", () => {
    const wins = biggestWins(dataset, { competition: "Brasileirao", limit: 5 });
    expect(wins.length).toBe(5);
    for (let i = 1; i < wins.length; i++) {
      expect(wins[i - 1].margin).toBeGreaterThanOrEqual(wins[i].margin);
    }
    expect(wins[0].margin).toBeGreaterThanOrEqual(3);
  });

  it("compares seasons", () => {
    const cmp = compareSeasons(dataset, [2018, 2019], { competition: "Brasileirao" });
    expect(cmp.length).toBe(2);
    expect(cmp[0].season).toBe(2018);
    expect(cmp[1].season).toBe(2019);
    for (const c of cmp) expect(c.matches).toBeGreaterThan(0);
  });
});
