import { describe, expect, it } from "vitest";
import { getDataset } from "../src/dataLoader.js";
import { brazilianPlayersByClub, playersByClub, searchPlayers } from "../src/queries/playerQueries.js";

const dataset = getDataset();

describe("searchPlayers", () => {
  it("finds a well-known player by name", () => {
    const result = searchPlayers(dataset, { name: "Neymar" });
    expect(result.total).toBeGreaterThan(0);
    expect(result.players[0].name).toContain("Neymar");
  });

  it("filters by nationality", () => {
    const result = searchPlayers(dataset, { nationality: "Brazil", limit: 100 });
    expect(result.total).toBeGreaterThan(0);
    for (const p of result.players) {
      expect(p.nationality).toBe("Brazil");
    }
  });

  it("sorts by Overall rating descending", () => {
    const result = searchPlayers(dataset, { nationality: "Brazil", limit: 20 });
    for (let i = 1; i < result.players.length; i++) {
      expect(result.players[i - 1].overall ?? 0).toBeGreaterThanOrEqual(result.players[i].overall ?? 0);
    }
  });

  it("filters by position", () => {
    const result = searchPlayers(dataset, { position: "GK", limit: 50 });
    expect(result.total).toBeGreaterThan(0);
    for (const p of result.players) {
      expect(p.position).toBe("GK");
    }
  });
});

describe("playersByClub", () => {
  it("prefers an exact club match over substring matches", () => {
    const result = playersByClub(dataset, "Santos");
    for (const p of result.topPlayers) {
      expect(p.club).toBe("Santos");
    }
  });
});

describe("brazilianPlayersByClub", () => {
  it("groups Brazilian players by matching club names", () => {
    const rows = brazilianPlayersByClub(dataset, ["Santos", "Cruzeiro", "Fluminense"]);
    expect(rows.length).toBeGreaterThan(0);
    for (const row of rows) {
      expect(row.playerCount).toBeGreaterThan(0);
    }
  });
});
