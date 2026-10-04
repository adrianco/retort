/**
 * The specification asks that at least 20 sample questions can be answered.
 * Each test maps a natural-language question to the MCP tool call an LLM
 * would make and checks the answer against known facts.
 */
import { describe, expect, it } from "vitest";
import { ask, queries } from "./helpers.js";

describe("match queries", () => {
  it('Q1 "Show me all Flamengo vs Fluminense matches"', () => {
    const out = ask("search_matches", { team: "Flamengo", opponent: "Fluminense", limit: 100 });
    expect(out).toMatch(/^Flamengo vs Fluminense/);
    expect(out).toMatch(/Head-to-head in dataset: Flamengo \d+ wins, Fluminense \d+ wins, \d+ draws/);
    expect(out).toContain("2023-11-11: Flamengo 1-1 Fluminense (Brasileirão Série A 2023)");
    const res = queries().searchMatches({ team: "Flamengo", opponent: "Fluminense" }, { limit: 1000 });
    expect(res.total).toBeGreaterThan(30);
    expect(res.matches.every((m) => [m.homeId, m.awayId].sort().join() === "flamengo,fluminense")).toBe(true);
  });

  it('Q2 "What matches did Palmeiras play in 2023?"', () => {
    const res = queries().searchMatches({ team: "Palmeiras", season: 2023 }, { limit: 100 });
    expect(res.total).toBeGreaterThanOrEqual(38);
    const comps = new Set(res.matches.map((m) => m.competition));
    expect(comps.has("serie-a")).toBe(true);
    expect(comps.has("copa-do-brasil")).toBe(true);
    expect(ask("search_matches", { team: "Palmeiras", season: 2023 })).toMatch(/Palmeiras — 2023: \d+ match\(es\) found/);
  });

  it('Q3 "Find all Copa do Brasil finals"', () => {
    const out = ask("cup_finals", { competition: "Copa do Brasil" });
    expect(out).toContain("2013: Athletico Paranaense vs Flamengo (agg 1-3) -> Flamengo won");
    expect(out).toContain("2019: Athletico Paranaense vs Internacional (agg 3-1) -> Athletico Paranaense won");
    expect(out).toContain("2023: Flamengo vs São Paulo (agg 1-2) -> São Paulo won");
    // stage filter on match search works too
    expect(ask("search_matches", { competition: "copa do brasil", stage: "final", season: 2018 })).toContain(
      "Corinthians 1-2 Cruzeiro (Copa do Brasil Final)",
    );
  });

  it('Q4 "When did Flamengo last play Corinthians?" / "What was the score?"', () => {
    const out = ask("search_matches", { team: "Flamengo", opponent: "Corinthians", limit: 1 });
    const res = queries().searchMatches({ team: "Flamengo", opponent: "Corinthians" }, { limit: 1 });
    const last = res.matches[0];
    expect(last.date >= "2023-01-01").toBe(true);
    expect(out).toContain(`${last.date}: `);
    expect(out).toMatch(/\d+-\d+/);
  });

  it("Q5 filters matches by date range across formats", () => {
    const res = queries().searchMatches({ team: "Grêmio", dateFrom: "01/05/2017", dateTo: "2017-05-31" }, { limit: 50 });
    expect(res.total).toBeGreaterThan(0);
    expect(res.matches.every((m) => m.date >= "2017-05-01" && m.date <= "2017-05-31")).toBe(true);
  });

  it("Q6 filters by venue (home/away)", () => {
    const home = queries().searchMatches({ team: "Santos", venue: "home", season: 2019, competition: "serie-a" });
    const away = queries().searchMatches({ team: "Santos", venue: "away", season: 2019, competition: "serie-a" });
    expect(home.total).toBe(19);
    expect(away.total).toBe(19);
    expect(home.matches.every((m) => m.homeId === "santos")).toBe(true);
  });
});

