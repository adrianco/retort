import { describe, it, expect, beforeAll } from "vitest";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { loadAll, canonicalMatches } from "../src/loader.js";
import { SoccerDatabase } from "../src/database.js";
import { normalizeTeamName } from "../src/normalize.js";

const here = dirname(fileURLToPath(import.meta.url));
const dataDir = join(here, "..", "data", "kaggle");

let db: SoccerDatabase;

beforeAll(() => {
  db = new SoccerDatabase(loadAll(dataDir));
});

describe("data coverage", () => {
  it("loads all six datasets at their full raw row counts", () => {
    // 4180 + 1337 + 1255 + 10296 + 6886 = 23954 raw match rows.
    const raw = loadAll(dataDir);
    expect(raw.matches.length).toBe(23954);
    expect(raw.players.length).toBe(18207);
  });

  it("canonicalizes overlapping datasets to fewer, non-duplicated matches", () => {
    // Canonical set drops cross-dataset duplication but stays large.
    expect(db.matches.length).toBeLessThan(23954);
    expect(db.matches.length).toBeGreaterThan(15000);
    expect(db.matches.length).toBe(canonicalMatches(loadAll(dataDir).matches).length);
    expect(db.players.length).toBe(18207);
  });

  it("represents every competition", () => {
    const comps = new Set(db.matches.map((m) => m.competition));
    expect(comps.has("Brasileirão Série A")).toBe(true);
    expect(comps.has("Copa do Brasil")).toBe(true);
    expect(comps.has("Copa Libertadores")).toBe(true);
  });
});

describe("real queries", () => {
  it("finds Flamengo vs Fluminense matches with a head-to-head", () => {
    const matches = db.findMatches({ team: "Flamengo", team2: "Fluminense" });
    expect(matches.length).toBeGreaterThan(0);
    const h2h = db.headToHead("Flamengo", "Fluminense");
    expect(h2h.teamAWins + h2h.teamBWins + h2h.draws).toBe(h2h.matches);
  });

  it("computes 2019 Brasileirão standings with Flamengo as champion", () => {
    const table = db.standings("Brasileirão Série A", 2019);
    expect(table.length).toBeGreaterThan(0);
    expect(normalizeTeamName(table[0].team)).toBe("flamengo");
    // Flamengo won the 2019 Brasileirão with 90 points.
    expect(table[0].points).toBe(90);
  });

  it("finds Brazilian players sorted by rating", () => {
    const players = db.findPlayers({ nationality: "Brazil", limit: 5 });
    expect(players.length).toBe(5);
    expect(players[0].overall! >= players[4].overall!).toBe(true);
    expect(players.every((p) => /brazil/i.test(p.nationality))).toBe(true);
  });

  it("finds a known player by name", () => {
    const players = db.findPlayers({ name: "Neymar" });
    expect(players.length).toBeGreaterThan(0);
    expect(players[0].nationality).toBe("Brazil");
  });

  it("computes overall match statistics with a plausible average", () => {
    const stats = db.statistics({});
    expect(stats.totalMatches).toBe(db.matches.length);
    expect(stats.averageGoals).toBeGreaterThan(1.5);
    expect(stats.averageGoals).toBeLessThan(4);
    expect(stats.homeWinRate).toBeGreaterThan(0.3);
  });

  it("groups Brazilian players at Brazilian clubs", () => {
    const groups = db.brazilianPlayersByClub();
    expect(groups.length).toBeGreaterThan(0);
    expect(groups[0].count).toBeGreaterThanOrEqual(groups[groups.length - 1].count);
  });
});

describe("performance", () => {
  it("answers an aggregate query in well under 5 seconds", () => {
    const start = performance.now();
    db.standings("Brasileirão Série A", 2019);
    db.findMatches({ team: "Palmeiras" });
    db.findPlayers({ nationality: "Brazil" });
    const elapsed = performance.now() - start;
    expect(elapsed).toBeLessThan(5000);
  });
});
