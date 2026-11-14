import { describe, expect, it } from 'vitest';
import { QueryError } from '../src/queries.js';
import { givenDataIsLoaded } from './helpers.js';

const db = givenDataIsLoaded();

describe('Feature: Data coverage', () => {
  it('Scenario: All six CSV files are loaded with the documented row counts', () => {
    expect(db.ds.counts).toEqual({
      'Brasileirao_Matches.csv': 4180,
      'Brazilian_Cup_Matches.csv': 1337,
      'Libertadores_Matches.csv': 1255,
      'BR-Football-Dataset.csv': 10296,
      'novo_campeonato_brasileiro.csv': 6886,
      'fifa_data.csv': 18207,
    });
    expect(db.players).toHaveLength(18207);
  });

  it.each(['brasileirao', 'copa_do_brasil', 'libertadores', 'br_football', 'historical'] as const)(
    'Scenario: File "%s" is individually queryable',
    (source) => {
      const ms = db.findMatches({ source });
      expect(ms.length).toBeGreaterThan(1000);
      expect(ms.every((m) => m.source === source)).toBe(true);
    },
  );

  it('Scenario: Overlapping files are not double counted', () => {
    // Série A 2015 exists in three files; the default view has exactly one 380-match season.
    expect(db.findMatches({ competition: 'Serie A', season: 2015 })).toHaveLength(380);
    expect(db.findMatches({ competition: 'Serie A', season: 2015, includeDuplicates: true }).length).toBeGreaterThan(760);
    expect(db.findMatches({ competition: 'Serie A', season: 2005 })).toHaveLength(462);
  });
});

