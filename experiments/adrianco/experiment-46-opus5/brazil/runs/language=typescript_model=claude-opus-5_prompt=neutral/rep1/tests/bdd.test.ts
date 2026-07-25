/**
 * Runs every `.feature` file as a vitest suite.
 *
 * One `describe` per Feature and one `it` per Scenario, with the Background
 * replayed before each. Steps execute the real MCP tool handlers, so these are
 * behavioural tests of the shipped server rather than of a test double.
 */

import { readdirSync, readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { beforeAll, describe, it } from 'vitest';
import { getGraph } from '../src/graph/graph.js';
import { parseFeature } from './support/gherkin.js';
import { createWorld, runStep } from './support/steps.js';

const featuresDir = join(dirname(fileURLToPath(import.meta.url)), 'features');
const featureFiles = readdirSync(featuresDir)
  .filter((name) => name.endsWith('.feature'))
  .sort();

beforeAll(() => {
  // Parse the CSVs once, outside any scenario's timing.
  getGraph();
});

if (featureFiles.length === 0) {
  throw new Error(`No .feature files found in ${featuresDir}`);
}

for (const file of featureFiles) {
  const feature = parseFeature(readFileSync(join(featuresDir, file), 'utf8'), file);

  describe(`Feature: ${feature.name}`, () => {
    for (const scenario of feature.scenarios) {
      it(`Scenario: ${scenario.name}`, () => {
        const world = createWorld();
        for (const step of [...feature.background, ...scenario.steps]) {
          try {
            runStep(world, step.text);
          } catch (error) {
            const reason = error instanceof Error ? error.message : String(error);
            throw new Error(`${step.keyword} ${step.text}\n  ${reason}`);
          }
        }
      });
    }
  });
}
