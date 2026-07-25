/**
 * Step definitions.
 *
 * Steps drive the MCP tool handlers directly -- the same functions the server
 * registers -- so a passing scenario is evidence about the shipped behaviour
 * rather than about a test-only shim.
 *
 * Patterns are written in a cut-down Cucumber-expression style: `{string}` for
 * a quoted argument, `{int}` and `{float}` for numbers, and `{json}` for a
 * trailing JSON literal.
 */

import { getGraph, type SoccerGraph } from '../../src/graph/graph.js';
import { toolByName, type ToolResult } from '../../src/tools/index.js';

export interface World {
  graph: SoccerGraph;
  /** Result of the most recent successful tool call. */
  result?: ToolResult;
  /** Error message from the most recent failed tool call. */
  error?: string;
  /** Name of the most recent tool called. */
  tool?: string;
}

export function createWorld(): World {
  return { graph: getGraph() };
}

type StepFn = (world: World, ...args: string[]) => void;

interface StepDefinition {
  pattern: RegExp;
  source: string;
  fn: StepFn;
}

const definitions: StepDefinition[] = [];

function define(expression: string, fn: StepFn): void {
  definitions.push({ pattern: toRegExp(expression), source: expression, fn });
}

function toRegExp(expression: string): RegExp {
  const escaped = expression.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const body = escaped
    .replace(/\\\{string\\\}/g, '"([^"]*)"')
    .replace(/\\\{int\\\}/g, '(-?\\d+)')
    .replace(/\\\{float\\\}/g, '(-?\\d+(?:\\.\\d+)?)')
    .replace(/\\\{json\\\}/g, '(\\{.*\\}|\\[.*\\])');
  return new RegExp(`^${body}$`);
}

export function runStep(world: World, text: string): void {
  // Every pattern is tried, not just the first: two definitions matching the
  // same sentence means the step's meaning depends on declaration order, which
  // is exactly the kind of silent mis-binding a test harness must not have.
  const matches = definitions
    .map((definition) => ({ definition, match: definition.pattern.exec(text) }))
    .filter((entry): entry is { definition: StepDefinition; match: RegExpExecArray } => entry.match !== null);

  if (matches.length === 0) {
    throw new Error(
      `Undefined step: "${text}".\nKnown steps:\n${definitions.map((d) => `  ${d.source}`).join('\n')}`,
    );
  }
  if (matches.length > 1) {
    throw new Error(
      `Ambiguous step: "${text}" matches ${matches.length} definitions:\n` +
        matches.map((m) => `  ${m.definition.source}`).join('\n'),
    );
  }

  const [only] = matches;
  only!.definition.fn(world, ...only!.match.slice(1));
}

// --- Given ---------------------------------------------------------------

define('the Brazilian soccer knowledge graph is loaded', (world) => {
  if (world.graph.matches.length === 0) throw new Error('no matches were loaded');
});

define('the match data is loaded', (world) => {
  if (world.graph.matches.length === 0) throw new Error('no matches were loaded');
});

define('the player data is loaded', (world) => {
  if (world.graph.players.length === 0) throw new Error('no players were loaded');
});

// --- When ----------------------------------------------------------------

define('I call {string} with {json}', (world, tool, args) => {
  callTool(world, tool!, JSON.parse(args!));
});

define('I call {string} with no arguments', (world, tool) => {
  callTool(world, tool!, {});
});

function callTool(world: World, name: string, args: unknown): void {
  const tool = toolByName(name);
  if (!tool) throw new Error(`No such tool: ${name}`);

  world.tool = name;
  delete world.result;
  delete world.error;

  const parsed = tool.schema.safeParse(args);
  if (!parsed.success) {
    world.error = parsed.error.issues
      .map((issue) => `${issue.path.join('.') || '(root)'}: ${issue.message}`)
      .join('; ');
    return;
  }

  try {
    world.result = tool.handler(world.graph, parsed.data as never);
  } catch (error) {
    world.error = error instanceof Error ? error.message : String(error);
  }
}

// --- Then ----------------------------------------------------------------

define('the call should succeed', (world) => {
  if (world.error) throw new Error(`expected success but got error: ${world.error}`);
  if (!world.result) throw new Error('no result was produced');
});

