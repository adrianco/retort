import { describe, it, expect } from "vitest";
import type { Match } from "../src/types.js";
import { averageGoalsPerMatch, homeAwayWinRates, biggestWins } from "../src/statsQueries.js";

function makeMatch(overrides: Partial<Match>): Match {
  return {
    id: "m1",
    source: "Brasileirao_Matches.csv",
    competition: "Brasileirão",
    date: new Date("2019-01-01T00:00:00Z"),
    season: 2019,
    homeTeam: "Flamengo",
    awayTeam: "Santos",
    homeGoals: 1,
    awayGoals: 0,
    ...overrides,
  };
}

describe("averageGoalsPerMatch", () => {
  it("averages total goals across all matches", () => {
    const matches: Match[] = [
      makeMatch({ id: "1", homeGoals: 2, awayGoals: 1 }),
      makeMatch({ id: "2", homeGoals: 0, awayGoals: 0 }),
      makeMatch({ id: "3", homeGoals: 3, awayGoals: 2 }),
    ];
    expect(averageGoalsPerMatch(matches)).toBeCloseTo((3 + 0 + 5) / 3, 5);
  });

  it("returns 0 for an empty match list", () => {
    expect(averageGoalsPerMatch([])).toBe(0);
  });
});

describe("homeAwayWinRates", () => {
  const matches: Match[] = [
    makeMatch({ id: "1", homeGoals: 2, awayGoals: 0 }), // home win
    makeMatch({ id: "2", homeGoals: 0, awayGoals: 1 }), // away win
    makeMatch({ id: "3", homeGoals: 1, awayGoals: 1 }), // draw
    makeMatch({ id: "4", homeGoals: 3, awayGoals: 0 }), // home win
  ];

  it("computes home win, away win and draw rates as percentages", () => {
    const rates = homeAwayWinRates(matches);
    expect(rates.homeWinRate).toBeCloseTo(50, 5);
    expect(rates.awayWinRate).toBeCloseTo(25, 5);
    expect(rates.drawRate).toBeCloseTo(25, 5);
  });
});

describe("biggestWins", () => {
  const matches: Match[] = [
    makeMatch({ id: "1", homeTeam: "Santos", awayTeam: "Bolivar", homeGoals: 8, awayGoals: 0 }),
    makeMatch({ id: "2", homeTeam: "Palmeiras", awayTeam: "Sao Paulo", homeGoals: 6, awayGoals: 0 }),
    makeMatch({ id: "3", homeTeam: "Flamengo", awayTeam: "Gremio", homeGoals: 5, awayGoals: 0 }),
    makeMatch({ id: "4", homeTeam: "Close", awayTeam: "Match", homeGoals: 1, awayGoals: 1 }),
  ];

  it("ranks matches by absolute goal margin descending", () => {
    const results = biggestWins(matches, 2);
    expect(results).toHaveLength(2);
    expect(results[0].match.id).toBe("1");
    expect(results[0].margin).toBe(8);
    expect(results[1].match.id).toBe("2");
  });

  it("excludes draws", () => {
    const results = biggestWins(matches, 10);
    expect(results.some((r) => r.match.id === "4")).toBe(false);
  });
});
