/*
 * ============================================================================
 * Context
 * ----------------------------------------------------------------------------
 * Test:    tests/sample-questions.test.ts
 * Purpose: Coverage test for the success criterion "At least 20 sample
 *          questions can be answered". Each `it` maps a natural-language
 *          question from the spec to the query-layer call that answers it and
 *          asserts a non-empty, sensible result.
 * ============================================================================
 */

import { describe, it, expect } from "vitest";
import { givenDataLoaded } from "./helpers.js";
import { findMatches, headToHead } from "../src/queries/matches.js";
import {
  teamRecord,
  teamCompetitions,
} from "../src/queries/teams.js";
import { findPlayers, playersByClub } from "../src/queries/players.js";
import {
  standings,
  competitionSummary,
  availableSeasons,
} from "../src/queries/competitions.js";
import {
  aggregateStats,
  biggestWins,
  topScoringTeams,
  bestVenueRecords,
} from "../src/queries/statistics.js";

const ds = givenDataLoaded();

describe("Feature: Answer 20+ sample questions from the specification", () => {
  it("Q1: Show me all Flamengo vs Fluminense matches", () => {
    expect(findMatches(ds, { team: "Flamengo", team2: "Fluminense" }).length).toBeGreaterThan(0);
  });

  it("Q2: What matches did Palmeiras play in 2019?", () => {
    expect(findMatches(ds, { team: "Palmeiras", season: 2019 }).length).toBeGreaterThan(0);
  });

  it("Q3: Find all Copa do Brasil matches", () => {
    expect(findMatches(ds, { competition: "Copa do Brasil" }).length).toBeGreaterThan(0);
  });

  it("Q4: What is Corinthians' home record in 2022?", () => {
    const r = teamRecord(ds, "Corinthians", { season: 2022, venue: "home" });
    expect(r.played).toBeGreaterThan(0);
  });

  it("Q5: Which team scored the most goals in Serie A 2019?", () => {
    const top = topScoringTeams(ds, { competition: "Brasileirão Série A", season: 2019 }, 1);
    expect(top[0].goalsFor).toBeGreaterThan(0);
  });

  it("Q6: Compare Palmeiras and Santos head-to-head", () => {
    const h = headToHead(ds, "Palmeiras", "Santos");
    expect(h.totalMatches).toBeGreaterThan(0);
  });

  it("Q7: Find all Brazilian players in the dataset", () => {
    expect(findPlayers(ds, { nationality: "Brazil", limit: 2000 }).length).toBeGreaterThan(500);
  });

  it("Q8: Who are the highest-rated players at Grêmio?", () => {
    const ps = findPlayers(ds, { club: "Gremio", sortBy: "overall" });
    expect(ps.length).toBeGreaterThan(0);
  });

  it("Q9: Show me all forwards (ST) from the dataset", () => {
    expect(findPlayers(ds, { position: "ST", limit: 10 }).length).toBeGreaterThan(0);
  });

  it("Q10: Who won the 2019 Brasileirão?", () => {
    expect(competitionSummary(ds, "Brasileirão Série A", 2019).champion).toBe("Flamengo");
  });

  it("Q11: Which teams were relegated in 2019?", () => {
    expect(competitionSummary(ds, "Brasileirão Série A", 2019).relegated.length).toBe(4);
  });

  it("Q12: What's the average goals per match in the Brasileirão?", () => {
    expect(aggregateStats(ds, { competition: "Brasileirão Série A" }).avgGoalsPerMatch).toBeGreaterThan(2);
  });

  it("Q13: Which team has the best home record (2019)?", () => {
    expect(bestVenueRecords(ds, "home", { competition: "Brasileirão Série A", season: 2019 }, { limit: 1 }).length).toBe(1);
  });

  it("Q14: Show me the biggest wins in the dataset", () => {
    expect(biggestWins(ds, {}, 5).length).toBe(5);
  });

  it("Q15: When did Flamengo last play Corinthians?", () => {
    const m = findMatches(ds, { team: "Flamengo", team2: "Corinthians", limit: 1 });
    expect(m[0].date).toBeTruthy();
  });

  it("Q16: Who is Gabriel Jesus? (name lookup)", () => {
    expect(findPlayers(ds, { name: "Gabriel Jesus" }).length).toBeGreaterThanOrEqual(1);
  });

  it("Q17: Which players play for Grêmio?", () => {
    expect(findPlayers(ds, { club: "Gremio" }).length).toBeGreaterThan(0);
  });

  it("Q18: What competitions has Palmeiras played in?", () => {
    expect(teamCompetitions(ds, "Palmeiras").length).toBeGreaterThan(0);
  });

  it("Q19: Who are the top Brazilian players?", () => {
    expect(findPlayers(ds, { nationality: "Brazil", limit: 1 })[0].name).toBe("Neymar Jr");
  });

  it("Q20: Compare the 2018 and 2019 seasons (avg goals)", () => {
    const a2018 = aggregateStats(ds, { competition: "Brasileirão Série A", season: 2018 });
    const a2019 = aggregateStats(ds, { competition: "Brasileirão Série A", season: 2019 });
    expect(a2018.scoredMatches).toBeGreaterThan(0);
    expect(a2019.scoredMatches).toBeGreaterThan(0);
  });

  it("Q21: What is the 2019 Brasileirão final standings table?", () => {
    expect(standings(ds, "Brasileirão Série A", 2019)).toHaveLength(20);
  });

  it("Q22: Which seasons of the Libertadores are available?", () => {
    expect(availableSeasons(ds, "Copa Libertadores").length).toBeGreaterThan(0);
  });

  it("Q23: Brazilian players grouped by club (cross-file insight)", () => {
    expect(playersByClub(ds, { nationality: "Brazil", limit: 5 }).length).toBeGreaterThan(0);
  });

  it("Q24: Find Santos away matches in 2019", () => {
    const m = findMatches(ds, { team: "Santos", side: "away", season: 2019 });
    expect(m.length).toBeGreaterThan(0);
  });
});
