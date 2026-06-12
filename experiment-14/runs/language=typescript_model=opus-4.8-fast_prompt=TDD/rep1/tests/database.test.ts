import { describe, it, expect, beforeEach } from "vitest";
import { SoccerDatabase } from "../src/database.js";
import type { Match, Player } from "../src/types.js";
import { normalizeTeamName, normalizeName, parseDate } from "../src/normalize.js";

function mkMatch(p: Partial<Match> & {
  home: string;
  away: string;
  hg: number;
  ag: number;
}): Match {
  return {
    competition: p.competition ?? "Brasileirão Série A",
    date: p.date ?? parseDate("2020-01-01"),
    season: p.season ?? 2020,
    round: p.round,
    stage: p.stage,
    homeTeam: p.home,
    awayTeam: p.away,
    homeKey: normalizeTeamName(p.home),
    awayKey: normalizeTeamName(p.away),
    homeGoals: p.hg,
    awayGoals: p.ag,
    arena: p.arena,
    source: p.source ?? "test",
    stats: p.stats,
  };
}

function mkPlayer(p: Partial<Player> & { name: string }): Player {
  return {
    id: p.id ?? 1,
    name: p.name,
    nameKey: normalizeName(p.name),
    age: p.age ?? 25,
    nationality: p.nationality ?? "Brazil",
    overall: p.overall ?? 75,
    potential: p.potential ?? 80,
    club: p.club ?? "Flamengo",
    clubKey: normalizeTeamName(p.club ?? "Flamengo"),
    position: p.position ?? "ST",
    jerseyNumber: p.jerseyNumber ?? 9,
    height: p.height ?? "",
    weight: p.weight ?? "",
  };
}

let db: SoccerDatabase;

beforeEach(() => {
  const matches: Match[] = [
    mkMatch({ home: "Flamengo-RJ", away: "Fluminense-RJ", hg: 2, ag: 1, season: 2023, date: parseDate("2023-09-03")!, round: "22" }),
    mkMatch({ home: "Fluminense-RJ", away: "Flamengo-RJ", hg: 1, ag: 0, season: 2023, date: parseDate("2023-05-28")!, round: "8" }),
    mkMatch({ home: "Flamengo-RJ", away: "Palmeiras-SP", hg: 3, ag: 0, season: 2023, date: parseDate("2023-07-01")!, round: "12" }),
    mkMatch({ home: "Palmeiras-SP", away: "Flamengo-RJ", hg: 1, ag: 1, season: 2023, date: parseDate("2023-02-01")!, round: "2" }),
    mkMatch({ home: "Santos-SP", away: "Palmeiras-SP", hg: 0, ag: 4, season: 2023, date: parseDate("2023-03-01")!, competition: "Copa do Brasil" }),
    mkMatch({ home: "Flamengo", away: "Corinthians", hg: 5, ag: 0, season: 2019, date: parseDate("2019-10-27")!, competition: "Copa Libertadores", stage: "final" }),
  ];
  const players: Player[] = [
    mkPlayer({ name: "Neymar Jr", nationality: "Brazil", overall: 92, position: "LW", club: "Paris Saint-Germain" }),
    mkPlayer({ name: "Gabriel Barbosa", nationality: "Brazil", overall: 83, position: "ST", club: "Flamengo" }),
    mkPlayer({ name: "Bruno Henrique", nationality: "Brazil", overall: 80, position: "LW", club: "Flamengo" }),
    mkPlayer({ name: "L. Messi", nationality: "Argentina", overall: 94, position: "RW", club: "FC Barcelona" }),
    mkPlayer({ name: "Dudu", nationality: "Brazil", overall: 79, position: "RM", club: "Palmeiras" }),
  ];
  db = new SoccerDatabase({ matches, players });
});

describe("findMatches", () => {
  it("finds matches between two teams regardless of side or naming", () => {
    const result = db.findMatches({ team: "Flamengo", team2: "Fluminense" });
    expect(result).toHaveLength(2);
  });

  it("sorts results most-recent first", () => {
    const result = db.findMatches({ team: "Flamengo", team2: "Fluminense" });
    expect(result[0].date! >= result[1].date!).toBe(true);
    expect(result[0].round).toBe("22");
  });

  it("finds all matches for a single team across competitions", () => {
    const result = db.findMatches({ team: "Flamengo" });
    expect(result).toHaveLength(5);
  });

  it("filters by season", () => {
    const result = db.findMatches({ team: "Flamengo", season: 2019 });
    expect(result).toHaveLength(1);
    expect(result[0].competition).toBe("Copa Libertadores");
  });

  it("filters by competition (partial name)", () => {
    const result = db.findMatches({ competition: "Libertadores" });
    expect(result).toHaveLength(1);
  });

  it("filters by date range", () => {
    const result = db.findMatches({
      from: parseDate("2023-06-01")!,
      to: parseDate("2023-12-31")!,
    });
    expect(result.every((m) => m.season === 2023)).toBe(true);
    expect(result).toHaveLength(2); // 2023-09-03 and 2023-07-01
  });

  it("filters by home/away side", () => {
    const home = db.findMatches({ homeTeam: "Flamengo" });
    expect(home.every((m) => m.homeKey === "flamengo")).toBe(true);
    expect(home).toHaveLength(3);
  });
});

