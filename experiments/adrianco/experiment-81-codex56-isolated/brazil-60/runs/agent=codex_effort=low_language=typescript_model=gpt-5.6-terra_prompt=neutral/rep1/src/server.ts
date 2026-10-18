#!/usr/bin/env node
import { createInterface } from "node:readline";
import { SoccerData } from "./data.js";
import { SoccerService } from "./service.js";

const service = new SoccerService(new SoccerData(process.env.SOCCER_DATA_DIR));
type Request = { jsonrpc?: string; id?: string | number; method: string; params?: Record<string, unknown> };
const tools = [
  ["search_matches", "Search all match datasets by team, opponent, competition, season, date range or stage."],
  ["team_statistics", "Calculate a team's wins, draws, losses and goals, optionally by venue, competition and season."],
  ["compare_teams", "Return head-to-head record and recent meetings for two teams."],
  ["competition_standings", "Calculate a competition table from available completed match results."],
  ["search_players", "Search FIFA players by name, nationality, club or position; results are rating-sorted."],
  ["competition_statistics", "Calculate goals, rates and biggest wins for a filtered set of matches."]
].map(([name, description]) => ({ name, description, inputSchema: { type: "object", additionalProperties: true } }));
function result(value: unknown) { return { content: [{ type: "text", text: JSON.stringify(value, null, 2) }], structuredContent: value }; }
function call(name: string, args: Record<string, unknown>) {
  switch (name) {
    case "search_matches": return service.findMatches(args as never);
    case "team_statistics": { const { team, ...filter } = args as { team?: string }; if (!team) throw new Error("team is required"); return service.teamStats(team, filter); }
    case "compare_teams": { const { teamA, teamB, ...filter } = args as { teamA?: string; teamB?: string }; if (!teamA || !teamB) throw new Error("teamA and teamB are required"); return service.headToHead(teamA, teamB, filter); }
    case "competition_standings": { const { competition, season } = args as { competition?: string; season?: number }; if (!competition || !season) throw new Error("competition and season are required"); return service.standings(competition, Number(season)); }
    case "search_players": return service.players(args as never);
    case "competition_statistics": return service.aggregate(args as never);
    default: throw new Error(`Unknown tool: ${name}`);
  }
}
function respond(request: Request, payload: unknown, error?: { code: number; message: string }) { if (request.id !== undefined) process.stdout.write(JSON.stringify(error ? { jsonrpc: "2.0", id: request.id, error } : { jsonrpc: "2.0", id: request.id, result: payload }) + "\n"); }
createInterface({ input: process.stdin, crlfDelay: Infinity }).on("line", line => { try { const req = JSON.parse(line) as Request; if (req.method === "initialize") respond(req, { protocolVersion: "2024-11-05", capabilities: { tools: {} }, serverInfo: { name: "brazilian-soccer", version: "1.0.0" } }); else if (req.method === "tools/list") respond(req, { tools }); else if (req.method === "tools/call") respond(req, result(call(String(req.params?.name), (req.params?.arguments ?? {}) as Record<string, unknown>))); else if (req.method !== "notifications/initialized") respond(req, null, { code: -32601, message: "Method not found" }); } catch (e) { const request = (() => { try { return JSON.parse(line) as Request; } catch { return { method: "unknown" }; } })(); respond(request, null, { code: -32602, message: e instanceof Error ? e.message : String(e) }); } });
