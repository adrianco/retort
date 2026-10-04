/**
 * End-to-end tests through the MCP protocol (in-memory transport): tool
 * discovery, the sample questions from the specification, error handling and
 * response-time requirements (< 2 s simple lookups, < 5 s aggregates).
 */
import type { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { beforeAll, describe, expect, it } from "vitest";
import { callTool, connectClient } from "./helpers.js";

let client: Client;
beforeAll(async () => {
  client = await connectClient();
});

describe("MCP tool discovery", () => {
  it("exposes all tools with input schemas", async () => {
    const { tools } = await client.listTools();
    const names = tools.map((t) => t.name).sort();
    expect(names).toEqual([
      "biggest_wins", "compare_seasons", "competition_stats", "cup_bracket", "cup_finals", "derby_matches", "find_team",
      "get_player", "head_to_head", "league_standings", "list_competitions", "players_by_club", "search_matches",
      "search_players", "team_profile", "team_rankings", "team_record",
    ]);
    for (const t of tools) {
      expect(t.description?.length).toBeGreaterThan(20);
      expect(t.inputSchema.type).toBe("object");
    }
  });
});

interface Sample {
  question: string;
  tool: string;
  args: Record<string, unknown>;
  expect: (string | RegExp)[];
  aggregate?: boolean;
}

const SAMPLES: Sample[] = [
  // Match queries
  { question: "Show me all Flamengo vs Fluminense matches", tool: "head_to_head", args: { team_a: "Flamengo", team_b: "Fluminense" },
    expect: ["Flamengo vs Fluminense (Fla-Flu derby)", /Head-to-head in dataset \(\d+ matches\): Flamengo \d+ wins, Fluminense \d+ wins, \d+ draws/] },
  { question: "What matches did Palmeiras play in 2023?", tool: "search_matches", args: { team: "Palmeiras", season: 2023 },
    expect: [/Palmeiras - matches \(2023\): \d+ found/, "2023-12-07: Cruzeiro 1-1 Palmeiras"] },
  { question: "Find all Copa do Brasil finals", tool: "cup_finals", args: { competition: "Copa do Brasil" },
    expect: ["Copa do Brasil finals in dataset:", "2019: aggregate Athletico Paranaense 3-1 Internacional -> Athletico Paranaense advance"] },
  { question: "When did Flamengo last play Corinthians?", tool: "head_to_head", args: { team_a: "Flamengo", team_b: "Corinthians", limit: 1 },
    expect: ["Most recent meeting: 2023-"] },
  { question: "What was the score of the 2019 Libertadores final?", tool: "search_matches", args: { competition: "Libertadores", season: 2019, stage: "final" },
    expect: ["2019-11-23: Flamengo 2-1 River Plate (Copa Libertadores Final)"] },
  // Team queries
  { question: "What is Corinthians' home record in 2022?", tool: "team_record", args: { team: "Corinthians", season: 2022, venue: "home", competition: "Brasileirão" },
    expect: ["Corinthians home record (Brasileirão Série A, 2022):", "- Matches: 19", /- Win rate: \d+\.\d%/] },
  { question: "Which team scored the most goals in Serie A 2023?", tool: "team_rankings", args: { metric: "goalsFor", competition: "Serie A", season: 2023, limit: 3 },
    expect: [/^1\. Grêmio .*GF 63/m] },
  { question: "Compare Palmeiras and Santos head-to-head", tool: "head_to_head", args: { team_a: "Palmeiras", team_b: "Santos" },
    expect: ["Palmeiras vs Santos (Clássico da Saudade derby)", /Palmeiras \d+ wins, Santos \d+ wins/] },
  { question: "What competitions has Palmeiras played in?", tool: "team_profile", args: { team: "Palmeiras" },
    expect: ["Brasileirão Série A:", "Copa do Brasil:", "Copa Libertadores:"] },
  { question: "Which team has the best home record?", tool: "team_rankings", args: { venue: "home", competition: "Brasileirão", metric: "winRate" },
    expect: [/Teams ranked by winRate \(home matches/, /^1\. \S+/m], aggregate: true },
  { question: "Which team has the best away record?", tool: "team_rankings", args: { venue: "away", metric: "winRate", min_matches: 100 },
    expect: [/Teams ranked by winRate \(away matches/], aggregate: true },
  // Player queries
  { question: "Find all Brazilian players in the dataset", tool: "search_players", args: { nationality: "Brazilian", limit: 10 },
    expect: ["Players (nationality Brazilian): 827 found", "1. Neymar Jr - Overall: 92"] },
  { question: "Who are the highest-rated players at Flamengo?", tool: "search_players", args: { club: "Flamengo" },
    expect: [/not licensed in FIFA 19/] },
  { question: "Show me all forwards from Grêmio", tool: "search_players", args: { club: "Gremio", position: "forward" },
    expect: [/Players \(club Gremio, position forward\): \d+ found/, "Club: Grêmio"] },
  { question: "Who is Gabriel Barbosa?", tool: "get_player", args: { name: "Gabriel Barbosa" },
    expect: ['"Gabriel Barbosa" is not in the FIFA 19 dataset. Closest matches:'] },
  { question: "Who is Neymar?", tool: "get_player", args: { name: "Neymar" },
    expect: ["Neymar Jr (FIFA ID 190871)", "Club: Paris Saint-Germain"] },
  { question: "Who are the top Brazilian players?", tool: "search_players", args: { nationality: "Brazil", min_overall: 85 },
    expect: ["Neymar Jr", "Casemiro"] },
  { question: "Brazilian players at Brazilian clubs", tool: "players_by_club", args: { nationality: "Brazil", brazilian_clubs_only: true },
    expect: [/- Grêmio: 20 players \(avg rating: \d+\.\d/] },
  // Competition queries
  { question: "Who won the 2019 Brasileirão?", tool: "league_standings", args: { season: 2019, limit: 3 },
    expect: ["1. Flamengo - 90 pts (28W, 6D, 4L)", "2. Santos - 74 pts (22W, 8D, 8L)", "3. Palmeiras - 74 pts (21W, 11D, 6L)", "Champion: Flamengo"] },
  { question: "Show the 2018 Copa Libertadores bracket", tool: "cup_bracket", args: { season: 2018, competition: "Libertadores" },
    expect: ["Quarterfinals:", "Semifinals:", "Final:", "River Plate advance"] },
  { question: "Which teams were relegated in 2020?", tool: "league_standings", args: { season: 2020 },
    expect: ["Relegated: Vasco da Gama, Goiás, Coritiba, Botafogo"] },
  // Statistical analysis
  { question: "What's the average goals per match in the Brasileirão?", tool: "competition_stats", args: { competition: "Brasileirão" },
    expect: [/average \d\.\d\d per match/, /Home wins: \d+ \(\d+\.\d%\)/], aggregate: true },
  { question: "Show me the biggest wins in the dataset", tool: "biggest_wins", args: { limit: 5 },
    expect: [/^1\. \d{4}-\d{2}-\d{2}: /m, "Average goals per match:"], aggregate: true },
  { question: "Compare the 2018 and 2019 seasons", tool: "compare_seasons", args: { seasons: [2018, 2019] },
    expect: ["2018: 380 matches", "champion Palmeiras", "champion Flamengo"], aggregate: true },
  { question: "Show me all derbies in 2023", tool: "derby_matches", args: { season: 2023 },
    expect: ["Fla-Flu (Flamengo vs Fluminense)", "Grenal (Grêmio vs Internacional)"] },
  { question: "Find matches in a date range (DD/MM/YYYY input)", tool: "search_matches", args: { team: "Grêmio", date_from: "01/11/2017", date_to: "30/11/2017", competition: "Libertadores" },
    expect: ["Lanús"] },
  { question: "Accepts state-suffixed team names", tool: "team_record", args: { team: "Palmeiras-SP", season: 2018, competition: "Serie A" },
    expect: ["Palmeiras record", "- Matches: 38", "Points: 80"] },
  { question: "Which datasets are loaded?", tool: "list_competitions", args: {},
    expect: ["Brasileirao_Matches.csv", "Brazilian_Cup_Matches.csv", "Libertadores_Matches.csv", "novo_campeonato_brasileiro.csv", "BR-Football-Dataset.csv", "fifa_data.csv: 18207"] },
];

describe("sample questions from the specification", () => {
  it(`covers at least 20 questions (${SAMPLES.length})`, () => {
    expect(SAMPLES.length).toBeGreaterThanOrEqual(20);
  });

  for (const s of SAMPLES) {
    it(s.question, async () => {
      const r = await callTool(client, s.tool, s.args);
      expect(r.isError, r.text).toBe(false);
      for (const e of s.expect) {
        if (typeof e === "string") expect(r.text).toContain(e);
        else expect(r.text).toMatch(e);
      }
      expect(r.ms).toBeLessThan(s.aggregate ? 5000 : 2000);
    });
  }
});

describe("cross-file queries", () => {
  it("combines match data and player data in a team profile", async () => {
    const r = await callTool(client, "team_profile", { team: "Atlético Mineiro" });
    expect(r.text).toContain("Brasileirão Série A:");
    expect(r.text).toContain("FIFA 19 squad: 20 players");
    expect(r.text).toMatch(/Brasileirão titles \(calculated from match data\): .*2021/);
  });

  it("adds the club's match record to a player profile", async () => {
    const r = await callTool(client, "search_players", { club: "Cruzeiro", limit: 1 });
    const name = /1\. (.+?) - Overall/.exec(r.text)![1];
    const p = await callTool(client, "get_player", { name });
    expect(p.text).toContain("Club: Cruzeiro");
    expect(p.text).toMatch(/Cruzeiro in Brasileirão match data: \d+ played/);
  });
});

describe("error handling", () => {
  it("returns a tool error for unknown teams", async () => {
    const r = await callTool(client, "team_record", { team: "Nonexistent United" });
    expect(r.isError).toBe(true);
    expect(r.text).toMatch(/No team matching/);
  });

  it("returns a tool error for seasons without data", async () => {
    const r = await callTool(client, "league_standings", { season: 1990 });
    expect(r.isError).toBe(true);
    expect(r.text).toMatch(/No Brasileirão Série A matches found for 1990/);
  });

  it("returns a tool error for unknown competitions", async () => {
    const r = await callTool(client, "search_matches", { competition: "Premier League" });
    expect(r.isError).toBe(true);
    expect(r.text).toMatch(/Unknown competition/);
  });

  it("explains ambiguous team names", async () => {
    const r = await callTool(client, "team_record", { team: "Atletico" });
    expect(r.isError).toBe(false);
    expect(r.text).toMatch(/interpreted as Atlético Mineiro/);
  });
});
