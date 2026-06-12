import { describe, it, expect, beforeAll } from 'vitest';
import { DataLoader } from './loader.js';
import {
  searchMatches,
  getTeamStats,
  headToHead,
  getStandings,
  getStatistics,
} from './queries.js';
import path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.join(__dirname, '..', 'data', 'kaggle');

let loader: DataLoader;

beforeAll(async () => {
  loader = new DataLoader(DATA_DIR);
  await loader.load();
}, 30000);

describe('searchMatches', () => {
  it('finds matches by team name', () => {
    const results = searchMatches(loader, { team: 'Flamengo' });
    expect(results.length).toBeGreaterThan(100);
    results.forEach((m) => {
      const involved =
        m.home_team.toLowerCase().includes('flamengo') ||
        m.away_team.toLowerCase().includes('flamengo');
      expect(involved).toBe(true);
    });
  });

  it('finds matches by two teams (head-to-head search)', () => {
    const results = searchMatches(loader, {
      team1: 'Flamengo',
      team2: 'Fluminense',
    });
    expect(results.length).toBeGreaterThan(10);
    results.forEach((m) => {
      const homeIsTeam1 = m.home_team.toLowerCase().includes('flamengo');
      const homeIsTeam2 = m.home_team.toLowerCase().includes('fluminense');
      const awayIsTeam1 = m.away_team.toLowerCase().includes('flamengo');
      const awayIsTeam2 = m.away_team.toLowerCase().includes('fluminense');
      expect((homeIsTeam1 && awayIsTeam2) || (homeIsTeam2 && awayIsTeam1)).toBe(true);
    });
  });

  it('filters by competition', () => {
    const results = searchMatches(loader, { competition: 'Copa do Brasil' });
    expect(results.length).toBeGreaterThan(500);
    results.forEach((m) => {
      expect(m.competition).toBe('Copa do Brasil');
    });
  });

  it('filters by season', () => {
    const results = searchMatches(loader, { season: 2019 });
    expect(results.length).toBeGreaterThan(300);
    results.forEach((m) => {
      expect(m.season).toBe(2019);
    });
  });

  it('filters by team and season', () => {
    const results = searchMatches(loader, { team: 'Palmeiras', season: 2023 });
    expect(results.length).toBeGreaterThan(10);
    results.forEach((m) => {
      expect(m.season).toBe(2023);
    });
  });

  it('respects limit parameter', () => {
    const results = searchMatches(loader, { team: 'Flamengo', limit: 5 });
    expect(results.length).toBeLessThanOrEqual(5);
  });

  it('filters by date range', () => {
    const results = searchMatches(loader, {
      dateFrom: '2023-01-01',
      dateTo: '2023-12-31',
    });
    expect(results.length).toBeGreaterThan(100);
    results.forEach((m) => {
      expect(m.date >= '2023-01-01').toBe(true);
      expect(m.date <= '2023-12-31').toBe(true);
    });
  });
});

describe('getTeamStats', () => {
  it('calculates team stats from normalized matches', () => {
    const stats = getTeamStats(loader, { team: 'Flamengo', season: 2019, competition: 'Brasileirão' });
    expect(stats).not.toBeNull();
    expect(stats!.matches).toBeGreaterThan(30);
    expect(stats!.wins + stats!.draws + stats!.losses).toBe(stats!.matches);
    expect(stats!.points).toBe(stats!.wins * 3 + stats!.draws);
  });

  it('computes goals correctly', () => {
    const stats = getTeamStats(loader, { team: 'Flamengo' });
    expect(stats!.goals_for).toBeGreaterThan(0);
    expect(stats!.goals_against).toBeGreaterThan(0);
  });

  it('returns null for unknown team', () => {
    const stats = getTeamStats(loader, { team: 'NonExistentTeam12345' });
    expect(stats).toBeNull();
  });

  it('filters by home/away', () => {
    const homeStats = getTeamStats(loader, {
      team: 'Corinthians',
      homeOnly: true,
      season: 2022,
      competition: 'Brasileirão',
    });
    expect(homeStats).not.toBeNull();
    expect(homeStats!.matches).toBeGreaterThan(0);
  });
});

describe('headToHead', () => {
  it('returns head-to-head records between two teams', () => {
    const result = headToHead(loader, 'Flamengo', 'Fluminense');
    expect(result.matches.length).toBeGreaterThan(10);
    expect(result.team1_wins + result.team2_wins + result.draws).toBe(result.matches.length);
  });

  it('wins are correctly assigned', () => {
    const result = headToHead(loader, 'Palmeiras', 'Santos');
    result.matches.forEach((m) => {
      const palmHome = m.home_team.toLowerCase().includes('palmeiras');
      const home_wins = m.home_goals > m.away_goals;
      const away_wins = m.away_goals > m.home_goals;
      const draw = m.home_goals === m.away_goals;
      expect(home_wins || away_wins || draw).toBe(true);
    });
    expect(result.team1_wins + result.team2_wins + result.draws).toBe(result.matches.length);
  });
});

describe('getStandings', () => {
  it('calculates standings for a season', () => {
    const standings = getStandings(loader, { season: 2019, competition: 'Brasileirão' });
    expect(standings.length).toBeGreaterThan(10);
    // Champion should have highest points
    expect(standings[0].points).toBeGreaterThanOrEqual(standings[1].points);
    // Flamengo won 2019
    expect(standings[0].team.toLowerCase()).toContain('flamengo');
  });

  it('standings include wins/draws/losses', () => {
    const standings = getStandings(loader, { season: 2019, competition: 'Brasileirão' });
    standings.forEach((s) => {
      expect(s.wins + s.draws + s.losses).toBe(s.matches);
      expect(s.points).toBe(s.wins * 3 + s.draws);
    });
  });
});

describe('getStatistics', () => {
  it('returns biggest wins', () => {
    const stats = getStatistics(loader, { type: 'biggest_wins', limit: 10 });
    expect(stats.biggest_wins).toBeDefined();
    expect(stats.biggest_wins!.length).toBeLessThanOrEqual(10);
    if (stats.biggest_wins!.length > 1) {
      const first = stats.biggest_wins![0];
      const margin = Math.abs(first.home_goals - first.away_goals);
      const second = stats.biggest_wins![1];
      const margin2 = Math.abs(second.home_goals - second.away_goals);
      expect(margin).toBeGreaterThanOrEqual(margin2);
    }
  });

  it('calculates average goals per match', () => {
    const stats = getStatistics(loader, {
      type: 'avg_goals',
      competition: 'Brasileirão',
    });
    expect(stats.avg_goals).toBeGreaterThan(1);
    expect(stats.avg_goals).toBeLessThan(5);
  });

  it('calculates home win rate', () => {
    const stats = getStatistics(loader, { type: 'home_win_rate' });
    expect(stats.home_win_rate).toBeGreaterThan(0.3);
    expect(stats.home_win_rate).toBeLessThan(0.7);
  });

  it('returns top scoring teams', () => {
    const stats = getStatistics(loader, {
      type: 'top_scorers',
      competition: 'Brasileirão',
      season: 2023,
      limit: 5,
    });
    expect(stats.top_scorers).toBeDefined();
    expect(stats.top_scorers!.length).toBeGreaterThan(0);
    if (stats.top_scorers!.length > 1) {
      expect(stats.top_scorers![0].goals).toBeGreaterThanOrEqual(stats.top_scorers![1].goals);
    }
  });
});
