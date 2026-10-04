import { test } from "node:test";
import assert from "node:assert/strict";
import { getDataset } from "../src/data.js";
import { parseCsv } from "../src/csv.js";
import { parseDate, teamKey, displayName } from "../src/normalize.js";
import * as q from "../src/queries.js";

const ds = getDataset();

test("csv parser handles quotes, commas and BOM", () => {
  const rows = parseCsv('﻿a,b\n"x, y","he said ""hi"""\n1,2\n');
  assert.deepEqual(rows, [{ a: "x, y", b: 'he said "hi"' }, { a: "1", b: "2" }]);
});

test("team name normalization", () => {
  assert.equal(teamKey("Palmeiras-SP"), "palmeiras");
  assert.equal(teamKey("América - MG"), "america mg");
  assert.equal(teamKey("Grêmio"), teamKey("Gremio"));
  assert.equal(teamKey("Sao Paulo"), teamKey("São Paulo-SP"));
  assert.equal(teamKey("Athletico Paranaense"), teamKey("Athletico-PR"));
  assert.equal(teamKey("Atletico Mineiro"), teamKey("Atlético-MG"));
  assert.equal(teamKey("Vasco da Gama"), teamKey("Vasco"));
  assert.equal(teamKey("Sport Club Corinthians Paulista"), "corinthians");
  assert.notEqual(teamKey("Botafogo-RJ"), teamKey("Botafogo-SP"));
  assert.equal(displayName("Flamengo-RJ"), "Flamengo");
});

test("date formats", () => {
  assert.equal(parseDate("29/03/2003"), "2003-03-29");
  assert.equal(parseDate("2012-05-19 18:30:00"), "2012-05-19");
  assert.equal(parseDate("2023-09-24"), "2023-09-24");
});

test("all six files load", () => {
  for (const f of ["Brasileirao_Matches.csv", "novo_campeonato_brasileiro.csv", "Brazilian_Cup_Matches.csv", "Libertadores_Matches.csv", "BR-Football-Dataset.csv", "fifa_data.csv"])
    assert.ok(ds.bySource[f] > 1000, f);
  assert.equal(ds.players.length, 18207);
});

test("UTF-8 accents preserved", () => {
  assert.ok(ds.matches.some((m) => m.home === "Grêmio"));
  assert.ok(ds.players.some((p) => p.club === "Atlético Mineiro"));
});

// ---- 20+ sample questions ----
test("Q1 Flamengo vs Fluminense matches + h2h", () => {
  const out = q.headToHead(ds, "Flamengo", "Fluminense");
  assert.match(out, /Flamengo \d+ wins, Fluminense \d+ wins, \d+ draws/);
  const h = q.headToHeadData(ds, "Flamengo", "Fluminense");
  assert.equal(h.aWins + h.bWins + h.draws, h.matches.length);
  assert.ok(h.matches.length > 30);
});

test("Q2 Palmeiras matches in 2022 across competitions", () => {
  const ms = q.filterMatches(ds, { team: "Palmeiras", season: 2022 });
  assert.ok(ms.length >= 38);
  assert.ok(new Set(ms.map((m) => m.competition)).size >= 2);
});

test("Q3 Copa do Brasil finals", () => {
  const ms = q.filterMatches(ds, { competition: "Copa do Brasil", stage: "final" });
  assert.ok(ms.some((m) => m.season === 2019 && /Athletico/.test(m.home + m.away)));
});

test("Q4 Corinthians home record 2022", () => {
  const out = q.teamRecord(ds, "Corinthians", { season: 2022, competition: "Brasileirão", venue: "home" });
  assert.match(out, /Corinthians home record \(2022 Brasileirão\)/);
  assert.match(out, /Win rate: \d+\.\d%/);
});

test("Q5 most goals in a Serie A season", () => {
  assert.match(q.rankTeams(ds, { competition: "Serie A", season: 2019, sortBy: "goalsFor", limit: 1 }), /1\. Flamengo/);
});

test("Q6 Palmeiras vs Santos h2h", () => {
  assert.ok(q.headToHeadData(ds, "Palmeiras", "Santos").matches.length > 20);
});

test("Q7 Brazilian players", () => {
  const ps = q.filterPlayers(ds, { nationality: "Brazil" });
  assert.ok(ps.length > 500);
  assert.equal(ps[0].name, "Neymar Jr");
});

