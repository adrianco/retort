import { test } from "node:test";
import assert from "node:assert/strict";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { SoccerData, normalizeTeam, teamMatches } from "../src/data.js";
import {
  findMatches,
  teamStats,
  headToHead,
  standings,
  findPlayers,
  overallStats,
  biggestWins,
} from "../src/queries.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const DATA_DIR = join(__dirname, "..", "data", "kaggle");

const data = new SoccerData();
data.load(DATA_DIR);

test("data loads matches and players", () => {
  assert.ok(data.matches.length > 10000, `expected many matches, got ${data.matches.length}`);
  assert.ok(data.players.length > 1000, `expected many players, got ${data.players.length}`);
});

test("normalizeTeam strips state suffix", () => {
  assert.equal(normalizeTeam("Palmeiras-SP"), "Palmeiras");
  assert.equal(normalizeTeam("Flamengo-RJ"), "Flamengo");
});

test("teamMatches handles accents and case", () => {
  assert.ok(teamMatches("sao paulo", "São Paulo"));
  assert.ok(teamMatches("Gremio", "Grêmio"));
});

test("findMatches finds Flamengo vs Fluminense", () => {
  const matches = findMatches(data, { team: "Flamengo", team2: "Fluminense", limit: 5 });
  assert.ok(matches.length > 0, "expected Fla-Flu matches");
  for (const m of matches) {
    const hasFla = teamMatches("Flamengo", m.homeTeam) || teamMatches("Flamengo", m.awayTeam);
    const hasFlu = teamMatches("Fluminense", m.homeTeam) || teamMatches("Fluminense", m.awayTeam);
    assert.ok(hasFla && hasFlu);
  }
});

test("findMatches filters by season", () => {
  const matches = findMatches(data, { team: "Palmeiras", season: 2019, limit: 100 });
  assert.ok(matches.length > 0);
  for (const m of matches) {
    assert.equal(m.season, 2019);
  }
});

test("teamStats returns sensible numbers for Palmeiras", () => {
  const s = teamStats(data, "Palmeiras");
  assert.ok(s.matches > 100);
  assert.equal(s.matches, s.wins + s.draws + s.losses);
  assert.equal(s.points, s.wins * 3 + s.draws);
});

test("headToHead for two teams", () => {
  const h2h = headToHead(data, "Flamengo", "Corinthians");
  assert.ok(h2h.matches > 0);
  assert.equal(h2h.matches, h2h.team1Wins + h2h.team2Wins + h2h.draws);
});

test("standings compute for a Brasileirão season", () => {
  const table = standings(data, 2019, "Brasileirão");
  assert.ok(table.length >= 10);
  // Points should be monotonically non-increasing
  for (let i = 1; i < table.length; i++) {
    assert.ok(table[i - 1].points >= table[i].points);
  }
});

test("findPlayers by name", () => {
  const results = findPlayers(data, { name: "Neymar", limit: 5 });
  assert.ok(results.length > 0);
  assert.ok(results[0].name.toLowerCase().includes("neymar"));
});

test("findPlayers by nationality Brazil", () => {
  const results = findPlayers(data, { nationality: "Brazil", limit: 20 });
  assert.ok(results.length > 0);
  for (const p of results) {
    assert.ok(p.nationality.toLowerCase().includes("brazil"));
  }
});

test("overallStats returns rates summing to 1", () => {
  const stats = overallStats(data, { competition: "Brasileirão" });
  assert.ok(stats.totalMatches > 0);
  const sum = stats.homeWinRate + stats.awayWinRate + stats.drawRate;
  assert.ok(Math.abs(sum - 1) < 0.001);
});

test("biggestWins sorted by goal diff", () => {
  const wins = biggestWins(data, { limit: 5 });
  assert.equal(wins.length, 5);
  for (let i = 1; i < wins.length; i++) {
    const prev = Math.abs((wins[i - 1].homeGoal ?? 0) - (wins[i - 1].awayGoal ?? 0));
    const cur = Math.abs((wins[i].homeGoal ?? 0) - (wins[i].awayGoal ?? 0));
    assert.ok(prev >= cur);
  }
});
