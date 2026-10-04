import { describe, expect, it } from "vitest";
import { MATCH_SOURCES } from "../src/data.js";
import { getKb } from "./helpers.js";

describe("dataset loading", () => {
  const kb = getKb();
  const { stats } = kb.data;

  it("loads all six CSV files", () => {
    // Rows with an unplayed result ("NA" score) are skipped; every other row is loaded.
    expect(stats.rowsPerSource["Brasileirao_Matches.csv"]).toBe(4098); // 4,180 rows, 82 unplayed
    expect(stats.rowsPerSource["Brazilian_Cup_Matches.csv"]).toBeGreaterThan(1300);
    expect(stats.rowsPerSource["Libertadores_Matches.csv"]).toBe(1253); // 1,255 rows, 2 without a score
    expect(stats.rowsPerSource["BR-Football-Dataset.csv"]).toBe(10296);
    expect(stats.rowsPerSource["novo_campeonato_brasileiro.csv"]).toBe(6886);
    expect(stats.rowsPerSource["fifa_data.csv"]).toBe(18207);
    expect(kb.data.players).toHaveLength(18207);
  });

  it("every match file contributes queryable matches", () => {
    for (const src of MATCH_SOURCES) {
      expect(kb.data.matches.some((m) => m.source === src), src).toBe(true);
    }
  });

  it("de-duplicates fixtures that appear in several files", () => {
    // 2012-2019 Série A appears in both Brasileirao_Matches.csv and novo_campeonato_brasileiro.csv.
    const novo2015 = kb.data.matches.filter((m) => m.source === "novo_campeonato_brasileiro.csv" && m.season === 2015);
    expect(novo2015).toHaveLength(380);
    expect(novo2015.every((m) => m.duplicateOf)).toBe(true);
    // A full Série A season has 380 unique matches.
    for (const season of [2010, 2015, 2019, 2021]) {
      expect(kb.data.canonical.filter((m) => m.competition === "brasileirao" && m.season === season)).toHaveLength(380);
    }
  });

  it("merges extra statistics from BR-Football into canonical matches", () => {
    const fla = kb.findMatches({ team: "Flamengo", season: 2019, competition: "brasileirao" });
    expect(fla.some((m) => m.stats?.homeShots !== undefined)).toBe(true);
    expect(fla.some((m) => m.stadium)).toBe(true);
  });

  it("parses every match date into ISO format", () => {
    for (const m of kb.data.matches) if (m.date) expect(m.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
    const novo = kb.data.matches.find((m) => m.source === "novo_campeonato_brasileiro.csv")!;
    expect(novo.date).toBe("2003-03-29");
  });

  it("keeps UTF-8 characters intact", () => {
    expect(kb.teamName("gremio")).toBe("Grêmio");
    expect(kb.teamName("sao-paulo")).toBe("São Paulo");
    expect(kb.data.players.some((p) => p.club === "Grêmio")).toBe(true);
    expect(kb.data.matches.some((m) => m.stadium === "Maracanã")).toBe(true);
  });

  it("loads quickly", () => {
    expect(stats.loadMs).toBeLessThan(5000);
  });
});
