/**
 * Shared test fixtures. Loads the real datasets once and exposes a few
 * hand-built matches/players for focused, deterministic unit scenarios.
 */
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { DataStore } from "../src/dataStore.js";
import type { Match, Player } from "../src/types.js";

const here = dirname(fileURLToPath(import.meta.url));
export const PROJECT_ROOT = join(here, "..");
export const DATA_DIR = join(PROJECT_ROOT, "data", "kaggle");

let cached: DataStore | null = null;

/** Load the full real data store once and reuse it across scenarios. */
export function realStore(): DataStore {
  if (!cached) {
    cached = new DataStore(DATA_DIR);
    cached.load();
  }
  return cached;
}

/**
 * Build a minimal match with sensible defaults for unit scenarios. When a test
 * sets `homeTeam`/`awayTeam` but not the raw variants, the raw names mirror the
 * display names (matching how real records behave when there is no suffix).
 */
export function makeMatch(overrides: Partial<Match> = {}): Match {
  const base: Match = {
    competition: "Brasileirão Série A",
    source: "test",
    date: new Date(Date.UTC(2023, 0, 1)),
    dateRaw: "2023-01-01",
    season: 2023,
    round: null,
    stage: null,
    homeTeam: "Home",
    awayTeam: "Away",
    homeTeamRaw: "Home",
    awayTeamRaw: "Away",
    homeGoals: 0,
    awayGoals: 0,
  };
  const merged = { ...base, ...overrides };
  if (overrides.homeTeam !== undefined && overrides.homeTeamRaw === undefined) {
    merged.homeTeamRaw = overrides.homeTeam;
  }
  if (overrides.awayTeam !== undefined && overrides.awayTeamRaw === undefined) {
    merged.awayTeamRaw = overrides.awayTeam;
  }
  if (overrides.homeTeamRaw !== undefined && overrides.homeTeam === undefined) {
    merged.homeTeam = overrides.homeTeamRaw;
  }
  if (overrides.awayTeamRaw !== undefined && overrides.awayTeam === undefined) {
    merged.awayTeam = overrides.awayTeamRaw;
  }
  return merged;
}

/** Build a minimal player with sensible defaults for unit scenarios. */
export function makePlayer(overrides: Partial<Player> = {}): Player {
  return {
    id: 1,
    name: "Test Player",
    age: 25,
    nationality: "Brazil",
    overall: 70,
    potential: 75,
    club: "Test FC",
    position: "ST",
    jerseyNumber: 9,
    height: "5'10",
    weight: "160lbs",
    preferredFoot: "Right",
    value: "€1M",
    wage: "€10K",
    ...overrides,
  };
}
