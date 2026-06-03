/**
 * ============================================================================
 * Context
 * ----------------------------------------------------------------------------
 * Module:  tests/helpers.ts
 * Purpose: Shared test fixtures. Loads the real bundled dataset once and
 *          exposes it to every BDD spec, plus tiny Given/When/Then helpers so
 *          the specs read like Gherkin scenarios (per TASK.md "Testing
 *          Approach").
 * ============================================================================
 */

import { loadDataset } from "../src/data/loader.js";
import type { Dataset } from "../src/data/types.js";

let ds: Dataset | null = null;

/** The full bundled dataset, loaded lazily and shared across specs. */
export function dataset(): Dataset {
  if (!ds) ds = loadDataset();
  return ds;
}

/** Narrative helpers — purely for readability of the BDD steps. */
export const given = <T>(_desc: string, fn: () => T): T => fn();
export const when = <T>(_desc: string, fn: () => T): T => fn();
