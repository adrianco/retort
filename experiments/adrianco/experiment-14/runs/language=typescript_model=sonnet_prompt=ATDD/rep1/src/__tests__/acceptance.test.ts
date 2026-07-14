import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

describe('Brazilian Soccer MCP Server - Acceptance Tests', () => {
  let client: Client;
  let transport: StdioClientTransport;

  beforeAll(async () => {
    transport = new StdioClientTransport({
      command: 'npx',
      args: ['tsx', path.join(__dirname, '../../src/index.ts')],
      env: { ...process.env, NODE_ENV: 'test' },
    });

    client = new Client({
      name: 'test-client',
      version: '1.0.0',
    }, {
      capabilities: {}
    });

    await client.connect(transport);
  }, 30000);

  afterAll(async () => {
    await client.close();
  });

  it('finds Flamengo matches in Brasileirao', async () => {
    const result = await client.callTool({
      name: 'find_matches',
      arguments: { team: 'Flamengo', competition: 'brasileirao', limit: 10 }
    });
    const text = (result.content as any)[0].text;
    const data = JSON.parse(text);
    expect(data.length).toBeGreaterThan(0);
    expect(data.some((m: any) =>
      m.home_team?.toLowerCase().includes('flamengo') ||
      m.away_team?.toLowerCase().includes('flamengo')
    )).toBe(true);
  });

  it('finds only 2019 season matches', async () => {
    const result = await client.callTool({
      name: 'find_matches',
      arguments: { competition: 'brasileirao', season: 2019, limit: 50 }
    });
    const text = (result.content as any)[0].text;
    const data = JSON.parse(text);
    expect(data.length).toBeGreaterThan(0);
    expect(data.every((m: any) => m.season === 2019 || m.season === '2019')).toBe(true);
  });

  it('gets Flamengo stats for 2019 Brasileirao', async () => {
    const result = await client.callTool({
      name: 'get_team_stats',
      arguments: { team: 'Flamengo', competition: 'brasileirao', season: 2019 }
    });
    const text = (result.content as any)[0].text;
    const data = JSON.parse(text);
    expect(data.team).toBeDefined();
    expect(data.wins).toBeDefined();
    expect(data.losses).toBeDefined();
    expect(data.draws).toBeDefined();
    expect(data.wins).toBeGreaterThan(0);
  });

  it('finds Brazilian players', async () => {
    const result = await client.callTool({
      name: 'find_players',
      arguments: { nationality: 'Brazil', limit: 10 }
    });
    const text = (result.content as any)[0].text;
    const data = JSON.parse(text);
    expect(data.length).toBeGreaterThan(0);
    expect(data.every((p: any) => p.Nationality === 'Brazil')).toBe(true);
  });

  it('finds Flamengo players', async () => {
    const result = await client.callTool({
      name: 'find_players',
      arguments: { club: 'Flamengo', limit: 10 }
    });
    const text = (result.content as any)[0].text;
    const data = JSON.parse(text);
    expect(data.length).toBeGreaterThan(0);
    expect(data.every((p: any) => p.Club?.toLowerCase().includes('flamengo'))).toBe(true);
  });

  it('gets head-to-head record for Palmeiras vs Santos', async () => {
    const result = await client.callTool({
      name: 'get_head_to_head',
      arguments: { team1: 'Palmeiras', team2: 'Santos' }
    });
    const text = (result.content as any)[0].text;
    const data = JSON.parse(text);
    expect(data.total_matches).toBeGreaterThan(0);
    expect(data.matches).toBeDefined();
  });

  it('gets 2019 Brasileirao standings with Flamengo first', async () => {
    const result = await client.callTool({
      name: 'get_standings',
      arguments: { competition: 'brasileirao', season: 2019 }
    });
    const text = (result.content as any)[0].text;
    const data = JSON.parse(text);
    expect(data.length).toBeGreaterThan(0);
    expect(data[0].team.toLowerCase()).toContain('flamengo');
  });

  it('finds Copa do Brasil matches', async () => {
    const result = await client.callTool({
      name: 'find_matches',
      arguments: { competition: 'copa_do_brasil', limit: 10 }
    });
    const text = (result.content as any)[0].text;
    const data = JSON.parse(text);
    expect(data.length).toBeGreaterThan(0);
  });

  it('finds Libertadores matches', async () => {
    const result = await client.callTool({
      name: 'find_matches',
      arguments: { competition: 'libertadores', limit: 10 }
    });
    const text = (result.content as any)[0].text;
    const data = JSON.parse(text);
    expect(data.length).toBeGreaterThan(0);
  });

  it('finds players with minimum rating', async () => {
    const result = await client.callTool({
      name: 'find_players',
      arguments: { minRating: 85, limit: 10 }
    });
    const text = (result.content as any)[0].text;
    const data = JSON.parse(text);
    expect(data.length).toBeGreaterThan(0);
    expect(data.every((p: any) => Number(p.Overall) >= 85)).toBe(true);
  });
});
