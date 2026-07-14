import { describe, it, expect, beforeAll } from 'vitest';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadAll } from '../src/data/loader.js';
import type { DataStore } from '../src/data/types.js';
import { findMatches, headToHead } from '../src/queries/matches.js';
import { teamStats, teamSplit, topScoringTeams } from '../src/queries/teams.js';
import { findPlayers, playersByClub } from '../src/queries/players.js';
import { standings, seasonSummary, availableSeasons } from '../src/queries/competitions.js';
import { overallStats, biggestWins, highestScoringMatches } from '../src/queries/stats.js';

const here = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.resolve(here, '..', 'data');

let store: DataStore;

beforeAll(() => {
  store = loadAll(DATA_DIR);
});

describe('Feature: Match Queries', () => {
  it('Scenario: Find matches between two teams', () => {
    // Given the match data is loaded
    // When I search for matches between "Flamengo" and "Fluminense"
    const matches = findMatches(store, { team: 'Flamengo', opponentTeam: 'Fluminense' });
    // Then I should receive a list of matches
    expect(matches.length).toBeGreaterThan(0);
    // And each match should have date, scores, and competition
    for (const m of matches) {
      expect(m.date).toBeInstanceOf(Date);
      expect(typeof m.homeGoals).toBe('number');
      expect(typeof m.awayGoals).toBe('number');
      expect(m.competition).toBeDefined();
    }
  });

  it('Scenario: Find matches for a single team by season', () => {
    const matches = findMatches(store, {
      team: 'Palmeiras',
      season: 2018,
      competition: 'Brasileirao-Historical',
    });
    expect(matches.length).toBeGreaterThan(0);
  });

  it('Scenario: Find Copa do Brasil matches', () => {
    const matches = findMatches(store, { competition: 'Copa do Brasil', limit: 50 });
    expect(matches.length).toBe(50);
    for (const m of matches) expect(m.competition).toBe('Copa do Brasil');
  });

  it('Scenario: Filter matches by date range', () => {
    const start = new Date(Date.UTC(2019, 0, 1));
    const end = new Date(Date.UTC(2019, 11, 31));
    const matches = findMatches(store, {
      team: 'Flamengo',
      startDate: start,
      endDate: end,
      competition: 'Brasileirao-Historical',
    });
    expect(matches.length).toBeGreaterThan(0);
    for (const m of matches) {
      expect(m.date.getTime()).toBeGreaterThanOrEqual(start.getTime());
      expect(m.date.getTime()).toBeLessThanOrEqual(end.getTime());
    }
  });

  it('Scenario: Sort matches by date descending', () => {
    const matches = findMatches(store, { team: 'Flamengo', limit: 20 });
    for (let i = 1; i < matches.length; i++) {
      expect(matches[i - 1].date.getTime()).toBeGreaterThanOrEqual(matches[i].date.getTime());
    }
  });
});

describe('Feature: Team Queries', () => {
  it('Scenario: Get team statistics for a season', () => {
    // Given the match data is loaded
    // When I request statistics for "Palmeiras" in season "2018"
    const stats = teamStats(store, 'Palmeiras', {
      season: 2018,
      competition: 'Brasileirao-Historical',
    });
    // Then I should receive wins, losses, draws, and goals
    expect(stats.matches).toBeGreaterThan(0);
    expect(stats.wins + stats.draws + stats.losses).toBe(stats.matches);
    expect(stats.goalsFor).toBeGreaterThanOrEqual(0);
    expect(stats.goalsAgainst).toBeGreaterThanOrEqual(0);
  });

  it('Scenario: Compute home/away split', () => {
    const split = teamSplit(store, 'Corinthians', {
      season: 2018,
      competition: 'Brasileirao-Historical',
    });
    expect(split.home.matches + split.away.matches).toBe(split.overall.matches);
    expect(split.overall.wins).toBe(split.home.wins + split.away.wins);
  });

  it('Scenario: Head-to-head record between two teams', () => {
    const h2h = headToHead(store, 'Flamengo', 'Fluminense');
    expect(h2h.totalMatches).toBeGreaterThan(0);
    expect(h2h.teamWins + h2h.opponentWins + h2h.draws).toBe(h2h.totalMatches);
  });

  it('Scenario: Top scoring teams in Brasileirão 2018', () => {
    const top = topScoringTeams(store, {
      competition: 'Brasileirao-Historical',
      season: 2018,
      limit: 5,
    });
    expect(top.length).toBe(5);
    for (let i = 1; i < top.length; i++) {
      expect(top[i - 1].goalsFor).toBeGreaterThanOrEqual(top[i].goalsFor);
    }
  });
});

