import { describe, it, expect } from 'vitest';
import { buildServer } from '../src/server';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';

async function makeClient() {
  const server = buildServer();
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  const client = new Client({ name: 'test-client', version: '1.0.0' });
  await Promise.all([
    server.connect(serverTransport),
    client.connect(clientTransport),
  ]);
  return { client, server };
}

function asText(result: { content: Array<{ type: string; text?: string }> }): string {
  return result.content
    .filter(c => c.type === 'text')
    .map(c => c.text ?? '')
    .join('\n');
}

describe('Feature: MCP server tool surface', () => {
  describe('Scenario: server lists all expected tools', () => {
    it('exposes every documented tool name', async () => {
      const { client, server } = await makeClient();
      const list = await client.listTools();
      const names = list.tools.map(t => t.name);
      for (const expected of [
        'find_matches',
        'team_record',
        'head_to_head',
        'competition_standings',
        'find_players',
        'top_scoring_teams',
        'biggest_wins',
        'aggregate_stats',
        'brazilian_players_by_club',
        'competitions_for_team',
      ]) {
        expect(names).toContain(expected);
      }
      await client.close();
      await server.close();
    });
  });

  describe('Scenario: tool execution returns formatted text', () => {
    it('find_matches returns a non-empty match list for Flamengo vs Corinthians', async () => {
      const { client, server } = await makeClient();
      const result = await client.callTool({
        name: 'find_matches',
        arguments: { team: 'Flamengo', opponent: 'Corinthians', limit: 5 },
      });
      const text = asText(result as any);
      expect(text).toMatch(/Found \d+ match/);
      await client.close();
      await server.close();
    });

    it('team_record returns a record summary for Palmeiras', async () => {
      const { client, server } = await makeClient();
      const result = await client.callTool({
        name: 'team_record',
        arguments: { team: 'Palmeiras', season: 2019, competition: 'Brasileirão' },
      });
      const text = asText(result as any);
      expect(text).toContain('Matches');
      expect(text).toContain('Wins');
      expect(text).toContain('Win rate');
      await client.close();
      await server.close();
    });

    it('competition_standings returns a ranked table', async () => {
      const { client, server } = await makeClient();
      const result = await client.callTool({
        name: 'competition_standings',
        arguments: { competition: 'Brasileirão', season: 2019, limit: 5 },
      });
      const text = asText(result as any);
      expect(text).toMatch(/standings/);
      expect(text).toMatch(/ 1\. /);
      await client.close();
      await server.close();
    });

    it('find_players returns top Brazilian players', async () => {
      const { client, server } = await makeClient();
      const result = await client.callTool({
        name: 'find_players',
        arguments: { nationality: 'Brazil', limit: 5 },
      });
      const text = asText(result as any);
      expect(text).toMatch(/Found \d+ player/);
      await client.close();
      await server.close();
    });

    it('aggregate_stats reports averages and rates', async () => {
      const { client, server } = await makeClient();
      const result = await client.callTool({
        name: 'aggregate_stats',
        arguments: { competition: 'Brasileirão' },
      });
      const text = asText(result as any);
      expect(text).toContain('Average goals per match');
      expect(text).toContain('Home wins');
      await client.close();
      await server.close();
    });
  });
});
