import { describe, it, expect } from "vitest";
import type { Match } from "../src/types.js";
import { teamRecord, compareTeams } from "../src/teamQueries.js";

function makeMatch(overrides: Partial<Match>): Match {
  return {
    id: "m1",
    source: "Brasileirao_Matches.csv",
    competition: "Brasileirão",
    date: new Date("2022-01-01T00:00:00Z"),
    season: 2022,
    homeTeam: "Corinthians",
    awayTeam: "Santos",
    homeGoals: 1,
    awayGoals: 0,
    ...overrides,
  };
}

describe("teamRecord", () => {
  const matches: Match[] = [
    makeMatch({ id: "1", homeTeam: "Corinthians", awayTeam: "Santos", homeGoals: 2, awayGoals: 0 }),
    makeMatch({ id: "2", homeTeam: "Palmeiras", awayTeam: "Corinthians", homeGoals: 1, awayGoals: 1 }),
    makeMatch({ id: "3", homeTeam: "Corinthians", awayTeam: "Flamengo", homeGoals: 0, awayGoals: 2 }),
    makeMatch({ id: "4", homeTeam: "Corinthians", awayTeam: "Sao Paulo", season: 2021, homeGoals: 3, awayGoals: 1 }),
  ];

  it("computes wins, draws, losses and goal tallies across home and away matches", () => {
    const record = teamRecord(matches, "Corinthians");
    expect(record.matchesPlayed).toBe(4);
    expect(record.wins).toBe(2);
    expect(record.draws).toBe(1);
    expect(record.losses).toBe(1);
    expect(record.goalsFor).toBe(2 + 1 + 0 + 3);
    expect(record.goalsAgainst).toBe(0 + 1 + 2 + 1);
    expect(record.winRate).toBeCloseTo(50, 5);
  });

  it("filters to only home matches when venue is 'home'", () => {
    const record = teamRecord(matches, "Corinthians", { venue: "home" });
    expect(record.matchesPlayed).toBe(3);
    expect(record.wins).toBe(2);
    expect(record.losses).toBe(1);
  });

  it("filters to only away matches when venue is 'away'", () => {
    const record = teamRecord(matches, "Corinthians", { venue: "away" });
    expect(record.matchesPlayed).toBe(1);
    expect(record.draws).toBe(1);
  });

  it("filters by season", () => {
    const record = teamRecord(matches, "Corinthians", { season: 2021 });
    expect(record.matchesPlayed).toBe(1);
    expect(record.wins).toBe(1);
  });
});

describe("compareTeams", () => {
  const matches: Match[] = [
    makeMatch({ id: "1", homeTeam: "Palmeiras", awayTeam: "Santos", homeGoals: 2, awayGoals: 1 }),
    makeMatch({ id: "2", homeTeam: "Santos", awayTeam: "Palmeiras", homeGoals: 0, awayGoals: 0 }),
  ];

  it("returns independent records for both teams plus head-to-head", () => {
    const result = compareTeams(matches, "Palmeiras", "Santos");
    expect(result.teamA.team).toBe("Palmeiras");
    expect(result.teamB.team).toBe("Santos");
    expect(result.teamA.wins).toBe(1);
    expect(result.teamA.draws).toBe(1);
    expect(result.headToHead.teamAWins).toBe(1);
    expect(result.headToHead.draws).toBe(1);
  });
});
