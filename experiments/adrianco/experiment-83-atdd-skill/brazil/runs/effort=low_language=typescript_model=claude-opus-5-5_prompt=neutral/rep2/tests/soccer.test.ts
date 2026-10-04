import { describe, it, expect, beforeAll } from "vitest";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { Dataset, normalizeTeam, parseCsv, parseDate } from "../src/data.js";
import { SoccerService } from "../src/queries.js";
import { runTool, TOOLS } from "../src/tools.js";
import { createServer } from "../src/server.js";

let svc: SoccerService;
beforeAll(() => { svc = new SoccerService(Dataset.load()); });
const ask = (tool: string, args: object = {}) => runTool(svc, tool, args);

describe("parsing & normalization", () => {
  it("parses quoted CSV with BOM and escaped quotes", () => {
    expect(parseCsv('﻿a,b\n"x, y","say ""hi"""\n')).toEqual([{ a: "x, y", b: 'say "hi"' }]);
  });
  it("handles multiple date formats", () => {
    expect(parseDate("29/03/2003")).toBe("2003-03-29");
    expect(parseDate("2012-05-19 18:30:00")).toBe("2012-05-19");
    expect(parseDate("2023-09-24")).toBe("2023-09-24");
  });
  it("normalizes team name variations", () => {
    for (const v of ["Palmeiras-SP", "Palmeiras", "Palmeiras - SP", "Sociedade Esportiva Palmeiras"]) expect(normalizeTeam(v)).toBe("palmeiras");
    expect(normalizeTeam("São Paulo")).toBe(normalizeTeam("Sao Paulo-SP"));
    expect(normalizeTeam("Grêmio")).toBe("gremio");
    expect(normalizeTeam("Sport Club Corinthians Paulista")).toBe("corinthians");
    expect(normalizeTeam("Atletico-MG")).toBe(normalizeTeam("Atletico Mineiro"));
    expect(normalizeTeam("Athletico-PR")).toBe(normalizeTeam("Atletico Paranaense"));
    expect(normalizeTeam("Atletico-GO")).not.toBe(normalizeTeam("Atletico-MG"));
  });
});

describe("data coverage", () => {
  it("loads all 6 CSV files", () => {
    const b = svc.ds.bySource;
    expect(b["Brasileirao_Matches.csv"]).toBeGreaterThan(4000);
    expect(b["Brazilian_Cup_Matches.csv"]).toBeGreaterThan(1300);
    expect(b["Libertadores_Matches.csv"]).toBeGreaterThan(1200);
    expect(b["BR-Football-Dataset.csv"]).toBe(10296);
    expect(b["novo_campeonato_brasileiro.csv"]).toBe(6886);
    expect(b["fifa_data.csv"]).toBe(18207);
  });
  it("keeps UTF-8 accents", () => {
    expect(ask("list_teams", { query: "gremio" })).toContain("Grêmio");
  });
});

