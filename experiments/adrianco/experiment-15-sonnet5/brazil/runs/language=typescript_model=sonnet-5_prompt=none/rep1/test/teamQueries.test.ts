import { describe, expect, it } from "vitest";
import { getDataset } from "../src/dataLoader.js";
import { teamCompetitions, teamRecord } from "../src/queries/teamQueries.js";

const dataset = getDataset();

describe("teamRecord", () => {
  it("computes a consistent W/D/L breakdown", () => {
    const record = teamRecord(dataset, "Corinthians", { competition: "Brasileirao", season: 2022 });
    expect(record.wins + record.draws + record.losses).toBe(record.matchesPlayed);
    expect(record.winRatePct).toBeCloseTo((record.wins / record.matchesPlayed) * 100, 5);
  });

  it("restricts to home games when venue is 'home'", () => {
    const home = teamRecord(dataset, "Corinthians", { competition: "Brasileirao", season: 2022, venue: "home" });
    const all = teamRecord(dataset, "Corinthians", { competition: "Brasileirao", season: 2022, venue: "all" });
    expect(home.matchesPlayed).toBeLessThan(all.matchesPlayed);
    expect(home.matchesPlayed).toBeGreaterThan(0);
  });

  it("home + away matches should sum to the 'all' venue total", () => {
    const home = teamRecord(dataset, "Flamengo", { competition: "Brasileirao", season: 2019, venue: "home" });
    const away = teamRecord(dataset, "Flamengo", { competition: "Brasileirao", season: 2019, venue: "away" });
    const all = teamRecord(dataset, "Flamengo", { competition: "Brasileirao", season: 2019, venue: "all" });
    expect(home.matchesPlayed + away.matchesPlayed).toBe(all.matchesPlayed);
    expect(home.wins + away.wins).toBe(all.wins);
  });

  it("returns zeroed record for an unknown team", () => {
    const record = teamRecord(dataset, "Totally Fictional FC");
    expect(record.matchesPlayed).toBe(0);
    expect(record.winRatePct).toBe(0);
  });
});

describe("teamCompetitions", () => {
  it("lists competitions a well-known team has played in", () => {
    const result = teamCompetitions(dataset, "Palmeiras");
    const names = result.competitions.map((c) => c.competition);
    expect(names).toContain("Brasileirao Serie A");
    expect(names).toContain("Copa Libertadores");
  });
});
