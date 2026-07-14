/**
 * Tests for the tool dispatch layer (`callTool`) — verifies that each MCP tool
 * routes to the right query and produces the human-readable answer shapes from
 * the specification's "Example answer format" sections.
 */
import { describe, expect, it } from "vitest";
import { TOOL_DEFS, callTool } from "../src/tools.js";
import { store } from "./helpers.js";

describe("tool definitions", () => {
  it("declares all required tools with input schemas", () => {
    const names = TOOL_DEFS.map((t) => t.name);
    expect(names).toEqual(
      expect.arrayContaining([
        "find_matches",
        "head_to_head",
        "team_record",
        "league_standings",
        "competition_stats",
        "search_players",
        "list_competitions",
      ]),
    );
    for (const t of TOOL_DEFS) {
      expect(t.inputSchema).toHaveProperty("type", "object");
      expect(t.description.length).toBeGreaterThan(20);
    }
  });
});

describe("callTool", () => {
  const s = store();

  it("find_matches renders match lines with scores", () => {
    const out = callTool(s, "find_matches", { team: "Flamengo", opponent: "Fluminense", season: 2019 });
    expect(out).toMatch(/Flamengo|Fluminense/);
    expect(out).toMatch(/\d+-\d+/);
  });

  it("head_to_head renders a summary line", () => {
    const out = callTool(s, "head_to_head", { teamA: "Palmeiras", teamB: "Santos" });
    expect(out).toMatch(/head-to-head/i);
    expect(out).toMatch(/wins/);
  });

  it("team_record renders the spec's record block", () => {
    const out = callTool(s, "team_record", { team: "Corinthians", season: 2022, competition: "Série A", venue: "home" });
    expect(out).toMatch(/Corinthians record/);
    expect(out).toMatch(/Wins:.*Draws:.*Losses:/);
    expect(out).toMatch(/Win rate: \d/);
  });

  it("league_standings marks the champion", () => {
    const out = callTool(s, "league_standings", { season: 2019, limit: 5 });
    expect(out).toMatch(/Flamengo.*Champion/);
    expect(out).toMatch(/1\. Flamengo/);
  });

  it("competition_stats reports averages and biggest wins", () => {
    const out = callTool(s, "competition_stats", { competition: "Série A", season: 2019 });
    expect(out).toMatch(/Average goals per match: \d/);
    expect(out).toMatch(/Biggest victories/);
  });

  it("search_players lists ranked Brazilian players", () => {
    const out = callTool(s, "search_players", { nationality: "Brazil", limit: 3 });
    expect(out).toMatch(/1\. Neymar/);
    expect(out).toMatch(/Overall: \d+/);
  });

  it("list_competitions summarizes coverage", () => {
    const out = callTool(s, "list_competitions");
    expect(out).toMatch(/Brasileirão Série A/);
    expect(out).toMatch(/Total matches:/);
  });

  it("gives a friendly message for unknown teams", () => {
    const out = callTool(s, "team_record", { team: "Definitely Not A Club" });
    expect(out).toMatch(/No team found/);
  });

  it("throws on an unknown tool name", () => {
    expect(() => callTool(s, "no_such_tool", {})).toThrow(/Unknown tool/);
  });
});
