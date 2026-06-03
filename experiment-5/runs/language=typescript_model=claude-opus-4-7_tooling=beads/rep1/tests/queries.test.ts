import { describe, it, expect, beforeAll } from 'vitest';
import { loadData, type SoccerData } from '../src/loader';
import {
  filterMatches,
  teamRecord,
  headToHead,
  competitionStandings,
  filterPlayers,
  topScoringTeams,
  biggestWins,
  aggregateStats,
  brazilianPlayersByClub,
  competitionsForTeam,
} from '../src/queries';

let data: SoccerData;

beforeAll(() => {
  data = loadData();
});

describe('Feature: Data loading', () => {
  describe('Scenario: all six CSV files are loaded', () => {
    it('loads thousands of matches and players', () => {
      expect(data.matches.length).toBeGreaterThan(10000);
      expect(data.players.length).toBeGreaterThan(15000);
    });

    it('covers all three Brazilian competitions', () => {
      const comps = new Set(data.matches.map(m => m.competition));
      expect(comps.has('Brasileirão')).toBe(true);
      expect(comps.has('Copa do Brasil')).toBe(true);
      expect(comps.has('Copa Libertadores')).toBe(true);
    });

    it('loads matches from each source file', () => {
      const sources = new Set(data.matches.map(m => m.source));
      expect(sources.has('Brasileirao_Matches.csv')).toBe(true);
      expect(sources.has('Brazilian_Cup_Matches.csv')).toBe(true);
      expect(sources.has('Libertadores_Matches.csv')).toBe(true);
      expect(sources.has('BR-Football-Dataset.csv')).toBe(true);
      expect(sources.has('novo_campeonato_brasileiro.csv')).toBe(true);
    });
  });
});

describe('Feature: Match queries', () => {
  describe('Scenario: find matches between two teams', () => {
    it('returns Flamengo vs Fluminense matches in the dataset', () => {
      const matches = filterMatches(data.matches, { team: 'Flamengo', opponent: 'Fluminense' });
      expect(matches.length).toBeGreaterThan(0);
      for (const m of matches) {
        const involvesBoth =
          (m.homeTeam.includes('flamengo') && m.awayTeam.includes('fluminense')) ||
          (m.awayTeam.includes('flamengo') && m.homeTeam.includes('fluminense'));
        expect(involvesBoth).toBe(true);
        expect(m.date).toMatch(/^\d{4}-\d{2}-\d{2}/);
        expect(typeof m.homeGoals).toBe('number');
        expect(typeof m.awayGoals).toBe('number');
      }
    });
  });

  describe('Scenario: filter matches by team and season', () => {
    it('returns Palmeiras matches in 2019', () => {
      const matches = filterMatches(data.matches, { team: 'Palmeiras', season: 2019 });
      expect(matches.length).toBeGreaterThan(0);
      for (const m of matches) expect(m.season).toBe(2019);
    });
  });

  describe('Scenario: filter matches by competition', () => {
    it('returns only Copa do Brasil matches when requested', () => {
      const matches = filterMatches(data.matches, { competition: 'Copa do Brasil', limit: 50 });
      expect(matches.length).toBeGreaterThan(0);
      for (const m of matches) expect(m.competition).toBe('Copa do Brasil');
    });
  });

  describe('Scenario: matches are sorted by most recent first', () => {
    it('returns matches in descending date order', () => {
      const matches = filterMatches(data.matches, { team: 'Corinthians', limit: 20 });
      for (let i = 1; i < matches.length; i++) {
        expect(matches[i - 1].date >= matches[i].date).toBe(true);
      }
    });
  });
});

describe('Feature: Team statistics', () => {
  describe('Scenario: compute season record for a team', () => {
    it('reports a coherent W/D/L for Palmeiras in 2019 Brasileirão', () => {
      const rec = teamRecord(data.matches, 'Palmeiras', { season: 2019, competition: 'Brasileirão' });
      expect(rec.matches).toBeGreaterThan(0);
      expect(rec.wins + rec.draws + rec.losses).toBe(rec.matches);
      expect(rec.points).toBe(rec.wins * 3 + rec.draws);
      expect(rec.goalDifference).toBe(rec.goalsFor - rec.goalsAgainst);
    });
  });

  describe('Scenario: home vs away record', () => {
    it('sums home and away matches back to overall total', () => {
      const home = teamRecord(data.matches, 'Corinthians', { season: 2022, competition: 'Brasileirão', venue: 'home' });
      const away = teamRecord(data.matches, 'Corinthians', { season: 2022, competition: 'Brasileirão', venue: 'away' });
      const all = teamRecord(data.matches, 'Corinthians', { season: 2022, competition: 'Brasileirão' });
      expect(home.matches + away.matches).toBe(all.matches);
      expect(home.goalsFor + away.goalsFor).toBe(all.goalsFor);
    });
  });
});

