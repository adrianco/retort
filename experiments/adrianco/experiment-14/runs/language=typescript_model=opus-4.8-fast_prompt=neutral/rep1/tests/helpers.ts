/**
 * Shared test helpers — builds the full store once and reuses it across the
 * suite (loading ~19k matches + ~18k players is the expensive part, so we pay
 * it a single time).
 */
import { createStore } from "../src/data.js";
import type { SoccerStore } from "../src/store.js";

let cached: SoccerStore | null = null;

export function store(): SoccerStore {
  if (!cached) cached = createStore();
  return cached;
}
