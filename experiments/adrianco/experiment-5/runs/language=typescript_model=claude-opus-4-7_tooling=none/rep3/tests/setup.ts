import { loadAll, defaultDataDir } from '../src/dataLoader.js';
import type { DataStore } from '../src/types.js';

/**
 * Loads the full dataset once and caches it for all tests. Tests should
 * await this in their `beforeAll`.
 */
let storePromise: Promise<DataStore> | null = null;

export function loadStore(): Promise<DataStore> {
  if (!storePromise) {
    storePromise = loadAll({ dataDir: defaultDataDir() });
  }
  return storePromise;
}
