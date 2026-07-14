/**
 * Context
 * -------
 * Shared test "world" for the BDD suite. Loads the real datasets once and
 * exposes a single cached DataStore so every Given/When/Then scenario runs
 * against the actual CSV data (true behaviour-driven verification, not mocks).
 */

import { DataStore } from "../../src/dataStore.js";

let store: DataStore | null = null;

/** Given the datasets are loaded — returns the shared, cached store. */
export function givenDataLoaded(): DataStore {
  if (store === null) {
    store = new DataStore();
    store.loadAll();
  }
  return store;
}
