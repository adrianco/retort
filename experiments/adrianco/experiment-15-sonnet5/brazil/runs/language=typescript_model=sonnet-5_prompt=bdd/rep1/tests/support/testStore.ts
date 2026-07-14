import path from "node:path";
import { fileURLToPath } from "node:url";
import { SoccerDataStore } from "../../src/data/store.js";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.join(__dirname, "..", "..", "data", "kaggle");

let cached: Promise<SoccerDataStore> | null = null;

/** Loads the real dataset once per test worker and reuses it across specs (loading is the slow part, not the queries). */
export function loadTestStore(): Promise<SoccerDataStore> {
  if (!cached) {
    cached = SoccerDataStore.load(DATA_DIR);
  }
  return cached;
}
