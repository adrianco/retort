import { describe, expect, it } from "vitest";
import { getKb } from "./helpers.js";

const kb = getKb();

describe("match queries", () => {
  it("finds matches by team and season across competitions", () => {
    const ms = kb.findMatches({ team: "Palmeiras", season: 2019 });
    const comps = new Set(ms.map((m) => m.competition));
    expect(comps).toEqual(new Set(["brasileirao", "copa-do-brasil", "libertadores"]));
    expect(ms.every((m) => m.home === "palmeiras" || m.away === "palmeiras")).toBe(true);
  });

  it("filters by venue, date range and competition", () => {
    const home = kb.findMatches({ team: "Santos", venue: "home", competition: "Brasileirão", season: 2018 });
    expect(home).toHaveLength(19);
    expect(home.every((m) => m.home === "santos")).toBe(true);
    const range = kb.findMatches({ team: "Flamengo", dateFrom: "2019-11-01", dateTo: "2019-11-30" });
    expect(range.length).toBeGreaterThan(0);
    expect(range.every((m) => m.date! >= "2019-11-01" && m.date! <= "2019-11-30")).toBe(true);
    // Flamengo won the 2019 Libertadores final on 23 Nov 2019.
    expect(range.some((m) => m.competition === "libertadores" && m.stage === "final" && m.homeGoals === 2 && m.awayGoals === 1)).toBe(true);
  });

  it("returns results newest first", () => {
    const ms = kb.findMatches({ team: "Corinthians" });
    for (let i = 1; i < ms.length; i++) expect((ms[i - 1].date ?? "") >= (ms[i].date ?? "")).toBe(true);
  });

  it("finds Copa do Brasil finals", () => {
    const finals = kb.cupFinals("Copa do Brasil");
    const bySeason = Object.fromEntries(finals.map((t) => [t.legs[0].season, t]));
    expect(bySeason[2019].winner).toBe("athletico-pr");
    expect(bySeason[2018].winner).toBe("cruzeiro");
    expect(bySeason[2020].winner).toBe("palmeiras");
    expect(bySeason[2023].winner).toBe("sao-paulo");
    expect(finals.every((t) => t.legs.length === 2)).toBe(true);
  });
});

describe("team queries", () => {
  it("head-to-head Flamengo vs Fluminense (Fla-Flu)", () => {
    const h = kb.headToHead("Flamengo", "Fluminense");
    expect(h.rivalry?.name).toBe("Fla-Flu");
    expect(h.matches.length).toBeGreaterThanOrEqual(40);
    expect(h.aWins + h.bWins + h.draws).toBe(h.matches.length);
  });

  it("team record with home filter", () => {
    const r = kb.teamRecord("Corinthians", { season: 2022, venue: "home", competition: "brasileirao" });
    expect(r.overall.matches).toBe(19);
    expect(r.overall.wins + r.overall.draws + r.overall.losses).toBe(19);
    expect(r.away.matches).toBe(0);
  });

  it("handles name variations when resolving teams", () => {
    for (const q of ["Sao Paulo", "São Paulo", "SAO PAULO-SP", "São Paulo FC"]) expect(kb.team(q).key).toBe("sao-paulo");
    expect(kb.team("Atlético Mineiro").key).toBe("atletico-mg");
    expect(kb.team("Fla").key).toBeDefined();
    expect(() => kb.team("Definitely Not A Club")).toThrow();
  });

  it("lists the competitions a team has played in", () => {
    const { competitions } = kb.teamCompetitions("Palmeiras");
    expect([...competitions.keys()].sort()).toEqual(["brasileirao", "copa-do-brasil", "libertadores"]);
  });

  it("ranks the best home records", () => {
    const r = kb.teamRankings({ venue: "home", competition: "brasileirao", metric: "winRate" });
    expect(r.rows.length).toBe(10);
    for (let i = 1; i < r.rows.length; i++) expect(r.rows[i - 1].winRate).toBeGreaterThanOrEqual(r.rows[i].winRate);
    expect(r.rows.every((x) => x.matches >= 19)).toBe(true);
  });
});

