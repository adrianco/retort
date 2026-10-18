import test from "node:test";
import assert from "node:assert/strict";
import { resolve } from "node:path";
import { SoccerData, isoDate, matchesName, parseCsv } from "../src/data.js";
import { SoccerService } from "../src/service.js";

const service = new SoccerService(new SoccerData(resolve(process.cwd(), "data/kaggle")));
test("Given quoted CSV fields, when parsed, then embedded commas remain in the field", () => { const row=parseCsv('a,b\n"one,two",three\n')[0]; assert.equal(row.a,"one,two"); assert.equal(row.b,"three"); });
test("Given Brazilian names and dates, when normalized, then variations match", () => { assert.equal(matchesName("Palmeiras-SP", "palmeiras"), true); assert.equal(matchesName("São Paulo", "sao paulo"), true); assert.equal(isoDate("29/03/2003"), "2003-03-29"); });
test("Given supplied datasets, when loaded, then every file contributes queryable data", () => { assert.ok(service.data.matches.length > 20000); assert.deepEqual(new Set(service.data.matches.map(m=>m.source)), new Set(["brasileirao","brazilian-cup","libertadores","extended","historical"])); assert.ok(service.data.players.length > 18000); });
test("Given match data, when searching Flamengo and Fluminense, then each result includes date, score and competition", () => { const found=service.findMatches({team:"Flamengo",opponent:"Fluminense"}); assert.ok(found.count > 0); assert.ok(found.matches.every(m=>m.date && m.score && m.competition)); });
test("Given 2023 matches, when calculating Palmeiras home record, then record totals are coherent", () => { const s=service.teamStats("Palmeiras",{season:2023,venue:"home"}); assert.ok(s.matches > 0); assert.equal(s.matches,s.wins+s.draws+s.losses); assert.ok(s.goalsFor >= 0); });
test("Given FIFA player data, when filtering Brazilian players, then nationality and rating ordering are returned", () => { const found=service.players({nationality:"Brazil",limit:10}); assert.ok(found.count > 0); assert.ok(found.players.every(p=>matchesName(p.nationality,"Brazil"))); assert.ok((found.players[0].overall ?? 0)>=(found.players.at(-1)?.overall ?? 0)); });
test("Given a season, when calculating standings, then points and positions are ordered", () => { const table=service.standings("Brasileirão",2019); assert.ok(table.length > 10); assert.equal(table[0].position,1); assert.ok(table[0].points>=table[1].points); });
test("Given overlapping league datasets, when calculating the 2019 Serie A table, then each fixture is counted once", () => {
  const table = service.standings("Brasileirão", 2019);
  const flamengo = table.find((row) => matchesName(row.team, "Flamengo"));
  assert.equal(table.length, 20);
  assert.deepEqual(flamengo && { position: flamengo.position, played: flamengo.played, points: flamengo.points }, { position: 1, played: 38, points: 90 });
  assert.ok(table.every((row) => row.played === 38));
});