describe("team queries", () => {
  it(`Q7 "What is Corinthians' home record in 2022?"`, () => {
    const out = ask("team_record", { team: "Corinthians", venue: "home", season: 2022, competition: "Brasileirão" });
    expect(out).toContain("Corinthians home record (Brasileirão Série A, 2022):");
    expect(out).toContain("- Matches: 19");
    expect(out).toMatch(/- Wins: \d+, Draws: \d+, Losses: \d+/);
    expect(out).toMatch(/- Win rate: \d+\.\d%/);
  });

  it('Q8 "Which team scored the most goals in Serie A 2023?"', () => {
    const r = queries().teamRankings("goals_for", { competition: "serie-a", season: 2023 });
    expect(r.rows[0].team).toBe("Grêmio");
    expect(r.rows[0].value).toBe(63);
    expect(ask("team_rankings", { metric: "goals_for", competition: "Serie A", season: 2023, limit: 3 })).toContain(
      "1. Grêmio - Goals scored: 63",
    );
  });

  it('Q9 "Compare Palmeiras and Santos head-to-head"', () => {
    const h = queries().headToHead("Palmeiras", "Santos");
    expect(h.total).toBe(h.winsA + h.winsB + h.draws);
    expect(h.total).toBeGreaterThan(30);
    expect(ask("head_to_head", { team_a: "Palmeiras", team_b: "Santos" })).toMatch(
      /Head-to-head in dataset \(\d+ matches\): Palmeiras \d+ wins, Santos \d+ wins, \d+ draws/,
    );
  });

  it('Q10 "What competitions has Palmeiras played in?"', () => {
    const out = ask("team_profile", { team: "Palmeiras" });
    expect(out).toContain("Brasileirão Série A");
    expect(out).toContain("Copa do Brasil");
    expect(out).toContain("Copa Libertadores");
  });

  it("Q11 handles team name variations consistently", () => {
    const a = queries().teamRecord("Sao Paulo", { season: 2019, competition: "serie-a" }).record;
    const b = queries().teamRecord("São Paulo-SP", { season: 2019, competition: "serie-a" }).record;
    const c = queries().teamRecord("sao paulo fc", { season: 2019, competition: "serie-a" }).record;
    expect(a).toEqual(b);
    expect(a).toEqual(c);
    expect(a.played).toBe(38);
  });
});

