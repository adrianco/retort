import { describe, it, expect } from "vitest";
import { findMatches, headToHead, lastMeeting } from "../src/queries/matches.js";
import { makeMatch, realStore } from "./fixtures.js";

describe("Finding matches by criteria", () => {
  it("given matches across seasons, when filtered by season, then only that season is returned", () => {
    // Given
    const matches = [
      makeMatch({ season: 2022 }),
      makeMatch({ season: 2023 }),
      makeMatch({ season: 2023 }),
    ];
    // When
    const result = findMatches(matches, { season: 2023 });
    // Then
    expect(result).toHaveLength(2);
  });

  it("given a team on either side, when filtered by team, then home and away appearances match", () => {
    // Given
    const matches = [
      makeMatch({ homeTeam: "Flamengo", awayTeam: "Vasco" }),
      makeMatch({ homeTeam: "Santos", awayTeam: "Flamengo" }),
      makeMatch({ homeTeam: "Santos", awayTeam: "Vasco" }),
    ];
    // When
    const result = findMatches(matches, { team: "Flamengo" });
    // Then
    expect(result).toHaveLength(2);
  });

  it("given a date range, when filtered, then only matches within the range are returned", () => {
    // Given
    const matches = [
      makeMatch({ date: new Date(Date.UTC(2020, 5, 1)) }),
      makeMatch({ date: new Date(Date.UTC(2023, 5, 1)) }),
    ];
    // When
    const result = findMatches(matches, { from: "2023-01-01", to: "2023-12-31" });
    // Then
    expect(result).toHaveLength(1);
  });
});

describe("Head-to-head records", () => {
  it("given three matches between two teams, when computed, then wins/draws are tallied per team", () => {
    // Given: A beats B, B beats A, and a draw
    const matches = [
      makeMatch({ homeTeam: "A", awayTeam: "B", homeGoals: 2, awayGoals: 1 }),
      makeMatch({ homeTeam: "B", awayTeam: "A", homeGoals: 3, awayGoals: 0 }),
      makeMatch({ homeTeam: "A", awayTeam: "B", homeGoals: 1, awayGoals: 1 }),
    ];
    // When
    const { record } = headToHead(matches, "A", "B");
    // Then
    expect(record).toMatchObject({ matches: 3, teamAWins: 1, teamBWins: 1, draws: 1 });
  });

  it("given an away win for team A, when computed, then A's goals are oriented correctly", () => {
    // Given: A wins away 3-0
    const matches = [makeMatch({ homeTeam: "B", awayTeam: "A", homeGoals: 0, awayGoals: 3 })];
    // When
    const { record } = headToHead(matches, "A", "B");
    // Then
    expect(record.teamAWins).toBe(1);
    expect(record.teamAGoals).toBe(3);
  });
});

describe("Last meeting between two real teams", () => {
  it("given the real dataset, when asked for the last Flamengo-Corinthians match, then a played match is returned", () => {
    // Given the loaded datasets
    const store = realStore();
    // When
    const match = lastMeeting(store.matches, "Flamengo", "Corinthians");
    // Then
    expect(match).not.toBeNull();
    expect(match!.homeGoals).not.toBeNull();
  });
});