test("Q8 highest-rated players at a Brazilian club", () => {
  const ps = q.filterPlayers(ds, { club: "Cruzeiro" });
  assert.ok(ps.length > 10 && ps.every((p) => p.club === "Cruzeiro"));
});

test("Q9 forwards at Santos (not Santos Laguna)", () => {
  const ps = q.filterPlayers(ds, { club: "Santos", position: "forward" });
  assert.ok(ps.length > 0 && ps.every((p) => p.club === "Santos"));
});

test("Q10 who won 2019 Brasileirão", () => {
  assert.match(q.champion(ds, 2019), /^Flamengo won the 2019 Brasileirão with 90 points/);
  const t = q.standingsData(ds, 2019);
  assert.equal(t.length, 20);
  assert.deepEqual([t[0].wins, t[0].draws, t[0].losses], [28, 6, 4]);
});

test("Q11 2018 Libertadores knockout matches", () => {
  const ms = q.filterMatches(ds, { competition: "Libertadores", season: 2018, stage: "final" });
  assert.ok(ms.length >= 1);
});

test("Q12 relegated in 2020", () => {
  const out = q.relegated(ds, 2020);
  for (const t of ["Vasco", "Goi", "Coritiba", "Botafogo"]) assert.match(out, new RegExp(t));
});

test("Q13 average goals per match", () => {
  assert.match(q.competitionStats(ds, "Brasileirão"), /Average goals per match: 2\.\d\d/);
});

test("Q14 best away record", () => {
  assert.match(q.rankTeams(ds, { competition: "Brasileirão", venue: "away" }), /1\. .* win rate/);
});

test("Q15 biggest wins", () => {
  const out = q.biggestWins(ds, {}, 5);
  assert.match(out, /margin 8/);
  assert.equal((out.match(/9-1 4 de Julho/g) ?? []).length, 1, "duplicates across files are removed");
});

test("Q16 last Flamengo vs Corinthians match", () => {
  const [m] = q.filterMatches(ds, { team: "Flamengo", opponent: "Corinthians" });
  assert.ok(m.date >= "2023-01-01");
});

test("Q17 who is Neymar (player lookup)", () => {
  assert.match(q.playerDetails(ds, "Neymar"), /Neymar Jr .*\n- Age: 26, Nationality: Brazil/);
  assert.match(q.playerDetails(ds, "Gabriel Barbosa"), /Closest matches/);
});

test("Q18 derbies in 2023", () => {
  assert.match(q.derbies(ds, { season: 2023 }), /Fla-Flu .* - \d+ matches/);
});

test("Q19 competitions Palmeiras played", () => {
  const out = q.teamCompetitions(ds, "Palmeiras");
  for (const c of ["Brasileirão", "Copa do Brasil", "Libertadores"]) assert.ok(out.includes(c));
});

test("Q20 best home record", () => {
  assert.match(q.rankTeams(ds, { venue: "home", limit: 3 }), /Teams ranked by winRate \(home/);
});

test("Q21 compare 2018 and 2019 seasons", () => {
  const out = q.compareSeasons(ds, [2018, 2019]);
  assert.match(out, /Palmeiras \(80 pts\)/);
  assert.match(out, /Flamengo \(90 pts\)/);
});

test("Q22 cross-file team profile (matches + players)", () => {
  const out = q.teamProfile(ds, "Grêmio");
  assert.match(out, /record/);
  assert.match(out, /FIFA squad \(\d+ players/);
});

test("Q23 Brazilian players at Brazilian clubs", () => {
  assert.match(q.brazilianClubsSummary(ds), /Cruzeiro: \d+ players \(avg rating: \d+/);
});

test("Q24 date range search", () => {
  const ms = q.filterMatches(ds, { dateFrom: "2019-12-01", dateTo: "2019-12-31", competition: "Brasileirão" });
  assert.ok(ms.length > 0 && ms.every((m) => m.date.startsWith("2019-12")));
});

test("performance: aggregate queries are fast", () => {
  const t = Date.now();
  q.rankTeams(ds, { venue: "away" });
  q.standings(ds, 2015);
  q.biggestWins(ds);
  q.searchPlayers(ds, { nationality: "Brazil" });
  assert.ok(Date.now() - t < 2000);
});

test("unknown competition gives an error", () => {
  assert.throws(() => q.parseCompetition("Premier League"));
});
