import { test } from "node:test";
import assert from "node:assert/strict";
import { Dataset, normalizeTeam, parseDate } from "../src/data.js";
import { findMatches, teamStats, headToHead, standings, findPlayers, globalStats, biggestWins, } from "../src/queries.js";
import { parseCSV } from "../src/csv.js";
let ds;
function load() {
    if (!ds)
        ds = Dataset.load();
    return ds;
}
test("parseCSV handles quoted fields and BOM", () => {
    const rows = parseCSV('\uFEFFa,b,c\n1,"hello, world",3\n');
    assert.equal(rows.length, 1);
    assert.equal(rows[0].b, "hello, world");
});
test("normalizeTeam strips state suffix and country code", () => {
    assert.equal(normalizeTeam("Palmeiras-SP"), "palmeiras");
    assert.equal(normalizeTeam("Nacional (URU)"), "nacional");
    assert.equal(normalizeTeam("Flamengo"), "flamengo");
});
test("parseDate handles ISO and Brazilian formats", () => {
    assert.equal(parseDate("2023-09-03"), "2023-09-03");
    assert.equal(parseDate("2012-05-19 18:30:00"), "2012-05-19");
    assert.equal(parseDate("29/03/2003"), "2003-03-29");
    assert.equal(parseDate(""), null);
});
test("dataset loads matches and players", () => {
    const d = load();
    assert.ok(d.matches.length > 10000, `matches=${d.matches.length}`);
    assert.ok(d.players.length > 10000, `players=${d.players.length}`);
});
test("find_matches filters by team pair", () => {
    const d = load();
    const res = findMatches(d, { teamA: "Flamengo", teamB: "Fluminense" });
    assert.ok(res.length > 0);
    for (const m of res) {
        const h = normalizeTeam(m.homeTeam);
        const a = normalizeTeam(m.awayTeam);
        assert.ok((h === "flamengo" && a === "fluminense") || (h === "fluminense" && a === "flamengo"));
    }
});
test("find_matches filters by team and season", () => {
    const d = load();
    const res = findMatches(d, { team: "Palmeiras", season: 2019 });
    assert.ok(res.length > 0);
    for (const m of res) {
        assert.equal(m.season, 2019);
        const involved = normalizeTeam(m.homeTeam) === "palmeiras" || normalizeTeam(m.awayTeam) === "palmeiras";
        assert.ok(involved);
    }
});
test("team_stats computes wins/draws/losses correctly", () => {
    const d = load();
    const s = teamStats(d, "Flamengo", { season: 2019, competition: "Brasileirão" });
    assert.ok(s.matches > 0);
    assert.equal(s.matches, s.wins + s.draws + s.losses);
});
test("head_to_head returns totals", () => {
    const d = load();
    const h = headToHead(d, "Palmeiras", "Santos");
    assert.ok(h.matches > 0);
    assert.equal(h.matches, h.teamAWins + h.teamBWins + h.draws);
});
test("standings: Flamengo wins 2019 Brasileirão", () => {
    const d = load();
    const table = standings(d, 2019, "Brasileirão");
    assert.ok(table.length >= 18);
    assert.equal(normalizeTeam(table[0].team), "flamengo");
});
test("find_players: top Brazilians are highly rated", () => {
    const d = load();
    const top = findPlayers(d, { nationality: "Brazil", limit: 5 });
    assert.equal(top.length, 5);
    assert.ok((top[0].overall ?? 0) >= 85);
});
test("find_players: search by name", () => {
    const d = load();
    const r = findPlayers(d, { name: "Neymar", limit: 3 });
    assert.ok(r.length > 0);
    assert.ok(r[0].name.toLowerCase().includes("neymar"));
});
test("global_stats: avg goals reasonable", () => {
    const d = load();
    const s = globalStats(d, { competition: "Brasileirão" });
    assert.ok(s.totalMatches > 0);
    assert.ok(s.avgGoalsPerMatch > 1 && s.avgGoalsPerMatch < 5);
    assert.ok(Math.abs(s.homeWinRate + s.awayWinRate + s.drawRate - 1) < 1e-9);
});
test("biggest_wins returns sorted by goal diff", () => {
    const d = load();
    const bw = biggestWins(d, { limit: 5 });
    assert.equal(bw.length, 5);
    const diffs = bw.map((m) => Math.abs(m.homeGoal - m.awayGoal));
    for (let i = 1; i < diffs.length; i++)
        assert.ok(diffs[i - 1] >= diffs[i]);
});