describe("player queries", () => {
  it('Q12 "Find all Brazilian players in the dataset" / "Who are the top Brazilian players?"', () => {
    const res = queries().searchPlayers({ nationality: "Brazil", limit: 5 });
    expect(res.total).toBe(827);
    expect(res.players[0].name).toBe("Neymar Jr");
    expect(res.players.map((p) => p.name)).toEqual(expect.arrayContaining(["Casemiro", "Coutinho", "Marcelo"]));
    expect(ask("search_players", { nationality: "Brazilian", limit: 3 })).toContain(
      "1. Neymar Jr - Overall: 92, Potential: 93, Position: LW",
    );
  });

  it('Q13 "Who is Neymar?" — player lookup by name', () => {
    const out = ask("get_player", { name: "neymar" });
    expect(out).toContain("Neymar Jr (FIFA ID 190871)");
    expect(out).toContain("Club: Paris Saint-Germain");
  });

  it('Q14 "Who is Gabriel Barbosa?" — not in FIFA 19, suggests similar players', () => {
    const out = ask("get_player", { name: "Gabriel Barbosa" });
    expect(out).toContain('No player named "Gabriel Barbosa"');
    expect(out).toContain("Gabriel Jesus");
  });

  it('Q15 "Which players play for Flamengo?" — explains club is not in FIFA data', () => {
    const out = ask("search_players", { club: "Flamengo" });
    expect(out).toContain("0 found");
    expect(out).toMatch(/Flamengo is not licensed in the FIFA 19 player file/);
  });

  it('Q16 "Who are the highest-rated players at Grêmio?" and "forwards from Santos"', () => {
    const top = queries().searchPlayers({ club: "Gremio", limit: 3 }).players;
    expect(top).toHaveLength(3);
    expect(top.every((p) => p.club === "Grêmio")).toBe(true);
    expect(top[0].overall! >= top[1].overall!).toBe(true);
    const fwd = queries().searchPlayers({ club: "Santos", position: "forward", limit: 50 }).players;
    expect(fwd.length).toBeGreaterThan(0);
    expect(fwd.every((p) => p.club === "Santos" && ["ST", "LS", "RS", "CF", "LF", "RF", "LW", "RW"].includes(p.position))).toBe(true);
  });

  it("Q17 Brazilian players at Brazilian clubs, grouped by club", () => {
    const out = ask("club_player_summary", { nationality: "Brazil", brazilian_clubs_only: true });
    expect(out).toMatch(/Brazil players at Brazilian clubs: 300 players across 15 clubs/);
    expect(out).toMatch(/- Grêmio: 20 players \(avg rating: \d+\.\d/);
  });
});

describe("competition queries", () => {
  it('Q18 "Who won the 2019 Brasileirão?"', () => {
    const out = ask("standings", { season: 2019, top: 3 });
    expect(out).toContain("1. Flamengo - 90 pts (28W, 6D, 4L)");
    expect(out).toContain("Champion");
    expect(out).toContain("2. Santos - 74 pts (22W, 8D, 8L)");
    expect(out).toContain("3. Palmeiras - 74 pts (21W, 11D, 6L)");
  });

  it('Q19 "Which teams were relegated in 2020?"', () => {
    const st = queries().standings("serie-a", 2020);
    expect(st.rows.slice(-4).map((r) => r.team).sort()).toEqual(["Botafogo", "Coritiba", "Goiás", "Vasco da Gama"]);
    expect(ask("standings", { season: 2020 })).toMatch(/Relegated \(bottom 4\): .*Botafogo/);
  });

  it('Q20 "Show the 2018 Copa Libertadores bracket"', () => {
    const out = ask("cup_bracket", { competition: "Libertadores", season: 2018 });
    expect(out).toContain("ROUND OF 16 (8 ties)");
    expect(out).toContain("QUARTERFINALS (4 ties)");
    expect(out).toContain("SEMIFINALS (2 ties)");
    expect(out).toContain("Boca Juniors vs River Plate (agg 3-5) -> River Plate won");
    expect(out).toContain("Champion: River Plate");
    // Away-goals exit inferred from who reached the next round
    expect(out).toMatch(/River Plate vs Grêmio \(agg 2-2\) -> River Plate advanced/);
  });

  it("Q21 historical champions from the 2003-2019 file and the 2023 season from BR-Football", () => {
    expect(queries().standings("serie-a", 2003).rows[0].team).toBe("Cruzeiro");
    expect(queries().standings("serie-a", 2010).rows[0].team).toBe("Fluminense");
    // 2023 comes only from BR-Football-Dataset.csv, which lacks 3 matches:
    // the table is flagged incomplete but the title race is still visible.
    const st2023 = queries().standings("serie-a", 2023);
    expect(st2023.complete).toBe(false);
    expect(st2023.rows.slice(0, 2).map((r) => r.team)).toContain("Palmeiras");
    expect(ask("standings", { season: 2023 })).toContain("may be incomplete");
    expect(queries().standings("serie-b", 2022).rows.slice(0, 4).map((r) => r.team)).toContain("Grêmio");
  });
});

describe("statistical analysis", () => {
  it(`Q22 "What's the average goals per match in the Brasileirão?"`, () => {
    const s = queries().matchStats({ competition: "Brasileirão" });
    expect(s.avgGoals).toBeGreaterThan(2.2);
    expect(s.avgGoals).toBeLessThan(2.8);
    const out = ask("match_statistics", { competition: "Brasileirão" });
    expect(out).toMatch(/Average goals per match: \d\.\d\d/);
    expect(out).toMatch(/Home win rate: \d+\.\d%/);
  });

  it('Q23 "Which team has the best away record?" / "best home record"', () => {
    const away = queries().teamRankings("away_win_rate", { competition: "serie-a" });
    const home = queries().teamRankings("home_win_rate", { competition: "serie-a" });
    expect(away.rows.length).toBeGreaterThan(0);
    expect(away.rows[0].record.played).toBeGreaterThanOrEqual(away.minMatches);
    for (let i = 1; i < away.rows.length; i++) expect(away.rows[i - 1].value).toBeGreaterThanOrEqual(away.rows[i].value);
    expect(home.rows[0].value).toBeGreaterThan(away.rows[0].value);
    expect(ask("team_rankings", { metric: "home_win_rate", competition: "serie-a" })).toMatch(/^Teams ranked by home win rate/);
  });

  it('Q24 "Show me the biggest wins in the dataset"', () => {
    const wins = queries().biggestWins({}, 5);
    const margins = wins.map((m) => Math.abs(m.homeGoals - m.awayGoals));
    expect(margins[0]).toBeGreaterThanOrEqual(7);
    expect([...margins].sort((a, b) => b - a)).toEqual(margins);
    expect(ask("biggest_wins", { competition: "libertadores", limit: 3 })).toMatch(/1\. \d{4}-\d{2}-\d{2}: .* 8-0 /);
  });

  it('Q25 "Compare the 2018 and 2019 seasons"', () => {
    const out = ask("compare_seasons", { seasons: [2018, 2019] });
    expect(out).toContain("Champion: Palmeiras (80 pts");
    expect(out).toContain("Champion: Flamengo (90 pts");
    expect(out).toMatch(/2018:\n- Matches: 380/);
  });

  it('Q26 "Show me all derbies in 2023"', () => {
    const d = queries().derbies({ season: 2023 }, 100);
    expect(d.total).toBeGreaterThan(10);
    const names = new Set(d.matches.map((x) => x.derby));
    expect(names.has("Fla-Flu")).toBe(true);
    expect(names.has("Grenal")).toBe(true);
    expect(d.matches.every((x) => x.match.season === 2023)).toBe(true);
    expect(ask("derbies", { season: 2023, limit: 3 })).toMatch(/\[[^\]]+\] 2023-\d\d-\d\d: /);
  });

  it("Q27 cross-file: team profile combines match data with FIFA squad", () => {
    const out = ask("team_profile", { team: "Gremio" });
    expect(out).toContain("Copa Libertadores");
    expect(out).toMatch(/FIFA 19 squad: 20 players \(avg overall \d+\.\d\)/);
  });
});
