import type { Readable, Writable } from "node:stream";
import { createInterface } from "node:readline";
import type { SoccerService } from "./soccer-service.js";

interface JsonRpcRequest {
  jsonrpc: "2.0";
  id?: string | number | null;
  method: string;
  params?: Record<string, unknown>;
}

interface JsonRpcResponse {
  jsonrpc: "2.0";
  id: string | number | null;
  result?: unknown;
  error?: { code: number; message: string; data?: unknown };
}

type JsonSchema = Record<string, unknown>;

interface ToolDefinition {
  name: string;
  title: string;
  description: string;
  inputSchema: JsonSchema;
}

const objectSchema = (properties: Record<string, JsonSchema>, required: string[] = []): JsonSchema => ({
  type: "object",
  properties,
  ...(required.length > 0 ? { required } : {}),
  additionalProperties: false,
});

const string = (description: string, values?: string[]): JsonSchema => ({ type: "string", description, ...(values ? { enum: values } : {}) });
const integer = (description: string, minimum?: number, maximum?: number): JsonSchema => ({ type: "integer", description, ...(minimum !== undefined ? { minimum } : {}), ...(maximum !== undefined ? { maximum } : {}) });

export const TOOL_DEFINITIONS: ToolDefinition[] = [
  {
    name: "search_matches",
    title: "Search Brazilian Soccer Matches",
    description: "Search all five match datasets by team, opponent, venue, date range, competition, season, round, or stage. Team names are accent-, suffix-, and alias-normalized.",
    inputSchema: objectSchema({
      team: string("Team playing home or away"), opponent: string("Opponent when team is provided"),
      homeTeam: string("Home team only"), awayTeam: string("Away team only"),
      competition: string("Competition, such as Brasileirão, Copa do Brasil, or Libertadores"),
      season: integer("Season year", 1900, 2100), dateFrom: string("Inclusive ISO date YYYY-MM-DD"), dateTo: string("Inclusive ISO date YYYY-MM-DD"),
      stage: string("Tournament stage"), round: string("Round label"), sort: string("Date order", ["asc", "desc"]),
      offset: integer("Pagination offset", 0), limit: integer("Maximum results", 1, 500),
    }),
  },
  {
    name: "get_team_statistics",
    title: "Get Team Statistics",
    description: "Calculate a team's matches, wins, draws, losses, goals, goal difference, points, and win rate, optionally by season, competition, and venue.",
    inputSchema: objectSchema({ team: string("Team name"), season: integer("Season year", 1900, 2100), competition: string("Competition"), venue: string("Match venue", ["home", "away", "all"]) }, ["team"]),
  },
  {
    name: "compare_teams",
    title: "Compare Teams Head-to-Head",
    description: "Return head-to-head matches and each team's record against the other.",
    inputSchema: objectSchema({ team1: string("First team"), team2: string("Second team"), season: integer("Optional season", 1900, 2100), competition: string("Optional competition") }, ["team1", "team2"]),
  },
  {
    name: "search_players",
    title: "Search FIFA Players",
    description: "Search FIFA players by name, nationality, club, position or position family, rating, and age.",
    inputSchema: objectSchema({ name: string("Partial player name"), nationality: string("Nationality"), club: string("Club name"), position: string("Position code or forward/midfielder/defender/goalkeeper"), minOverall: integer("Minimum overall rating", 0, 100), maxAge: integer("Maximum age", 14, 60), limit: integer("Maximum results", 1, 500) }),
  },
  {
    name: "get_standings",
    title: "Calculate Competition Standings",
    description: "Calculate a season table from match results using 3 points for a win and standard tie-break ordering.",
    inputSchema: objectSchema({ season: integer("Season year", 1900, 2100), competition: string("Competition; defaults to Brasileirão Série A") }, ["season"]),
  },
  {
    name: "get_competition_statistics",
    title: "Analyze a Competition",
    description: "Calculate goals per match, home/away/draw rates, and biggest wins for a competition and optional season.",
    inputSchema: objectSchema({ competition: string("Competition"), season: integer("Optional season", 1900, 2100) }, ["competition"]),
  },
  {
    name: "explore_soccer_graph",
    title: "Explore the Soccer Knowledge Graph",
    description: "Return a bounded node/edge subgraph connecting teams, matches, competitions, and FIFA players.",
    inputSchema: objectSchema({ team: string("Center graph on a team"), player: string("Filter player nodes by name"), competition: string("Filter matches by competition"), season: integer("Filter matches by season", 1900, 2100), limit: integer("Maximum match and player results", 1, 100) }),
  },
  {
    name: "answer_soccer_question",
    title: "Answer a Natural-Language Soccer Question",
    description: "Route a natural-language question to match, team, player, competition, standings, derby, or statistical analysis.",
    inputSchema: objectSchema({ question: string("Question about the supplied Brazilian soccer datasets") }, ["question"]),
  },
  {
    name: "dataset_summary",
    title: "Describe Dataset Coverage",
    description: "Return row counts, date coverage, team and competition counts, and per-file loading evidence.",
    inputSchema: objectSchema({}),
  },
];

