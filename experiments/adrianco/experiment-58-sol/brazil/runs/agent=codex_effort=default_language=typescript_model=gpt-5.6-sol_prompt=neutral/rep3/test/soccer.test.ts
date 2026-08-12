import { mkdtemp, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { SoccerDataStore } from "../src/data-store.js";
import { normalizeTeamName, parseDate } from "../src/normalize.js";
import { NaturalLanguageQuery } from "../src/query.js";
import { createServer } from "../src/server.js";
import { SoccerService } from "../src/service.js";

let fixtureDirectory: string;
let store: SoccerDataStore;
let service: SoccerService;

const files: Record<string, string> = {
  "Brasileirao_Matches.csv": `datetime,home_team,home_team_state,away_team,away_team_state,home_goal,away_goal,season,round
2019-01-01 20:00:00,Flamengo-RJ,RJ,Fluminense-RJ,RJ,2,1,2019,1
2019-01-08 20:00:00,Fluminense-RJ,RJ,Flamengo-RJ,RJ,0,0,2019,2
2019-01-15 20:00:00,Palmeiras-SP,SP,Flamengo-RJ,RJ,3,0,2019,3
`,
  "Brazilian_Cup_Matches.csv": `round,datetime,home_team,away_team,home_goal,away_goal,season
Final,2020-03-01 16:00:00,Palmeiras,Corinthians,1,0,2020
`,
  "Libertadores_Matches.csv": `datetime,home_team,away_team,home_goal,away_goal,season,stage
2021-11-27 17:00:00,Palmeiras,Brazil,2,1,2021,final
`,
  "BR-Football-Dataset.csv": `tournament,home,home_goal,away_goal,away,home_corner,away_corner,home_attack,away_attack,home_shots,away_shots,time,date,ht_diff,at_diff,ht_result,at_result,total_corners
Serie A,Flamengo,2,1,Fluminense,4,3,10,8,6,3,20:00:00,2019-01-01,0,0,DRAW,HOME,7
Serie B,Sport,4,0,Nautico,2,2,4,4,5,1,18:00:00,2022-05-01,0,0,DRAW,HOME,4
`,
  "novo_campeonato_brasileiro.csv": `ID,Data,Ano,Rodada,Equipe_mandante,Equipe_visitante,Gols_mandante,Gols_visitante,Mandante_UF,Visitante_UF,Vencedor,Arena,OBS
1,01/01/2019,2019,1,Flamengo,Fluminense,2,1,RJ,RJ,Mandante,Maracana,
`,
  "fifa_data.csv": `,ID,Name,Age,Nationality,Overall,Potential,Club,Position,Jersey Number,Height,Weight,Finishing,Dribbling
0,10,Neymar Jr,26,Brazil,92,93,Paris Saint-Germain,LW,10,5'9,150lbs,87,96
1,11,Player Two,22,Brazil,75,82,Flamengo,ST,9,6'0,170lbs,80,70
2,12,Keeper,30,Argentina,80,80,Palmeiras,GK,1,6'3,190lbs,10,20
`
};

beforeAll(async () => {
  fixtureDirectory = await mkdtemp(path.join(tmpdir(), "soccer-mcp-test-"));
  await Promise.all(Object.entries(files).map(([name, contents]) => writeFile(path.join(fixtureDirectory, name), contents, "utf8")));
  store = await SoccerDataStore.load({ dataDirectory: fixtureDirectory });
  service = new SoccerService(store);
});

afterAll(async () => {
  await rm(fixtureDirectory, { recursive: true, force: true });
});

describe("normalization and loading", () => {
  it("normalizes accents, state suffixes, full names, and ambiguous Atlético variants", () => {
    expect(normalizeTeamName("São Paulo-SP")).toBe("sao paulo");
    expect(normalizeTeamName("Sport Club Corinthians Paulista")).toBe("corinthians");
    expect(normalizeTeamName("Atletico-MG")).toBe("atletico mineiro");
    expect(normalizeTeamName("Atletico-PR")).toBe("athletico paranaense");
  });

  it("normalizes ISO, timestamp, and Brazilian dates", () => {
    expect(parseDate("2023-09-24 18:30:00")).toBe("2023-09-24");
    expect(parseDate("29/03/2003")).toBe("2003-03-29");
    expect(parseDate("bad date")).toBeNull();
  });

  it("loads all six files and merges exact duplicate matches with provenance", () => {
    expect(store.summary.players).toBe(3);
    expect(Object.keys(store.summary.sources)).toHaveLength(5);
    const derby = service.searchMatches({ team: "Flamengo", opponent: "Fluminense", newestFirst: false });
    expect(derby.total).toBe(2);
    expect(derby.items[0]?.sources.map((source) => source.file)).toEqual(expect.arrayContaining([
      "Brasileirao_Matches.csv", "BR-Football-Dataset.csv", "novo_campeonato_brasileiro.csv"
    ]));
  });
});

describe("query service", () => {
  it("searches matches by team variation, competition, season, and stage", () => {
    expect(service.searchMatches({ team: "Flamengo-RJ", season: 2019 }).total).toBe(3);
    expect(service.searchMatches({ competition: "Libertadores", stage: "final" }).total).toBe(1);
    expect(service.searchMatches({ competition: "Copa do Brasil", finals: true }).total).toBe(1);
  });

  it("calculates records without double-counting overlapping sources", () => {
    expect(service.teamStats("Flamengo", { season: 2019, competition: "Brasileirão" })).toMatchObject({
      matches: 3, wins: 1, draws: 1, losses: 1, goalsFor: 2, goalsAgainst: 4, points: 4
    });
    expect(service.headToHead("Flamengo", "Fluminense")).toMatchObject({ matches: 2, teamAWins: 1, teamBWins: 0, draws: 1 });
  });

  it("calculates deterministic standings", () => {
    const standings = service.standings(2019);
    expect(standings.map((row) => row.team)).toEqual(["Flamengo-RJ", "Palmeiras-SP", "Fluminense-RJ"]);
    expect(standings[0]).toMatchObject({ points: 4, wins: 1, position: 1 });
  });

  it("searches and sorts players", () => {
    const players = service.searchPlayers({ nationality: "Brazil", minOverall: 70 });
    expect(players.total).toBe(2);
    expect(players.items[0]?.name).toBe("Neymar Jr");
    expect(service.searchPlayers({ club: "Flamengo", position: "ST" }).items[0]?.name).toBe("Player Two");
  });

  it("computes aggregate statistics and graph relationships", () => {
    const stats = service.statistics({ season: 2019, competition: "Serie A" });
    expect(stats).toMatchObject({ matches: 3, totalGoals: 6, averageGoals: 2 });
    expect(stats.biggestVictories[0]).toMatchObject({ margin: 3 });
    const graph = service.relationships("Flamengo", 2019);
    expect(graph.counts).toMatchObject({ matches: 3, competitions: 1, opponents: 2, players: 1 });
    expect(graph.edges.some((edge) => edge.relationship === "plays_for")).toBe(true);
  });

  it("summarizes knockout finals without treating them as league standings", () => {
    const summary = service.competitionSummary("Copa do Brasil", 2020);
    expect(summary.standings).toEqual([]);
    expect(summary.champion).toBe("Palmeiras");
    expect(summary.finalMatches).toHaveLength(1);
  });
});

describe("natural-language behavior", () => {
  const questions: Array<[string, string]> = [
    ["Show me Flamengo vs Fluminense matches", "head_to_head"],
    ["Compare Palmeiras and Corinthians head to head", "head_to_head"],
    ["When did Flamengo last play?", "match_search"],
    ["What matches did Palmeiras play in 2020?", "match_search"],
    ["Find all Copa do Brasil finals", "match_search"],
    ["What is Flamengo's home record in 2019?", "team_statistics"],
    ["Show Flamengo statistics in 2019", "team_statistics"],
    ["Who won the 2019 Brasileirão?", "standings"],
    ["Who won the 2021 Libertadores?", "competition_summary"],
    ["Show the 2019 Brasileirão standings", "standings"],
    ["Which teams were relegated in 2019?", "standings"],
    ["Find Brazilian players", "player_search"],
    ["Who are the highest rated players?", "player_search"],
    ["Show forwards from Flamengo", "player_search"],
    ["What's the average goals per match in Serie A?", "statistics"],
    ["Show the biggest wins", "statistics"],
    ["What is the home win rate?", "statistics"],
    ["What competitions has Flamengo played in?", "team_competitions"],
    ["Show all derbies in 2019", "derbies"],
    ["Which team has the best home record in 2019?", "team_ranking"],
    ["Which team scored the most goals in 2019?", "team_ranking"]
  ];

  it.each(questions)("routes: %s", (question, expectedIntent) => {
    const response = new NaturalLanguageQuery(service).answer(question);
    expect(response.intent).toBe(expectedIntent);
    expect(response.answer.length).toBeGreaterThan(10);
  });

  it("interprets cup finals as the highest numbered round", () => {
    const response = new NaturalLanguageQuery(service).answer("Find all Copa do Brasil finals");
    expect(response.data).toMatchObject({ total: 1 });
  });
});

describe("MCP integration", () => {
  it("lists and invokes tools through the protocol transport", async () => {
    const server = await createServer({ dataDirectory: fixtureDirectory });
    const client = new Client({ name: "test-client", version: "1.0.0" });
    const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
    await Promise.all([server.connect(serverTransport), client.connect(clientTransport)]);
    try {
      const tools = await client.listTools();
      expect(tools.tools.map((tool) => tool.name)).toEqual(expect.arrayContaining([
        "search_matches", "team_statistics", "head_to_head", "search_players", "calculate_standings",
        "competition_summary", "analyze_statistics", "explore_relationships", "answer_question"
      ]));
      const response = await client.callTool({ name: "answer_question", arguments: { question: "Show Flamengo vs Fluminense matches" } });
      expect(response.isError).not.toBe(true);
      expect(response.content).toEqual(expect.arrayContaining([expect.objectContaining({ type: "text" })]));

      const standings = await client.callTool({ name: "calculate_standings", arguments: { season: 2019 } });
      expect(standings.isError).not.toBe(true);
      expect(standings.structuredContent).toMatchObject({
        season: 2019,
        competition: "Brasileirão Serie A"
      });
      expect(standings.structuredContent?.standings).toEqual(expect.arrayContaining([
        expect.objectContaining({ position: 1, team: "Flamengo-RJ" })
      ]));
    } finally {
      await client.close();
      await server.close();
    }
  });
});
