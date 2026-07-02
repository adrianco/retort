import { describe, expect, it } from "vitest";
import { getDataset } from "../src/dataLoader.js";

describe("getDataset", () => {
  const dataset = getDataset();

  it("loads matches from all match sources", () => {
    const sources = new Set(dataset.matches.map((m) => m.source));
    expect(sources).toEqual(
      new Set(["Brasileirao", "Copa do Brasil", "Libertadores", "BR-Football", "Historical-Brasileirao"]),
    );
  });

  it("loads a plausible number of matches and players", () => {
    // Brasileirao (4180) + Historical fallback for seasons before 2012 + Copa do Brasil (1337)
    // + Libertadores (1255) + BR-Football rows not already covered elsewhere (Serie B/C + unique seasons)
    expect(dataset.matches.length).toBeGreaterThan(16000);
    expect(dataset.players.length).toBe(18207);
  });

  it("does not double-count BR-Football rows already covered by the dedicated Brasileirao/Copa do Brasil datasets", () => {
    const brFootballSerieA2019 = dataset.matches.filter(
      (m) => m.source === "BR-Football" && m.competition === "Serie A" && m.season === 2019,
    );
    expect(brFootballSerieA2019.length).toBe(0);
    // Serie B/C have no other source and should be kept in full.
    const serieB = dataset.matches.filter((m) => m.source === "BR-Football" && m.competition === "Serie B");
    expect(serieB.length).toBeGreaterThan(0);
  });

  it("dedupes Brasileirao seasons covered by the primary dataset", () => {
    const season2015 = dataset.matches.filter((m) => m.competition === "Brasileirao Serie A" && m.season === 2015);
    const sources = new Set(season2015.map((m) => m.source));
    // 2015 is covered by both Brasileirao_Matches.csv and novo_campeonato_brasileiro.csv;
    // only the primary source should be kept.
    expect(sources).toEqual(new Set(["Brasileirao"]));
  });

  it("falls back to the historical dataset for seasons only it covers", () => {
    const season2005 = dataset.matches.filter((m) => m.competition === "Brasileirao Serie A" && m.season === 2005);
    expect(season2005.length).toBeGreaterThan(0);
    const sources = new Set(season2005.map((m) => m.source));
    expect(sources).toEqual(new Set(["Historical-Brasileirao"]));
  });

  it("parses goals as numbers and dates as Date objects", () => {
    const withScore = dataset.matches.find((m) => m.homeGoals !== null && m.date !== null);
    expect(withScore).toBeDefined();
    expect(typeof withScore!.homeGoals).toBe("number");
    expect(withScore!.date).toBeInstanceOf(Date);
  });

  it("caches the dataset across calls", () => {
    expect(getDataset()).toBe(dataset);
  });
});
