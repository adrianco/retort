/**
 * Integration tests for the data store against the real bundled datasets.
 * These assert both structural facts (all files load, dedup works) and a few
 * historically-verifiable results (2019 Brasileirão standings) so regressions
 * in loading/normalization are caught.
 */
import { describe, expect, it } from "vitest";
import { dedupeMatches } from "../src/loader.js";
import type { Match } from "../src/types.js";
import { store } from "./helpers.js";

describe("data loading", () => {
  it("loads matches and players from all datasets", () => {
    const s = store();
    expect(s.matches.length).toBeGreaterThan(15000);
    expect(s.players.length).toBe(18207);
  });

  it("exposes all five competitions", () => {
    const comps = store().listCompetitions();
    expect(comps).toContain("Brasileirão Série A");
    expect(comps).toContain("Copa do Brasil");
    expect(comps).toContain("Copa Libertadores");
    expect(comps).toContain("Brasileirão Série B");
    expect(comps).toContain("Brasileirão Série C");
  });
});

describe("dedupeMatches", () => {
  it("collapses the same fixture seen across sources, keeping richest data", () => {
    const base: Omit<Match, "source" | "round" | "stats"> = {
      competition: "Brasileirão Série A",
      date: "2019-04-27",
      season: 2019,
      stage: null,
      homeTeam: "Flamengo",
      homeTeamId: "flamengo",
      awayTeam: "Cruzeiro",
      awayTeamId: "cruzeiro",
      homeGoals: 3,
      awayGoals: 1,
      venue: null,
    };
    const a: Match = { ...base, source: "novo", round: "1" };
    const b: Match = {
      ...base,
      date: "2019-04-28", // off-by-one across sources
      source: "br-football",
      round: null,
      stats: {
        homeCorners: 5, awayCorners: 3, homeShots: 10, awayShots: 4,
        homeAttacks: 80, awayAttacks: 40, totalCorners: 8,
      },
    };
    const merged = dedupeMatches([a, b]);
    expect(merged).toHaveLength(1);
    expect(merged[0].round).toBe("1"); // filled from the non-stats record
    expect(merged[0].stats).toBeDefined(); // kept from the rich record
    expect(merged[0].date).toBe("2019-04-27"); // earlier (local) date preferred
  });
});

describe("2019 Brasileirão standings (historically verifiable)", () => {
  it("has 380 matches across 20 teams", () => {
    const matches = store().findMatches({ competition: "Série A", season: 2019 });
    const teams = new Set(matches.flatMap((m) => [m.homeTeamId, m.awayTeamId]));
    expect(matches).toHaveLength(380);
    expect(teams.size).toBe(20);
  });

  it("crowns Flamengo champion with 90 points (28W 6D 4L)", () => {
    const rows = store().standings("Brasileirão Série A", 2019);
    const champ = rows[0];
    expect(champ.team).toBe("Flamengo");
    expect(champ.points).toBe(90);
    expect(champ.wins).toBe(28);
    expect(champ.draws).toBe(6);
    expect(champ.losses).toBe(4);
    expect(champ.played).toBe(38);
  });
});

describe("findMatches filters", () => {
  it("filters by team + venue", () => {
    const home = store().findMatches({ team: "Corinthians", season: 2019, venue: "home", competition: "Série A" });
    expect(home.length).toBeGreaterThan(0);
    expect(home.every((m) => m.homeTeamId === "corinthians")).toBe(true);
  });

  it("filters by date range", () => {
    const ms = store().findMatches({ team: "Flamengo", startDate: "2019-01-01", endDate: "2019-12-31" });
    expect(ms.length).toBeGreaterThan(0);
    expect(ms.every((m) => m.date! >= "2019-01-01" && m.date! <= "2019-12-31")).toBe(true);
  });

  it("returns matches sorted by date ascending", () => {
    const ms = store().findMatches({ team: "Palmeiras", season: 2018 });
    const dates = ms.map((m) => m.date ?? "");
    expect([...dates].sort()).toEqual(dates);
  });
});

describe("headToHead", () => {
  it("computes the Fla-Flu derby record consistently", () => {
    const h = store().headToHead("Flamengo", "Fluminense");
    expect(h.teamA?.display).toBe("Flamengo");
    expect(h.teamB?.display).toBe("Fluminense");
    expect(h.matches.length).toBe(h.aWins + h.bWins + h.draws +
      h.matches.filter((m) => m.homeGoals === null).length);
    expect(h.matches.length).toBeGreaterThan(10);
  });

  it("returns nulls for an unknown team", () => {
    const h = store().headToHead("Flamengo", "Nonexistent United");
    expect(h.teamB).toBeNull();
    expect(h.matches).toHaveLength(0);
  });
});

describe("teamRecord", () => {
  it("aggregates wins/draws/losses that sum to games played", () => {
    const rec = store().teamRecord("Palmeiras", { season: 2019, competition: "Série A" });
    expect(rec).not.toBeNull();
    expect(rec!.wins + rec!.draws + rec!.losses).toBe(rec!.played);
    expect(rec!.points).toBe(rec!.wins * 3 + rec!.draws);
  });
});

describe("competitionStats", () => {
  it("computes average goals and home win rate for 2019 Série A", () => {
    const stats = store().competitionStats({ competition: "Série A", season: 2019 });
    expect(stats.decided).toBe(380);
    expect(stats.avgGoals).toBeGreaterThan(2);
    expect(stats.avgGoals).toBeLessThan(3.5);
    expect(stats.homeWins + stats.awayWins + stats.draws).toBe(380);
    expect(stats.biggestMargins.length).toBeGreaterThan(0);
  });
});
