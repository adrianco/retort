/*
 * ============================================================================
 * Context
 * ----------------------------------------------------------------------------
 * Test helper: tests/helpers.ts
 * Purpose: Load the dataset once for the whole test run (it is cached by the
 *          loader) and expose it to the BDD test files.
 * ============================================================================
 */

import { loadDataset, type Dataset } from "../src/data/loader.js";

let ds: Dataset | null = null;

/** "Given the data is loaded" — returns the shared, cached dataset. */
export function givenDataLoaded(): Dataset {
  if (!ds) ds = loadDataset();
  return ds;
}