const SAMPLE_QUESTIONS = [
  "Show me all Flamengo vs Fluminense matches",
  "What matches did Palmeiras play in 2023?",
  "Find all Copa do Brasil finals",
  "What is Corinthians' home record in 2022?",
  "Which team scored the most goals in Serie A 2023?",
  "Compare Palmeiras and Santos head-to-head",
  "Find all Brazilian players in the dataset",
  "Who are the highest-rated players at Flamengo?",
  "Show me all forwards from São Paulo FC",
  "Who won the 2019 Brasileirão?",
  "Show the 2018 Copa Libertadores bracket",
  "Which teams were relegated in 2020?",
  "What's the average goals per match in the Brasileirão?",
  "Which team has the best away record in 2023?",
  "Show me the biggest wins in the dataset",
  "When did Flamengo last play Corinthians?",
  "Who is Gabriel Barbosa?",
  "Which players play for Flamengo?",
  "Show me all derbies in 2023",
  "What competitions has Palmeiras played in?",
];

function toolResult(value: unknown): Record<string, unknown> {
  return {
    content: [{ type: "text", text: typeof value === "string" ? value : JSON.stringify(value, null, 2) }],
    structuredContent: value,
  };
}

function requiredString(args: Record<string, unknown>, name: string): string {
  const value = args[name];
  if (typeof value !== "string" || value.trim() === "") throw new Error(`'${name}' must be a non-empty string`);
  return value;
}

function optionalString(args: Record<string, unknown>, name: string): string | undefined {
  return typeof args[name] === "string" ? args[name] : undefined;
}

function optionalNumber(args: Record<string, unknown>, name: string): number | undefined {
  return typeof args[name] === "number" && Number.isFinite(args[name]) ? args[name] : undefined;
}

export class BrazilianSoccerMcpServer {
  constructor(private readonly service: SoccerService) {}

