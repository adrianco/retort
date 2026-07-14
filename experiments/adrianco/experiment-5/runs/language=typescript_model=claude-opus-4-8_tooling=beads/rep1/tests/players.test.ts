/**
 * ============================================================================
 * Context
 * ----------------------------------------------------------------------------
 * Feature: Player Queries
 * Covers search by name / nationality / club / position and club squads,
 * mirroring the player examples in TASK.md.
 * ============================================================================
 */

import { describe, it, expect } from "vitest";
import { dataset } from "./helpers.js";
import { searchPlayers, clubSquad } from "../src/queries/players.js";

describe("Feature: Player Queries", () => {
  it("Scenario: Find all Brazilian players", () => {
    const ds = dataset();
    const res = searchPlayers(ds, { nationality: "Brazil" }, 5);
    expect(res.count).toBeGreaterThan(500);
    // And the results are ranked by overall rating (Neymar tops the list)
    expect(res.players[0].overall).toBeGreaterThanOrEqual(
      res.players[1].overall ?? 0
    );
    expect(res.players[0].nationality).toBe("Brazil");
  });

  it("Scenario: Search a player by name (accent-insensitive)", () => {
    const ds = dataset();
    const res = searchPlayers(ds, { name: "neymar" });
    expect(res.count).toBeGreaterThan(0);
    expect(res.players.some((p) => /Neymar/i.test(p.name))).toBe(true);
  });

  it("Scenario: Filter players by position", () => {
    const ds = dataset();
    const res = searchPlayers(ds, { nationality: "Brazil", position: "GK" }, 10);
    expect(res.count).toBeGreaterThan(0);
    expect(res.players.every((p) => p.position === "GK")).toBe(true);
  });

  it("Scenario: Filter by minimum overall rating", () => {
    const ds = dataset();
    const res = searchPlayers(ds, { minOverall: 85 }, 100);
    expect(res.players.every((p) => (p.overall ?? 0) >= 85)).toBe(true);
  });

  it("Scenario: List a club's squad ranked by rating", () => {
    const ds = dataset();
    const squad = clubSquad(ds, "Santos");
    expect(squad.count).toBeGreaterThan(0);
    expect(squad.avgOverall).toBeGreaterThan(0);
    // Ranked descending by overall
    const ratings = squad.players.map((p) => p.overall ?? 0);
    expect(ratings).toEqual([...ratings].sort((a, b) => b - a));
  });
});