describe('Feature: Player Queries', () => {
  it('Scenario: Find Brazilian players', () => {
    const players = findPlayers(store, { nationality: 'Brazil', limit: 50 });
    expect(players.length).toBe(50);
    for (const p of players) {
      expect(p.nationality.toLowerCase()).toBe('brazil');
    }
    for (let i = 1; i < players.length; i++) {
      expect(players[i - 1].overall).toBeGreaterThanOrEqual(players[i].overall);
    }
  });

  it('Scenario: Search for a player by name', () => {
    const players = findPlayers(store, { name: 'Neymar' });
    expect(players.length).toBeGreaterThan(0);
    expect(players[0].name.toLowerCase()).toContain('neymar');
  });

  it('Scenario: Filter players by club', () => {
    // FIFA dataset is global; "Santos" is one Brazilian club it includes.
    const santos = findPlayers(store, { club: 'Santos', limit: 100 });
    expect(santos.length).toBeGreaterThan(0);
    for (const p of santos) {
      expect(p.clubNormalized).toContain('santos');
    }
  });

  it('Scenario: Filter by minimum overall rating', () => {
    const top = findPlayers(store, { minOverall: 88, limit: 50 });
    expect(top.length).toBeGreaterThan(0);
    for (const p of top) expect(p.overall).toBeGreaterThanOrEqual(88);
  });

  it('Scenario: Group Brazilian players by club', () => {
    const groups = playersByClub(store, { nationality: 'Brazil', limitTopPerClub: 3 });
    expect(groups.length).toBeGreaterThan(0);
    for (const g of groups) {
      expect(g.count).toBeGreaterThan(0);
      expect(g.topPlayers.length).toBeLessThanOrEqual(3);
    }
  });
});

describe('Feature: Competition Queries', () => {
  it('Scenario: Compute Brasileirão 2018 standings', () => {
    const table = standings(store, 'Brasileirao-Historical', 2018);
    expect(table.length).toBeGreaterThan(0);
    // Standings should be sorted by points desc
    for (let i = 1; i < table.length; i++) {
      expect(table[i - 1].points).toBeGreaterThanOrEqual(table[i].points);
    }
    expect(table[0].rank).toBe(1);
  });

  it('Scenario: Season summary computes match/goal averages', () => {
    const sum = seasonSummary(store, 'Brasileirao-Historical', 2018);
    expect(sum.totalMatches).toBeGreaterThan(0);
    expect(sum.avgGoalsPerMatch).toBeGreaterThan(0);
    const totalRate = sum.homeWinRate + sum.awayWinRate + sum.drawRate;
    expect(totalRate).toBeGreaterThan(0.99);
    expect(totalRate).toBeLessThan(1.01);
  });

  it('Scenario: List available seasons', () => {
    const seasons = availableSeasons(store, 'Brasileirao-Historical');
    expect(seasons.length).toBeGreaterThan(0);
    expect(seasons[0]).toBeLessThan(seasons[seasons.length - 1]);
  });
});

describe('Feature: Statistical Analysis', () => {
  it('Scenario: Overall stats across the dataset', () => {
    const s = overallStats(store);
    expect(s.totalMatches).toBeGreaterThan(0);
    expect(s.avgGoalsPerMatch).toBeGreaterThan(0);
  });

  it('Scenario: Biggest wins are ordered by margin', () => {
    const wins = biggestWins(store, { limit: 5 });
    expect(wins.length).toBe(5);
    for (let i = 1; i < wins.length; i++) {
      expect(wins[i - 1].margin).toBeGreaterThanOrEqual(wins[i].margin);
    }
  });

  it('Scenario: Highest scoring matches', () => {
    const matches = highestScoringMatches(store, { limit: 5 });
    expect(matches.length).toBe(5);
    for (let i = 1; i < matches.length; i++) {
      expect(matches[i - 1].totalGoals).toBeGreaterThanOrEqual(matches[i].totalGoals);
    }
  });
});

