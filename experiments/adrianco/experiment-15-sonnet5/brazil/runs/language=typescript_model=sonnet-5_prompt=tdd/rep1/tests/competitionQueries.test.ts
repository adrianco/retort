import { describe, it, expect } from "vitest";
import type { Match } from "../src/types.js";
import { calculateStandings } from "../src/competitionQueries.js";

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

describe("calculateStandings", () => {
  // Round robin: Flamengo beats Santos, Flamengo draws Palmeiras, Santos beats Palmeiras
  const matches: Match[] = [
    makeMatch({ id: "1", homeTeam: "Flamengo", awayTeam: "Santos", homeGoals: 2, awayGoals: 0 }),
    makeMatch({ id: "2", homeTeam: "Palmeiras", awayTeam: "Flamengo", homeGoals: 1, awayGoals: 1 }),
    makeMatch({ id: "3", homeTeam: "Santos", awayTeam: "Palmeiras", homeGoals: 2, awayGoals: 1 }),
    makeMatch({ id: "4", competition: "Copa do Brasil", homeTeam: "Flamengo", awayTeam: "Santos", homeGoals: 5, awayGoals: 0 }),
    makeMatch({ id: "5", season: 2018, homeTeam: "Flamengo", awayTeam: "Santos", homeGoals: 5, awayGoals: 0 }),
  ];

  it("filters to the requested competition and season only", () => {
    const standings = calculateStandings(matches, "Brasileirão", 2019);
    const totalPlayed = standings.reduce((sum, row) => sum + row.played, 0);
    expect(totalPlayed).toBe(6); // 3 matches x 2 teams each
  });

  it("awards 3 points for a win and 1 for a draw", () => {
    const standings = calculateStandings(matches, "Brasileirão", 2019);
    const flamengo = standings.find((r) => r.team === "Flamengo")!;
    const santos = standings.find((r) => r.team === "Santos")!;
    const palmeiras = standings.find((r) => r.team === "Palmeiras")!;

    expect(flamengo.points).toBe(4); // 1 win + 1 draw
    expect(santos.points).toBe(3); // 1 win + 1 loss
    expect(palmeiras.points).toBe(1); // 1 draw + 1 loss
  });

  it("sorts standings by points descending, then goal difference", () => {
    const standings = calculateStandings(matches, "Brasileirão", 2019);
    expect(standings.map((r) => r.team)).toEqual(["Flamengo", "Santos", "Palmeiras"]);
  });

  it("computes goal difference and goals for/against correctly", () => {
    const standings = calculateStandings(matches, "Brasileirão", 2019);
    const flamengo = standings.find((r) => r.team === "Flamengo")!;
    expect(flamengo.goalsFor).toBe(3);
    expect(flamengo.goalsAgainst).toBe(1);
    expect(flamengo.goalDifference).toBe(2);
  });
});
