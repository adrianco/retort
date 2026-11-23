import { test } from "node:test";
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { Graph, club, files } from "./data.js";
import { query } from "./queries.js";

const graph = new Graph("data/kaggle");
function search(name: string, args: Record<string, unknown>) {
  const page = query(graph, name, args);
  assert.ok("results" in page);
  return page;
}
test("Given the supplied CSVs, each original match and FIFA player is queryable", () => {
  const counts = [4180, 6886, 1337, 1255, 10296];
  files.forEach((source, i) => {
    const page = search("matches", { source, limit: 1 });
    assert.equal(page.total, counts[i]);
    assert.ok("details" in page.results[0]);
  });
  assert.equal(search("players", {}).total, 18207);
});
test("Given overlapping league sources, the 2019 table counts each fixture once", () => {
  const table = search("records", { competition: "Brasileirão", season: 2019 });
  assert.equal(table.total, 20);
  const winner = table.results[0];
  assert.ok("points" in winner);
  assert.deepEqual(
    [winner.team, winner.points, winner.wins, winner.draws, winner.losses],
    ["flamengo", 90, 28, 6, 4],
  );
  assert.ok(
    table.results.every((row) => "matches" in row && row.matches === 38),
  );
});
test("When a derby is queried in either direction, dates, results and records agree", () => {
  const filters = {
    team: "Flamengo-RJ",
    opponent: "Fluminense",
    season: 2019,
    competition: "Serie A",
    derby: true,
  };
  const fixtures = search("matches", filters);
  assert.equal(fixtures.total, 2);
  const first = fixtures.results[0];
  assert.ok(
    "date" in first &&
      first.date &&
      first.homeGoals !== null &&
      first.awayGoals !== null,
  );
  const row = search("records", filters).results[0];
  assert.ok(
    "matches" in row &&
      row.matches === 2 &&
      Number(row.wins) + Number(row.draws) + Number(row.losses) === 2,
  );
  const home = search("matches", { ...filters, venue: "home" });
  assert.equal(home.total, 1);
  assert.equal(search("matches", { ...filters, from: "01/01/2020" }).total, 0);
});
test("When club spelling varies, a player club links to corresponding match records", () => {
  assert.equal(
    club("Sport Club Corinthians Paulista"),
    club("Corinthians - SP"),
  );
  assert.equal(club("São Paulo FC"), club("Sao Paulo-SP"));
  assert.notEqual(club("Atlético-MG"), club("Atlético-PR"));
  const players = search("players", {
    club: "Grêmio",
    nationality: "Brazilian",
    details: true,
  });
  assert.ok(players.total > 0);
  const player = players.results[0];
  assert.ok("Dribbling" in player);
  assert.ok(search("matches", { team: player.Club }).total > 0);
});
test("When asking about cup finals or knockout rounds, stages identify the relevant legs", () => {
  assert.equal(
    search("matches", {
      competition: "Copa do Brasil",
      stage: "final",
      season: 2012,
    }).total,
    2,
  );
  assert.equal(
    search("matches", {
      competition: "Libertadores",
      stage: "final",
      season: 2018,
    }).total,
    2,
  );
});
test("When ranking victories or comparing seasons, only scored games contribute to results", () => {
  const wins = search("matches", { order: "biggest_win", limit: 1 }).results[0];
  assert.ok(
    "homeGoals" in wins &&
      Math.abs(Number(wins.homeGoals) - Number(wins.awayGoals)) >= 8,
  );
  const stats = query(graph, "statistics", {
    competition: "Serie A",
    from: "2018-01-01",
    to: "2019-12-31",
    group: "season",
  });
  assert.ok(Array.isArray(stats));
  assert.deepEqual(
    stats.map((s) => s.played),
    [380, 380],
  );
  for (const s of stats)
    assert.equal(s.homeWins + s.awayWins + s.draws, s.played);
  assert.throws(() => query(graph, "matches", { from: "2020-02-31" }));
});
test("Given a stdio client, discovery, notifications, calls and error recovery work", () => {
  const requests = [
    "{",
    ...[
      {
        id: 1,
        method: "initialize",
        params: {
          protocolVersion: "2025-06-18",
          capabilities: {},
          clientInfo: { name: "test", version: "1" },
        },
      },
      { method: "notifications/initialized" },
      { id: 2, method: "tools/list" },
      {
        id: 3,
        method: "tools/call",
        params: { name: "players", arguments: { limit: -1 } },
      },
      {
        id: 4,
        method: "tools/call",
        params: {
          name: "players",
          arguments: { name: "Neymar", nationality: "Brazil", limit: 1 },
        },
      },
    ].map((r) => JSON.stringify({ ...r, jsonrpc: "2.0" })),
  ];
  const child = spawnSync(process.execPath, ["dist/server.js"], {
    input: requests.join("\n"),
    encoding: "utf8",
    timeout: 10000,
  });
  assert.equal(child.status, 0, child.stderr);
  const replies = child.stdout
    .trim()
    .split("\n")
    .map((s) => JSON.parse(s));
  assert.equal(replies.length, 5);
  assert.equal(replies[0].error.code, -32700);
  assert.ok(replies[1].result.capabilities.tools);
  assert.equal(replies[2].result.tools.length, 4);
  assert.ok(replies[3].result.isError);
  assert.equal(
    JSON.parse(replies[4].result.content[0].text).results[0].name,
    "Neymar Jr",
  );
});
const examples: [
  string,
  string,
  Record<string, unknown>,
  (rows: any[]) => boolean,
][] = [
  [
    "When did Flamengo last play Corinthians?",
    "matches",
    { team: "Flamengo", opponent: "Corinthians", played: true, limit: 1 },
    (r) => r.length === 1 && !!r[0].date,
  ],
  [
    "Which games did Palmeiras play in 2023?",
    "matches",
    { team: "Palmeiras", season: 2023 },
    (r) => r.length > 0 && r.every((x) => x.season === 2023),
  ],
  [
    "Which 2023 games were derbies?",
    "matches",
    { season: 2023, derby: true },
    (r) => r.length > 0,
  ],
  [
    "What is the 2018 Libertadores knockout schedule?",
    "matches",
    { season: 2018, competition: "Libertadores", stage: "quarterfinals" },
    (r) => r.length === 8,
  ],
  [
    "Where did the historical opening match take place?",
    "matches",
    { source: files[1], order: "earliest", limit: 1 },
    (r) => !!r[0].details.Arena,
  ],
  [
    "What were the corner totals for the latest cup result?",
    "matches",
    { source: files[4], competition: "Copa do Brasil", limit: 1 },
    (r) => Number.isFinite(+r[0].details.total_corners),
  ],
  [
    "Which fixtures have no recorded result?",
    "matches",
    { played: false },
    (r) =>
      r.length > 0 &&
      r.every((x) => x.homeGoals === null || x.awayGoals === null),
  ],
  [
    "Who had the best home record in 2019?",
    "records",
    { season: 2019, competition: "Serie A", venue: "home", sort: "win_rate" },
    (r) => r[0].team === "flamengo",
  ],
  [
    "Who scored most in 2019?",
    "records",
    { season: 2019, competition: "Serie A", sort: "goals" },
    (r) => r[0].goalsFor === 86,
  ],
  [
    "Which clubs occupied the bottom four places in 2020?",
    "records",
    { season: 2020, competition: "Serie A", offset: 16 },
    (r) => r.length === 4 && r.some((x) => x.team === "vasco da gama"),
  ],
  [
    "What was Corinthians’ 2022 home record?",
    "records",
    {
      team: "Corinthians",
      season: 2022,
      competition: "Serie A",
      venue: "home",
    },
    (r) => r[0].matches === 19,
  ],
  [
    "Which club had the best 2018 away record?",
    "records",
    { season: 2018, competition: "Serie A", venue: "away", sort: "win_rate" },
    (r) => r[0].matches === 19 && r[0].winRate >= r[1].winRate,
  ],
  [
    "Which competitions feature Palmeiras?",
    "statistics",
    { team: "Palmeiras", group: "competition" },
    (r) => r.some((x) => x.group === "Copa Libertadores"),
  ],
  [
    "How many goals per match in Série A?",
    "statistics",
    { competition: "Serie A" },
    (r) => r[0].averageGoals > 1,
  ],
  [
    "How often did the home team win in 2019?",
    "statistics",
    { season: 2019, competition: "Serie A" },
    (r) => r[0].homeWinRate > 0 && r[0].homeWinRate < 100,
  ],
  [
    "How did Santos perform away against Palmeiras?",
    "records",
    { team: "Santos", opponent: "Palmeiras", venue: "away" },
    (r) => r.length === 1 && r[0].matches > 0,
  ],
  [
    "Who are the highest-rated Brazilian players?",
    "players",
    { nationality: "Brazil" },
    (r) => r[0].name === "Neymar Jr",
  ],
  [
    "Who plays goalkeeper at Liverpool?",
    "players",
    { club: "Liverpool", position: "GK" },
    (r) => r.some((x) => x.name === "Alisson"),
  ],
  [
    "Which forwards play at Barcelona?",
    "players",
    { club: "FC Barcelona", position: "forward" },
    (r) => r.some((x) => x.name === "L. Messi"),
  ],
  [
    "What are Neymar’s skill attributes?",
    "players",
    { name: "Neymar", details: true },
    (r) => Number(r[0].Dribbling) > 90,
  ],
];
for (const [question, name, args, check] of examples) {
  test(question, () => {
    const start = performance.now();
    const result = query(graph, name, args);
    assert.ok(check(Array.isArray(result) ? result : result.results));
    assert.ok(
      performance.now() - start <
        (name === "records" || name === "statistics" ? 5000 : 2000),
    );
  });
}
