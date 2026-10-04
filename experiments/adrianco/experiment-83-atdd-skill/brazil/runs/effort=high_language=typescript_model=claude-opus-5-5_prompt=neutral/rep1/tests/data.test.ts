import { describe, expect, it } from "vitest";
import { FILES } from "../src/data.js";
import { queries } from "./helpers.js";

describe("dataset loading", () => {
  const ds = queries().ds;

  it("loads all six CSV files", () => {
    const files = ds.sources.map((s) => s.file).sort();
    expect(files).toEqual(Object.values(FILES).sort());
    const rows = Object.fromEntries(ds.sources.map((s) => [s.file, s.rows]));
    expect(rows[FILES.brasileirao]).toBe(4180);
    expect(rows[FILES.cup]).toBe(1337);
    expect(rows[FILES.libertadores]).toBe(1255);
    expect(rows[FILES.brFootball]).toBe(10296);
    expect(rows[FILES.historical]).toBe(6886);
    expect(rows[FILES.fifa]).toBe(18207);
    expect(ds.players).toHaveLength(18207);
  });

  it("every match file contributes matches", () => {
    for (const f of [FILES.brasileirao, FILES.cup, FILES.libertadores, FILES.brFootball, FILES.historical]) {
      expect(ds.matches.some((m) => m.sources.includes(f)), f).toBe(true);
    }
  });

  it("merges duplicate fixtures across files (one row per real match)", () => {
    for (let season = 2006; season <= 2022; season++) {
      const n = ds.matches.filter((m) => m.competition === "serie-a" && m.season === season).length;
      // 20-team double round robin; 2009 lacks one match and 2016's
      // Chapecoense v Atlético-MG was never played.
      expect(n, `serie-a ${season}`).toBeGreaterThanOrEqual(379);
      expect(n, `serie-a ${season}`).toBeLessThanOrEqual(380);
    }
    // A 2019 match present in three files is stored once, with all sources.
    const m = ds.matches.find(
      (x) => x.competition === "serie-a" && x.season === 2019 && x.homeId === "flamengo" && x.awayId === "gremio",
    )!;
    expect(m.sources.sort()).toEqual([FILES.brFootball, FILES.brasileirao, FILES.historical].sort());
    expect(m.arena).toBeTruthy(); // from novo_campeonato_brasileiro.csv
    expect(m.round).toBeDefined(); // from Brasileirao_Matches.csv
    expect(m.stats?.homeShots).not.toBeNull(); // from BR-Football-Dataset.csv
  });

  it("assigns the COVID-delayed 2020 season matches played in 2021 to season 2020", () => {
    const late = ds.matches.filter((m) => m.competition === "serie-a" && m.date >= "2021-01-01" && m.date <= "2021-02-28");
    expect(late.length).toBeGreaterThan(50);
    expect(late.every((m) => m.season === 2020)).toBe(true);
  });

  it("normalises dates from every file to ISO format", () => {
    expect(ds.matches.every((m) => /^\d{4}-\d{2}-\d{2}$/.test(m.date))).toBe(true);
    // novo_campeonato_brasileiro uses DD/MM/YYYY: first match 29/03/2003
    expect(ds.matches[0].date).toBe("2003-03-29");
  });

  it("keeps UTF-8 names intact", () => {
    expect(queries().teamName("gremio")).toBe("Grêmio");
    expect(queries().teamName("sao-paulo")).toBe("São Paulo");
    expect(ds.players.some((p) => p.name === "Neymar Jr")).toBe(true);
  });

  it("links Brazilian FIFA clubs to match-data teams (cross-file)", () => {
    expect(ds.brazilianClubs.has("Grêmio")).toBe(true);
    expect(ds.brazilianClubs.has("Real Madrid")).toBe(false);
    const sport = ds.players.filter((p) => p.club === "Sport Club do Recife");
    expect(sport.length).toBeGreaterThan(0);
    expect(sport.every((p) => p.teamId === "sport")).toBe(true);
    expect(ds.players.filter((p) => p.club === "América FC (Minas Gerais)").every((p) => p.teamId === "america-mg")).toBe(true);
  });

  it("loads quickly", () => {
    expect(ds.loadMs).toBeLessThan(5000);
  });
});