describe("headToHead", () => {
  it("computes win/draw counts between two teams", () => {
    const h2h = db.headToHead("Flamengo", "Palmeiras");
    expect(h2h.matches).toBe(2);
    expect(h2h.teamAWins).toBe(1); // Flamengo 3-0
    expect(h2h.teamBWins).toBe(0);
    expect(h2h.draws).toBe(1); // 1-1
  });
});

describe("teamRecord", () => {
  it("aggregates wins, draws, losses and goals", () => {
    const rec = db.teamRecord("Flamengo", { season: 2023 });
    // 2023 Flamengo matches: W(2-1), L(0-1 away at Flu), W(3-0), D(1-1)
    expect(rec.matches).toBe(4);
    expect(rec.wins).toBe(2);
    expect(rec.draws).toBe(1);
    expect(rec.losses).toBe(1);
    expect(rec.goalsFor).toBe(6);
    expect(rec.goalsAgainst).toBe(3);
    expect(rec.points).toBe(7);
  });

  it("supports home-only venue filtering", () => {
    const rec = db.teamRecord("Flamengo", { season: 2023, venue: "home" });
    expect(rec.matches).toBe(2); // 2-1 vs Flu, 3-0 vs Palmeiras
    expect(rec.wins).toBe(2);
  });
});

describe("standings", () => {
  it("computes a points table for a competition+season", () => {
    const table = db.standings("Brasileirão Série A", 2023);
    expect(table[0].team).not.toBe("");
    // Flamengo: W,L,W,D => 7 pts; leader should be Flamengo with most points.
    expect(table[0].points).toBeGreaterThanOrEqual(table[table.length - 1].points);
    const fla = table.find((t) => normalizeTeamName(t.team) === "flamengo")!;
    expect(fla.points).toBe(7);
  });
});

describe("statistics", () => {
  it("computes average goals and home win rate over a filter", () => {
    const s = db.statistics({ season: 2023 });
    // 2023 matches: 5 matches. Goals: (2+1)+(1+0)+(3+0)+(1+1)+(0+4)=13 => avg 2.6
    expect(s.totalMatches).toBe(5);
    expect(s.averageGoals).toBeCloseTo(2.6, 5);
    // home wins in 2023: 2-1(yes),1-0(yes),3-0(yes),1-1(no),0-4(no) => 3/5
    expect(s.homeWinRate).toBeCloseTo(0.6, 5);
  });

  it("lists biggest victories by margin", () => {
    const big = db.biggestWins({ limit: 2 });
    expect(big[0].homeGoals === 5 || big[0].awayGoals === 5).toBe(true);
    expect(big).toHaveLength(2);
  });
});

describe("findPlayers", () => {
  it("searches by name substring", () => {
    const res = db.findPlayers({ name: "gabriel" });
    expect(res).toHaveLength(1);
    expect(res[0].name).toBe("Gabriel Barbosa");
  });

  it("filters by nationality and sorts by overall desc", () => {
    const res = db.findPlayers({ nationality: "Brazil" });
    expect(res[0].name).toBe("Neymar Jr");
    expect(res.every((p) => p.nationality === "Brazil")).toBe(true);
  });

  it("filters by club", () => {
    const res = db.findPlayers({ club: "Flamengo" });
    expect(res).toHaveLength(2);
    expect(res[0].overall! >= res[1].overall!).toBe(true);
  });

  it("filters by position and applies limit", () => {
    const res = db.findPlayers({ position: "LW", limit: 1 });
    expect(res).toHaveLength(1);
    expect(res[0].position).toBe("LW");
  });
});

describe("playersByClub", () => {
  it("groups Brazilian players at Brazilian clubs with average rating", () => {
    const groups = db.brazilianPlayersByClub();
    const fla = groups.find((g) => normalizeTeamName(g.club) === "flamengo")!;
    expect(fla.count).toBe(2);
    expect(fla.averageOverall).toBeCloseTo((83 + 80) / 2, 5);
  });
});
