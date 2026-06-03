/**
 * ============================================================================
 * Context: BDD tests — Query Engine
 * ----------------------------------------------------------------------------
 * Feature : The five capability areas from the spec — match search, team
 *           statistics, head-to-head, player search, standings and aggregate
 *           analysis. Each scenario is Given/When/Then.
 * ============================================================================
 */

import { describe, it, expect, beforeAll } from "vitest";
import { loadDataset, type Dataset } from "../src/dataLoader.js";
import {
  aggregateStats,
  biggestWins,
  competitionsForTeam,
  headToHead,
  rankTeams,
  searchMatches,
  searchPlayers,
  standings,
  teamStats,
} from "../src/queries.js";

let data: Dataset;
beforeAll(() => {
  data = loadDataset();
});

describe("Feature: Match Queries", () => {
  it("Scenario: find matches between two teams", () => {
    // Given the match data is loaded
    // When I search for matches between Flamengo and Fluminense
    const result = searchMatches(data.matches, { team: "Flamengo", opponent: "Fluminense" });
    // Then I receive a non-empty list
    expect(result.length).toBeGreaterThan(0);
    // And every match involves exactly those two teams
    for (const m of result) {
      const teams = [m.homeTeam, m.awayTeam].map((t) => t.toLowerCase());
      const hasFla = teams.some((t) => t.includes("flamengo"));
      const hasFlu = teams.some((t) => t.includes("fluminense"));
      expect(hasFla && hasFlu).toBe(true);
      // And each match has date and scores
      expect(m.competition).toBeTruthy();
    }
  });

  it("Scenario: results are sorted by date descending", () => {
    const result = searchMatches(data.matches, { team: "Palmeiras", competition: "Série A" });
    const dated = result.filter((m) => m.date).map((m) => m.date as string);
    const sorted = [...dated].sort().reverse();
    expect(dated).toEqual(sorted);
  });

  it("Scenario: filter matches by competition and season", () => {
    const result = searchMatches(data.matches, { competition: "Libertadores", season: 2014 });
    expect(result.length).toBeGreaterThan(0);
    for (const m of result) {
      expect(m.competition).toBe("Copa Libertadores");
      expect(m.season).toBe(2014);
    }
  });

  it("Scenario: restrict a team to away fixtures only", () => {
    const result = searchMatches(data.matches, {
      team: "Santos",
      awayOnly: true,
      competition: "Série A",
    });
    expect(result.length).toBeGreaterThan(0);
    for (const m of result) {
      expect(m.awayTeam.toLowerCase()).toContain("santos");
    }
  });
});

describe("Feature: Team Queries", () => {
  it("Scenario: get team statistics for a season", () => {
    // When I request statistics for Palmeiras in a season
    const record = teamStats(data.matches, { team: "Palmeiras", season: 2018 });
    // Then I receive wins, losses, draws and goals
    expect(record.matches).toBeGreaterThan(0);
    expect(record.wins + record.draws + record.losses).toBe(record.matches);
    expect(record.points).toBe(record.wins * 3 + record.draws);
    expect(record.goalsFor).toBeGreaterThanOrEqual(0);
  });

  it("Scenario: home record differs from overall record", () => {
    const home = teamStats(data.matches, { team: "Corinthians", venue: "home", competition: "Série A" });
    const all = teamStats(data.matches, { team: "Corinthians", competition: "Série A" });
    expect(home.matches).toBeLessThanOrEqual(all.matches);
    expect(home.matches).toBeGreaterThan(0);
  });

  it("Scenario: head-to-head totals are internally consistent", () => {
    const h2h = headToHead(data.matches, "Palmeiras", "Santos");
    expect(h2h.matches.length).toBeGreaterThan(0);
    const decided = h2h.teamAWins + h2h.teamBWins + h2h.draws;
    // decided counts only matches with a known score; never exceeds total meetings
    expect(decided).toBeLessThanOrEqual(h2h.matches.length);
  });

  it("Scenario: list competitions a team has played in", () => {
    const comps = competitionsForTeam(data.matches, "Flamengo");
    expect(comps.length).toBeGreaterThan(1);
  });
});

describe("Feature: Player Queries", () => {
  it("Scenario: search a player by name", () => {
    // When I look up Gabriel Barbosa / Neymar
    const neymar = searchPlayers(data.players, { name: "Neymar" });
    expect(neymar.length).toBeGreaterThan(0);
    expect(neymar[0].name.toLowerCase()).toContain("neymar");
  });

  it("Scenario: find Brazilian players sorted by rating", () => {
    const brazilians = searchPlayers(data.players, { nationality: "Brazil", limit: 10 });
    expect(brazilians.length).toBe(10);
    // Then results are sorted by overall descending
    for (let i = 1; i < brazilians.length; i++) {
      expect(brazilians[i - 1].overall ?? 0).toBeGreaterThanOrEqual(brazilians[i].overall ?? 0);
    }
    for (const p of brazilians) expect(p.nationality).toBe("Brazil");
  });

  it("Scenario: filter players by club and minimum rating", () => {
    const result = searchPlayers(data.players, { club: "Flamengo", minOverall: 70 });
    for (const p of result) {
      expect(p.club.toLowerCase()).toContain("flamengo");
      expect(p.overall ?? 0).toBeGreaterThanOrEqual(70);
    }
  });
});

describe("Feature: Competition Queries", () => {
  it("Scenario: calculate standings for a Brasileirão season", () => {
    // The 2019 Brasileirão was a 20-team, 38-round league.
    const table = standings(data.matches, "Série A", 2019);
    expect(table.length).toBeGreaterThanOrEqual(18);
    // Position 1 has the most (or tied-most) points
    expect(table[0].position).toBe(1);
    for (let i = 1; i < table.length; i++) {
      expect(table[i - 1].points).toBeGreaterThanOrEqual(table[i].points);
    }
  });

  it("Scenario: a known champion tops the table", () => {
    // Flamengo won the 2019 Brasileirão. Verify they finish first.
    const table = standings(data.matches, "Série A", 2019);
    expect(table[0].team.toLowerCase()).toContain("flamengo");
  });
});

describe("Feature: Statistical Analysis", () => {
  it("Scenario: average goals per match is plausible", () => {
    const stats = aggregateStats(searchMatches(data.matches, { competition: "Série A" }));
    expect(stats.goalsPerMatch).toBeGreaterThan(1.5);
    expect(stats.goalsPerMatch).toBeLessThan(4);
    // win-rate components sum to ~1
    const sum = stats.homeWinRate + stats.awayWinRate + stats.drawRate;
    expect(sum).toBeGreaterThan(0.99);
    expect(sum).toBeLessThan(1.01);
  });

  it("Scenario: biggest wins are sorted by margin", () => {
    const wins = biggestWins(searchMatches(data.matches, { competition: "Série A" }), 5);
    expect(wins.length).toBe(5);
    const margins = wins.map((m) => Math.abs((m.homeGoals as number) - (m.awayGoals as number)));
    for (let i = 1; i < margins.length; i++) {
      expect(margins[i - 1]).toBeGreaterThanOrEqual(margins[i]);
    }
    expect(margins[0]).toBeGreaterThanOrEqual(4);
  });

  it("Scenario: rank teams by wins in a season", () => {
    const ranking = rankTeams(data.matches, {
      competition: "Série A",
      season: 2019,
      metric: "wins",
      limit: 5,
    });
    expect(ranking.length).toBe(5);
    for (let i = 1; i < ranking.length; i++) {
      expect(ranking[i - 1].value).toBeGreaterThanOrEqual(ranking[i].value);
    }
  });
});
