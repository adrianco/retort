import { describe, it, expect, beforeAll } from 'vitest';
import { DataLoader } from './loader.js';
import { handleTool } from './tools.js';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.join(__dirname, '..', 'data', 'kaggle');

let loader: DataLoader;

beforeAll(async () => {
  loader = new DataLoader(DATA_DIR);
  await loader.load();
}, 30000);

describe('handleTool - search_matches', () => {
  it('returns formatted match results for a team', async () => {
    const result = await handleTool(loader, 'search_matches', {
      team: 'Flamengo',
      limit: 5,
    });
    expect(result).toContain('Flamengo');
    expect(result).toContain('-');
  });

  it('returns head-to-head results for two teams', async () => {
    const result = await handleTool(loader, 'search_matches', {
      team1: 'Flamengo',
      team2: 'Fluminense',
    });
    expect(result).toContain('Flamengo');
    expect(result).toContain('Fluminense');
  });

  it('filters by competition', async () => {
    const result = await handleTool(loader, 'search_matches', {
      competition: 'Copa do Brasil',
      limit: 5,
    });
    expect(result).toContain('Copa do Brasil');
  });
});

describe('handleTool - get_team_stats', () => {
  it('returns team statistics', async () => {
    const result = await handleTool(loader, 'get_team_stats', {
      team: 'Flamengo',
      season: 2019,
      competition: 'Brasileirão',
    });
    expect(result).toContain('Flamengo');
    expect(result).toContain('Wins');
  });

  it('returns error for unknown team', async () => {
    const result = await handleTool(loader, 'get_team_stats', {
      team: 'NoSuchTeamXYZ',
    });
    expect(result).toContain('No data');
  });
});

describe('handleTool - search_players', () => {
  it('returns player search results', async () => {
    const result = await handleTool(loader, 'search_players', {
      name: 'Neymar',
    });
    expect(result).toContain('Neymar');
    expect(result).toContain('Overall');
  });

  it('returns top Brazilian players', async () => {
    const result = await handleTool(loader, 'search_players', {
      nationality: 'Brazil',
      limit: 5,
    });
    expect(result).toContain('Brazil');
  });
});

describe('handleTool - get_standings', () => {
  it('returns league standings', async () => {
    const result = await handleTool(loader, 'get_standings', {
      season: 2019,
      competition: 'Brasileirão',
    });
    expect(result).toContain('2019');
    expect(result).toContain('pts');
    expect(result.toLowerCase()).toContain('flamengo');
  });
});

describe('handleTool - get_statistics', () => {
  it('returns biggest wins', async () => {
    const result = await handleTool(loader, 'get_statistics', {
      type: 'biggest_wins',
      limit: 5,
    });
    expect(result).toContain('Biggest Wins');
  });

  it('returns avg goals', async () => {
    const result = await handleTool(loader, 'get_statistics', {
      type: 'avg_goals',
      competition: 'Brasileirão',
    });
    expect(result).toContain('Average goals');
  });

  it('returns home win rate', async () => {
    const result = await handleTool(loader, 'get_statistics', {
      type: 'home_win_rate',
    });
    expect(result).toContain('Home win rate');
    expect(result).toContain('%');
  });
});

describe('handleTool - head_to_head', () => {
  it('returns head-to-head comparison', async () => {
    const result = await handleTool(loader, 'head_to_head', {
      team1: 'Flamengo',
      team2: 'Fluminense',
    });
    expect(result).toContain('Flamengo');
    expect(result).toContain('Fluminense');
    expect(result).toContain('wins');
  });
});

describe('handleTool - error handling', () => {
  it('returns error for unknown tool', async () => {
    const result = await handleTool(loader, 'unknown_tool', {});
    expect(result).toContain('Unknown tool');
  });
});
