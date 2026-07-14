/**
 * ============================================================================
 * Context
 * ----------------------------------------------------------------------------
 * Feature: Competition Queries
 * Covers league standings computed from match results and season summaries
 * (champion / relegation). Includes a known-answer check: Flamengo won the
 * 2019 Brasileirão (the example in TASK.md).
 * ============================================================================
 */

import { describe, it, expect } from "vitest";
import { dataset } from "./helpers.js";
import { standings, seasonSummary } from "../src/queries/competitions.js";

describe("Feature: Competition Queries", () => {
  it("Scenario: Compute 2019 Brasileirão standings (known answer)", () => {
    const ds = dataset();
    const table = standings(ds, "Brasileirão Série A", 2019);
    // Then a 20-team table is produced
    expect(table.rows.length).toBe(20);
    // And Flamengo are champions with a 90-point haul
    expect(table.rows[0].team).toMatch(/Flamengo/);
    expect(table.rows[0].points).toBe(90);
    // And every team played 38 games
    expect(table.rows.every((r) => r.played === 38)).toBe(true);
  });

  it("Scenario: standings are internally consistent", () => {
    const ds = dataset();
    const table = standings(ds, "Brasileirão Série A", 2018);
    for (const r of table.rows) {
      expect(r.wins + r.draws + r.losses).toBe(r.played);
      expect(r.points).toBe(r.wins * 3 + r.draws);
      expect(r.goalDiff).toBe(r.goalsFor - r.goalsAgainst);
    }
    // And total wins equal total losses across the league
    const wins = table.rows.reduce((s, r) => s + r.wins, 0);
    const losses = table.rows.reduce((s, r) => s + r.losses, 0);
    expect(wins).toBe(losses);
  });

  it("Scenario: Identify the season champion and relegation zone", () => {
    const ds = dataset();
    const summary = seasonSummary(ds, "Brasileirão Série A", 2019);
    expect(summary.champion).toMatch(/Flamengo/);
    expect(summary.relegated.length).toBe(4);
    expect(summary.totalTeams).toBe(20);
  });
});
