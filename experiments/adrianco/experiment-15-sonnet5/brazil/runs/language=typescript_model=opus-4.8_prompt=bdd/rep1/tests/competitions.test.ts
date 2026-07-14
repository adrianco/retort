import { describe, it, expect } from "vitest";
import { calculateStandings, brasileiraoStandings, brasileiraoChampion } from "../src/queries/competitions.js";
import { makeMatch, realStore } from "./fixtures.js";

describe("Calculating standings from results", () => {
  it("given a win and a draw, when a table is built, then points follow 3-for-win / 1-for-draw", () => {
    // Given: A beats B, then A draws C
    const matches = [
      makeMatch({ homeTeam: "A", awayTeam: "B", homeGoals: 1, awayGoals: 0 }),
      makeMatch({ homeTeam: "A", awayTeam: "C", homeGoals: 2, awayGoals: 2 }),
    ];
    // When
    const table = calculateStandings(matches);
    // Then: A has 4 points and tops the table
    expect(table[0]).toMatchObject({ team: "A", points: 4, position: 1 });
  });

  it("given clubs differing only by state suffix, when a table is built, then they are separate rows", () => {
    // Given: Atlético-MG and Atlético-PR each play a match
    const matches = [
      makeMatch({ homeTeamRaw: "Atlético-MG", awayTeamRaw: "X", homeGoals: 1, awayGoals: 0 }),
      makeMatch({ homeTeamRaw: "Atlético-PR", awayTeamRaw: "Y", homeGoals: 1, awayGoals: 0 }),
    ];
    // When
    const table = calculateStandings(matches);
    // Then: both Atléticos appear, not merged
    const atleticos = table.filter((r) => r.team.startsWith("Atlético"));
    expect(atleticos).toHaveLength(2);
  });
});

describe("Brasileirão season outcomes from real data", () => {
  it("given the 2019 season, when the table is built, then Flamengo are champions with 90 points", () => {
    // Given the loaded datasets
    const store = realStore();
    // When
    const champ = brasileiraoChampion(store.matches, 2019);
    // Then
    expect(champ).not.toBeNull();
    expect(champ!.team).toContain("Flamengo");
    expect(champ!.points).toBe(90);
  });

  it("given the 2019 season, when the table is built, then it has exactly 20 teams", () => {
    // Given the loaded datasets
    const store = realStore();
    // When
    const table = brasileiraoStandings(store.matches, 2019);
    // Then: no double-counting from overlapping datasets
    expect(table).toHaveLength(20);
  });
});