define('the call should fail', (world) => {
  if (!world.error) throw new Error('expected an error but the call succeeded');
});

define('the error should mention {string}', (world, fragment) => {
  if (!world.error) throw new Error('expected an error but the call succeeded');
  if (!world.error.toLowerCase().includes(fragment!.toLowerCase())) {
    throw new Error(`error "${world.error}" does not mention "${fragment}"`);
  }
});

define('the answer should contain {string}', (world, fragment) => {
  const text = requireResult(world).text;
  if (!text.includes(fragment!)) {
    throw new Error(`answer does not contain "${fragment}".\n---\n${text}\n---`);
  }
});

define('the answer should not contain {string}', (world, fragment) => {
  const text = requireResult(world).text;
  if (text.includes(fragment!)) {
    throw new Error(`answer unexpectedly contains "${fragment}".\n---\n${text}\n---`);
  }
});

define('the answer should match {string}', (world, pattern) => {
  const text = requireResult(world).text;
  if (!new RegExp(pattern!).test(text)) {
    throw new Error(`answer does not match /${pattern}/.\n---\n${text}\n---`);
  }
});

define('the field {string} should equal {string}', (world, path, expected) => {
  const actual = readPath(world, path!);
  if (String(actual) !== expected) {
    throw new Error(`${path} is ${JSON.stringify(actual)}, expected "${expected}"`);
  }
});

define('the field {string} should equal {int}', (world, path, expected) => {
  const actual = requireNumber(world, path!);
  if (actual !== Number(expected)) {
    throw new Error(`${path} is ${JSON.stringify(actual)}, expected ${expected}`);
  }
});

define('the field {string} should be at least {int}', (world, path, expected) => {
  const actual = requireNumber(world, path!);
  if (!(actual >= Number(expected))) {
    throw new Error(`${path} is ${actual}, expected at least ${expected}`);
  }
});

define('the field {string} should be at most {int}', (world, path, expected) => {
  const actual = requireNumber(world, path!);
  if (!(actual <= Number(expected))) {
    throw new Error(`${path} is ${actual}, expected at most ${expected}`);
  }
});

define('the field {string} should be between {int} and {int}', (world, path, low, high) => {
  const actual = requireNumber(world, path!);
  if (!(actual >= Number(low) && actual <= Number(high))) {
    throw new Error(`${path} is ${actual}, expected between ${low} and ${high}`);
  }
});

/**
 * Numeric assertions must not accept a coerced value.
 *
 * `Number(null)`, `Number([])` and `Number(true)` are all finite, so coercing
 * would let a field that regressed from a count to `null` or `[]` satisfy
 * "should be at least 0".
 */
function requireNumber(world: World, path: string): number {
  const actual = readPath(world, path);
  if (typeof actual !== 'number' || !Number.isFinite(actual)) {
    throw new Error(`${path} is ${JSON.stringify(actual)}, which is not a number`);
  }
  return actual;
}

define('the field {string} should be true', (world, path) => {
  if (readPath(world, path!) !== true) throw new Error(`${path} is not true`);
});

define('the field {string} should be null', (world, path) => {
  const actual = readPath(world, path!);
  if (actual !== null) throw new Error(`${path} is ${JSON.stringify(actual)}, expected null`);
});

define('the list {string} should have {int} items', (world, path, expected) => {
  const value = readPath(world, path!);
  if (!Array.isArray(value)) throw new Error(`${path} is not a list`);
  if (value.length !== Number(expected)) {
    throw new Error(`${path} has ${value.length} items, expected ${expected}`);
  }
});

define('the list {string} should not be empty', (world, path) => {
  const value = readPath(world, path!);
  if (!Array.isArray(value)) throw new Error(`${path} is not a list`);
  if (value.length === 0) throw new Error(`${path} is empty`);
});

define('the list {string} should be empty', (world, path) => {
  const value = readPath(world, path!);
  if (!Array.isArray(value)) throw new Error(`${path} is not a list`);
  if (value.length !== 0) throw new Error(`${path} has ${value.length} items, expected none`);
});

define('the fields {string} should sum to the field {string}', (world, parts, total) => {
  const addends = parts!.split(',').map((p) => p.trim());
  const sum = addends.reduce((acc, p) => acc + requireNumber(world, p), 0);
  const expected = requireNumber(world, total!);
  if (sum !== expected) {
    throw new Error(`${addends.join(' + ')} = ${sum}, expected ${total} = ${expected}`);
  }
});