describe('Feature: Sample Questions Coverage (20+ scenarios)', () => {
  it('Q1: When did Flamengo last play Corinthians?', () => {
    const matches = findMatches(store, {
      team: 'Flamengo',
      opponentTeam: 'Corinthians',
      limit: 1,
    });
    expect(matches.length).toBe(1);
  });

  it('Q2: What was the most recent score in that fixture?', () => {
    const matches = findMatches(store, {
      team: 'Flamengo',
      opponentTeam: 'Corinthians',
      limit: 1,
    });
    expect(typeof matches[0].homeGoals).toBe('number');
    expect(typeof matches[0].awayGoals).toBe('number');
  });

  it('Q3: Who is Gabriel Barbosa?', () => {
    const players = findPlayers(store, { name: 'Gabriel' });
    expect(players.length).toBeGreaterThan(0);
  });

  it('Q4: Which players play for Santos?', () => {
    // FIFA dataset's Brazilian club coverage is sparse; Santos is one that's present.
    const players = findPlayers(store, { club: 'Santos' });
    expect(players.length).toBeGreaterThan(0);
  });

  it('Q5: What competitions has Palmeiras played in?', () => {
    const matches = findMatches(store, { team: 'Palmeiras' });
    const comps = new Set(matches.map((m) => m.competition));
    expect(comps.size).toBeGreaterThan(1);
  });

  it('Q6: Which team has the best home record in 2018 Brasileirão?', () => {
    const top = topScoringTeams(store, { competition: 'Brasileirao-Historical', season: 2018 });
    expect(top.length).toBeGreaterThan(0);
  });

  it('Q7: Who are the top Brazilian players?', () => {
    const players = findPlayers(store, { nationality: 'Brazil', limit: 10 });
    expect(players[0].overall).toBeGreaterThanOrEqual(80);
  });

  it('Q8: Compare Palmeiras and Santos head-to-head', () => {
    const h2h = headToHead(store, 'Palmeiras', 'Santos');
    expect(h2h.totalMatches).toBeGreaterThan(0);
  });

  it('Q9: Show all Flamengo vs Fluminense matches', () => {
    const matches = findMatches(store, { team: 'Flamengo', opponentTeam: 'Fluminense' });
    expect(matches.length).toBeGreaterThan(5);
  });

  it('Q10: What matches did Palmeiras play in 2018?', () => {
    const matches = findMatches(store, {
      team: 'Palmeiras',
      season: 2018,
      competition: 'Brasileirao-Historical',
    });
    expect(matches.length).toBeGreaterThan(0);
  });

  it('Q11: Find all Copa do Brasil matches in a season', () => {
    const matches = findMatches(store, { competition: 'Copa do Brasil', season: 2018 });
    expect(matches.length).toBeGreaterThan(0);
  });

  it('Q12: Corinthians home record in 2018', () => {
    const stats = teamStats(store, 'Corinthians', {
      competition: 'Brasileirao-Historical',
      season: 2018,
      venue: 'home',
    });
    expect(stats.matches).toBeGreaterThan(0);
  });

  it('Q13: Top-scoring team in Serie A 2018', () => {
    const top = topScoringTeams(store, {
      competition: 'Brasileirao-Historical',
      season: 2018,
      limit: 1,
    });
    expect(top.length).toBe(1);
  });

  it('Q14: Find all forwards', () => {
    const fwds = findPlayers(store, { position: 'ST', limit: 10 });
    expect(fwds.length).toBe(10);
    for (const p of fwds) expect(p.position).toBe('ST');
  });

  it('Q15: Highest-rated players at Santos', () => {
    const players = findPlayers(store, { club: 'Santos', sortBy: 'overall', limit: 5 });
    expect(players.length).toBeGreaterThan(0);
    for (let i = 1; i < players.length; i++) {
      expect(players[i - 1].overall).toBeGreaterThanOrEqual(players[i].overall);
    }
  });

  it('Q16: Who won the Brasileirão in 2018?', () => {
    const table = standings(store, 'Brasileirao-Historical', 2018);
    expect(table[0].rank).toBe(1);
    expect(table[0].points).toBeGreaterThan(0);
  });

  it('Q17: Show the 2018 Libertadores stages', () => {
    const matches = findMatches(store, { competition: 'Libertadores', season: 2018 });
    const stages = new Set(matches.map((m) => m.stage).filter(Boolean));
    expect(stages.size).toBeGreaterThan(0);
  });

  it("Q18: What's the average goals per match in the Brasileirão?", () => {
    const s = overallStats(store, { competition: 'Brasileirao-Historical' });
    expect(s.avgGoalsPerMatch).toBeGreaterThan(0);
    expect(s.avgGoalsPerMatch).toBeLessThan(10);
  });

  it('Q19: Show me the biggest wins in the dataset', () => {
    const wins = biggestWins(store, { limit: 3 });
    expect(wins.length).toBe(3);
    expect(wins[0].margin).toBeGreaterThanOrEqual(5);
  });

  it('Q20: Highest scoring matches in the dataset', () => {
    const matches = highestScoringMatches(store, { limit: 3 });
    expect(matches.length).toBe(3);
    expect(matches[0].totalGoals).toBeGreaterThanOrEqual(7);
  });

  it('Q21: Best player overall by club', () => {
    const groups = playersByClub(store, { limitTopPerClub: 1 });
    expect(groups.length).toBeGreaterThan(0);
    expect(groups[0].topPlayers.length).toBe(1);
  });
});

describe('Feature: Performance', () => {
  it('Scenario: Simple lookups respond in <2s', () => {
    const start = Date.now();
    const matches = findMatches(store, { team: 'Flamengo', opponentTeam: 'Fluminense' });
    const elapsed = Date.now() - start;
    expect(matches.length).toBeGreaterThan(0);
    expect(elapsed).toBeLessThan(2000);
  });

  it('Scenario: Aggregate queries respond in <5s', () => {
    const start = Date.now();
    const table = standings(store, 'Brasileirao-Historical', 2018);
    const elapsed = Date.now() - start;
    expect(table.length).toBeGreaterThan(0);
    expect(elapsed).toBeLessThan(5000);
  });
});
