#!/usr/bin/env node
/**
 * A small CLI that calls the same tool handlers the MCP server exposes.
 *
 * Useful for exercising the graph without an MCP client:
 *
 *   npm run ask -- head_to_head '{"teamA":"Flamengo","teamB":"Fluminense"}'
 *   npm run ask -- competition_standings '{"season":2019}'
 *   npm run ask -- --list
 */

import { getGraph } from '../graph/graph.js';
import { TOOLS, toolByName } from '../tools/index.js';

function usage(): string {
  return [
    'Usage: npm run ask -- <tool> [json-arguments]',
    '       npm run ask -- --list',
    '',
    'Tools:',
    ...TOOLS.map((tool) => `  ${tool.name.padEnd(24)} ${tool.title}`),
  ].join('\n');
}

function main(): number {
  const [name, rawArgs] = process.argv.slice(2);

  if (!name || name === '--help' || name === '-h' || name === '--list') {
    console.log(usage());
    return name ? 0 : 1;
  }

  const tool = toolByName(name);
  if (!tool) {
    console.error(`Unknown tool "${name}".\n\n${usage()}`);
    return 1;
  }

  let parsedArgs: unknown = {};
  if (rawArgs) {
    try {
      parsedArgs = JSON.parse(rawArgs);
    } catch (error) {
      console.error(`Arguments must be JSON: ${(error as Error).message}`);
      return 1;
    }
  }

  const input = tool.schema.safeParse(parsedArgs);
  if (!input.success) {
    console.error(`Invalid arguments for ${name}:`);
    for (const issue of input.error.issues) {
      console.error(`  ${issue.path.join('.') || '(root)'}: ${issue.message}`);
    }
    return 1;
  }

  try {
    console.log(tool.handler(getGraph(), input.data as never).text);
    return 0;
  } catch (error) {
    console.error(error instanceof Error ? error.message : String(error));
    return 1;
  }
}

// `process.exit` truncates output that is still buffered, which through a pipe
// (as `npm run ask` always is) cuts anything past ~64 KB mid-line while still
// reporting success. Setting the code instead lets Node flush and exit
// normally.
process.exitCode = main();