define('every item in {string} should have {string} of at least {int}', (world, path, field, min) => {
  forEachItem(world, path!, (item, index) => {
    const value = item[field!];
    if (typeof value !== 'number' || !(value >= Number(min))) {
      throw new Error(`${path}[${index}].${field} is ${JSON.stringify(value)}, expected >= ${min}`);
    }
  });
});

define('every item in {string} should have {string} of at most {int}', (world, path, field, max) => {
  forEachItem(world, path!, (item, index) => {
    const value = item[field!];
    if (typeof value !== 'number' || !(value <= Number(max))) {
      throw new Error(`${path}[${index}].${field} is ${JSON.stringify(value)}, expected <= ${max}`);
    }
  });
});

define('every item in {string} should have {string} equal to {string}', (world, path, field, expected) => {
  forEachItem(world, path!, (item, index) => {
    if (String(item[field!]) !== expected) {
      throw new Error(
        `${path}[${index}].${field} is ${JSON.stringify(item[field!])}, expected "${expected}"`,
      );
    }
  });
});

define('the list {string} should be sorted by {string} descending', (world, path, field) => {
  const values: number[] = [];
  forEachItem(world, path!, (item, index) => {
    const value = item[field!];
    if (typeof value !== 'number') {
      throw new Error(`${path}[${index}].${field} is not a number`);
    }
    values.push(value);
  });
  for (let i = 1; i < values.length; i++) {
    if (values[i]! > values[i - 1]!) {
      throw new Error(`${path} is not descending by ${field}: ${values[i - 1]} then ${values[i]}`);
    }
  }
});

/** Run an assertion over every element, refusing to pass on an empty list. */
function forEachItem(
  world: World,
  path: string,
  check: (item: Record<string, unknown>, index: number) => void,
): void {
  const value = readPath(world, path);
  if (!Array.isArray(value)) throw new Error(`${path} is not a list`);
  if (value.length === 0) throw new Error(`${path} is empty, so the check is vacuous`);
  value.forEach((item, index) => check(item as Record<string, unknown>, index));
}

define('every item in {string} should have a {string}', (world, path, field) => {
  const value = readPath(world, path!);
  if (!Array.isArray(value)) throw new Error(`${path} is not a list`);
  if (value.length === 0) throw new Error(`${path} is empty, so the check is vacuous`);
  value.forEach((item, index) => {
    const record = item as Record<string, unknown>;
    if (record[field!] === undefined || record[field!] === null) {
      throw new Error(`${path}[${index}] has no "${field}"`);
    }
  });
});

define('every item in {string} should involve {string}', (world, path, teamId) => {
  const value = readPath(world, path!);
  if (!Array.isArray(value)) throw new Error(`${path} is not a list`);
  if (value.length === 0) throw new Error(`${path} is empty, so the check is vacuous`);
  value.forEach((item, index) => {
    const record = item as Record<string, unknown>;
    if (record['homeTeamId'] !== teamId && record['awayTeamId'] !== teamId) {
      throw new Error(`${path}[${index}] does not involve ${teamId}`);
    }
  });
});

function requireResult(world: World): ToolResult {
  if (world.error) throw new Error(`the call failed: ${world.error}`);
  if (!world.result) throw new Error('no tool has been called yet');
  return world.result;
}

/** Read `a.b[0].c` out of the last result's structured payload. */
function readPath(world: World, path: string): unknown {
  let current: unknown = requireResult(world).data;
  for (const segment of path.split('.')) {
    const parsed = /^([^[\]]*)((?:\[\d+\])*)$/.exec(segment);
    if (!parsed) throw new Error(`bad path segment "${segment}"`);
    if (parsed[1]) {
      if (current === null || typeof current !== 'object') {
        throw new Error(`cannot read "${segment}" from ${JSON.stringify(current)}`);
      }
      current = (current as Record<string, unknown>)[parsed[1]];
    }
    for (const index of parsed[2]!.match(/\d+/g) ?? []) {
      if (!Array.isArray(current)) throw new Error(`"${segment}" is not indexable`);
      current = current[Number(index)];
    }
  }
  return current;
}
