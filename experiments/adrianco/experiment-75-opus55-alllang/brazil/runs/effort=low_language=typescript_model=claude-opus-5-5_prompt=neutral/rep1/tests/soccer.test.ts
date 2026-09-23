import { beforeAll, describe, expect, it } from "vitest";
import { loadDataset, type Dataset } from "../src/data.js";
import { createHandlers } from "../src/tools.js";
import { normalizeTeam, parseDate } from "../src/normalize.js";
import { parseCsv } from "../src/csv.js";
import * as Q from "../src/queries.js";

let ds: Dataset;
let h: ReturnType<typeof createHandlers>;
beforeAll(() => { ds = loadDataset(); h = createHandlers(ds); });

describe("Feature: Data loading", () => {
  it("Scenario: all 6 CSV files are loadable", () => {
    expect(Object.keys(ds.fileCounts)).toHaveLength(6);
    expect(ds.fileCounts["Brasileirao_Matches.csv"]).toBeGreaterThan(4000);
    expect(ds.fileCounts["Brazilian_Cup_Matches.csv"]).toBeGreaterThan(1300);
    expect(ds.fileCounts["Libertadores_Matches.csv"]).toBeGreaterThan(1200);
    expect(ds.fileCounts["BR-Football-Dataset.csv"]).toBe(10296);
    expect(ds.fileCounts["novo_campeonato_brasileiro.csv"]).toBe(6886);
    expect(ds.fileCounts["fifa_data.csv"]).toBe(18207);
  });
  it("Scenario: every file is queryable", () => {
    const sources = new Set(Q.findMatches(ds, { team: "Flamengo" }).map((m) => m.source));
    expect(sources.size).toBeGreaterThanOrEqual(3);
    for (const f of ["Brasileirao_Matches.csv", "Brazilian_Cup_Matches.csv", "Libertadores_Matches.csv", "BR-Football-Dataset.csv", "novo_campeonato_brasileiro.csv"])
      expect(ds.matches.some((m) => m.source === f)).toBe(true);
  });
  it("Scenario: UTF-8 accents preserved", () => {
    expect(ds.matches.some((m) => m.home === "Grêmio")).toBe(true);
    expect(ds.players.some((p) => p.club === "Atlético Mineiro")).toBe(true);
  });
});

describe("Feature: Normalization", () => {
  it.each([
    ["Palmeiras-SP", "palmeiras"], ["Palmeiras", "palmeiras"], ["Sport Club Corinthians Paulista", "corinthians"],
    ["São Paulo - SP", "sao paulo"], ["Sao Paulo", "sao paulo"], ["Atlético - MG", "atletico-mg"], ["Atletico Mineiro", "atletico-mg"],
    ["Athletico-PR", "atletico-pr"], ["Atlético Paranaense", "atletico-pr"], ["Vasco Da Gama RJ", "vasco"], ["Gremio RS", "gremio"],
    ["4 de Julho EC", "4 de julho"], ["Botafogo-RJ", "botafogo"], ["Botafogo - SP", "botafogo-sp"], ["Nacional (URU)", "nacional"],
  ])("normalizes %s -> %s", (raw, key) => expect(normalizeTeam(raw)).toBe(key));
  it("handles multiple date formats", () => {
    expect(parseDate("2023-09-24")).toBe("2023-09-24");
    expect(parseDate("29/03/2003")).toBe("2003-03-29");
    expect(parseDate("2012-05-19 18:30:00")).toBe("2012-05-19");
    expect(parseDate("Jul 1, 2004")).toBe("2004-07-01");
  });
  it("parses quoted CSV", () => {
    expect(parseCsv('a,b\n"x, y","say ""hi"""\n')).toEqual([{ a: "x, y", b: 'say "hi"' }]);
  });
});

