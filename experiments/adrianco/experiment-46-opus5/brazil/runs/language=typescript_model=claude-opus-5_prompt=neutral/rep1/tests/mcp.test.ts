/**
 * End-to-end MCP protocol test.
 *
 * A real SDK client is connected to the real server over an in-memory
 * transport, so this covers the parts the direct handler tests cannot: the
 * tool manifest a client actually sees, JSON-Schema generation from the Zod
 * shapes, argument validation at the protocol boundary, and the shape of both
 * successful and failed tool results.
 */

import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';
import { getGraph } from '../src/graph/graph.js';
import { createServer } from '../src/server.js';
import { TOOLS } from '../src/tools/index.js';

let client: Client;

beforeAll(async () => {
  const server = createServer(getGraph());
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  client = new Client({ name: 'test-client', version: '1.0.0' });
  await Promise.all([server.connect(serverTransport), client.connect(clientTransport)]);
});

afterAll(async () => {
  await client?.close();
});

function textOf(result: { content?: unknown }): string {
  const content = (result.content ?? []) as Array<{ type: string; text?: string }>;
  return content
    .filter((block) => block.type === 'text')
    .map((block) => block.text ?? '')
    .join('\n');
}

describe('MCP protocol surface', () => {
  it('advertises every tool with a description and an object schema', async () => {
    const { tools } = await client.listTools();
    expect(tools).toHaveLength(TOOLS.length);

    for (const tool of tools) {
      expect(tool.description, tool.name).toBeTruthy();
      expect(tool.inputSchema.type, tool.name).toBe('object');
    }
    expect(tools.map((t) => t.name).sort()).toEqual(TOOLS.map((t) => t.name).sort());
  });

  it('marks the tools as read-only', async () => {
    const { tools } = await client.listTools();
    for (const tool of tools) {
      expect(tool.annotations?.readOnlyHint, tool.name).toBe(true);
    }
  });

  it('answers a match query', async () => {
    const result = await client.callTool({
      name: 'search_matches',
      arguments: { team: 'Flamengo', opponent: 'Fluminense', limit: 5 },
    });
    expect(result.isError).toBeFalsy();
    expect(textOf(result)).toContain('Flamengo');
    expect((result.structuredContent as { total: number }).total).toBeGreaterThan(10);
  });

  it('answers a standings query', async () => {
    const result = await client.callTool({
      name: 'competition_standings',
      arguments: { competition: 'serie-a', season: 2019 },
    });
    const data = result.structuredContent as { champion: { team: string } };
    expect(data.champion.team).toBe('Flamengo');
  });

  it('answers a player query', async () => {
    const result = await client.callTool({
      name: 'search_players',
      arguments: { nationality: 'Brazil', limit: 3 },
    });
    const data = result.structuredContent as { total: number };
    expect(data.total).toBe(827);
  });

  it('returns an unresolved team as an error result the model can read', async () => {
    const result = await client.callTool({
      name: 'team_stats',
      arguments: { team: 'Definitely Not A Club' },
    });
    expect(result.isError).toBe(true);
    expect(textOf(result)).toContain('No team matched');
  });

  // The SDK reports both of these as `isError` results rather than transport
  // failures, which is what lets a model read the reason and retry.
  it('rejects arguments that violate the schema', async () => {
    const result = await client.callTool({
      name: 'competition_standings',
      arguments: { season: 'last year' },
    });
    expect(result.isError).toBe(true);
    expect(textOf(result)).toMatch(/season/i);
  });

  it('rejects an unknown tool', async () => {
    const result = await client.callTool({ name: 'no_such_tool', arguments: {} });
    expect(result.isError).toBe(true);
    expect(textOf(result)).toContain('no_such_tool');
  });

  it('applies schema defaults supplied by the client', async () => {
    const result = await client.callTool({ name: 'search_matches', arguments: { team: 'Santos' } });
    const data = result.structuredContent as { returned: number };
    expect(data.returned).toBe(20);
  });
});