describe('Feature: Head-to-head', () => {
  describe('Scenario: compare two clubs', () => {
    it('Palmeiras vs Santos returns consistent counts', () => {
      const h = headToHead(data.matches, 'Palmeiras', 'Santos');
      expect(h.matches).toBeGreaterThan(0);
      expect(h.teamAWins + h.teamBWins + h.draws).toBe(h.matches);
      expect(h.history.length).toBe(h.matches);
    });
  });
});

describe('Feature: Competition standings', () => {
  describe('Scenario: 2019 Brasileirão final table', () => {
    it('ranks Flamengo first in 2019', () => {
      const standings = competitionStandings(data.matches, 'Brasileirão', 2019);
      expect(standings.length).toBeGreaterThan(15);
      expect(standings[0].team).toBe('flamengo');
      expect(standings[0].rank).toBe(1);
      expect(standings[0].points).toBeGreaterThan(standings[1].points);
    });

    it('every standing row has matches equal to W+D+L', () => {
      const standings = competitionStandings(data.matches, 'Brasileirão', 2019);
      for (const row of standings) {
        expect(row.wins + row.draws + row.losses).toBe(row.matches);
      }
    });
  });
});

describe('Feature: Player queries', () => {
  describe('Scenario: find Brazilian players', () => {
    it('returns players with Brazil as nationality', () => {
      const players = filterPlayers(data.players, { nationality: 'Brazil', limit: 50 });
      expect(players.length).toBeGreaterThan(0);
      for (const p of players) expect((p.nationality || '').toLowerCase()).toBe('brazil');
    });

    it('returns Neymar among top-rated Brazilians', () => {
      const players = filterPlayers(data.players, { nationality: 'Brazil', sortBy: 'overall', order: 'desc', limit: 10 });
      const names = players.map(p => p.name).join(' | ').toLowerCase();
      expect(names).toContain('neymar');
    });
  });

  describe('Scenario: search by player name', () => {
    it('finds Messi by partial name', () => {
      const players = filterPlayers(data.players, { name: 'Messi', limit: 5 });
      expect(players.length).toBeGreaterThan(0);
      expect(players.some(p => p.name.toLowerCase().includes('messi'))).toBe(true);
    });
  });

  describe('Scenario: filter by club', () => {
    it('returns Santos players when filtering by club', () => {
      const players = filterPlayers(data.players, { club: 'Santos', limit: 50 });
      expect(players.length).toBeGreaterThan(0);
      for (const p of players) {
        expect((p.club || '').toLowerCase()).toContain('santos');
      }
    });
  });
});

describe('Feature: Statistical analysis', () => {
  describe('Scenario: aggregate statistics for the Brasileirão', () => {
    it('reports average goals per match in a reasonable range', () => {
      const s = aggregateStats(data.matches, { competition: 'Brasileirão' });
      expect(s.totalMatches).toBeGreaterThan(0);
      expect(s.averageGoalsPerMatch).toBeGreaterThan(1.5);
      expect(s.averageGoalsPerMatch).toBeLessThan(4);
      expect(s.homeWinRate + s.awayWinRate + s.drawRate).toBeCloseTo(1, 2);
      expect(s.homeWinRate).toBeGreaterThan(s.awayWinRate);
    });
  });

  describe('Scenario: top scoring teams', () => {
    it('returns rankings sorted descending by goals', () => {
      const rows = topScoringTeams(data.matches, { competition: 'Brasileirão', season: 2019, limit: 5 });
      expect(rows.length).toBe(5);
      for (let i = 1; i < rows.length; i++) {
        expect(rows[i - 1].goals >= rows[i].goals).toBe(true);
      }
    });
  });

  describe('Scenario: biggest wins in the dataset', () => {
    it('returns matches sorted by goal margin', () => {
      const wins = biggestWins(data.matches, { limit: 5 });
      expect(wins.length).toBe(5);
      for (let i = 1; i < wins.length; i++) {
        const a = Math.abs(wins[i - 1].homeGoals - wins[i - 1].awayGoals);
        const b = Math.abs(wins[i].homeGoals - wins[i].awayGoals);
        expect(a >= b).toBe(true);
      }
      expect(Math.abs(wins[0].homeGoals - wins[0].awayGoals)).toBeGreaterThanOrEqual(5);
    });
  });
});

describe('Feature: Cross-file relationships', () => {
  describe('Scenario: Brazilian players by club summary', () => {
    it('returns groups with non-empty clubs and positive counts', () => {
      const rows = brazilianPlayersByClub(data.players);
      expect(rows.length).toBeGreaterThan(0);
      for (const r of rows.slice(0, 10)) {
        expect(r.count).toBeGreaterThan(0);
        expect(r.club).toBeTruthy();
      }
    });
  });

  describe('Scenario: list competitions a team has played in', () => {
    it('reports Brasileirão for Palmeiras', () => {
      const comps = competitionsForTeam(data.matches, 'Palmeiras');
      expect(comps).toContain('Brasileirão');
    });
  });
});
