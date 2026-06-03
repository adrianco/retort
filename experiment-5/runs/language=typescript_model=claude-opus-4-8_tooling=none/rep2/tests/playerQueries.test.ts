/**
 * ============================================================================
 * File: tests/playerQueries.test.ts
 * Feature: Player Queries (spec capability 3)
 * ----------------------------------------------------------------------------
 * Context:
 *   GWT scenarios over the FIFA player dataset: search by name, nationality,
 *   club and position, sorted by overall rating — mirroring the spec's
 *   "top Brazilian players" and "players at Flamengo" examples.
 * ============================================================================
 */

import { describe, it, expect, beforeAll } from "vitest";
import { KnowledgeGraph } from "../src/knowledgeGraph.js";
import { graph } from "./helpers.js";

let g: KnowledgeGraph;
beforeAll(() => {
  g = graph();
});

describe("Feature: Player Queries", () => {
  it("Scenario: find a player by name", () => {
    // When I search for "Neymar"
    const players = g.findPlayers({ name: "Neymar" });
    // Then at least one player is returned and the name matches
    expect(players.length).toBeGreaterThan(0);
    expect(players[0].name.toLowerCase()).toContain("neymar");
  });

  it("Scenario: filter by nationality, sorted by rating", () => {
    const players = g.findPlayers({ nationality: "Brazil", limit: 10 });
    expect(players.length).toBe(10);
    for (const p of players) expect(p.nationality).toBe("Brazil");
    // Sorted descending by overall
    for (let i = 1; i < players.length; i++) {
      expect((players[i - 1].overall ?? 0) >= (players[i].overall ?? 0)).toBe(true);
    }
  });

  it("Scenario: the top Brazilian player is Neymar", () => {
    const [top] = g.findPlayers({ nationality: "Brazil", limit: 1 });
    expect(top.name).toContain("Neymar");
    expect(top.overall).toBeGreaterThanOrEqual(90);
  });

  it("Scenario: filter players by club", () => {
    // Note: FIFA 19 only licensed some Brazilian clubs (Santos, Grêmio,
    // Internacional, Fluminense, ...); Flamengo/Palmeiras are absent.
    const players = g.findPlayers({ club: "Santos" });
    expect(players.length).toBeGreaterThan(0);
    for (const p of players) expect(p.clubKey).toBe("santos");
  });

  it("Scenario: filter by position", () => {
    const keepers = g.findPlayers({ position: "GK", nationality: "Brazil", limit: 5 });
    expect(keepers.length).toBeGreaterThan(0);
    for (const p of keepers) expect(p.position).toBe("GK");
  });

  it("Scenario: minimum overall rating filter", () => {
    const elite = g.findPlayers({ minOverall: 88 });
    expect(elite.length).toBeGreaterThan(0);
    for (const p of elite) expect(p.overall!).toBeGreaterThanOrEqual(88);
  });
});
