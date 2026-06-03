/**
 * Context
 * -------
 * Feature: Competition Queries (spec section 4).
 * League standings computed from match results (3pts win / 1pt draw). The
 * 2019 Brasileirão is a known reference point: Flamengo were champions with
 * 90 points, which the spec's example output cites.
 */

import { describe, it, expect } from "vitest";
import { givenDataLoaded } from "./support/world.js";
import { standings } from "../src/queries.js";

describe("Feature: Competition Queries", () => {
  it("Scenario: 2019 Brasileirão standings name Flamengo champions on 90 points", () => {
    // Given the match data is loaded
    const store = givenDataLoaded();
    // When I compute the 2019 Brasileirão table
    const table = standings(store, "Brasileirão", 2019);
    // Then there are 20 teams and Flamengo top the table on 90 points
    expect(table.length).toBe(20);
    expect(table[0].team).toMatch(/Flamengo/i);
    expect(table[0].points).toBe(90);
    expect(table[0].wins).toBe(28);
  });

  it("Scenario: points equal 3*wins + draws for every row", () => {
    const store = givenDataLoaded();
    const table = standings(store, "Brasileirão", 2018);
    expect(table.length).toBeGreaterThan(0);
    for (const r of table) {
      expect(r.points).toBe(r.wins * 3 + r.draws);
      expect(r.wins + r.draws + r.losses).toBe(r.played);
      expect(r.goalDifference).toBe(r.goalsFor - r.goalsAgainst);
    }
  });

  it("Scenario: standings are sorted by points then goal difference", () => {
    const store = givenDataLoaded();
    const table = standings(store, "Brasileirão", 2017);
    for (let i = 1; i < table.length; i++) {
      const prev = table[i - 1];
      const cur = table[i];
      const ok =
        prev.points > cur.points ||
        (prev.points === cur.points && prev.goalDifference >= cur.goalDifference);
      expect(ok).toBe(true);
    }
  });
});
