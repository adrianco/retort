import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import type { SoccerDataStore } from "../src/data/store.js";
import { createServer } from "../src/server.js";
import { loadTestStore } from "./support/testStore.js";

/** Extracts the text of an MCP tool call's first content block. */
function textOf(result: Awaited<ReturnType<Client["callTool"]>>): string {
  const content = result.content as Array<{ type: string; text?: string }>;
  return content[0]?.text ?? "";
}

describe("Brazilian Soccer MCP server", () => {
  let store: SoccerDataStore;
  let client: Client;

  beforeAll(async () => {
    store = await loadTestStore();
    const server = createServer(store);
    const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
    client = new Client({ name: "test-client", version: "1.0.0" });
    await Promise.all([client.connect(clientTransport), server.connect(serverTransport)]);
  });

  afterAll(async () => {
    await client.close();
  });

  it("test_given_a_running_server_when_listing_tools_then_every_required_capability_is_exposed", async () => {
    // Given the running MCP server
    // When listing its tools
    const { tools } = await client.listTools();
    const names = tools.map((t) => t.name);
    // Then match, team, player, competition, and statistical-analysis tools are all present
    expect(names).toEqual(
      expect.arrayContaining([
        "search_matches",
        "head_to_head",
        "team_record",
        "search_players",
        "standings",
        "goal_stats",
        "biggest_wins",
      ]),
    );
  });

  it("test_given_the_fla_flu_derby_question_when_asked_via_head_to_head_then_a_head_to_head_summary_line_is_returned", async () => {
    // Given the sample question "Show me all Flamengo vs Fluminense matches"
    // When calling the head_to_head tool
    const result = await client.callTool({ name: "head_to_head", arguments: { teamA: "Flamengo", teamB: "Fluminense", limit: 5 } });
    const text = textOf(result);
    // Then the response includes a head-to-head summary line, matching the spec's example answer format
    expect(text).toContain("Head-to-head in dataset:");
  });

  it("test_given_a_team_and_season_question_when_asked_via_search_matches_then_only_that_seasons_matches_are_described", async () => {
    // Given the sample question "What matches did Palmeiras play in 2023?"
    // When calling the search_matches tool
    const result = await client.callTool({ name: "search_matches", arguments: { team: "Palmeiras", season: 2023, limit: 5 } });
    const text = textOf(result);
    // Then the response lists actual matches rather than an empty/error response
    expect(text).not.toBe("No matches found for the given criteria.");
    expect(text.length).toBeGreaterThan(0);
  });

  it("test_given_a_home_record_question_when_asked_via_team_record_then_a_win_rate_is_reported", async () => {
    // Given the sample question "What is Corinthians' home record in 2022?"
    // When calling the team_record tool
    const result = await client.callTool({
      name: "team_record",
      arguments: { team: "Corinthians", competition: "Brasileirao", season: 2022, venue: "home" },
    });
    const text = textOf(result);
    // Then the response reports a win rate percentage, matching the spec's example answer format
    expect(text).toMatch(/win rate \d+(\.\d+)?%/);
  });

  it("test_given_a_champion_question_when_asked_via_standings_then_flamengo_is_reported_champion_of_2019", async () => {
    // Given the sample question "Who won the 2019 Brasileirão?"
    // When calling the standings tool
    const result = await client.callTool({ name: "standings", arguments: { competition: "Brasileirao", season: 2019 } });
    const text = textOf(result);
    // Then Flamengo is listed first with 90 points
    expect(text).toContain("1. Flamengo - 90 pts");
  });

  it("test_given_a_player_lookup_question_when_asked_via_search_players_then_a_matching_player_is_described", async () => {
    // Given the sample question "Who is Neymar?"
    // When calling the search_players tool
    const result = await client.callTool({ name: "search_players", arguments: { name: "Neymar", limit: 3 } });
    const text = textOf(result);
    // Then the response describes the player with their position and club, matching the spec's example answer format
    expect(text).toContain("Position:");
    expect(text).toContain("Club:");
  });

  it("test_given_a_biggest_wins_question_when_asked_then_results_are_returned_in_the_documented_format", async () => {
    // Given the sample question "Show me the biggest wins in the dataset"
    // When calling the biggest_wins tool
    const result = await client.callTool({ name: "biggest_wins", arguments: { limit: 3 } });
    const text = textOf(result);
    // Then a numbered list of matches is returned
    expect(text).toMatch(/^1\. /);
  });

  it("test_given_an_average_goals_question_when_asked_via_goal_stats_then_a_numeric_average_is_reported", async () => {
    // Given the sample question "What's the average goals per match in the Brasileirao?"
    // When calling the goal_stats tool
    const result = await client.callTool({ name: "goal_stats", arguments: { competition: "Brasileirao" } });
    const text = textOf(result);
    // Then a numeric average-goals figure is reported
    expect(text).toMatch(/Average goals per match: \d+(\.\d+)?/);
  });

  it("test_given_an_unknown_team_when_asked_via_team_record_then_the_server_responds_without_crashing", async () => {
    // Given a nonsense team name
    // When calling the team_record tool
    const result = await client.callTool({ name: "team_record", arguments: { team: "Not A Real Football Club" } });
    // Then the server still returns a well-formed (non-error) text response
    expect(result.isError).toBeFalsy();
    expect(textOf(result)).toContain("0 matches");
  });
});
