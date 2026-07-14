import { describe, it, expect } from "vitest";
import {
  filterPlayers,
  rankByOverall,
  searchPlayersByName,
  summarizeByClub,
} from "../src/queries/players.js";
import { makePlayer, realStore } from "./fixtures.js";

describe("Filtering players", () => {
  it("given players of mixed nationality, when filtered by nationality, then only that nationality remains", () => {
    // Given
    const players = [
      makePlayer({ name: "A", nationality: "Brazil" }),
      makePlayer({ name: "B", nationality: "Argentina" }),
    ];
    // When
    const result = filterPlayers(players, { nationality: "Brazil" });
    // Then
    expect(result.map((p) => p.name)).toEqual(["A"]);
  });

  it("given a role word, when filtered by position 'goalkeeper', then only GKs remain", () => {
    // Given
    const players = [
      makePlayer({ name: "Keeper", position: "GK" }),
      makePlayer({ name: "Striker", position: "ST" }),
    ];
    // When
    const result = filterPlayers(players, { position: "goalkeeper" });
    // Then
    expect(result.map((p) => p.name)).toEqual(["Keeper"]);
  });
});

describe("Ranking players", () => {
  it("given players of varied rating, when ranked, then the highest overall comes first", () => {
    // Given
    const players = [
      makePlayer({ name: "Low", overall: 70 }),
      makePlayer({ name: "High", overall: 92 }),
    ];
    // When
    const result = rankByOverall(players);
    // Then
    expect(result[0].name).toBe("High");
  });
});

describe("Summarizing players by club", () => {
  it("given several players in two clubs, when summarized, then counts per club are correct", () => {
    // Given
    const players = [
      makePlayer({ club: "Flamengo", overall: 80 }),
      makePlayer({ club: "Flamengo", overall: 70 }),
      makePlayer({ club: "Santos", overall: 75 }),
    ];
    // When
    const summaries = summarizeByClub(players);
    // Then
    const flamengo = summaries.find((s) => s.club === "Flamengo");
    expect(flamengo).toMatchObject({ playerCount: 2, averageOverall: 75 });
  });
});

describe("Searching real player data", () => {
  it("given the FIFA dataset, when searching 'Neymar', then a Brazilian forward is found", () => {
    // Given the loaded datasets
    const store = realStore();
    // When
    const results = searchPlayersByName(store.players, "Neymar", 5);
    // Then
    expect(results.length).toBeGreaterThan(0);
    expect(results[0].nationality).toBe("Brazil");
  });

  it("given the FIFA dataset, when filtering Brazilians, then hundreds of players are returned", () => {
    // Given the loaded datasets
    const store = realStore();
    // When
    const brazilians = filterPlayers(store.players, { nationality: "Brazil" });
    // Then
    expect(brazilians.length).toBeGreaterThan(500);
  });
});
