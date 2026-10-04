import { describe, expect, it } from 'vitest';
import { COMPETITIONS } from '../src/data.js';
import { resolveCompetition } from '../src/queries.js';
import { kb } from './helpers.js';

describe('Feature: Match Queries', () => {
  it('Scenario: Find matches between two teams', () => {
    // When I search for matches between "Flamengo" and "Fluminense"
    const matches = kb.findMatches({ team: 'Flamengo', opponent: 'Fluminense' });
    // Then I should receive a list of matches, each with date, scores and competition
    expect(matches.length).toBeGreaterThan(30);
    const [fla, flu] = [kb.team('Flamengo'), kb.team('Fluminense')];
    for (const m of matches) {
      expect([m.home, m.away].sort()).toEqual([fla, flu].sort());
      expect(m.date).toBeTruthy();
      expect(m.competition).toBeTruthy();
    }
    // And most recent first
    expect(matches[0].date >= matches[matches.length - 1].date).toBe(true);
  });

  it('Scenario: Filter by home team, away team, season and date range', () => {
    const home = kb.findMatches({ homeTeam: 'Palmeiras', season: 2019, competition: 'Brasileirão' });
    expect(home).toHaveLength(19);
    expect(home.every((m) => m.home === kb.team('Palmeiras'))).toBe(true);
    const away = kb.findMatches({ awayTeam: 'Palmeiras', season: 2019, competition: 'Brasileirão' });
    expect(away).toHaveLength(19);
    const may = kb.findMatches({ team: 'Santos', dateFrom: '2015-05-01', dateTo: '2015-05-31' });
    expect(may.length).toBeGreaterThan(0);
    expect(may.every((m) => m.date >= '2015-05-01' && m.date <= '2015-05-31')).toBe(true);
  });

  it('Scenario: Filter by competition', () => {
    for (const c of Object.values(COMPETITIONS)) {
      const ms = kb.findMatches({ competition: c });
      expect(ms.length).toBeGreaterThan(1000);
      expect(ms.every((m) => m.competition === c)).toBe(true);
    }
    expect(resolveCompetition('brasileirao')).toBe(COMPETITIONS.serieA);
    expect(resolveCompetition('Copa do Brasil')).toBe(COMPETITIONS.cup);
    expect(resolveCompetition('copa libertadores')).toBe(COMPETITIONS.libertadores);
    expect(() => resolveCompetition('Premier')).toThrow(/Unknown competition/);
  });

  it('Scenario: Find all Copa do Brasil finals', () => {
    const finals = kb.findMatches({ competition: 'Copa do Brasil', stage: 'final' });
    expect(finals).toHaveLength(24); // 2012-2023, two legs each
    const pair = (season: number) =>
      [...new Set(finals.filter((m) => m.season === season).flatMap((m) => [kb.teamName(m.home), kb.teamName(m.away)]))].sort();
    expect(pair(2015)).toEqual(['Palmeiras', 'Santos']);
    expect(pair(2020)).toEqual(['Grêmio', 'Palmeiras']);
    expect(pair(2023)).toEqual(['Flamengo', 'São Paulo']);
  });

  it('Scenario: Find derbies in a season', () => {
    const derbies = kb.derbies({ season: 2019 });
    expect(derbies.length).toBeGreaterThan(20);
    expect(derbies.every((m) => kb.derbyName(m.home, m.away))).toBe(true);
    expect(kb.derbyName(kb.team('Internacional'), kb.team('Gremio'))).toBe('Grenal');
  });
});

describe('Feature: Team Queries', () => {
  it('Scenario: Get team statistics', () => {
    // When I request statistics for "Flamengo" in season 2019
    const r = kb.teamRecord('Flamengo', { season: 2019, competition: 'Brasileirão' });
    // Then I should receive wins, losses, draws, and goals
    expect(r).toMatchObject({ matches: 38, wins: 28, draws: 6, losses: 4, goalsFor: 86, goalsAgainst: 37, points: 90 });
    expect(r.winRate).toBeCloseTo(73.7, 1);
  });

  it('Scenario: Home and away records add up to the full record', () => {
    const f = { season: 2022, competition: 'Brasileirão' };
    const all = kb.teamRecord('Corinthians', f);
    const home = kb.teamRecord('Corinthians', { ...f, venue: 'home' });
    const away = kb.teamRecord('Corinthians', { ...f, venue: 'away' });
    expect(home.matches).toBe(19);
    for (const k of ['matches', 'wins', 'draws', 'losses', 'goalsFor', 'goalsAgainst'] as const) {
      expect(home[k] + away[k]).toBe(all[k]);
    }
  });

  it('Scenario: Compare teams head-to-head', () => {
    const h = kb.headToHead('Palmeiras', 'Santos');
    expect(h.matches.length).toBeGreaterThan(30);
    expect(h.winsA + h.winsB + h.draws).toBe(h.matches.length);
    const reverse = kb.headToHead('Santos', 'Palmeiras');
    expect([reverse.winsA, reverse.winsB, reverse.goalsA]).toEqual([h.winsB, h.winsA, h.goalsB]);
  });

  it('Scenario: List the competitions a team has played in', () => {
    const comps = kb.teamCompetitions('Palmeiras').map((c) => c.competition);
    expect(comps).toEqual(expect.arrayContaining([COMPETITIONS.serieA, COMPETITIONS.cup, COMPETITIONS.libertadores]));
  });

  it('Scenario: A team with no matches in scope gets an empty record', () => {
    expect(kb.teamRecord('Flamengo', { season: 1990 }).matches).toBe(0);
  });
});

