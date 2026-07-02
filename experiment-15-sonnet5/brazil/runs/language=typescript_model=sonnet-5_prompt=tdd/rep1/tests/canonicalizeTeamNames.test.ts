import { describe, it, expect } from "vitest";
import type { Match } from "../src/types.js";
import { canonicalizeTeamNames } from "../src/normalize.js";

function makeMatch(overrides: Partial<Match>): Match {
  return {
    id: "m1",
    source: "x",
    competition: "Brasileirão",
    date: new Date("2020-01-01T00:00:00Z"),
    season: 2020,
    homeTeam: "Home",
    awayTeam: "Away",
    homeGoals: 0,
    awayGoals: 0,
    ...overrides,
  };
}

describe("canonicalizeTeamNames", () => {
  it("unifies accented and unaccented spellings of the same team to one display name", () => {
    const matches: Match[] = [
      makeMatch({ id: "1", homeTeam: "Gremio", awayTeam: "Santos" }),
      makeMatch({ id: "2", homeTeam: "Grêmio", awayTeam: "Santos" }),
      makeMatch({ id: "3", homeTeam: "Sao Paulo", awayTeam: "São Paulo" }),
    ];
    const result = canonicalizeTeamNames(matches);
    const gremioNames = new Set([result[0].homeTeam, result[1].homeTeam]);
    expect(gremioNames.size).toBe(1);
    expect([...gremioNames][0]).toBe("Grêmio");

    const saoPauloNames = new Set([result[2].homeTeam, result[2].awayTeam]);
    expect(saoPauloNames.size).toBe(1);
  });

  it("prefers a properly-cased spelling over an ALL-CAPS variant", () => {
    const matches: Match[] = [
      makeMatch({ id: "1", homeTeam: "CSA", awayTeam: "X" }),
      makeMatch({ id: "2", homeTeam: "Csa", awayTeam: "X" }),
      makeMatch({ id: "3", homeTeam: "Csa", awayTeam: "X" }),
    ];
    const result = canonicalizeTeamNames(matches);
    expect(result.every((m) => m.homeTeam === "Csa")).toBe(true);
  });

  it("leaves already-consistent team names unchanged", () => {
    const matches: Match[] = [
      makeMatch({ id: "1", homeTeam: "Flamengo", awayTeam: "Vasco" }),
      makeMatch({ id: "2", homeTeam: "Flamengo", awayTeam: "Vasco" }),
    ];
    const result = canonicalizeTeamNames(matches);
    expect(result.every((m) => m.homeTeam === "Flamengo" && m.awayTeam === "Vasco")).toBe(true);
  });

  it("does not mutate the input matches", () => {
    const matches: Match[] = [makeMatch({ id: "1", homeTeam: "Gremio", awayTeam: "Grêmio" })];
    canonicalizeTeamNames(matches);
    expect(matches[0].homeTeam).toBe("Gremio");
  });

  it("keeps distinct same-named clubs from different states separate using state info", () => {
    const matches: Match[] = [
      ...Array.from({ length: 5 }, (_, i) =>
        makeMatch({ id: `mg-${i}`, homeTeam: "Atletico", homeTeamState: "MG", awayTeam: "Palmeiras" })),
      ...Array.from({ length: 4 }, (_, i) =>
        makeMatch({ id: `go-${i}`, homeTeam: "Atletico", homeTeamState: "GO", awayTeam: "Palmeiras" })),
      makeMatch({ id: "accent-variant", homeTeam: "Atlético", homeTeamState: "MG", awayTeam: "Santos" }),
    ];
    const result = canonicalizeTeamNames(matches);
    const mgResult = result.find((m) => m.id === "mg-0")!;
    const goResult = result.find((m) => m.id === "go-0")!;
    const accentResult = result.find((m) => m.id === "accent-variant")!;
    expect(mgResult.homeTeam).toBe(accentResult.homeTeam);
    expect(mgResult.homeTeam).not.toBe(goResult.homeTeam);
    expect(mgResult.homeTeam).toContain("MG");
    expect(goResult.homeTeam).toContain("GO");
  });

  it("does not add a state suffix when a base name is unambiguous", () => {
    const matches: Match[] = [
      makeMatch({ id: "1", homeTeam: "Palmeiras", homeTeamState: "SP", awayTeam: "Santos" }),
      makeMatch({ id: "2", homeTeam: "Palmeiras", awayTeam: "Santos" }),
    ];
    const result = canonicalizeTeamNames(matches);
    expect(result[0].homeTeam).toBe("Palmeiras");
    expect(result[1].homeTeam).toBe("Palmeiras");
  });

  it("ignores a rare stray homonym so a dominant club keeps its plain display name", () => {
    const matches: Match[] = [
      ...Array.from({ length: 12 }, (_, i) =>
        makeMatch({ id: `dominant-${i}`, homeTeam: "Flamengo", homeTeamState: "RJ", awayTeam: "Vasco" })),
      makeMatch({ id: "stray", homeTeam: "Flamengo", homeTeamState: "PI", awayTeam: "Vasco" }),
    ];
    const result = canonicalizeTeamNames(matches);
    expect(result.every((m) => m.homeTeam === "Flamengo")).toBe(true);
  });
});
