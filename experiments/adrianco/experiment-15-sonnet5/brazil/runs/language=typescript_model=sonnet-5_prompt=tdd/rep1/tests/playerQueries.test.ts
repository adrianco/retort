import { describe, it, expect } from "vitest";
import type { Player } from "../src/types.js";
import {
  searchPlayersByName,
  findPlayersByClub,
  findPlayersByNationality,
  topRatedPlayers,
} from "../src/playerQueries.js";

const players: Player[] = [
  { id: "1", name: "Neymar Jr", nationality: "Brazil", club: "Paris Saint-Germain", overall: 92, position: "LW" },
  { id: "2", name: "Alisson", nationality: "Brazil", club: "Liverpool", overall: 89, position: "GK" },
  { id: "3", name: "Casemiro", nationality: "Brazil", club: "Real Madrid", overall: 89, position: "CDM" },
  { id: "4", name: "L. Messi", nationality: "Argentina", club: "FC Barcelona", overall: 94, position: "RF" },
  { id: "5", name: "Gabriel Barbosa", nationality: "Brazil", club: "Flamengo", overall: 80, position: "ST" },
];

describe("searchPlayersByName", () => {
  it("finds a player by exact name", () => {
    const results = searchPlayersByName(players, "Gabriel Barbosa");
    expect(results.map((p) => p.id)).toEqual(["5"]);
  });

  it("is case-insensitive and matches partial names", () => {
    const results = searchPlayersByName(players, "messi");
    expect(results.map((p) => p.id)).toEqual(["4"]);
  });

  it("returns an empty array when no player matches", () => {
    expect(searchPlayersByName(players, "Nobody")).toEqual([]);
  });
});

describe("findPlayersByClub", () => {
  it("finds players whose club matches, case-insensitively", () => {
    const results = findPlayersByClub(players, "flamengo");
    expect(results.map((p) => p.id)).toEqual(["5"]);
  });
});

describe("findPlayersByNationality", () => {
  it("finds all players of a given nationality sorted by rating descending", () => {
    const results = findPlayersByNationality(players, "Brazil");
    expect(results.map((p) => p.id)).toEqual(["1", "2", "3", "5"]);
  });
});

describe("topRatedPlayers", () => {
  it("returns players sorted by overall rating descending", () => {
    const results = topRatedPlayers(players);
    expect(results.map((p) => p.id)).toEqual(["4", "1", "2", "3", "5"]);
  });

  it("respects a limit", () => {
    const results = topRatedPlayers(players, { limit: 2 });
    expect(results.map((p) => p.id)).toEqual(["4", "1"]);
  });

  it("filters by nationality before ranking", () => {
    const results = topRatedPlayers(players, { nationality: "Brazil", limit: 2 });
    expect(results.map((p) => p.id)).toEqual(["1", "2"]);
  });

  it("filters by club before ranking", () => {
    const results = topRatedPlayers(players, { club: "Flamengo" });
    expect(results.map((p) => p.id)).toEqual(["5"]);
  });

  it("filters by position before ranking", () => {
    const results = topRatedPlayers(players, { position: "GK" });
    expect(results.map((p) => p.id)).toEqual(["2"]);
  });

  it("filters by a partial, case-insensitive name", () => {
    const results = topRatedPlayers(players, { name: "messi" });
    expect(results.map((p) => p.id)).toEqual(["4"]);
  });
});
