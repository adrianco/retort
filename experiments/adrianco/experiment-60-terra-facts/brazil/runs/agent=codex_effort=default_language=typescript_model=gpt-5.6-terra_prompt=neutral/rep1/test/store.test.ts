import assert from "node:assert/strict";
import test from "node:test";
import { mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { once } from "node:events";
import { spawn } from "node:child_process";
import { SoccerStore } from "../src/store.ts";
import { handle } from "../src/server.ts";

async function fixture(): Promise<SoccerStore> {
  const dir = await mkdtemp(join(tmpdir(), "soccer-mcp-"));
  const write = (name: string, data: string) => writeFile(join(dir, name), data);
  await Promise.all([
    write("Brasileirao_Matches.csv", 'datetime,home_team,home_team_state,away_team,away_team_state,home_goal,away_goal,season,round\n2023-09-03,Flamengo-RJ,RJ,Fluminense-RJ,RJ,2,1,2023,22\n2023-05-28,Fluminense-RJ,RJ,Flamengo-RJ,RJ,1,0,2023,8\n'),
    write("Brazilian_Cup_Matches.csv", 'round,datetime,home_team,away_team,home_goal,away_goal,season\nFinal,2023-09-24,Flamengo,Palmeiras,1,0,2023\n'),
    write("Libertadores_Matches.csv", 'datetime,home_team,away_team,home_goal,away_goal,season,stage\n2023-04-01,Palmeiras,Santos,3,0,2023,group stage\n'),
    write("BR-Football-Dataset.csv", 'tournament,home,home_goal,away_goal,away,date\nCopa do Brasil,Flamengo,2,2,Santos,2023-01-01\n'),
    write("novo_campeonato_brasileiro.csv", 'ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena\n1,29/03/2019,2019,1,Flamengo,Palmeiras,2,0,RJ,SP,Mandante,Maracana\n'),
    write("fifa_data.csv", 'ID,Name,Age,Nationality,Overall,Potential,Club,Position,Jersey Number,Height,Weight\n1,Neymar Jr,27,Brazil,92,93,Paris Saint-Germain,LW,10,5\'9,150lbs\n2,Gabriel Barbosa,22,Brazil,82,85,Flamengo,ST,9,5\'10,170lbs\n'),
  ]);
  return SoccerStore.load(dir);
}

test("normalises state suffixes and returns head-to-head results", async () => { const store = await fixture(); const h2h = store.headToHead("Flamengo", "Fluminense", { season: 2023 }); assert.equal(h2h.matches.length, 2); assert.equal(h2h.teamAWins, 1); assert.equal(h2h.teamBWins, 1); });
test("calculates a home record and computed standings", async () => { const store = await fixture(); const record = store.record("Flamengo", { season: 2023, competition: "Brasileirão", venue: "home" }); assert.deepEqual(record, { team: "Flamengo", matches: 1, wins: 1, draws: 0, losses: 0, goalsFor: 2, goalsAgainst: 1, points: 3, winRate: 100 }); assert.equal(store.standings(2023)[0].team, "Flamengo"); });
test("searches players by accented/case-insensitive filters and respects ratings", async () => { const store = await fixture(); const players = store.searchPlayers({ club: "flamengo", nationality: "brazil" }); assert.equal(players.length, 1); assert.equal(players[0].name, "Gabriel Barbosa"); });
test("exposes MCP initialize, tools, and tool calls", async () => { const store = await fixture(); const initialized = await handle({ jsonrpc: "2.0", id: 1, method: "initialize" }, store) as { capabilities: unknown }; assert.ok(initialized.capabilities); const result = await handle({ jsonrpc: "2.0", id: 2, method: "tools/call", params: { name: "search_matches", arguments: { team: "Flamengo", season: 2023 } } }, store) as { content: { text: string }[] }; assert.equal(JSON.parse(result.content[0].text).length, 3); const standings = await handle({ jsonrpc: "2.0", id: 3, method: "tools/call", params: { name: "standings", arguments: { season: 2019, competition: "Brasileirão" } } }, store) as { content: { text: string }[] }; assert.equal(JSON.parse(standings.content[0].text)[0].team, "Flamengo"); });
test("declares concrete MCP input schemas", async () => { const store = await fixture(); const listed = await handle({ jsonrpc: "2.0", id: 1, method: "tools/list" }, store) as { tools: { name: string; inputSchema: { properties: Record<string, unknown>; required?: string[] } }[] }; const matches = listed.tools.find((tool) => tool.name === "search_matches")!; const standings = listed.tools.find((tool) => tool.name === "standings")!; assert.ok(matches.inputSchema.properties.team); assert.deepEqual(standings.inputSchema.required, ["season"]); });
test("uses a single canonical Brasileirão source and one row per normalized team in standings", async () => {
  const store = new SoccerStore([
    { id: "modern", competition: "Brasileirão", source: "serie-a", season: 2019, homeTeam: "Flamengo-RJ", awayTeam: "Santos-SP", homeGoals: 2, awayGoals: 0 },
    { id: "historic-duplicate", competition: "Brasileirão", source: "historic", season: 2019, homeTeam: "Flamengo", awayTeam: "Santos", homeGoals: 2, awayGoals: 0 },
    { id: "modern-return", competition: "Brasileirão", source: "serie-a", season: 2019, homeTeam: "Santos", awayTeam: "Flamengo", homeGoals: 1, awayGoals: 1 },
  ], []);
  const table = store.standings(2019);
  assert.equal(table.length, 2); assert.deepEqual(table[0], { rank: 1, team: "Flamengo", played: 2, wins: 1, draws: 1, losses: 0, goalsFor: 3, goalsAgainst: 1, points: 4, goalDifference: 2 });
});
test("starts the documented entrypoint and serves MCP requests on stdio", async () => {
  const child = spawn(process.execPath, ["--experimental-strip-types", "src/server.ts"], { cwd: process.cwd(), stdio: ["pipe", "pipe", "pipe"] });
  let output = ""; child.stdout.setEncoding("utf8"); child.stdout.on("data", (chunk) => { output += chunk; });
  child.stdin.write('{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1"}}}\n');
  child.stdin.write('{"jsonrpc":"2.0","id":2,"method":"tools/list"}\n');
  await new Promise((resolve) => setTimeout(resolve, 300)); child.kill(); await once(child, "exit");
  const responses = output.trim().split("\n").map((line) => JSON.parse(line));
  assert.equal(responses[0].result.serverInfo.name, "brazilian-soccer-mcp");
  assert.ok(responses[1].result.tools.some((tool: { name: string }) => tool.name === "standings"));
});
test("loads every supplied dataset into the unified graph", async () => { const store = await fixture(); assert.equal(store.matches.length, 6); assert.equal(store.players.length, 2); assert.equal(store.findMatches({ competition: "Copa do Brasil" }).length, 1); assert.equal(store.findMatches({ competition: "Libertadores" }).length, 1); });
test("filters matches by competition, season and date, and calculates aggregate statistics", async () => {
  const store = await fixture();
  const cupFinal = store.findMatches({ competition: "Copa do Brasil", season: 2023, from: "2023-09-01", to: "2023-10-01" });
  assert.equal(cupFinal.length, 1); assert.equal(cupFinal[0].round, "Final");
  const stats = store.statistics({ competition: "Brasileirão", season: 2023 });
  assert.deepEqual({ matches: stats.matches, totalGoals: stats.totalGoals, averageGoalsPerMatch: stats.averageGoalsPerMatch, homeWins: stats.homeWins, awayWins: stats.awayWins, draws: stats.draws }, { matches: 2, totalGoals: 4, averageGoalsPerMatch: 2, homeWins: 2, awayWins: 0, draws: 0 });
});
