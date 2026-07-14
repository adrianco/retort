import { describe, it, expect, beforeAll } from "vitest";
import { resolve } from "node:path";
import { loadAll } from "../src/loader.js";
import type { Dataset } from "../src/types.js";

let dataset: Dataset;

beforeAll(() => {
  dataset = loadAll(resolve(process.cwd(), "data/kaggle"));
});

describe("loader", () => {
  it("loads all matches across files", () => {
    expect(dataset.matches.length).toBeGreaterThan(20_000);
  });

  it("loads all player rows", () => {
    expect(dataset.players.length).toBeGreaterThan(18_000);
  });

  it("normalizes team names on matches", () => {
    const palmeiras = dataset.matches.filter((m) => m.homeTeam === "palmeiras" || m.awayTeam === "palmeiras");
    expect(palmeiras.length).toBeGreaterThan(100);
  });

  it("parses ISO dates", () => {
    const sample = dataset.matches.find((m) => m.competition === "Brasileirao" && m.date);
    expect(sample?.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it("parses Brazilian dates from historical Brasileirão", () => {
    const sample = dataset.matches.find((m) => m.competition === "BrasileiraoHistorical" && m.date);
    expect(sample?.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  });

  it("includes extended stats on BR-Football-Dataset", () => {
    const sample = dataset.matches.find((m) => m.competition === "BRDataset" && m.homeShots !== null && m.homeShots !== undefined);
    expect(sample?.homeShots).toBeGreaterThanOrEqual(0);
  });
});
