/**
 * tests/fixture.ts
 * -----------------------------------------------------------------------------
 * CONTEXT
 *   Shared test fixture. Loads the real dataset once and exposes it to every
 *   BDD spec, so the "Given the data is loaded" step is a fast cached lookup.
 * -----------------------------------------------------------------------------
 */

import { loadDataset } from "../src/data/loader.js";
import type { Dataset } from "../src/types.js";

let ds: Dataset | null = null;

/** Given the full dataset is loaded (cached across all specs). */
export function givenDataset(): Dataset {
  if (!ds) ds = loadDataset();
  return ds;
}
