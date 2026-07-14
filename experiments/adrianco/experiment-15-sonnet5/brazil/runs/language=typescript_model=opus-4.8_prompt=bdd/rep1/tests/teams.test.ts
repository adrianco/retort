import { describe, it, expect } from "vitest";
import { teamStats } from "../src/queries/teams.js";
import { makeMatch, realStore } from "./fixtures.js";

describe("Team win/draw/loss records", () => {
  it("given a mix of results, when aggregated, then wins draws and losses are counted", () => {
    // Given: one win, one draw, one loss for Corinthians
    const matches = [
      makeMatch({ homeTeam: "Corinthians", awayTeam: "X", homeGoals: 2, awayGoals: 0 }),
      makeMatch({ homeTeam: "Y", awayTeam: "Corinthians", homeGoals: 1, awayGoals: 1 }),
      makeMatch({ homeTeam: "Corinthians", awayTeam: "Z", homeGoals: 0, awayGoals: 3 }),
    ];
    // When
    const stats = teamStats(matches, "Corinthians");
    // Then
    expect(stats).toMatchObject({ played: 3, wins: 1, draws: 1, losses: 1, points: 4 });
  });

  it("given home and away matches, when aggregated, then the home split isolates home games", () => {
    // Given: one home win, one away loss
    const matches = [
      makeMatch({ homeTeam: "Corinthians", awayTeam: "X", homeGoals: 2, awayGoals: 0 }),
      makeMatch({ homeTeam: "Z", awayTeam: "Corinthians", homeGoals: 4, awayGoals: 1 }),
    ];
    // When
    const stats = teamStats(matches, "Corinthians");
    // Then
    expect(stats.home).toMatchObject({ played: 1, wins: 1 });
    expect(stats.away).toMatchObject({ played: 1, losses: 1 });
  });

  it("given the real dataset, when computing Corinthians' 2021 home record, then it is a full season", () => {
    // Given the loaded datasets (2021 Brasileirão is complete in the data)
    const store = realStore();
    // When: home record in the 2021 Brasileirão
    const stats = teamStats(store.matches, "Corinthians", {
      season: 2021,
      competition: "Brasileirão",
    });
    // Then: a 20-team league means 19 home fixtures
    expect(stats.home.played).toBe(19);
  });
});
