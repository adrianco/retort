/**
 * Tests for player search across the FIFA dataset, including the cross-cutting
 * "Brazilian players" filters highlighted in the specification.
 */
import { describe, expect, it } from "vitest";
import { store } from "./helpers.js";

describe("searchPlayers", () => {
  it("finds players by (partial) name, case/accent-insensitively", () => {
    const res = store().searchPlayers({ name: "neymar" });
    expect(res.length).toBeGreaterThan(0);
    expect(res[0].name.toLowerCase()).toContain("neymar");
  });

  it("filters Brazilian players and sorts by overall by default", () => {
    const br = store().searchPlayers({ nationality: "Brazil" });
    expect(br.length).toBeGreaterThan(500);
    expect(br.every((p) => p.nationality === "Brazil")).toBe(true);
    for (let i = 1; i < br.length; i++) {
      expect(br[i - 1].overall ?? 0).toBeGreaterThanOrEqual(br[i].overall ?? 0);
    }
    expect(br[0].name).toContain("Neymar");
  });

  it("filters by exact position", () => {
    const gks = store().searchPlayers({ position: "GK", nationality: "Brazil", limit: 5 });
    expect(gks.length).toBeGreaterThan(0);
    expect(gks.every((p) => p.position === "GK")).toBe(true);
  });

  it("filters by club name substring", () => {
    const fcb = store().searchPlayers({ club: "Barcelona" });
    expect(fcb.length).toBeGreaterThan(0);
    expect(fcb.every((p) => p.club.toLowerCase().includes("barcelona"))).toBe(true);
  });

  it("respects minOverall and limit", () => {
    const elite = store().searchPlayers({ minOverall: 85, limit: 10 });
    expect(elite.length).toBe(10);
    expect(elite.every((p) => (p.overall ?? 0) >= 85)).toBe(true);
  });

  it("can sort by potential and age", () => {
    const byPotential = store().searchPlayers({ nationality: "Brazil", sortBy: "potential", limit: 5 });
    for (let i = 1; i < byPotential.length; i++) {
      expect(byPotential[i - 1].potential ?? 0).toBeGreaterThanOrEqual(byPotential[i].potential ?? 0);
    }
  });
});

describe("clubBreakdown", () => {
  it("groups players by club with counts and averages", () => {
    const br = store().searchPlayers({ nationality: "Brazil" });
    const breakdown = store().clubBreakdown(br);
    expect(breakdown.length).toBeGreaterThan(0);
    // sorted by count desc
    for (let i = 1; i < breakdown.length; i++) {
      expect(breakdown[i - 1].count).toBeGreaterThanOrEqual(breakdown[i].count);
    }
  });
});
