import { beforeAll, describe, expect, it } from "vitest";
import { SoccerDataStore } from "../src/data-store.js";
import { NaturalLanguageQuery } from "../src/query.js";
import { SoccerService } from "../src/service.js";

let store: SoccerDataStore;
let service: SoccerService;

beforeAll(async () => {
  store = await SoccerDataStore.load();
  service = new SoccerService(store);
}, 10_000);

describe("bundled datasets", () => {
  it("loads and queries all six supplied CSV files", () => {
    expect(store.summary.matches).toBeGreaterThan(18_000);
    expect(store.summary.players).toBe(18_207);
    expect(store.summary.sources).toMatchObject({
      "Brasileirao_Matches.csv": expect.any(Number),
      "Brazilian_Cup_Matches.csv": expect.any(Number),
      "Libertadores_Matches.csv": expect.any(Number),
      "BR-Football-Dataset.csv": expect.any(Number),
      "novo_campeonato_brasileiro.csv": expect.any(Number)
    });
    expect(service.searchPlayers({ nationality: "Brazil", limit: 1 }).total).toBeGreaterThan(800);
  });

  it("calculates the known 2019 Brasileirão leader without overlap inflation", () => {
    const table = service.standings(2019);
    expect(table[0]).toMatchObject({ team: "Flamengo-RJ", points: 90, wins: 28, draws: 6, losses: 4 });
    expect(table).toHaveLength(20);
  });

  it("handles cross-file search and analysis within the performance budget", () => {
    const started = performance.now();
    const headToHead = service.headToHead("Flamengo", "Fluminense");
    const stats = service.statistics({ competition: "Brasileirão" });
    const players = service.searchPlayers({ nationality: "Brazil", minOverall: 85 });
    const elapsed = performance.now() - started;
    expect(headToHead.matches).toBeGreaterThan(20);
    expect(stats.matches).toBeGreaterThan(4_000);
    expect(players.items[0]?.name).toBe("Neymar Jr");
    expect(elapsed).toBeLessThan(2_000);
  });

  it("produces a formatted natural-language answer", () => {
    const response = new NaturalLanguageQuery(service).answer("Who won the 2019 Brasileirão?");
    expect(response.intent).toBe("standings");
    expect(response.answer).toContain("90 points");
  });
});
