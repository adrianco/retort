import { describe, it, expect, beforeAll } from 'vitest';
import { loadStore } from './setup.js';
import { buildServer } from '../src/server.js';
import type { DataStore } from '../src/types.js';

/**
 * Feature: MCP Server tool surface
 *
 * Exercise the server through its public API (registered tools). These
 * tests verify that all tools are wired up correctly and return
 * non-empty text responses for canonical sample questions from TASK.md.
 */
describe('Feature: MCP server tool surface', () => {
  let store: DataStore;
  beforeAll(async () => {
    store = await loadStore();
  });

  /**
   * Invoke a registered tool directly through the internal registry.
   * This avoids spinning up a real transport for testing.
   */
  let cachedServer: Awaited<ReturnType<typeof buildServer>> | null = null;
  async function getServer() {
    if (!cachedServer) cachedServer = await buildServer({ store });
    return cachedServer;
  }

  async function callTool(toolName: string, args: Record<string, unknown>): Promise<string> {
    const server = await getServer();
    // Reach into the internal registry to call the tool handler directly.
    const registered = (server as any)._registeredTools[toolName];
    if (!registered) throw new Error(`Tool ${toolName} not registered`);
    const extra = { signal: new AbortController().signal };
    const res = await registered.handler(args, extra);
    return (res.content as { type: string; text: string }[])
      .filter((c) => c.type === 'text')
      .map((c) => c.text)
      .join('\n');
  }

  it('find_matches returns formatted match list', async () => {
    const out = await callTool('find_matches', {
      team: 'Flamengo',
      opponent: 'Fluminense',
      limit: 5,
    });
    expect(out).toContain('Flamengo');
    expect(out).toContain('Fluminense');
  });

  it('head_to_head includes win counts', async () => {
    const out = await callTool('head_to_head', {
      teamA: 'Flamengo',
      teamB: 'Fluminense',
    });
    expect(out).toMatch(/Head-to-head/i);
    expect(out).toMatch(/wins/);
  });

  it('team_record returns wins/draws/losses summary', async () => {
    const out = await callTool('team_record', {
      team: 'Corinthians',
      season: 2022,
      competition: 'Brasileirão',
      homeOnly: true,
    });
    expect(out).toContain('Wins:');
    expect(out).toContain('Goals For:');
  });

  it('standings produces league table', async () => {
    const out = await callTool('standings', {
      competition: 'Brasileirão',
      season: 2019,
      limit: 5,
    });
    const lines = out.split('\n');
    expect(lines.length).toBe(5);
    expect(lines[0]).toMatch(/^ 1\./);
    expect(lines[0].toLowerCase()).toContain('flamengo');
  });

  it('top_scoring_teams ranks by goals', async () => {
    const out = await callTool('top_scoring_teams', {
      competition: 'Brasileirão',
      season: 2019,
      limit: 5,
    });
    const lines = out.split('\n');
    expect(lines.length).toBe(5);
    expect(lines[0]).toMatch(/^1\./);
  });

  it('season_champion identifies winner', async () => {
    const out = await callTool('season_champion', {
      competition: 'Brasileirão',
      season: 2019,
    });
    expect(out.toLowerCase()).toContain('flamengo');
    expect(out.toLowerCase()).toContain('champion');
  });

  it('find_players finds Neymar', async () => {
    const out = await callTool('find_players', {
      name: 'Neymar',
      limit: 3,
    });
    expect(out.toLowerCase()).toContain('neymar');
  });

  it('players_by_club groups Brazilians by club', async () => {
    const out = await callTool('players_by_club', {
      nationality: 'Brazil',
      limit: 10,
    });
    expect(out.length).toBeGreaterThan(0);
    expect(out.split('\n').length).toBeGreaterThan(0);
  });

  it('biggest_wins lists margin-sorted results', async () => {
    const out = await callTool('biggest_wins', { limit: 5 });
    const lines = out.split('\n').filter(Boolean);
    expect(lines.length).toBe(5);
  });

  it('overall_stats reports averages', async () => {
    const out = await callTool('overall_stats', {
      competition: 'Brasileirão',
    });
    expect(out).toMatch(/Average goals/);
    expect(out).toMatch(/Home wins/);
  });

  it('seasons_available lists seasons', async () => {
    const out = await callTool('seasons_available', {
      competition: 'Brasileirão',
    });
    expect(out).toMatch(/2019/);
  });

  it('knockout_bracket groups by stage', async () => {
    const out = await callTool('knockout_bracket', {
      competition: 'Libertadores',
      season: 2018,
    });
    expect(out).toMatch(/==/);
  });
});
