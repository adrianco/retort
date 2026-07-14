import path from 'path';
import { fileURLToPath } from 'url';
import { loadAllData } from './dataLoader.js';
import { handleFindMatches, handleHeadToHead, handleTeamRecord, handleStandings, handleSearchPlayers, handleTopPlayers, handleBiggestWins, handleAverageGoals } from './handlers.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.join(__dirname, '..', 'data', 'kaggle');

describe('MCP tool handlers (integration with real data)', () => {
  let data: Awaited<ReturnType<typeof loadAllData>>;

  beforeAll(async () => {
    data = await loadAllData(DATA_DIR);
  }, 30000);

  describe('handleFindMatches', () => {
    it('finds Flamengo matches in brasileirao 2019', () => {
      const result = handleFindMatches(data, { team: 'Flamengo', competition: 'Brasileirao', season: 2019 });
      expect(result.matches.length).toBeGreaterThan(0);
      expect(result.total).toBeGreaterThan(0);
    });

    it('finds Flamengo vs Fluminense matches', () => {
      const result = handleFindMatches(data, { team: 'Flamengo', opponent: 'Fluminense' });
      expect(result.matches.length).toBeGreaterThan(0);
    });

    it('returns formatted match summaries', () => {
      const result = handleFindMatches(data, { team: 'Palmeiras', season: 2022, competition: 'Brasileirao' });
      expect(result.matches.length).toBeGreaterThan(0);
      expect(result.matches[0]).toHaveProperty('date');
      expect(result.matches[0]).toHaveProperty('homeTeam');
      expect(result.matches[0]).toHaveProperty('awayTeam');
      expect(result.matches[0]).toHaveProperty('score');
      expect(result.matches[0]).toHaveProperty('competition');
    });
  });

  describe('handleHeadToHead', () => {
    it('returns head-to-head stats for Flamengo vs Fluminense', () => {
      const result = handleHeadToHead(data, { teamA: 'Flamengo', teamB: 'Fluminense' });
      expect(result.total).toBeGreaterThan(0);
      expect(result).toHaveProperty('teamAWins');
      expect(result).toHaveProperty('teamBWins');
      expect(result).toHaveProperty('draws');
    });
  });

  describe('handleTeamRecord', () => {
    it('returns Corinthians 2022 home record', () => {
      const result = handleTeamRecord(data, { team: 'Corinthians', season: 2022, competition: 'Brasileirao', homeOnly: true });
      expect(result.played).toBeGreaterThan(0);
      expect(result).toHaveProperty('wins');
      expect(result).toHaveProperty('winRate');
    });
  });

  describe('handleStandings', () => {
    it('returns 2019 brasileirao standings with Flamengo first', () => {
      const result = handleStandings(data, { season: 2019, competition: 'Brasileirao' });
      expect(result.standings.length).toBeGreaterThan(0);
      expect(result.standings[0].team).toBe('Flamengo');
    });

    it('includes points, wins, draws, losses', () => {
      const result = handleStandings(data, { season: 2019, competition: 'Brasileirao' });
      const first = result.standings[0];
      expect(first).toHaveProperty('points');
      expect(first).toHaveProperty('wins');
      expect(first).toHaveProperty('draws');
      expect(first).toHaveProperty('losses');
    });
  });

  describe('handleSearchPlayers', () => {
    it('finds Gabriel Jesus by name', () => {
      const result = handleSearchPlayers(data, { name: 'Gabriel Jesus' });
      expect(result.players.length).toBeGreaterThan(0);
    });

    it('finds Brazilian players at Fluminense', () => {
      const result = handleSearchPlayers(data, { nationality: 'Brazil', club: 'Fluminense' });
      expect(result.players.length).toBeGreaterThan(0);
      expect(result.players.every((p: { nationality: string }) => p.nationality === 'Brazil')).toBe(true);
    });
  });

  describe('handleTopPlayers', () => {
    it('returns top Brazilian players sorted by overall', () => {
      const result = handleTopPlayers(data, { nationality: 'Brazil', limit: 10 });
      expect(result.players.length).toBe(10);
      expect(result.players[0].overall).toBeGreaterThanOrEqual(result.players[9].overall);
    });
  });

  describe('handleBiggestWins', () => {
    it('returns biggest wins in brasileirao', () => {
      const result = handleBiggestWins(data, { competition: 'Brasileirao', limit: 5 });
      expect(result.matches.length).toBe(5);
      expect(result.matches[0].goalDiff).toBeGreaterThanOrEqual(result.matches[4].goalDiff);
    });
  });

  describe('handleAverageGoals', () => {
    it('returns average goals per match in brasileirao', () => {
      const result = handleAverageGoals(data, { competition: 'Brasileirao' });
      expect(result.average).toBeGreaterThan(1);
      expect(result.average).toBeLessThan(10);
      expect(result.matchCount).toBeGreaterThan(0);
    });
  });
});