describe("Feature: Match Queries", () => {
  it("Scenario: Find matches between two teams", () => {
    // Given the match data is loaded / When I search Flamengo vs Fluminense
    const ms = Q.findMatches(ds, { team: "Flamengo", opponent: "Fluminense" });
    // Then I receive a list of matches with date, scores and competition
    expect(ms.length).toBeGreaterThan(20);
    for (const m of ms) {
      expect(m.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(Number.isInteger(m.homeGoals) && Number.isInteger(m.awayGoals)).toBe(true);
      expect(m.competition).toBeTruthy();
      expect([m.homeKey, m.awayKey].sort()).toEqual(["flamengo", "fluminense"]);
    }
    expect(h.head_to_head({ teamA: "Flamengo", teamB: "Fluminense" })).toMatch(/Fla-Flu derby[\s\S]*Head-to-head in dataset/);
  });
  it("Scenario: matches by team and season", () => {
    const ms = Q.findMatches(ds, { team: "Palmeiras", season: 2023 });
    expect(ms.length).toBeGreaterThan(38);
    expect(ms.every((m) => m.season === 2023)).toBe(true);
  });
  it("Scenario: no duplicates across overlapping files", () => {
    // 2022 is present in both Brasileirao_Matches.csv and BR-Football-Dataset.csv
    const ms = Q.findMatches(ds, { team: "Palmeiras", season: 2022, competition: "Brasileirão" });
    expect(ms.length).toBe(38);
  });
  it("Scenario: Copa do Brasil finals", () => {
    const ms = Q.findMatches(ds, { competition: "Copa do Brasil", stage: "final" });
    expect(ms.length).toBeGreaterThan(0);
    expect(ms.some((m) => m.season === 2020 && [m.homeKey, m.awayKey].includes("palmeiras"))).toBe(true);
  });
  it("Scenario: date range and venue filters", () => {
    const ms = Q.findMatches(ds, { team: "Santos", venue: "home", dateFrom: "2015-01-01", dateTo: "2015-12-31" });
    expect(ms.length).toBeGreaterThan(0);
    expect(ms.every((m) => m.homeKey === "santos" && m.date.startsWith("2015"))).toBe(true);
  });
  it("Scenario: last Flamengo vs Corinthians match", () => {
    const [last] = Q.findMatches(ds, { team: "Flamengo", opponent: "Corinthians" });
    expect(last.date >= "2023-01-01").toBe(true);
  });
  it("Scenario: derbies in a season", () => {
    const d = Q.derbies(ds, { season: 2019 });
    expect(d.map((x) => x.derby)).toContain("Grenal");
  });
});

describe("Feature: Team Queries", () => {
  it("Scenario: Get team statistics", () => {
    // When I request statistics for Palmeiras in season 2023
    const { record } = Q.teamRecord(ds, "Palmeiras", { season: 2023, competition: "Brasileirão" });
    expect(record.matches).toBeGreaterThanOrEqual(37); // 2023 comes from BR-Football-Dataset only, which misses a fixture
    expect(record.wins + record.draws + record.losses).toBe(record.matches);
    expect(record.goalsFor).toBeGreaterThan(0);
    expect(h.team_stats({ team: "Palmeiras", season: 2023 })).toMatch(/Wins: \d+, Draws: \d+, Losses: \d+/);
  });
  it("Scenario: home record", () => {
    const out = h.team_stats({ team: "Corinthians", season: 2022, venue: "home", competition: "Brasileirão" });
    expect(out).toContain("Corinthians home record");
    expect(out).toMatch(/Win rate: \d+\.\d%/);
  });
  it("Scenario: competitions a team played in", () => {
    const comps = Q.teamCompetitions(ds, "Palmeiras").map((c) => c.competition);
    expect(comps).toEqual(expect.arrayContaining(["Brasileirão Série A", "Copa do Brasil", "Copa Libertadores"]));
  });
  it("Scenario: ambiguous team name is flagged", () => {
    expect(h.team_stats({ team: "Atletico" })).toContain("matches several clubs");
  });
});

describe("Feature: Competition Queries", () => {
  it("Scenario: Who won the 2019 Brasileirão?", () => {
    const t = Q.standings(ds, 2019);
    expect(t).toHaveLength(20);
    expect(t[0].team).toBe("Flamengo");
    expect(t[0].points).toBe(90);
    expect(h.standings({ season: 2019 })).toMatch(/1\. Flamengo - 90 pts \(28W, 6D, 4L.*Champion/);
  });
  it("Scenario: relegated teams in 2020", () => {
    const out = h.standings({ season: 2020 });
    const relegated = out.split("\n").filter((l) => l.includes("Relegated"));
    expect(relegated).toHaveLength(4);
    expect(out).toMatch(/Botafogo.*Relegated/);
  });
  it("Scenario: historical season from 2003-2019 file", () => {
    expect(Q.standings(ds, 2005).length).toBeGreaterThanOrEqual(20);
  });
  it("Scenario: Libertadores stage", () => {
    const out = h.search_matches({ competition: "Libertadores", season: 2018, stage: "final" });
    expect(out).toMatch(/final/);
  });
});

describe("Feature: Statistical Analysis", () => {
  it("Scenario: average goals per match", () => {
    const s = Q.competitionStats(ds, { competition: "Brasileirão" });
    expect(s.avgGoals).toBeGreaterThan(2);
    expect(s.avgGoals).toBeLessThan(3.5);
    expect(h.competition_stats({ competition: "Brasileirão" })).toMatch(/Average goals per match: \d\.\d\d/);
  });
  it("Scenario: biggest wins sorted by margin", () => {
    const ws = Q.biggestWins(ds, { limit: 10 });
    const margins = ws.map((m) => Math.abs(m.homeGoals - m.awayGoals));
    expect([...margins].sort((a, b) => b - a)).toEqual(margins);
    expect(margins[0]).toBeGreaterThanOrEqual(7);
  });
  it("Scenario: best away record", () => {
    expect(h.best_records({ venue: "away", competition: "Brasileirão" })).toMatch(/^Best away records[\s\S]*1\. /);
  });
  it("Scenario: team scored the most goals in a season", () => {
    const s = Q.competitionStats(ds, { competition: "Brasileirão", season: 2019 });
    expect(s.topScoringTeams[0].team).toBe("Flamengo");
  });
});

describe("Feature: Player Queries", () => {
  it("Scenario: top Brazilian players", () => {
    const ps = Q.searchPlayers(ds, { nationality: "Brazilian", limit: 3 });
    expect(ps[0].name).toBe("Neymar Jr");
    expect(ps.every((p) => p.nationality === "Brazil")).toBe(true);
  });
  it("Scenario: players at a club (accent-insensitive)", () => {
    const ps = Q.searchPlayers(ds, { club: "Gremio", limit: 100 });
    expect(ps.length).toBe(20);
    expect(ps.every((p) => p.club === "Grêmio")).toBe(true);
  });
  it("Scenario: club match is not a substring match", () => {
    expect(Q.searchPlayers(ds, { club: "Santos", limit: 100 }).every((p) => p.club === "Santos")).toBe(true);
  });
  it("Scenario: forwards by position group", () => {
    const ps = Q.searchPlayers(ds, { club: "Cruzeiro", position: "forward", limit: 100 });
    expect(ps.length).toBeGreaterThan(0);
    expect(ps.every((p) => ["ST", "CF", "LF", "RF", "LS", "RS", "LW", "RW"].includes(p.position))).toBe(true);
  });
  it("Scenario: player by name", () => {
    expect(h.get_player({ name: "Neymar" })).toMatch(/Neymar Jr[\s\S]*Overall: 92/);
    expect(h.get_player({ name: "Nobody Atall" })).toMatch(/No player/);
  });
  it("Scenario: cross-file query (players + matches)", () => {
    const rows = Q.brazilianClubPlayers(ds, { brazilianOnly: true });
    expect(rows.map((r) => r.club)).toContain("Cruzeiro");
    const profile = h.team_profile({ team: "Cruzeiro" });
    expect(profile).toMatch(/all-time record[\s\S]*Brasileirão Série A[\s\S]*Overall: \d+/);
  });
});

describe("Feature: Performance and robustness", () => {
  it("answers 20+ sample questions each within 2s", () => {
    const calls: [string, any][] = [
      ["search_matches", { team: "Flamengo", opponent: "Fluminense" }], ["search_matches", { team: "Palmeiras", season: 2023 }],
      ["search_matches", { competition: "Copa do Brasil", stage: "final" }], ["team_stats", { team: "Corinthians", season: 2022, venue: "home" }],
      ["competition_stats", { competition: "Série A", season: 2023 }], ["head_to_head", { teamA: "Palmeiras", teamB: "Santos" }],
      ["search_players", { nationality: "Brazil" }], ["search_players", { club: "Fluminense" }], ["search_players", { club: "São Paulo", position: "forward" }],
      ["standings", { season: 2019 }], ["search_matches", { competition: "Libertadores", season: 2018 }], ["standings", { season: 2020 }],
      ["competition_stats", { competition: "Brasileirão" }], ["best_records", { venue: "away" }], ["biggest_wins", {}],
      ["search_matches", { team: "Flamengo", opponent: "Corinthians", limit: 1 }], ["get_player", { name: "Gabriel" }],
      ["derbies", { season: 2023 }], ["team_competitions", { team: "Palmeiras" }], ["best_records", { venue: "home" }],
      ["standings", { season: 2018 }], ["team_profile", { team: "Internacional" }], ["brazilian_club_players", {}], ["dataset_info", {}],
    ];
    for (const [n, a] of calls) {
      const t = performance.now();
      const out = h[n](a);
      expect(performance.now() - t).toBeLessThan(2000);
      expect(out.length).toBeGreaterThan(10);
    }
  });
  it("rejects unknown competitions clearly", () => {
    expect(() => h.search_matches({ competition: "Premier League" })).toThrow(/Unknown competition/);
  });
});
