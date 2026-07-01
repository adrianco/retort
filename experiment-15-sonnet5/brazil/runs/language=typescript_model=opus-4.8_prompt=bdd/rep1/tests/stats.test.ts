import { describe, it, expect } from "vitest";
import { aggregateStats, biggestWins, topScoringTeams } from "../src/queries/stats.js";
import { makeMatch, realStore } from "./fixtures.js";

describe("Aggregate match statistics", () => {
  it("given three matches, when aggregated, then average goals per match is correct", () => {
    // Given: total 6 goals over 3 matches
    const matches = [
      makeMatch({ homeGoals: 2, awayGoals: 1 }),
      makeMatch({ homeGoals: 1, awayGoals: 1 }),
      makeMatch({ homeGoals: 0, awayGoals: 1 }),
    ];
    // When
    const agg = aggregateStats(matches);
    // Then
    expect(agg.averageGoalsPerMatch).toBe(2);
  });

  it("given a home win and an away win, when aggregated, then win rates split evenly", () => {
    // Given
    const matches = [
      makeMatch({ homeGoals: 3, awayGoals: 0 }),
      makeMatch({ homeGoals: 0, awayGoals: 2 }),
    ];
    // When
    const agg = aggregateStats(matches);
    // Then
    expect(agg.homeWins).toBe(1);
    expect(agg.awayWins).toBe(1);
    expect(agg.homeWinRate).toBeCloseTo(0.5);
  });
});

describe("Biggest wins", () => {
  it("given matches of varied margins, when ranked, then the largest margin comes first", () => {
    // Given
    const matches = [
      makeMatch({ homeTeam: "A", awayTeam: "B", homeGoals: 2, awayGoals: 1 }),
      makeMatch({ homeTeam: "C", awayTeam: "D", homeGoals: 8, awayGoals: 0 }),
    ];
    // When
    const wins = biggestWins(matches, {}, 5);
    // Then
    expect(wins[0].margin).toBe(8);
    expect(wins[0].match.homeTeam).toBe("C");
  });
});

describe("Top scoring teams", () => {
  it("given matches, when totalled, then the highest-scoring team ranks first", () => {
    // Given: A scores 3+2, B scores 0+1
    const matches = [
      makeMatch({ homeTeam: "A", awayTeam: "B", homeGoals: 3, awayGoals: 0 }),
      makeMatch({ homeTeam: "B", awayTeam: "A", homeGoals: 1, awayGoals: 2 }),
    ];
    // When
    const totals = topScoringTeams(matches, {}, 5);
    // Then
    expect(totals[0].team).toBe("A");
    expect(totals[0].goalsFor).toBe(5);
  });
});

describe("Aggregate statistics over real data", () => {
  it("given the real Brasileirão, when aggregated, then average goals per match is football-plausible", () => {
    // Given the loaded datasets
    const store = realStore();
    // When
    const agg = aggregateStats(store.matches, { competition: "Brasileirão" });
    // Then: real leagues sit roughly between 2 and 3 goals per game
    expect(agg.averageGoalsPerMatch).toBeGreaterThan(2);
    expect(agg.averageGoalsPerMatch).toBeLessThan(3.5);
  });
});
