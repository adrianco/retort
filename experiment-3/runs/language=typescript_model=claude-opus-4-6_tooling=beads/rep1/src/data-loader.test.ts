import { describe, it, expect, beforeAll } from "vitest";
import { resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { loadAllData } from "./data-loader.js";
import type { DataStore } from "./types.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const DATA_DIR = resolve(__dirname, "..", "data", "kaggle");

describe("Data Loading", () => {
  let data: DataStore;

  beforeAll(() => {
    data = loadAllData(DATA_DIR);
  });

  describe("Given the match data is loaded", () => {
    it("should load thousands of matches from all CSV files", () => {
      expect(data.matches.length).toBeGreaterThan(10000);
    });

    it("should have matches with required fields", () => {
      for (const m of data.matches.slice(0, 100)) {
        expect(m.homeTeam).toBeTruthy();
        expect(m.awayTeam).toBeTruthy();
        expect(typeof m.homeGoals).toBe("number");
        expect(typeof m.awayGoals).toBe("number");
        expect(m.competition).toBeTruthy();
      }
    });

    it("should include Brasileirão matches", () => {
      const brasileirao = data.matches.filter((m) =>
        m.competition.includes("Brasileirão")
      );
      expect(brasileirao.length).toBeGreaterThan(1000);
    });

    it("should include Copa do Brasil matches", () => {
      const cup = data.matches.filter((m) =>
        m.competition.includes("Copa do Brasil")
      );
      expect(cup.length).toBeGreaterThan(500);
    });

    it("should include Copa Libertadores matches", () => {
      const libertadores = data.matches.filter((m) =>
        m.competition.includes("Libertadores")
      );
      expect(libertadores.length).toBeGreaterThan(500);
    });

    it("should parse dates correctly", () => {
      const withDates = data.matches.filter((m) => m.date);
      expect(withDates.length).toBeGreaterThan(0);
      for (const m of withDates.slice(0, 50)) {
        expect(m.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      }
    });

    it("should normalize team names", () => {
      const flamengo = data.matches.filter(
        (m) => m.homeTeam === "Flamengo" || m.awayTeam === "Flamengo"
      );
      expect(flamengo.length).toBeGreaterThan(0);
      const flamengoRJ = data.matches.filter(
        (m) => m.homeTeam === "Flamengo-RJ" || m.awayTeam === "Flamengo-RJ"
      );
      expect(flamengoRJ.length).toBe(0);
    });
  });

  describe("Given the player data is loaded", () => {
    it("should load thousands of players", () => {
      expect(data.players.length).toBeGreaterThan(15000);
    });

    it("should have players with required fields", () => {
      for (const p of data.players.slice(0, 100)) {
        expect(p.name).toBeTruthy();
        expect(typeof p.overall).toBe("number");
        expect(p.overall).toBeGreaterThan(0);
        expect(p.nationality).toBeTruthy();
      }
    });

    it("should include Brazilian players", () => {
      const brazilians = data.players.filter((p) => p.nationality === "Brazil");
      expect(brazilians.length).toBeGreaterThan(500);
    });

    it("should include known star players", () => {
      const messi = data.players.find((p) => p.name.includes("Messi"));
      expect(messi).toBeDefined();
      expect(messi!.overall).toBeGreaterThanOrEqual(90);
    });
  });
});
