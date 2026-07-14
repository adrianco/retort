/**
 * ============================================================================
 * File: tests/helpers.ts
 * Project: Brazilian Soccer MCP Server — BDD test support
 * ----------------------------------------------------------------------------
 * Context:
 *   Shared fixtures for the Behaviour-Driven (Given/When/Then) test suite.
 *   The full knowledge graph (~16k matches, ~18k players) is loaded once and
 *   memoized so each feature file can reuse it without repeated CSV parsing.
 * ============================================================================
 */

import { join } from "node:path";
import { fileURLToPath } from "node:url";
import { dirname } from "node:path";
import { KnowledgeGraph } from "../src/knowledgeGraph.js";

const here = dirname(fileURLToPath(import.meta.url));
export const DATA_DIR = join(here, "..", "data", "kaggle");

let cached: KnowledgeGraph | undefined;

/** Load (and memoize) the knowledge graph from the bundled datasets. */
export function graph(): KnowledgeGraph {
  if (!cached) cached = KnowledgeGraph.fromDirectory(DATA_DIR);
  return cached;
}
