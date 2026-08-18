import { createInterface } from "node:readline";
import { fileURLToPath } from "node:url";
import { SoccerStore } from "./store.ts";
import type { Competition } from "./types.ts";

type Request = { jsonrpc: "2.0"; id?: string | number; method: string; params?: Record<string, unknown> };
const competitionSchema = { type: "string", enum: ["Brasileirão", "Copa do Brasil", "Libertadores", "Brazilian Football"] };
const stringSchema = { type: "string", minLength: 1 };
const positiveIntSchema = { type: "integer", minimum: 1 };
const tool = (name: string, description: string, properties: Record<string, unknown>, required: string[] = []) => ({
  name, description,
  inputSchema: { type: "object", properties, required, additionalProperties: false },
});
const tools = [
  tool("search_matches", "Find football matches by team, opponent, competition, season, date range, round, or stage.", { team: stringSchema, opponent: stringSchema, competition: competitionSchema, season: positiveIntSchema, from: { type: "string", format: "date" }, to: { type: "string", format: "date" }, round: stringSchema, stage: stringSchema, limit: positiveIntSchema }),
  tool("team_record", "Calculate a team's wins, draws, losses, goals, points, and win rate.", { team: stringSchema, season: positiveIntSchema, competition: competitionSchema, venue: { type: "string", enum: ["home", "away", "all"] } }, ["team"]),
  tool("head_to_head", "Compare two teams and return their matches and head-to-head record.", { teamA: stringSchema, teamB: stringSchema, season: positiveIntSchema, competition: competitionSchema }, ["teamA", "teamB"]),
  tool("search_players", "Search FIFA players by name, nationality, club, or position; sorted by rating.", { name: stringSchema, nationality: stringSchema, club: stringSchema, position: stringSchema, limit: positiveIntSchema }),
  tool("standings", "Calculate a season table from match results.", { season: positiveIntSchema, competition: competitionSchema }, ["season"]),
  tool("competition_statistics", "Calculate goals, outcomes, and biggest wins for a competition or season.", { season: positiveIntSchema, competition: competitionSchema }),
  tool("ask_question", "Answer a simple natural-language Brazilian soccer question using the loaded datasets.", { question: stringSchema }, ["question"]),
];

const text = (value: unknown) => ({ content: [{ type: "text", text: JSON.stringify(value, null, 2) }] });
const competition = (value: unknown): Competition | undefined => ["Brasileirão", "Copa do Brasil", "Libertadores", "Brazilian Football"].includes(String(value)) ? value as Competition : undefined;

export async function handle(request: Request, store: SoccerStore): Promise<unknown> {
  if (request.method === "initialize") return { protocolVersion: "2024-11-05", capabilities: { tools: {} }, serverInfo: { name: "brazilian-soccer-mcp", version: "1.0.0" } };
  if (request.method === "tools/list") return { tools };
  if (request.method === "resources/list") return { resources: [{ uri: "brazilian-soccer://datasets", name: "Dataset coverage", description: "The six locally loaded Brazilian football CSV datasets.", mimeType: "application/json" }] };
  if (request.method === "resources/read") return { contents: [{ uri: "brazilian-soccer://datasets", mimeType: "application/json", text: JSON.stringify({ matchSources: ["Brasileirao_Matches.csv", "Brazilian_Cup_Matches.csv", "Libertadores_Matches.csv", "BR-Football-Dataset.csv", "novo_campeonato_brasileiro.csv"], playerSource: "fifa_data.csv" }) }] };
  if (request.method !== "tools/call") throw new Error(`Unsupported method: ${request.method}`);
  const args = request.params?.arguments as Record<string, unknown> ?? {}; const name = String(request.params?.name);
  if (name === "search_matches") return text(store.findMatches({ team: string(args.team), opponent: string(args.opponent), competition: competition(args.competition), season: number(args.season), from: string(args.from), to: string(args.to), round: string(args.round), stage: string(args.stage), limit: number(args.limit) }));
  if (name === "team_record") return text(store.record(required(args.team, "team"), { season: number(args.season), competition: competition(args.competition), venue: args.venue as "home" | "away" | "all" }));
  if (name === "head_to_head") return text(store.headToHead(required(args.teamA, "teamA"), required(args.teamB, "teamB"), { season: number(args.season), competition: competition(args.competition) }));
  if (name === "search_players") return text(store.searchPlayers({ name: string(args.name), nationality: string(args.nationality), club: string(args.club), position: string(args.position), limit: number(args.limit) }));
  if (name === "standings") return text(store.standings(requiredNumber(args.season, "season"), competition(args.competition)));
  if (name === "competition_statistics") return text(store.statistics({ season: number(args.season), competition: competition(args.competition) }));
  if (name === "ask_question") return text(answerQuestion(required(args.question, "question"), store));
  throw new Error(`Unknown tool: ${name}`);
}
const string = (v: unknown) => typeof v === "string" && v.trim() ? v.trim() : undefined;
const number = (v: unknown) => typeof v === "number" ? v : typeof v === "string" && v.trim() ? Number(v) : undefined;
const required = (v: unknown, field: string) => { const result = string(v); if (!result) throw new Error(`${field} is required`); return result; };
const requiredNumber = (v: unknown, field: string) => { const result = number(v); if (result === undefined || !Number.isFinite(result)) throw new Error(`${field} is required`); return result; };

export function answerQuestion(question: string, store: SoccerStore): unknown {
  const q = question.toLowerCase(); const season = Number(/\b(19|20)\d{2}\b/.exec(q)?.[0]) || undefined;
  const teams = ["flamengo", "fluminense", "palmeiras", "corinthians", "santos", "são paulo", "gremio", "grêmio", "vasco", "botafogo", "cruzeiro", "atletico mineiro", "atlético mineiro"].filter((team) => q.includes(team));
  if (/highest.rated|top .*players|melhores jogadores/.test(q)) return store.searchPlayers({ club: teams[0], nationality: q.includes("brazil") || q.includes("brasileir") ? "Brazil" : undefined, limit: 10 });
  if (/standings|table|who won|campe/.test(q) && season) return store.standings(season);
  if (/average goals|m[eé]dia.*gol|biggest win|maior.*vit[oó]ria/.test(q)) return store.statistics({ season });
  if (/head.to.head|compare|confront/.test(q) && teams.length >= 2) return store.headToHead(teams[0], teams[1], { season });
  if (teams.length >= 2) return store.findMatches({ team: teams[0], opponent: teams[1], season });
  if (teams.length === 1) return store.findMatches({ team: teams[0], season });
  return { message: "I could not identify the requested teams or analysis. Use a dedicated MCP tool with explicit filters.", tools: tools.map((tool) => tool.name) };
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const store = await SoccerStore.load(process.env.SOCCER_DATA_DIR);
  const input = createInterface({ input: process.stdin, crlfDelay: Infinity });
  for await (const line of input) {
    try {
      const request = JSON.parse(line) as Request;
      const result = await handle(request, store);
      if (request.id !== undefined) process.stdout.write(`${JSON.stringify({ jsonrpc: "2.0", id: request.id, result })}\n`);
    } catch (error) {
      process.stdout.write(`${JSON.stringify({ jsonrpc: "2.0", id: null, error: { code: -32603, message: error instanceof Error ? error.message : String(error) } })}\n`);
    }
  }
}