describe("competition queries", () => {
  it("calculates the 2019 Brasileirão table", () => {
    const t = kb.standings(2019);
    expect(t.complete).toBe(true);
    expect(t.rows).toHaveLength(20);
    const [first, second, third] = t.rows;
    expect(first).toMatchObject({ name: "Flamengo", points: 90, wins: 28, draws: 6, losses: 4, note: "Champion" });
    expect(second).toMatchObject({ name: "Santos", points: 74, wins: 22, draws: 8, losses: 8 });
    expect(third).toMatchObject({ name: "Palmeiras", points: 74, wins: 21, draws: 11, losses: 6 });
    expect(t.rows.filter((r) => r.note === "Relegated").map((r) => r.name)).toEqual(["Cruzeiro", "CSA", "Chapecoense", "Avaí"]);
  });

  it("knows historical champions and relegations", () => {
    const champions: Record<number, string> = {
      2003: "cruzeiro", 2004: "santos", 2005: "corinthians", 2006: "sao-paulo", 2009: "flamengo", 2010: "fluminense",
      2013: "cruzeiro", 2015: "corinthians", 2016: "palmeiras", 2018: "palmeiras", 2020: "flamengo", 2021: "atletico-mg", 2022: "palmeiras",
    };
    for (const [season, team] of Object.entries(champions)) expect(kb.standings(Number(season)).rows[0].team, season).toBe(team);
    const relegated2020 = kb.standings(2020).rows.filter((r) => r.note === "Relegated").map((r) => r.team);
    expect(relegated2020).toEqual(["vasco", "goias", "coritiba", "botafogo"]);
  });

  it("builds the 2018 Libertadores bracket", () => {
    const b = kb.bracket(2018, "Libertadores");
    expect(b.stages.map((s) => s.stage)).toEqual(["round of 16", "quarterfinals", "semifinals", "final"]);
    const final = b.stages.at(-1)!.ties[0];
    expect(final.winner).toBe("river-plate");
    expect(b.stages[0].ties).toHaveLength(8);
  });

  it("rejects standings for knockout competitions", () => {
    expect(() => kb.standings(2018, "Libertadores")).toThrow(/knockout/);
  });
});

describe("statistics", () => {
  it("computes goals per match and result rates", () => {
    const s = kb.competitionStats({ competition: "brasileirao" }).overall;
    expect(s.matches).toBeGreaterThan(8000);
    expect(s.avgGoals).toBeGreaterThan(2);
    expect(s.avgGoals).toBeLessThan(3);
    expect(s.homeWinRate + s.drawRate + s.awayWinRate).toBeCloseTo(1, 6);
  });

  it("finds the biggest wins sorted by margin", () => {
    const list = kb.biggestWins({ competition: "brasileirao", limit: 10 });
    const margins = list.map((m) => Math.abs(m.homeGoals - m.awayGoals));
    expect(margins[0]).toBeGreaterThanOrEqual(6);
    for (let i = 1; i < margins.length; i++) expect(margins[i - 1]).toBeGreaterThanOrEqual(margins[i]);
  });

  it("compares two seasons", () => {
    const [a, b] = kb.compareSeasons([2018, 2019]);
    expect(a.champion?.name).toBe("Palmeiras");
    expect(b.champion?.name).toBe("Flamengo");
    expect(a.matches).toBe(380);
  });

  it("finds derbies in a season", () => {
    const d = kb.derbies({ season: 2023 });
    expect(d.map((x) => x.rivalry.name)).toContain("Grenal");
    for (const { rivalry, matches } of d) {
      for (const m of matches) expect(new Set([m.home, m.away])).toEqual(new Set(rivalry.teams));
    }
  });
});

describe("player queries", () => {
  it("filters Brazilian players sorted by rating", () => {
    const r = kb.searchPlayers({ nationality: "Brazilian", limit: 3 });
    expect(r.total).toBe(827);
    expect(r.players[0].name).toBe("Neymar Jr");
    expect(r.players.every((p) => p.nationality === "Brazil")).toBe(true);
  });

  it("filters by club and position group", () => {
    const r = kb.searchPlayers({ club: "Grêmio", position: "forwards", limit: 50 });
    expect(r.total).toBeGreaterThan(0);
    expect(r.players.every((p) => p.club === "Grêmio" && ["ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"].includes(p.position))).toBe(true);
    // "Santos" must not match the Mexican club Santos Laguna.
    expect(kb.searchPlayers({ club: "Santos", limit: 100 }).players.every((p) => p.club === "Santos")).toBe(true);
  });

  it("searches by name accent-insensitively", () => {
    expect(kb.searchPlayers({ name: "neymar" }).players[0].name).toBe("Neymar Jr");
    const r = kb.searchPlayers({ name: "Gabriel Jesus" });
    expect(r.players[0].name).toBe("Gabriel Jesus");
  });

  it("falls back to partial matches for unknown names", () => {
    const r = kb.searchPlayers({ name: "Gabriel Barbosa" });
    expect(r.fuzzy).toBe(true);
    expect(r.players.length).toBeGreaterThan(0);
  });

  it("links players at Brazilian clubs to match-data teams", () => {
    const groups = kb.playersByClub({ nationality: "Brazil", brazilianClubsOnly: true });
    expect(groups.length).toBeGreaterThanOrEqual(15);
    expect(groups.every((g) => g.clubKey && kb.data.teams.has(g.clubKey))).toBe(true);
    const profile = kb.teamProfile("Gremio");
    expect(profile.squad.length).toBe(20);
    expect(profile.record.overall.matches).toBeGreaterThan(500);
  });
});
