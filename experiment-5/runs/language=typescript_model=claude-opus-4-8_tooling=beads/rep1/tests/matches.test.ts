/**
 * ============================================================================
 * Context
 * ----------------------------------------------------------------------------
 * Feature: Match Queries  (mirrors the Gherkin in TASK.md "Testing Approach")
 * Covers searching matches between two teams, by competition / season / date,
 * and head-to-head records.
 * ============================================================================
 */

import { describe, it, expect } from "vitest";
import { dataset, given, when } from "./helpers.js";
import { searchMatches, headToHead } from "../src/queries/matches.js";

describe("Feature: Match Queries", () => {
  it("Scenario: Find matches between two teams", () => {
    const ds = given("the match data is loaded", () => dataset());
    const res = when("I search for matches between Flamengo and Fluminense", () =>
      searchMatches(ds, { team: "Flamengo", opponent: "Fluminense" })
    );
    // Then I should receive a list of matches
    expect(res.count).toBeGreaterThan(10);
    // And each match should have date, scores, and competition
    for (const m of res.matches) {
      expect(m.competition).toBeTruthy();
      expect(m.homeGoal).not.toBeNull();
      expect(m.awayGoal).not.toBeNull();
    }
  });

  it("Scenario: Find matches a team played in a given season", () => {
    const ds = dataset();
    const res = searchMatches(ds, { team: "Palmeiras", season: 2019 });
    expect(res.count).toBeGreaterThan(0);
    expect(res.matches.every((m) => m.season === 2019)).toBe(true);
  });

  it("Scenario: Filter matches by competition", () => {
    const ds = dataset();
    const res = searchMatches(ds, { competition: "Copa Libertadores" });
    expect(res.count).toBeGreaterThan(0);
    expect(res.matches.every((m) => m.competition === "Copa Libertadores")).toBe(
      true
    );
  });

  it("Scenario: Filter matches by date range", () => {
    const ds = dataset();
    const res = searchMatches(ds, { from: "2019-01-01", to: "2019-12-31" });
    expect(res.count).toBeGreaterThan(0);
    for (const m of res.matches) {
      expect(m.date!.getUTCFullYear()).toBe(2019);
    }
  });

  it("Scenario: results are sorted most-recent first", () => {
    const ds = dataset();
    const res = searchMatches(ds, { team: "Santos" }, 50);
    const times = res.matches.map((m) => m.date?.getTime() ?? -Infinity);
    const sorted = [...times].sort((a, b) => b - a);
    expect(times).toEqual(sorted);
  });

  it("Scenario: Head-to-head record between rivals", () => {
    const ds = dataset();
    const h2h = headToHead(ds, "Palmeiras", "Santos");
    // Then the totals are internally consistent
    expect(h2h.total).toBeGreaterThan(0);
    expect(h2h.teamAWins + h2h.teamBWins + h2h.draws).toBe(h2h.total);
    expect(h2h.text).toContain("Palmeiras");
    expect(h2h.text).toContain("Santos");
  });

  it("Scenario: Head-to-head is symmetric in match count", () => {
    const ds = dataset();
    const ab = headToHead(ds, "Corinthians", "São Paulo");
    const ba = headToHead(ds, "São Paulo", "Corinthians");
    expect(ab.total).toBe(ba.total);
    expect(ab.teamAWins).toBe(ba.teamBWins);
  });
});
