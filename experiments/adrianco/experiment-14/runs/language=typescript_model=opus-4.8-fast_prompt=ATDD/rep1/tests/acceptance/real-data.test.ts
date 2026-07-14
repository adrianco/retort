/**
 * Acceptance: the shipped Kaggle datasets are all loadable and queryable
 * through the MCP interface (TASK.md "Data Coverage" success criteria).
 *
 * This drives the production data-loading path against the real CSV files and
 * then asks questions through the MCP client, exactly as a real user would.
 */
import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';
import { loadDataset } from '../../src/data/loaders.js';
import { createSoccerServer } from '../../src/server.js';

const dataDir = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  '../../data/kaggle',
);

let client: Client;
let server: ReturnType<typeof createSoccerServer>;

async function call(tool: string, args: Record<string, unknown> = {}) {
  const res: any = await client.callTool({ name: tool, arguments: args });
  if (res.isError) throw new Error(res.content?.map((c: any) => c.text).join('\n'));
  if (res.structuredContent) return res.structuredContent;
  return JSON.parse(res.content.find((c: any) => c.type === 'text').text);
}

beforeAll(async () => {
  const store = loadDataset(dataDir);
  server = createSoccerServer(store);
  const [ct, st] = InMemoryTransport.createLinkedPair();
  client = new Client({ name: 'real-data-test', version: '1.0.0' });
  await Promise.all([server.connect(st), client.connect(ct)]);
});

afterAll(async () => {
  await client.close();
  await server.close();
});

describe('Real Kaggle datasets via MCP', () => {
  it('loads a substantial number of matches and players from all files', async () => {
    const stats = await call('dataset_summary');
    // 5 match files (~24k rows) + FIFA players (~18k).
    expect(stats.totalMatches).toBeGreaterThan(20000);
    expect(stats.totalPlayers).toBeGreaterThan(15000);
    expect(stats.competitions.length).toBeGreaterThanOrEqual(3);
  });

  it('finds real Fla-Flu derby matches', async () => {
    const res = await call('find_matches', { team: 'Flamengo', opponent: 'Fluminense' });
    expect(res.count).toBeGreaterThan(0);
    for (const m of res.matches) {
      const teams = `${m.homeTeam} ${m.awayTeam}`;
      expect(teams).toMatch(/Flamengo/);
      expect(teams).toMatch(/Fluminense/);
    }
  });

  it('finds Brazilian players in the FIFA dataset', async () => {
    const res = await call('find_players', { nationality: 'Brazil', sortBy: 'overall', limit: 5 });
    expect(res.count).toBeGreaterThan(100);
    expect(res.players.length).toBe(5);
    // Sorted descending by rating.
    const ratings = res.players.map((p: any) => p.overall);
    expect(ratings).toEqual([...ratings].sort((a, b) => b - a));
  });

  it('computes the 2019 Brasileirão champion from match results', async () => {
    const res = await call('competition_standings', { competition: 'Brasileirão', season: 2019 });
    expect(res.standings.length).toBe(20); // 20-team league.
    // Flamengo (RJ) won the 2019 Brasileirão; the display may carry its state.
    expect(res.champion).toMatch(/Flamengo/);
    expect(res.standings[0].points).toBe(90); // famous 90-point campaign.
  });

  it('answers a cross-file query: a club has both players and matches', async () => {
    // Santos appears in both the FIFA player data and the match datasets.
    const players = await call('find_players', { club: 'Santos' });
    const matches = await call('find_matches', { team: 'Santos' });
    expect(players.count).toBeGreaterThan(0);
    expect(matches.count).toBeGreaterThan(0);
  });
});
