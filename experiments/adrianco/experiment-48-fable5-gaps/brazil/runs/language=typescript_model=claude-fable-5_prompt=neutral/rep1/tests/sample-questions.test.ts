/**
 * Feature: Sample questions coverage
 *
 * The specification requires that at least 20 sample questions can be
 * answered. Each question below maps to a tool call and must produce a
 * non-empty, informative answer (not a "no results" fallback).
 */
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { beforeAll, afterAll, describe, expect, it } from "vitest";
import { createServer } from "../src/server.js";
import { dataset } from "./helpers.js";

let client: Client;

beforeAll(async () => {
  const server = createServer(dataset());
  const [ct, st] = InMemoryTransport.createLinkedPair();
  client = new Client({ name: "sample-questions", version: "1.0.0" });
  await Promise.all([server.connect(st), client.connect(ct)]);
});

afterAll(async () => {
  await client.close();
});

interface Question {
  question: string;
  tool: string;
  args: Record<string, unknown>;
  /** The answer must contain this pattern to count as answered. */
  expect: RegExp;
}

const QUESTIONS: Question[] = [
  { question: "Show me all Flamengo vs Fluminense matches", tool: "search_matches", args: { team: "Flamengo", opponent: "Fluminense", limit: 50 }, expect: /Found \d+ match/ },
  { question: "What matches did Palmeiras play in 2023?", tool: "search_matches", args: { team: "Palmeiras", season: 2023 }, expect: /Palmeiras/ },
  { question: "When did Flamengo last play Corinthians?", tool: "search_matches", args: { team: "Flamengo", opponent: "Corinthians", limit: 1 }, expect: /\d{4}-\d{2}-\d{2}/ },
  { question: "Find Copa do Brasil matches in 2018", tool: "search_matches", args: { competition: "Copa do Brasil", season: 2018 }, expect: /Copa do Brasil/ },
  { question: "Show me Libertadores group-stage matches in 2013", tool: "search_matches", args: { competition: "Libertadores", season: 2013 }, expect: /Copa Libertadores/ },
  { question: "Show me Grêmio matches between June and August 2019", tool: "search_matches", args: { team: "Grêmio", date_from: "2019-06-01", date_to: "2019-08-31" }, expect: /Gr/ },
  { question: "What is Corinthians' home record in 2022?", tool: "team_stats", args: { team: "Corinthians", season: 2022, competition: "Brasileirão", venue: "home" }, expect: /Matches: 19/ },
  { question: "How has São Paulo performed overall?", tool: "team_stats", args: { team: "São Paulo" }, expect: /Win rate/ },
  { question: "Compare Palmeiras and Santos head-to-head", tool: "head_to_head", args: { team1: "Palmeiras", team2: "Santos" }, expect: /wins.*draws/s },
  { question: "Compare Grêmio and Internacional (the Grenal derby)", tool: "head_to_head", args: { team1: "Grêmio", team2: "Internacional" }, expect: /meetings in dataset/ },
  { question: "Who won the 2019 Brasileirão?", tool: "league_standings", args: { season: 2019 }, expect: /Champion.*Flamengo.*90 points/ },
  { question: "Which teams were relegated in 2019?", tool: "league_standings", args: { season: 2019 }, expect: /relegation zone.*(Cruzeiro|Avai|Chapecoense|Csa)/i },
  { question: "Show the 2003 historical season standings", tool: "league_standings", args: { season: 2003 }, expect: /Champion.*Cruzeiro/ },
  { question: "Who won the 2022 Série B?", tool: "league_standings", args: { season: 2022, competition: "Serie B" }, expect: /Champion.*Cruzeiro/ },
  // Gabigol is not in this FIFA snapshot under "Gabriel Barbosa"; the tool
  // must still answer helpfully with the closest name matches.
  { question: "Who is Gabriel Barbosa?", tool: "player_profile", args: { name: "Gabriel Barbosa" }, expect: /closest name match[\s\S]*Gabriel|Barbosa/ },
  { question: "Who is Neymar?", tool: "player_profile", args: { name: "Neymar" }, expect: /Nationality: Brazil/ },
  { question: "Find all Brazilian players in the dataset", tool: "search_players", args: { nationality: "Brazil", limit: 20 }, expect: /Found \d+ player/ },
  { question: "Who are the highest-rated players at Grêmio?", tool: "search_players", args: { club: "Grêmio", limit: 10 }, expect: /Overall: \d+/ },
  { question: "Show me strikers with rating at least 85", tool: "search_players", args: { position: "ST", min_overall: 85 }, expect: /Position: ST/ },
  { question: "What's the average goals per match in the Brasileirão?", tool: "competition_stats", args: { competition: "Brasileirão" }, expect: /Average goals per match/ },
  { question: "Which team has the best away record?", tool: "best_records", args: { venue: "away", competition: "Serie A", min_matches: 100 }, expect: /win rate/ },
  { question: "Show me the biggest wins in the dataset", tool: "biggest_wins", args: { limit: 10 }, expect: /Biggest victories/ },
  { question: "What competitions has Palmeiras played in?", tool: "team_competitions", args: { team: "Palmeiras" }, expect: /Brasileirão Série A[\s\S]*Copa/ },
  { question: "What data is available?", tool: "data_summary", args: {}, expect: /matches loaded/ },
];

describe("Feature: Sample questions coverage (spec requires ≥ 20)", () => {
  it(`Given the server, the suite covers ${QUESTIONS.length} questions (>= 20)`, () => {
    expect(QUESTIONS.length).toBeGreaterThanOrEqual(20);
  });

  for (const q of QUESTIONS) {
    it(`Q: "${q.question}" → ${q.tool} answers informatively`, async () => {
      const res = await client.callTool({ name: q.tool, arguments: q.args });
      const content = res.content as { type: string; text: string }[];
      const text = content.map((c) => c.text).join("\n");
      expect(text).not.toMatch(/^No (matches|players|qualifying)/);
      expect(text).toMatch(q.expect);
    });
  }
});
