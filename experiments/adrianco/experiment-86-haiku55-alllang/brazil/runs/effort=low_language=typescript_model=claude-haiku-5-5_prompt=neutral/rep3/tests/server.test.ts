/*
 * Context: End-to-end feature tests for the MCP server. A real MCP client talks to
 * createServer() over the SDK's in-memory transport, so these cover schema validation,
 * tool registration and error reporting exactly as an LLM client would see them.
 * Uses the fixture dataset via the DATA_DIR override.
 * Related: src/server.ts, tests/fixtures/make-fixture.ts.
 */
import { describe, expect, it, beforeAll, afterAll } from 'vitest';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';
import { createServer } from '../src/server.js';
import { clearDatasetCache } from '../src/dataset.js';
import { makeFixtureDir } from './fixtures/make-fixture.js';

type ToolResult = { content: { type: string; text: string }[]; isError?: boolean };

describe('Feature: MCP server exposes soccer queries to an LLM', () => {
  let client: Client;
  let close: () => Promise<void>;
  const previous = process.env.DATA_DIR;

  beforeAll(async () => {
    process.env.DATA_DIR = makeFixtureDir();
    clearDatasetCache();
    const server = createServer();
    const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
    await server.connect(serverTransport);
    client = new Client({ name: 'test-client', version: '0.0.0' });
    await client.connect(clientTransport);
    close = async () => {
      await client.close();
      await server.close();
    };
  });

  afterAll(async () => {
    await close?.();
    process.env.DATA_DIR = previous;
    clearDatasetCache();
  });

  const call = async (name: string, args: Record<string, unknown>) =>
    (await client.callTool({ name, arguments: args })) as ToolResult;

  it('Scenario: all query tools are advertised', async () => {
    const { tools } = await client.listTools();
    expect(tools.map((t) => t.name).sort()).toEqual([
      'aggregate_stats', 'biggest_wins', 'club_squad_summary', 'head_to_head',
      'search_matches', 'search_players', 'standings', 'team_stats',
    ]);
  });

  it('Scenario: find matches between two teams returns formatted lines', async () => {
    const r = await call('search_matches', { team: 'Flamengo', opponent: 'Palmeiras' });
    expect(r.isError).toBeFalsy();
    expect(r.content[0].text).toContain('2023-05-01: Palmeiras 3-1 Flamengo (Brasileirão Série A 1)');
  });

  it('Scenario: team statistics for a season', async () => {
    const r = await call('team_stats', { team: 'Palmeiras-SP', season: 2019, competition: 'Brasileirão Série A' });
    expect(r.content[0].text).toContain('- Wins: 2, Draws: 1, Losses: 0');
  });

  it('Scenario: standings reports the 2019 table', async () => {
    const r = await call('standings', { season: 2019 });
    expect(r.content[0].text).toMatch(/1\s+Palmeiras\s+7/);
  });

  it('Scenario: head-to-head summary', async () => {
    const r = await call('head_to_head', { teamA: 'Palmeiras', teamB: 'Santos' });
    expect(r.content[0].text).toContain('Matches: 3, Palmeiras wins: 1, Santos wins: 0, Draws: 2');
  });

  it('Scenario: aggregate statistics include average goals per match', async () => {
    const r = await call('aggregate_stats', { competition: 'Brasileirão Série A', season: 2019 });
    expect(r.content[0].text).toContain('Average goals per match: 1.67');
  });

  it('Scenario: player search returns ratings', async () => {
    const r = await call('search_players', { nationality: 'Brazil', minOverall: 85 });
    expect(r.content[0].text).toContain('1. Neymar Jr - Overall: 92');
    expect(r.content[0].text).toContain('Gabriel Barbosa');
  });

  it('Scenario: club squad summary for Brazilian clubs', async () => {
    const r = await call('club_squad_summary', { nationality: 'Brazil', brazilianClubsOnly: true });
    expect(r.content[0].text).toContain('- Flamengo: 2 players (avg overall 84.5)');
  });

  it('Scenario: unknown team is reported as a tool error the LLM can act on', async () => {
    const r = await call('team_stats', { team: 'Nao Existe FC' });
    expect(r.isError).toBe(true);
    expect(r.content[0].text).toContain('No team matching "Nao Existe FC"');
  });

  it('Scenario: invalid input is rejected by the schema', async () => {
    const r = await client.callTool({ name: 'standings', arguments: { season: 'twenty nineteen' } })
      .catch((e: Error) => ({ isError: true, error: e }));
    expect(r.isError).toBe(true);
  });
});