  async handle(request: JsonRpcRequest): Promise<JsonRpcResponse | null> {
    if (request.id === undefined) return null;
    const id = request.id ?? null;
    try {
      switch (request.method) {
        case "initialize": {
          const requested = typeof request.params?.protocolVersion === "string" ? request.params.protocolVersion : "2025-11-25";
          return this.ok(id, {
            protocolVersion: requested,
            capabilities: { tools: { listChanged: false }, resources: { subscribe: false, listChanged: false }, prompts: { listChanged: false } },
            serverInfo: { name: "brazilian-soccer-mcp", version: "1.0.0" },
            instructions: "Use answer_soccer_question for natural language, or the typed analytics tools for precise filters. All data is read-only and local; scorer events are not present.",
          });
        }
        case "ping": return this.ok(id, {});
        case "tools/list": return this.ok(id, { tools: TOOL_DEFINITIONS.map((tool) => ({ ...tool, annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false } })) });
        case "tools/call": return this.ok(id, await this.callTool(request.params ?? {}));
        case "resources/list": return this.ok(id, { resources: [
          { uri: "soccer://dataset/summary", name: "Brazilian Soccer Dataset Summary", mimeType: "application/json", description: "Coverage and per-source row counts" },
          { uri: "soccer://dataset/questions", name: "Example Soccer Questions", mimeType: "application/json", description: "Twenty supported question patterns" },
        ] });
        case "resources/read": return this.ok(id, this.readResource(requiredString(request.params ?? {}, "uri")));
        case "prompts/list": return this.ok(id, { prompts: [{ name: "analyze_brazilian_soccer", title: "Analyze Brazilian Soccer", description: "Ask a grounded question about the bundled datasets", arguments: [{ name: "question", description: "Your soccer question", required: true }] }] });
        case "prompts/get": return this.ok(id, this.getPrompt(request.params ?? {}));
        default: return { jsonrpc: "2.0", id, error: { code: -32601, message: `Method not found: ${request.method}` } };
      }
    } catch (error) {
      return { jsonrpc: "2.0", id, error: { code: -32602, message: error instanceof Error ? error.message : String(error) } };
    }
  }

  private ok(id: string | number | null, result: unknown): JsonRpcResponse {
    return { jsonrpc: "2.0", id, result };
  }

  private async callTool(params: Record<string, unknown>): Promise<Record<string, unknown>> {
    const name = requiredString(params, "name");
    const args = typeof params.arguments === "object" && params.arguments !== null ? params.arguments as Record<string, unknown> : {};
    switch (name) {
      case "search_matches": return toolResult(this.service.searchMatches({
        ...this.matchFilters(args),
        ...(optionalString(args, "homeTeam") ? { homeTeam: optionalString(args, "homeTeam") } : {}),
        ...(optionalString(args, "awayTeam") ? { awayTeam: optionalString(args, "awayTeam") } : {}),
        ...(optionalString(args, "dateFrom") ? { dateFrom: optionalString(args, "dateFrom") } : {}),
        ...(optionalString(args, "dateTo") ? { dateTo: optionalString(args, "dateTo") } : {}),
        ...(optionalString(args, "stage") ? { stage: optionalString(args, "stage") } : {}),
        ...(optionalString(args, "round") ? { round: optionalString(args, "round") } : {}),
        ...(optionalString(args, "sort") === "asc" || optionalString(args, "sort") === "desc" ? { sort: optionalString(args, "sort") as "asc" | "desc" } : {}),
        ...(optionalNumber(args, "offset") !== undefined ? { offset: optionalNumber(args, "offset") } : {}),
        ...(optionalNumber(args, "limit") !== undefined ? { limit: optionalNumber(args, "limit") } : {}),
      }));
      case "get_team_statistics": return toolResult(this.service.getTeamStatistics(requiredString(args, "team"), {
        ...this.statFilters(args),
        ...(optionalString(args, "venue") ? { venue: optionalString(args, "venue") as "home" | "away" | "all" } : {}),
      }));
      case "compare_teams": return toolResult(this.service.compareTeams(requiredString(args, "team1"), requiredString(args, "team2"), this.statFilters(args)));
      case "search_players": return toolResult(this.service.searchPlayers({
        ...(optionalString(args, "name") ? { name: optionalString(args, "name") } : {}),
        ...(optionalString(args, "nationality") ? { nationality: optionalString(args, "nationality") } : {}),
        ...(optionalString(args, "club") ? { club: optionalString(args, "club") } : {}),
        ...(optionalString(args, "position") ? { position: optionalString(args, "position") } : {}),
        ...(optionalNumber(args, "minOverall") !== undefined ? { minOverall: optionalNumber(args, "minOverall") } : {}),
        ...(optionalNumber(args, "maxAge") !== undefined ? { maxAge: optionalNumber(args, "maxAge") } : {}),
        ...(optionalNumber(args, "limit") !== undefined ? { limit: optionalNumber(args, "limit") } : {}),
      }));
      case "get_standings": return toolResult(this.service.getStandings(optionalNumber(args, "season") ?? (() => { throw new Error("'season' must be a number"); })(), optionalString(args, "competition")));
      case "get_competition_statistics": return toolResult(this.service.getCompetitionStatistics(requiredString(args, "competition"), optionalNumber(args, "season")));
      case "explore_soccer_graph": return toolResult(this.service.exploreGraph({
        ...(optionalString(args, "team") ? { team: optionalString(args, "team") } : {}),
        ...(optionalString(args, "player") ? { player: optionalString(args, "player") } : {}),
        ...(optionalString(args, "competition") ? { competition: optionalString(args, "competition") } : {}),
        ...(optionalNumber(args, "season") !== undefined ? { season: optionalNumber(args, "season") } : {}),
        ...(optionalNumber(args, "limit") !== undefined ? { limit: optionalNumber(args, "limit") } : {}),
      }));
      case "answer_soccer_question": return toolResult(this.service.answerQuestion(requiredString(args, "question")));
      case "dataset_summary": return toolResult(this.service.data.summary);
      default: throw new Error(`Unknown tool: ${name}`);
    }
  }

  private matchFilters(args: Record<string, unknown>): Record<string, unknown> {
    return {
      ...(optionalString(args, "team") ? { team: optionalString(args, "team") } : {}),
      ...(optionalString(args, "opponent") ? { opponent: optionalString(args, "opponent") } : {}),
      ...this.statFilters(args),
    };
  }

  private statFilters(args: Record<string, unknown>): Record<string, unknown> {
    return {
      ...(optionalNumber(args, "season") !== undefined ? { season: optionalNumber(args, "season") } : {}),
      ...(optionalString(args, "competition") ? { competition: optionalString(args, "competition") } : {}),
    };
  }

  private readResource(uri: string): { contents: Array<Record<string, unknown>> } {
    if (uri === "soccer://dataset/summary") return { contents: [{ uri, mimeType: "application/json", text: JSON.stringify(this.service.data.summary, null, 2) }] };
    if (uri === "soccer://dataset/questions") return { contents: [{ uri, mimeType: "application/json", text: JSON.stringify(SAMPLE_QUESTIONS, null, 2) }] };
    throw new Error(`Unknown resource: ${uri}`);
  }

  private getPrompt(params: Record<string, unknown>): Record<string, unknown> {
    if (requiredString(params, "name") !== "analyze_brazilian_soccer") throw new Error("Unknown prompt");
    const args = typeof params.arguments === "object" && params.arguments !== null ? params.arguments as Record<string, unknown> : {};
    const question = requiredString(args, "question");
    return { description: "Analyze a question using only the bundled soccer datasets", messages: [{ role: "user", content: { type: "text", text: `Use the Brazilian soccer tools to answer this question. State when a requested fact is not inferable from the data.\n\n${question}` } }] };
  }
}

export async function serveStdio(server: BrazilianSoccerMcpServer, input: Readable = process.stdin, output: Writable = process.stdout): Promise<void> {
  const lines = createInterface({ input, crlfDelay: Infinity });
  for await (const line of lines) {
    if (!line.trim()) continue;
    let response: JsonRpcResponse | null;
    try {
      response = await server.handle(JSON.parse(line) as JsonRpcRequest);
    } catch (error) {
      response = { jsonrpc: "2.0", id: null, error: { code: -32700, message: "Parse error", data: error instanceof Error ? error.message : String(error) } };
    }
    if (response) output.write(`${JSON.stringify(response)}\n`);
  }
}
