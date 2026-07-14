/**
 * Context
 * -------
 * Feature: Player Queries (spec section 3).
 * Search by name, nationality (Brazilian players), club and position, sorted
 * by FIFA Overall rating. Uses clubs/players that genuinely exist in the
 * provided FIFA dataset (e.g. Santos, Grêmio; Neymar Jr) rather than ones the
 * export omits.
 */

import { describe, it, expect } from "vitest";
import { givenDataLoaded } from "./support/world.js";
import { findPlayers } from "../src/queries.js";

describe("Feature: Player Queries", () => {
  it("Scenario: Find all Brazilian players", () => {
    // Given the player data is loaded
    const store = givenDataLoaded();
    // When I filter by nationality Brazil
    const players = findPlayers(store, { nationality: "Brazil" });
    // Then I get many players, all Brazilian, sorted by Overall desc
    expect(players.length).toBeGreaterThan(100);
    for (const p of players) expect(p.nationality).toBe("Brazil");
    for (let i = 1; i < players.length; i++) {
      expect(players[i - 1].overall ?? 0).toBeGreaterThanOrEqual(players[i].overall ?? 0);
    }
  });

  it("Scenario: Top Brazilian player is Neymar", () => {
    const store = givenDataLoaded();
    const top = findPlayers(store, { nationality: "Brazil", limit: 1 })[0];
    expect(top.name).toMatch(/Neymar/i);
    expect(top.overall ?? 0).toBeGreaterThanOrEqual(90);
  });

  it("Scenario: Search a player by name", () => {
    const store = givenDataLoaded();
    const players = findPlayers(store, { name: "Gabriel Jesus", limit: 1 });
    expect(players.length).toBe(1);
    expect(players[0].name).toMatch(/Gabriel Jesus/i);
    expect(players[0].nationality).toBe("Brazil");
  });

  it("Scenario: Filter players by club", () => {
    // Santos is a Brazilian club present in the FIFA dataset.
    const store = givenDataLoaded();
    const players = findPlayers(store, { club: "Santos", limit: 50 });
    expect(players.length).toBeGreaterThan(0);
    for (const p of players) expect(/santos/i.test(p.club)).toBe(true);
  });

  it("Scenario: Filter by position", () => {
    const store = givenDataLoaded();
    const keepers = findPlayers(store, { position: "GK", limit: 20 });
    expect(keepers.length).toBeGreaterThan(0);
    for (const p of keepers) expect(p.position).toBe("GK");
  });

  it("Scenario: Filter by minimum overall rating", () => {
    const store = givenDataLoaded();
    const elite = findPlayers(store, { minOverall: 88 });
    expect(elite.length).toBeGreaterThan(0);
    for (const p of elite) expect(p.overall ?? 0).toBeGreaterThanOrEqual(88);
  });
});
