import path from 'path';
import { fileURLToPath } from 'url';
import { loadAllData, type BrazileiraoMatch, type CupMatch, type LibertadoresMatch, type BRFootballMatch, type HistoricalMatch, type FifaPlayer } from './dataLoader.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.join(__dirname, '..', 'data', 'kaggle');

describe('loadAllData', () => {
  let data: Awaited<ReturnType<typeof loadAllData>>;

  beforeAll(async () => {
    data = await loadAllData(DATA_DIR);
  }, 30000);

  describe('brasileirao matches', () => {
    it('loads brasileirao matches', () => {
      expect(data.brasileirao.length).toBeGreaterThan(4000);
    });

    it('parses match fields correctly', () => {
      const match = data.brasileirao[0] as BrazileiraoMatch;
      expect(match.home_team).toBeDefined();
      expect(match.away_team).toBeDefined();
      expect(typeof match.home_goal).toBe('number');
      expect(typeof match.away_goal).toBe('number');
      expect(typeof match.season).toBe('number');
      expect(match.datetime).toBeDefined();
    });

    it('includes normalized team names', () => {
      const match = data.brasileirao[0] as BrazileiraoMatch;
      expect(match.home_team_normalized).toBeDefined();
      expect(match.away_team_normalized).toBeDefined();
    });
  });

  describe('copa do brasil matches', () => {
    it('loads cup matches', () => {
      expect(data.copaBrasil.length).toBeGreaterThan(1000);
    });

    it('parses cup match fields', () => {
      const match = data.copaBrasil[0] as CupMatch;
      expect(match.home_team).toBeDefined();
      expect(match.away_team).toBeDefined();
      expect(typeof match.home_goal).toBe('number');
      expect(typeof match.away_goal).toBe('number');
    });
  });

  describe('libertadores matches', () => {
    it('loads libertadores matches', () => {
      expect(data.libertadores.length).toBeGreaterThan(1000);
    });

    it('includes stage info', () => {
      const match = data.libertadores[0] as LibertadoresMatch;
      expect(match.stage).toBeDefined();
    });
  });

  describe('BR football dataset', () => {
    it('loads BR football matches', () => {
      expect(data.brFootball.length).toBeGreaterThan(10000);
    });

    it('parses extended stats', () => {
      const match = data.brFootball[0] as BRFootballMatch;
      expect(match.tournament).toBeDefined();
      expect(match.home).toBeDefined();
      expect(match.away).toBeDefined();
    });
  });

  describe('historical brasileirao', () => {
    it('loads historical matches', () => {
      expect(data.historical.length).toBeGreaterThan(6000);
    });

    it('parses portuguese column names', () => {
      const match = data.historical[0] as HistoricalMatch;
      expect(match.equipe_mandante).toBeDefined();
      expect(match.equipe_visitante).toBeDefined();
      expect(typeof match.gols_mandante).toBe('number');
      expect(typeof match.gols_visitante).toBe('number');
    });
  });

  describe('FIFA players', () => {
    it('loads FIFA players', () => {
      expect(data.fifaPlayers.length).toBeGreaterThan(18000);
    });

    it('parses player fields', () => {
      const player = data.fifaPlayers[0] as FifaPlayer;
      expect(player.name).toBeDefined();
      expect(player.nationality).toBeDefined();
      expect(typeof player.overall).toBe('number');
      expect(player.club).toBeDefined();
      expect(player.position).toBeDefined();
    });
  });
});