describe('Feature: Competition Queries', () => {
  it('Scenario: Standings are calculated from match results', () => {
    const table = kb.standings(2019);
    expect(table).toHaveLength(20);
    expect(table.slice(0, 3).map((r) => [kb.teamName(r.team), r.points, r.wins, r.draws, r.losses])).toEqual([
      ['Flamengo', 90, 28, 6, 4],
      ['Santos', 74, 22, 8, 8],
      ['Palmeiras', 74, 21, 11, 6],
    ]);
    expect(table.slice(-4).map((r) => kb.teamName(r.team)).sort()).toEqual(['Avaí', 'CSA', 'Chapecoense', 'Cruzeiro']);
  });

  it.each([
    [2017, 'Corinthians'],
    [2018, 'Palmeiras'],
    [2020, 'Flamengo'],
    [2021, 'Atlético-MG'],
    [2022, 'Palmeiras'],
  ])('Scenario: the %i Brasileirão champion is %s', (season, champion) => {
    expect(kb.teamName(kb.standings(season)[0].team)).toBe(champion);
  });

  it('Scenario: Seasons available per competition', () => {
    expect(kb.seasons('Brasileirão')[0]).toBe(2003);
    expect(kb.seasons('Libertadores')).toEqual([2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022]);
  });
});

describe('Feature: Statistical Analysis', () => {
  it('Scenario: Average goals per match and home advantage', () => {
    const s = kb.leagueStats({ competition: 'Brasileirão' });
    expect(s.goalsPerMatch).toBeGreaterThan(2);
    expect(s.goalsPerMatch).toBeLessThan(3);
    expect(s.homeWins + s.draws + s.awayWins).toBe(s.matches);
    expect(s.homeWinRate).toBeGreaterThan(s.awayWinRate);
    expect(s.homeWinRate + s.drawRate + s.awayWinRate).toBeCloseTo(100, 6);
  });

  it('Scenario: Biggest wins are ordered by margin', () => {
    const wins = kb.biggestWins({}, 10);
    const margins = wins.map((m) => Math.abs(m.homeGoals - m.awayGoals));
    expect(margins[0]).toBeGreaterThanOrEqual(7);
    expect(margins).toEqual([...margins].sort((a, b) => b - a));
  });

  it('Scenario: Best home and away records', () => {
    const home = kb.rankTeams({ competition: 'Brasileirão', venue: 'home', minMatches: 100 });
    const away = kb.rankTeams({ competition: 'Brasileirão', venue: 'away', minMatches: 100 });
    expect(home[0].winRate).toBeGreaterThan(away[0].winRate);
    expect(home.every((r) => r.matches >= 100)).toBe(true);
    expect(home[0].winRate).toBeGreaterThanOrEqual(home[1].winRate);
  });

  it('Scenario: Top scoring team of a season', () => {
    const top = kb.rankTeams({ competition: 'Serie A', season: 2019, metric: 'goalsFor' })[0];
    expect(kb.teamName(top.team)).toBe('Flamengo');
    expect(top.goalsFor).toBe(86);
  });
});

describe('Feature: Player Queries', () => {
  it('Scenario: Search a player by name, ignoring accents and case', () => {
    const [p] = kb.findPlayers({ name: 'neymar' });
    expect(p).toMatchObject({ name: 'Neymar Jr', nationality: 'Brazil', overall: 92, position: 'LW', club: 'Paris Saint-Germain' });
    expect(p.skills.Dribbling).toBe(96);
  });

  it('Scenario: Filter by nationality, sorted by rating', () => {
    const br = kb.findPlayers({ nationality: 'Brazilian' });
    expect(br).toHaveLength(827);
    expect(br[0].name).toBe('Neymar Jr');
    expect(br.every((p) => p.nationality === 'Brazil')).toBe(true);
    expect(br.map((p) => p.overall)).toEqual([...br.map((p) => p.overall)].sort((a, b) => b - a));
  });

  it('Scenario: Filter by Brazilian club and position group', () => {
    const santos = kb.findPlayers({ club: 'Santos' });
    expect(santos.length).toBeGreaterThan(10);
    expect(santos.every((p) => p.club === 'Santos')).toBe(true); // not "Santos Laguna"
    const forwards = kb.findPlayers({ club: 'Santos', position: 'forwards' });
    expect(forwards.length).toBeGreaterThan(0);
    expect(forwards.every((p) => ['ST', 'LS', 'RS', 'CF', 'LF', 'RF', 'LW', 'RW'].includes(p.position))).toBe(true);
    expect(kb.findPlayers({ club: 'Gremio', position: 'GK' }).every((p) => p.position === 'GK')).toBe(true);
  });

  it('Scenario: Filter by a foreign club and minimum rating', () => {
    const ps = kb.findPlayers({ club: 'Real Madrid', minOverall: 88 });
    expect(ps.length).toBeGreaterThan(3);
    expect(ps.every((p) => p.club === 'Real Madrid' && p.overall >= 88)).toBe(true);
  });

  it('Scenario: Cross-file - FIFA clubs are linked to teams in the match data', () => {
    const squads = kb.brazilianClubSquads('Brazil');
    const clubs = squads.map((s) => kb.teamName(s.clubId));
    expect(clubs).toEqual(expect.arrayContaining(['Grêmio', 'Santos', 'Atlético-MG', 'Athletico-PR', 'Sport', 'América-MG']));
    // Portugal's Boavista FC must not be mistaken for Boavista-RJ.
    expect(kb.findPlayers({ club: 'Boavista FC' }).every((p) => p.clubId === undefined)).toBe(true);
    for (const s of squads) expect(kb.findMatches({ team: kb.teamName(s.clubId) }).length).toBeGreaterThan(0);
  });
});