describe("sample questions", () => {
  it("1. Show me all Flamengo vs Fluminense matches", () => {
    const out = ask("head_to_head", { teamA: "Flamengo", teamB: "Fluminense" });
    expect(out).toContain("Fla-Flu");
    expect(out).toMatch(/Head-to-head in dataset \(\d+ matches\): Flamengo \d+ wins, Fluminense \d+ wins, \d+ draws/);
  });
  it("2. What matches did Palmeiras play in 2023?", () => {
    const ms = svc.filterMatches({ team: "Palmeiras", season: 2023 });
    expect(ms.length).toBeGreaterThan(30);
    expect(ms.every((m) => m.homeKey === "palmeiras" || m.awayKey === "palmeiras")).toBe(true);
  });
  it("3. Find all Copa Libertadores finals", () => {
    const ms = svc.filterMatches({ competition: "Libertadores", stage: "final" });
    expect(ms.length).toBeGreaterThanOrEqual(10);
    expect(ms.every((m) => m.stage === "final")).toBe(true);
  });
  it("4. Copa do Brasil final round matches", () => {
    expect(ask("search_matches", { competition: "Copa do Brasil", stage: "8" })).toMatch(/Copa do Brasil Round 8/);
  });
  it("5. Corinthians' home record in 2022", () => {
    const r = svc.teamRecord("Corinthians", { venue: "home", season: 2022, competition: "Brasileirão" });
    expect(r.played).toBe(19);
    expect(r.wins + r.draws + r.losses).toBe(19);
    expect(ask("team_record", { team: "Corinthians", venue: "home", season: 2022, competition: "Brasileirão" })).toContain("Win rate:");
  });
  it("6. Who won the 2019 Brasileirão?", () => {
    const rows = svc.standings(2019);
    expect(rows).toHaveLength(20);
    expect(rows[0]).toMatchObject({ team: "Flamengo", points: 90, wins: 28, draws: 6, losses: 4 });
    expect(ask("standings", { season: 2019 })).toMatch(/1\. Flamengo - 90 pts \(28W, 6D, 4L.*Champion/);
  });
  it("7. Historical season from DD/MM/YYYY file: 2005 standings", () => {
    const rows = svc.standings(2005);
    expect(rows[0].team).toBe("Corinthians");
  });
  it("8. Which teams were relegated in 2020?", () => {
    expect(ask("standings", { season: 2020 })).toMatch(/Relegated \(bottom 4\): .*Botafogo/);
  });
  it("9. Which team scored the most goals in Serie A 2022?", () => {
    expect(ask("top_scoring_teams", { season: 2022, competition: "Serie A" })).toMatch(/1\. \S+/);
  });
  it("10. Compare Palmeiras and Santos head-to-head", () => {
    const h = svc.headToHead("Palmeiras", "Santos");
    expect(h.matches.length).toBe(h.aWins + h.bWins + h.draws);
    expect(h.matches.length).toBeGreaterThan(20);
  });
  it("11. When did Flamengo last play Corinthians?", () => {
    const out = ask("last_match", { team: "Flamengo", opponent: "Corinthians" });
    expect(out).toMatch(/Score: \d+-\d+/);
  });
  it("12. Find all Brazilian players / top Brazilian players", () => {
    const r = svc.searchPlayers({ nationality: "Brazil" });
    expect(r.total).toBeGreaterThan(800);
    expect(r.players[0].name).toBe("Neymar Jr");
  });
  it("13. Who are the highest-rated players at Flamengo-like Brazilian clubs (Grêmio)?", () => {
    const r = svc.searchPlayers({ club: "Gremio" });
    expect(r.total).toBeGreaterThan(10);
    expect(r.players.every((p) => p.club === "Grêmio")).toBe(true);
  });
  it("14. Show forwards at a club", () => {
    const r = svc.searchPlayers({ club: "Juventus", position: "forwards" });
    expect(r.total).toBeGreaterThan(0);
    expect(r.players.some((p) => p.name === "Cristiano Ronaldo")).toBe(true);
  });
  it("15. Brazilian players at Brazilian clubs", () => {
    expect(ask("players_by_club", {})).toMatch(/Grêmio: \d+ players \(avg rating: \d+\)/);
  });
  it("16. Who is Neymar?", () => {
    expect(ask("player_details", { name: "neymar" })).toMatch(/Neymar Jr[\s\S]*Paris Saint-Germain[\s\S]*Dribbling/);
  });
  it("17. Average goals per match in the Brasileirão", () => {
    const s = svc.aggregateStats({ competition: "Brasileirão" });
    expect(s.avgGoals).toBeGreaterThan(2);
    expect(s.avgGoals).toBeLessThan(3);
    expect(s.homeWinRate + s.awayWinRate + s.drawRate).toBeCloseTo(1);
  });
  it("18. Which team has the best away record?", () => {
    expect(ask("best_records", { venue: "away", competition: "Brasileirão", minMatches: 50 })).toMatch(/1\. .* win rate/);
  });
  it("19. Biggest wins", () => {
    const ms = svc.biggestWins({}, 5);
    const margins = ms.map((m) => Math.abs(m.homeGoals - m.awayGoals));
    expect(margins).toEqual([...margins].sort((a, b) => b - a));
    expect(margins[0]).toBeGreaterThanOrEqual(7);
  });
  it("20. Derbies in 2023", () => {
    const out = ask("derbies", { season: 2023 });
    expect(out).toContain("Fla-Flu");
    expect(out).toContain("Gre-Nal");
  });
  it("21. What competitions has Palmeiras played in?", () => {
    const c = svc.teamCompetitions("Palmeiras").map((x) => x.competition);
    expect(c).toEqual(expect.arrayContaining(["Brasileirão", "Copa do Brasil", "Libertadores"]));
  });
  it("22. Compare the 2018 and 2019 seasons", () => {
    const out = ask("compare_seasons", { seasons: [2018, 2019] });
    expect(out).toMatch(/2018 Brasileirão: 380 matches.*champion Palmeiras/);
    expect(out).toMatch(/2019 Brasileirão: 380 matches.*champion Flamengo/);
  });
  it("23. Cross-file: team profile combines matches and players", () => {
    const out = ask("team_profile", { team: "Internacional" });
    expect(out).toContain("Competitions:");
    expect(out).toMatch(/FIFA players at club: [1-9]/);
  });
  it("24. Team name variations resolve to the same matches", () => {
    const a = svc.filterMatches({ team: "Palmeiras-SP" }).length;
    expect(svc.filterMatches({ team: "Sociedade Esportiva Palmeiras" }).length).toBe(a);
  });
  it("25. Date range filtering", () => {
    const ms = svc.filterMatches({ team: "Santos", dateFrom: "2015-01-01", dateTo: "2015-12-31" });
    expect(ms.length).toBeGreaterThan(0);
    expect(ms.every((m) => m.date >= "2015-01-01" && m.date <= "2015-12-31")).toBe(true);
  });
});

describe("performance", () => {
  it("answers aggregate queries quickly", () => {
    for (const [n, a] of [["best_records", { venue: "home" }], ["team_profile", { team: "Flamengo" }], ["biggest_wins", {}], ["list_teams", {}]] as const) {
      const t = performance.now();
      ask(n, a);
      expect(performance.now() - t).toBeLessThan(2000);
    }
  });
});

describe("MCP server", () => {
  it("lists and calls tools over the MCP protocol", async () => {
    const server = createServer(svc);
    const client = new Client({ name: "test", version: "1.0.0" });
    const [ct, st] = InMemoryTransport.createLinkedPair();
    await Promise.all([server.connect(st), client.connect(ct)]);
    const { tools } = await client.listTools();
    expect(tools.map((t) => t.name).sort()).toEqual(Object.keys(TOOLS).sort());
    const res = await client.callTool({ name: "standings", arguments: { season: 2019, limit: 3 } });
    expect((res.content as any)[0].text).toContain("Flamengo - 90 pts");
    await client.close();
  });
});