describe('Feature: Match Queries', () => {
  it('Scenario: Find matches between two teams', () => {
    // When I search for matches between "Flamengo" and "Fluminense"
    const ms = db.findMatches({ team: 'Flamengo', opponent: 'Fluminense' });
    // Then I should receive a list of matches, each with date, scores and competition
    expect(ms.length).toBeGreaterThan(30);
    for (const m of ms) {
      expect([m.homeKey, m.awayKey].sort()).toEqual(['flamengo', 'fluminense']);
      expect(m.date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      expect(m.competition).toBeTruthy();
    }
    expect(ms.filter((m) => m.homeGoals !== null).length).toBeGreaterThan(30);
    // And they are ordered most recent first
    expect(ms[0].date! >= ms[ms.length - 1].date!).toBe(true);
  });

  it('Scenario: Name variants return the same matches', () => {
    const a = db.findMatches({ team: 'Palmeiras', season: 2019 });
    const b = db.findMatches({ team: 'Palmeiras-SP', season: 2019 });
    const c = db.findMatches({ team: 'palmeiras - sp', season: 2019 });
    expect(a.length).toBeGreaterThan(38);
    expect(b).toEqual(a);
    expect(c).toEqual(a);
  });

  it('Scenario: Filter by team, season, venue and competition', () => {
    const home = db.findMatches({ team: 'Corinthians', venue: 'home', season: 2019, competition: 'Brasileirão' });
    expect(home).toHaveLength(19);
    expect(home.every((m) => m.homeKey === 'corinthians' && m.season === 2019)).toBe(true);
    const away = db.findMatches({ team: 'Corinthians', venue: 'away', season: 2019, competition: 'Brasileirão' });
    expect(away).toHaveLength(19);
  });

  it('Scenario: Filter by date range (either date format)', () => {
    const ms = db.findMatches({ dateFrom: '2019-10-01', dateTo: '31/10/2019', competition: 'Serie A' });
    expect(ms.length).toBeGreaterThan(20);
    expect(ms.every((m) => m.date! >= '2019-10-01' && m.date! <= '2019-10-31')).toBe(true);
  });

  it('Scenario: Find all Copa do Brasil finals', () => {
    const finals = db.findMatches({ competition: 'Copa do Brasil', stage: 'final' });
    expect(finals.length).toBeGreaterThanOrEqual(16);
    const f2019 = finals.filter((m) => m.season === 2019);
    expect(f2019).toHaveLength(2);
    expect(f2019.map((m) => [m.homeKey, m.awayKey].sort().join(' v '))).toEqual([
      'athletico pr v internacional',
      'athletico pr v internacional',
    ]);
  });

  it('Scenario: Libertadores matches can be filtered by stage', () => {
    const semis = db.findMatches({ competition: 'Libertadores', season: 2019, stage: 'semifinals' });
    expect(semis).toHaveLength(4);
    expect(semis.some((m) => m.homeKey === 'flamengo' && m.awayKey === 'gremio' && m.homeGoals === 5)).toBe(true);
  });

  it('Scenario: Unknown and ambiguous team names give helpful errors', () => {
    expect(() => db.findMatches({ team: 'Real Madrid Castilla' })).toThrow(QueryError);
    expect(() => db.findMatches({ team: 'Atlético' })).toThrow(/ambiguous.*Atlético-MG/s);
    expect(() => db.findMatches({ competition: 'Bundesliga' })).toThrow(/Unknown competition/);
    expect(() => db.findMatches({ dateFrom: 'yesterday' })).toThrow(/Unrecognised date/);
  });
});

describe('Feature: Team Queries', () => {
  it('Scenario: Get team statistics for a season', () => {
    // When I request statistics for "Flamengo" in season 2019 (Brasileirão)
    const s = db.teamStats('Flamengo', { season: 2019, competition: 'Brasileirão' });
    // Then I should receive wins, losses, draws, and goals (Flamengo: 28W 6D 4L, 86-37, 90 pts)
    expect(s.overall).toMatchObject({ matches: 38, wins: 28, draws: 6, losses: 4, goalsFor: 86, goalsAgainst: 37, points: 90 });
    expect(s.home.matches + s.away.matches).toBe(38);
    expect(s.overall.winRate).toBeCloseTo(73.7, 1);
  });

  it('Scenario: Home record', () => {
    const s = db.teamStats('Corinthians', { season: 2019, competition: 'Serie A', venue: 'home' });
    expect(s.overall.matches).toBe(19);
    expect(s.overall.wins + s.overall.draws + s.overall.losses).toBe(19);
    expect(s.overall).toEqual(s.home);
  });

  it('Scenario: Compare two teams head-to-head', () => {
    const h = db.headToHead('Palmeiras', 'Santos');
    expect(h.played).toBeGreaterThan(30);
    expect(h.winsA + h.winsB + h.draws).toBe(h.played);
    expect(h.rivalry).toBe('Clássico da Saudade');
    // And the comparison is symmetric
    const r = db.headToHead('Santos-SP', 'Palmeiras-SP');
    expect(r.winsA).toBe(h.winsB);
    expect(r.goalsA).toBe(h.goalsB);
  });

  it('Scenario: Which competitions has a team played in (cross-file)', () => {
    const p = db.teamProfile('Palmeiras');
    expect(p.competitions.map((c) => c.competition)).toEqual(
      expect.arrayContaining(['Brasileirão Série A', 'Copa do Brasil', 'Copa Libertadores']),
    );
    expect(p.aliases).toEqual(expect.arrayContaining(['Palmeiras', 'Palmeiras-SP', 'Palmeiras - SP']));
  });

  it('Scenario: Team profile joins match data with FIFA player data', () => {
    const p = db.teamProfile('Gremio');
    expect(p.overall.matches).toBeGreaterThan(500);
    expect(p.players.length).toBe(20);
    expect(p.players.every((x) => x.club === 'Grêmio')).toBe(true);
    expect(p.rivals.map((r) => r.team)).toContain('Internacional');
  });
});

describe('Feature: Competition Queries', () => {
  it('Scenario: Who won the 2019 Brasileirão', () => {
    const s = db.standings(2019);
    expect(s.complete).toBe(true);
    expect(s.champion).toBe('Flamengo');
    expect(s.rows).toHaveLength(20);
    expect(s.rows.slice(0, 3).map((r) => [r.team, r.points, r.wins, r.draws, r.losses])).toEqual([
      ['Flamengo', 90, 28, 6, 4],
      ['Santos', 74, 22, 8, 8],
      ['Palmeiras', 74, 21, 11, 6],
    ]);
    expect(s.relegated).toEqual(expect.arrayContaining(['Cruzeiro', 'CSA', 'Chapecoense', 'Avaí']));
  });

  it('Scenario: Standings from the historical file (pre-2012)', () => {
    const s = db.standings(2009);
    expect(s.champion).toBe('Flamengo');
    expect(s.rows[0].points).toBe(67);
  });

  it('Scenario: Standings totals are internally consistent', () => {
    const s = db.standings(2017, 'Serie A');
    const sum = (f: (r: (typeof s.rows)[0]) => number) => s.rows.reduce((t, r) => t + f(r), 0);
    expect(sum((r) => r.wins)).toBe(sum((r) => r.losses));
    expect(sum((r) => r.goalsFor)).toBe(sum((r) => r.goalsAgainst));
    expect(sum((r) => r.matches)).toBe(760);
    expect(s.champion).toBe('Corinthians');
  });

  it('Scenario: Incomplete seasons do not declare a champion', () => {
    const s = db.standings(2022);
    expect(s.matchesUnplayed).toBeGreaterThan(0);
    expect(s.champion).toBeNull();
    expect(() => db.standings(1990)).toThrow(/Available seasons/);
  });

  it('Scenario: Show the 2018 Copa Libertadores bracket', () => {
    const c = db.cupSummary('Libertadores', 2018);
    expect(c.stages.map((s) => s.stage)).toEqual(['group stage', 'round of 16', 'quarterfinals', 'semifinals', 'final']);
    expect(c.stages[1].ties).toHaveLength(8);
    expect(c.final!.teams.sort()).toEqual(['Boca Juniors', 'River Plate']);
    expect(c.champion).toBe('River Plate');
  });

  it('Scenario: Copa do Brasil winner from the two-leg final', () => {
    const c = db.cupSummary('Copa do Brasil', 2019);
    expect(c.final!.aggregate!.slice().sort()).toEqual([1, 3]);
    expect(c.champion).toBe('Athletico-PR');
  });
});

describe('Feature: Statistical Analysis', () => {
  it('Scenario: Average goals per match in the Brasileirão', () => {
    const s = db.leagueStats({ competition: 'Brasileirão' });
    expect(s.matches).toBeGreaterThan(8000);
    expect(s.avgGoalsPerMatch).toBeGreaterThan(2.2);
    expect(s.avgGoalsPerMatch).toBeLessThan(3);
    expect(s.homeWins + s.draws + s.awayWins).toBe(s.matches);
    expect(s.homeWinRate + s.drawRate + s.awayWinRate).toBeCloseTo(100, 0);
    expect(s.homeWinRate).toBeGreaterThan(s.awayWinRate);
  });

  it('Scenario: Biggest wins in the dataset', () => {
    const ms = db.biggestWins({}, 5);
    expect(ms).toHaveLength(5);
    const margins = ms.map((m) => Math.abs(m.homeGoals! - m.awayGoals!));
    expect(margins).toEqual([...margins].sort((a, b) => b - a));
    expect(margins[0]).toBeGreaterThanOrEqual(7);
    const one = db.biggestWins({ team: 'Flamengo', competition: 'Serie A', season: 2019 }, 1)[0];
    expect([one.homeKey, one.awayKey]).toContain('flamengo');
  });

  it('Scenario: Which team scored the most goals in a season', () => {
    const top = db.rankTeams('goals_for', { competition: 'Serie A', season: 2019 }, { limit: 3 });
    expect(top[0]).toMatchObject({ team: 'Flamengo', value: 86 });
  });

  it('Scenario: Best home and away records', () => {
    const home = db.rankTeams('win_rate', { competition: 'Serie A', venue: 'home' }, { minMatches: 100 });
    const away = db.rankTeams('win_rate', { competition: 'Serie A', venue: 'away' }, { minMatches: 100 });
    expect(home).toHaveLength(10);
    expect(home[0].value).toBeGreaterThan(away[0].value);
    expect(home.every((r) => r.record.matches >= 100)).toBe(true);
    expect(home.map((r) => r.value)).toEqual([...home.map((r) => r.value)].sort((a, b) => b - a));
  });

  it('Scenario: Compare the 2018 and 2019 seasons', () => {
    const c = db.compareSeasons(2018, 2019);
    expect(c.a.champion).toBe('Palmeiras');
    expect(c.b.champion).toBe('Flamengo');
    expect(c.a.stats.matches).toBe(380);
    expect(c.b.stats.totalGoals).toBe(876);
  });

  it('Scenario: Show derbies in a season', () => {
    const ds = db.derbies({ season: 2019, competition: 'Serie A' });
    expect(ds.length).toBeGreaterThan(20);
    expect(ds.some((d) => d.name === 'Fla-Flu')).toBe(true);
    expect(ds.some((d) => d.name === 'Grenal')).toBe(true);
  });

  it('Scenario: Extended statistics (corners, shots) from BR-Football-Dataset', () => {
    const s = db.extendedStats({ team: 'Palmeiras', season: 2023 });
    expect(s.matches).toBeGreaterThan(30);
    expect(s.corners!.for).toBeGreaterThan(2);
    expect(s.shots!.for).toBeGreaterThan(5);
  });
});

describe('Feature: Player Queries', () => {
  it('Scenario: Search a player by name', () => {
    const r = db.searchPlayers({ name: 'Neymar' });
    expect(r.players[0]).toMatchObject({ name: 'Neymar Jr', nationality: 'Brazil', overall: 92, position: 'LW', club: 'Paris Saint-Germain' });
    expect(r.players[0].attributes.Dribbling).toBe(96);
  });

  it('Scenario: Find all Brazilian players, best first', () => {
    const r = db.searchPlayers({ nationality: 'Brazilian', limit: 1000 });
    expect(r.total).toBe(827);
    expect(r.players.every((p) => p.nationality === 'Brazil')).toBe(true);
    expect(r.players[0].name).toBe('Neymar Jr');
    const overall = r.players.map((p) => p.overall);
    expect(overall).toEqual([...overall].sort((a, b) => b - a));
  });

  it('Scenario: Filter by club and position group', () => {
    const squad = db.searchPlayers({ club: 'Santos', limit: 100 });
    expect(squad.players.filter((p) => p.club === 'Santos')).toHaveLength(20);
    const fwd = db.searchPlayers({ club: 'Grêmio', position: 'forwards' });
    expect(fwd.total).toBeGreaterThan(0);
    expect(fwd.players.every((p) => ['ST', 'CF', 'LF', 'RF', 'LW', 'RW', 'LS', 'RS'].includes(p.position))).toBe(true);
    const gk = db.searchPlayers({ nationality: 'Brazil', position: 'GK', limit: 1 });
    expect(gk.players[0]).toMatchObject({ name: 'Ederson', position: 'GK' });
  });

  it('Scenario: Club name variants match FIFA club names', () => {
    expect(db.searchPlayers({ club: 'Atlético-MG' }).total).toBe(20);
    expect(db.searchPlayers({ club: 'Sport Recife' }).total).toBe(20);
  });

  it('Scenario: Brazilian players at Brazilian clubs', () => {
    const rows = db.clubSummary({ nationality: 'Brazil', brazilianClubsOnly: true, limit: 50 });
    const clubs = rows.map((r) => r.club);
    expect(clubs).toEqual(expect.arrayContaining(['Grêmio', 'Santos', 'Cruzeiro', 'Fluminense']));
    expect(clubs).not.toContain('Boavista FC'); // Portuguese club sharing a name with Boavista-RJ
    expect(rows.every((r) => r.avgOverall > 50 && r.players > 0)).toBe(true);
  });

  it('Scenario: A full-name search falls back to partial matches', () => {
    const r = db.searchPlayers({ name: 'Gabriel Barbosa' });
    expect(r.partialNameMatch).toBe(true);
    expect(r.total).toBeGreaterThan(0);
  });
});

describe('Feature: Query performance', () => {
  it('Scenario: Simple lookups respond in under 2 seconds', () => {
    const t = performance.now();
    db.findMatches({ team: 'Flamengo', opponent: 'Corinthians' });
    db.searchPlayers({ name: 'Gabriel' });
    expect(performance.now() - t).toBeLessThan(2000);
  });
  it('Scenario: Aggregate queries respond in under 5 seconds', () => {
    const t = performance.now();
    db.standings(2019);
    db.leagueStats();
    db.rankTeams('win_rate', { venue: 'away' });
    db.compareSeasons(2018, 2019);
    expect(performance.now() - t).toBeLessThan(5000);
  });
});
