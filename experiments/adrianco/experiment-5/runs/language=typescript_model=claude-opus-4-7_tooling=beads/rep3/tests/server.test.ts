import { describe, it, expect, beforeAll } from 'vitest';
import { buildServer } from '../src/server.js';
import { DataStore } from '../src/types.js';
import type { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';

let server: McpServer;
let store: DataStore;
let client: Client;

beforeAll(async () => {
  const built = await buildServer();
  server = built.server;
  store = built.store;
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  client = new Client({ name: 'test-client', version: '1.0.0' });
  await Promise.all([
    server.connect(serverTransport),
    client.connect(clientTransport),
  ]);
});

async function callText(name: string, args: Record<string, unknown> = {}): Promise<string> {
  const res = await client.callTool({ name, arguments: args });
  const first = (res.content as Array<{ type: string; text?: string }>)[0];
  return first?.text ?? '';
}

describe('Feature: MCP server tools', () => {
  describe('Scenario: List tools', () => {
    it('Given the server is connected, When tools are listed, Then expected tools are exposed', async () => {
      const list = await client.listTools();
      const names = list.tools.map((t) => t.name);
      expect(names).toContain('find_matches');
      expect(names).toContain('head_to_head');
      expect(names).toContain('team_stats');
      expect(names).toContain('standings');
      expect(names).toContain('find_players');
      expect(names).toContain('aggregate_stats');
      expect(names).toContain('biggest_wins');
      expect(names).toContain('dataset_overview');
    });
  });

  describe('Scenario: dataset_overview describes loaded data', () => {
    it('When dataset_overview is called, Then output mentions match and player counts', async () => {
      const text = await callText('dataset_overview');
      expect(text).toContain('matches');
      expect(text).toContain('players');
      expect(text).toContain(`${store.players.length}`);
    });
  });

  describe('Scenario: find_matches returns matches', () => {
    it('Given two rival teams, When find_matches is invoked, Then a non-empty list comes back', async () => {
      const text = await callText('find_matches', {
        team: 'Flamengo',
        opponent: 'Fluminense',
        limit: 10,
      });
      expect(text).toMatch(/Total: \d+ match/);
      expect(text.toLowerCase()).toContain('flamengo');
    });
  });

  describe('Scenario: standings exposes table', () => {
    it('When Brasileirao 2019 standings tool is called, Then Flamengo appears at top', async () => {
      const text = await callText('standings', {
        competition: 'Brasileirao',
        season: 2019,
        limit: 5,
      });
      expect(text).toContain('Brasileirao 2019 standings');
      const firstRow = text.split('\n').slice(3, 4)[0] ?? '';
      expect(firstRow.toLowerCase()).toContain('flamengo');
    });
  });

  describe('Scenario: find_players supports nationality filter', () => {
    it('When nationality=Brazil with high minOverall, Then result rows are Brazilians', async () => {
      const text = await callText('find_players', {
        nationality: 'Brazil',
        minOverall: 85,
        limit: 5,
      });
      expect(text).toMatch(/Total: \d+ player/);
      expect(text).toContain('Nationality: Brazil');
    });
  });

  describe('Scenario: aggregate_stats returns sensible numbers', () => {
    it('When aggregated over Brasileirao, Then average goals/match is plausible', async () => {
      const text = await callText('aggregate_stats', { competition: 'Brasileirao' });
      const m = text.match(/Average goals\/match: (\d+\.\d+)/);
      expect(m).not.toBeNull();
      const avg = Number(m![1]);
      expect(avg).toBeGreaterThan(1);
      expect(avg).toBeLessThan(5);
    });
  });
});
