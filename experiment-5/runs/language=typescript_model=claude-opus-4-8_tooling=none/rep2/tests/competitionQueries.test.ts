/**
 * ============================================================================
 * File: tests/competitionQueries.test.ts
 * Feature: Competition Queries (spec capability 4)
 * ----------------------------------------------------------------------------
 * Context:
 *   GWT scenarios validating league tables computed from match results,
 *   including the well-documented 2019 Brasileirão (Flamengo champions with
 *   90 points) used as a ground-truth anchor.
 * ============================================================================
 */

import { describe, it, expect, beforeAll } from "vitest";
import { KnowledgeGraph } from "../src/knowledgeGraph.js";
import { graph } from "./helpers.js";

let g: KnowledgeGraph;
beforeAll(() => {
  g = graph();
});

describe("Feature: Competition Queries", () => {
  it("Scenario: who won the 2019 Brasileirão", () => {
    // When I compute the 2019 Série A standings
    const table = g.standings("Brasileirão Série A", 2019);
    // Then Flamengo top the table with 90 points (28W 6D 4L)
    expect(table[0].team).toBe("Flamengo");
    expect(table[0].points).toBe(90);
    expect(table[0].wins).toBe(28);
    expect(table[0].draws).toBe(6);
    expect(table[0].losses).toBe(4);
  });

  it("Scenario: a Série A table has 20 teams each playing 38 games", () => {
    const table = g.standings("Brasileirão Série A", 2018);
    expect(table.length).toBe(20);
    for (const row of table) expect(row.played).toBe(38);
  });

  it("Scenario: points equal 3*wins + draws", () => {
    const table = g.standings("Brasileirão Série A", 2020);
    for (const row of table) {
      expect(row.points).toBe(row.wins * 3 + row.draws);
      expect(row.wins + row.draws + row.losses).toBe(row.played);
    }
  });

  it("Scenario: the table is ordered by points then goal difference", () => {
    const table = g.standings("Brasileirão Série A", 2017);
    for (let i = 1; i < table.length; i++) {
      const prev = table[i - 1];
      const cur = table[i];
      const ordered =
        prev.points > cur.points ||
        (prev.points === cur.points && prev.goalDifference >= cur.goalDifference);
      expect(ordered).toBe(true);
    }
  });

  it("Scenario: list available competitions and seasons", () => {
    const comps = g.listCompetitions();
    expect(comps).toContain("Brasileirão Série A");
    expect(comps).toContain("Copa do Brasil");
    expect(comps).toContain("Copa Libertadores");
    expect(g.seasons("Brasileirão Série A").length).toBeGreaterThan(5);
  });
});
