import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';
import { getDataset } from '../src/loader.js';
import { createServer } from '../src/tools.js';
import type { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';

/**
 * End-to-end checks over the real MCP protocol (in-memory transport), using
 * the provided data. Each scenario is a natural-language question from the spec.
 */
describe('Feature: MCP tools answer spec questions', () => {
  let server: McpServer;
  let client: Client;

  const ask = async (name: string, args: Record<string, unknown> = {}): Promise<string> => {
    const result = await client.callTool({ name, arguments: args });
    const first = (result.content as Array<{ type: string; text: string }>)[0];
    if (result.isError) throw new Error(first.text);
    return first.text;
  };

  beforeAll(async () => {
    server = createServer(getDataset());
    const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
    await server.connect(serverTransport);
    client = new Client({ name: 'test-client', version: '0.0.0' });
    await client.connect(clientTransport);
  });

  afterAll(async () => {
    await client.close();
    await server.close();
  });

  it('exposes the expected tools', async () => {
    const { tools } = await client.listTools();
    expect(tools.map((t) => t.name).sort()).toEqual([
      'biggest_wins', 'club_summary', 'dataset_info', 'head_to_head', 'league_stats',
      'rank_teams', 'search_matches', 'search_players', 'standings', 'team_profile', 'team_record',
    ]);
  });

  describe('Scenario: Find matches between two teams', () => {
    it('Given the data, when I search Flamengo vs Fluminense, then matches are listed with scores and competition', async () => {
      const text = await ask('search_matches', { team: 'Flamengo', opponent: 'Fluminense', limit: 3 });
      expect(text).toMatch(/(Flamengo \d+-\d+ Fluminense|Fluminense \d+-\d+ Flamengo) \(Brasileirão Série A/);
      expect(text).toContain('Total matches:');
    });
  });

  describe('Scenario: Get team statistics', () => {
    it('Given Palmeiras in 2023, when I request its record, then wins, draws, losses and goals appear', async () => {
      const text = await ask('team_record', { team: 'Palmeiras', season: 2023, competition: 'Brasileirão Série A' });
      expect(text).toMatch(/Matches: 3[78]\b/);
      expect(text).toMatch(/Wins: \d+, Draws: \d+, Losses: \d+/);
      expect(text).toMatch(/Win rate: \d+\.\d%/);
    });
  });

  describe('Scenario: Compare teams head-to-head', () => {
    it('Given Palmeiras and Santos, when I compare them, then a head-to-head summary is returned', async () => {
      const text = await ask('head_to_head', { team_a: 'Palmeiras', team_b: 'Santos' });
      expect(text).toContain('Head-to-head in dataset:');
    });
  });

  describe('Scenario: Competition standings', () => {
    it('Given the 2019 Brasileirão, when I ask for standings, then Flamengo is champion with 90 points', async () => {
      const text = await ask('standings', { season: 2019 });
      expect(text).toContain('1. Flamengo - 90 pts');
    });
  });

  describe('Scenario: Statistical analysis', () => {
    it('Given Brasileirão, when I ask for league stats, then average goals per match is reported', async () => {
      const text = await ask('league_stats', { competition: 'Brasileirão Série A' });
      expect(text).toMatch(/Average goals per match: \d\.\d{2}/);
      expect(text).toMatch(/Home win rate: \d+\.\d%/);
    });

    it('Given the whole dataset, when I ask for the best home record, then teams are ranked by home win rate', async () => {
      const text = await ask('rank_teams', { metric: 'win_rate', venue: 'home', competition: 'Brasileirão Série A', season: 2023, min_matches: 10, limit: 3 });
      expect(text.split('\n')[1]).toMatch(/^1\. .* - \d+\.\d%/);
    });

    it('Given the whole dataset, when I ask for the biggest wins, then margins are listed', async () => {
      const text = await ask('biggest_wins', { limit: 3 });
      expect(text.split('\n').filter((l) => l.startsWith('- '))).toHaveLength(3);
    });
  });

  describe('Scenario: Player queries', () => {
    it('Given Brazilian players, when I filter by club Santos, then only Santos players appear', async () => {
      const text = await ask('search_players', { nationality: 'Brazil', club: 'Santos', limit: 5 });
      expect(text).toContain('Club: Santos');
      expect(text).not.toContain('Club: Palmeiras');
    });

    it('Given a club that is not in the FIFA file, then the answer says no players were found', async () => {
      const text = await ask('search_players', { club: 'Flamengo' });
      expect(text).toContain('No players found.');
    });

    it('Given "Gabriel Jesus", when I search by name, then the FIFA record is found', async () => {
      const text = await ask('search_players', { name: 'Gabriel Jesus' });
      expect(text).toContain('Gabriel Jesus - Overall:');
    });

    it('Given a team name, when I ask for its profile, then both match record and squad are returned', async () => {
      const text = await ask('team_profile', { team: 'Santos', player_limit: 3 });
      expect(text).toContain('match record');
      expect(text).toContain('Players at Santos');
    });
  });

  it('Given a competition name the server does not know, then the tool reports an error', async () => {
    await expect(ask('league_stats', { competition: 'Premier League' })).rejects.toThrow(/Unknown competition/);
  });

  it('Given a query, then the response is produced in under 5 seconds', async () => {
    const started = Date.now();
    await ask('league_stats', {});
    expect(Date.now() - started).toBeLessThan(5000);
  });
});
