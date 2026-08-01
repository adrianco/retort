import assert from "node:assert/strict";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { normalizeCompetition, normalizeTeam, SoccerData } from "./soccer-data.js";

const data = new SoccerData(join(dirname(fileURLToPath(import.meta.url)), "../data/kaggle"));

test("loads and exposes all six supplied CSV datasets", () => {
  assert.ok(data.matches.length > 20_000);
  assert.ok(data.players.length > 18_000);
  assert.deepEqual(new Set(data.matches.map((m) => m.source)), new Set(["Brasileirao_Matches.csv", "Brazilian_Cup_Matches.csv", "Libertadores_Matches.csv", "novo_campeonato_brasileiro.csv", "BR-Football-Dataset.csv"]));
});

test("normalizes accents, state suffixes, and full-name aliases", () => {
  assert.equal(normalizeTeam("São Paulo-SP"), normalizeTeam("Sao Paulo FC"));
  assert.equal(normalizeTeam("Sport Club Corinthians Paulista"), normalizeTeam("Corinthians"));
});

test("normalizes the extended dataset's Serie A competition label", () => {
  assert.equal(normalizeCompetition("Serie A"), "Brasileirão");
  const matches = data.findMatches({ team: "Palmeiras", season: 2023, competition: "Brasileirão" });
  assert.ok(matches.length > 0);
  assert.ok(matches.some((match) => match.source === "BR-Football-Dataset.csv"));
});

test("finds team matches and supplies complete match records", () => {
  const matches = data.findMatches({ team: "Flamengo", season: 2023 });
  assert.ok(matches.length > 0);
  assert.ok(matches.every((m) => m.date && Number.isFinite(m.homeGoals) && Number.isFinite(m.awayGoals)));
});

test("calculates a record and a head-to-head comparison", () => {
  const record = data.teamStatistics("Palmeiras", { season: 2023, competition: "Brasileirão" });
  assert.ok(record.matches > 0);
  assert.equal(record.matches, record.wins + record.draws + record.losses);
  const h2h = data.headToHead("Flamengo", "Fluminense");
  assert.equal(h2h.matches.length, h2h.teamAWins + h2h.teamBWins + h2h.draws);
});

test("searches player data and builds points-based standings", () => {
  assert.ok(data.searchPlayers({ nationality: "Brazil", limit: 5 }).length > 0);
  const table = data.standings(2019);
  assert.ok(table.length > 10);
  assert.ok(table[0].points >= table[1].points);
});
