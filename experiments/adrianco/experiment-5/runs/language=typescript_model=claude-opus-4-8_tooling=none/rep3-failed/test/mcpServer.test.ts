/**
 * ============================================================================
 * Context Block — File: test/mcpServer.test.ts
 * Project: Brazilian Soccer MCP Server
 * Purpose: Integration BDD specs that drive the actual MCP server end-to-end
 *          over an in-memory transport: list its tools and call them as a real
 *          MCP client would, asserting both the human-readable text and the
 *          structured content come back correctly.
 * ============================================================================
 */

import { describe, it, expect, beforeAll } from 'vitest';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';
import { createServer } from '../src/createServer.js';
import { givenLoadedDatabase } from './helpers.js';

let client: Client;

beforeAll(async () => {
  // Given a running MCP server backed by the loaded data, and a connected client
  const server = createServer(givenLoadedDatabase());
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  client = new Client({ name: 'test-client', version: '1.0.0' });
  await Promise.all([
    server.connect(serverTransport),
    client.connect(clientTransport),
  ]);
});

describe('Feature: MCP server tool surface', () => {
  it('Scenario: the server advertises all expected tools', async () => {
    const { tools } = await client.listTools();
    const names = tools.map((t) => t.name).sort();
    expect(names).toEqual(
      [
        'biggest_wins',
        'data_summary',
        'head_to_head',
        'league_stats',
        'list_competitions',
        'players_by_club',
        'search_matches',
        'search_players',
        'standings',
        'team_stats',
      ].sort(),
    );
  });

  it('Scenario: calling search_matches returns text and structured data', async () => {
    const res = await client.callTool({
      name: 'search_matches',
      arguments: { team: 'Flamengo', opponent: 'Fluminense', limit: 5 },
    });
    const content = res.content as Array<{ type: string; text: string }>;
    expect(content[0].type).toBe('text');
    expect(content[0].text.toLowerCase()).toContain('flamengo');
    const structured = res.structuredContent as { data: unknown[] };
    expect(Array.isArray(structured.data)).toBe(true);
    expect(structured.data.length).toBeGreaterThan(0);
  });

  it('Scenario: calling standings returns the 2019 champion first', async () => {
    const res = await client.callTool({
      name: 'standings',
      arguments: { competition: 'Brasileirão', season: 2019 },
    });
    const content = res.content as Array<{ type: string; text: string }>;
    expect(content[0].text.toLowerCase()).toContain('flamengo');
    expect(content[0].text).toContain('Champion');
  });

  it('Scenario: calling search_players finds a known player', async () => {
    const res = await client.callTool({
      name: 'search_players',
      arguments: { name: 'Neymar' },
    });
    const structured = res.structuredContent as { data: Array<{ name: string }> };
    expect(structured.data[0].name.toLowerCase()).toContain('neymar');
  });

  it('Scenario: input validation rejects a bad argument type', async () => {
    await expect(
      client.callTool({
        name: 'standings',
        // season must be an integer; a string should be rejected by the schema
        arguments: { competition: 'Brasileirão', season: 'not-a-number' as unknown as number },
      }),
    ).rejects.toBeTruthy();
  });
});
