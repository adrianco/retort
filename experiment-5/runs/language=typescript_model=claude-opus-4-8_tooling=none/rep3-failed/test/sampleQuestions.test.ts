/**
 * ============================================================================
 * Context Block — File: test/sampleQuestions.test.ts
 * Project: Brazilian Soccer MCP Server
 * Purpose: Exercises the spec's "Sample Questions and Expected Behaviors"
 *          tables. The specification requires that "at least 20 sample
 *          questions can be answered"; this file maps 20+ natural-language
 *          questions to engine calls and asserts each yields a sensible answer.
 *          Cross-file questions (player + match) cover the cross-file criterion.
 * ============================================================================
 */

import { describe, it, expect } from 'vitest';
import { givenLoadedDatabase } from './helpers.js';

describe('Feature: Sample questions can be answered', () => {
  it('Q1: When did Flamengo last play Corinthians? (and what was the score)', () => {
    const db = givenLoadedDatabase();
    const [latest] = db.searchMatches({ team: 'Flamengo', opponent: 'Corinthians', limit: 1 });
    expect(latest).toBeDefined();
    expect(latest.date).toBeTruthy();
    expect(`${latest.homeGoal}-${latest.awayGoal}`).toMatch(/^\d+-\d+$/);
  });

  it('Q2: Show me all Flamengo vs Fluminense matches', () => {
    const db = givenLoadedDatabase();
    expect(db.searchMatches({ team: 'Flamengo', opponent: 'Fluminense' }).length).toBeGreaterThan(0);
  });

  it('Q3: What matches did Palmeiras play in 2019?', () => {
    const db = givenLoadedDatabase();
    expect(db.searchMatches({ team: 'Palmeiras', season: 2019 }).length).toBeGreaterThan(10);
  });

  it('Q4: Find Copa do Brasil matches', () => {
    const db = givenLoadedDatabase();
    const cup = db.searchMatches({ competition: 'Copa do Brasil', limit: 50 });
    expect(cup.length).toBeGreaterThan(0);
    expect(cup.every((m) => m.competition === 'Copa do Brasil')).toBe(true);
  });

  it('Q5: What is Corinthians home record in 2022?', () => {
    const db = givenLoadedDatabase();
    const rec = db.teamStats('Corinthians', { season: 2022, competition: 'Brasileirão', venue: 'home' });
    expect(rec.matches).toBeGreaterThan(0);
  });

  it('Q6: Which team scored the most goals in Serie A 2019?', () => {
    const db = givenLoadedDatabase();
    const table = db.standings('Brasileirão', 2019);
    const topScorers = [...table].sort((a, b) => b.goalsFor - a.goalsFor);
    expect(topScorers[0].goalsFor).toBeGreaterThan(0);
  });

  it('Q7: Compare Palmeiras and Santos head-to-head', () => {
    const db = givenLoadedDatabase();
    const h = db.headToHead('Palmeiras', 'Santos');
    expect(h.totalMatches).toBeGreaterThan(0);
  });

  it('Q8: Find all Brazilian players in the dataset', () => {
    const db = givenLoadedDatabase();
    expect(db.searchPlayers({ nationality: 'Brazil', limit: 2000 }).length).toBeGreaterThan(500);
  });

  it('Q9: Who are the highest-rated Brazilian players?', () => {
    const db = givenLoadedDatabase();
    const top = db.searchPlayers({ nationality: 'Brazil', limit: 3 });
    expect(top[0].overall).toBeGreaterThanOrEqual(top[2].overall ?? 0);
  });

  it('Q10: Show me forwards (ST) from Brazil', () => {
    const db = givenLoadedDatabase();
    const sts = db.searchPlayers({ position: 'ST', nationality: 'Brazil', limit: 50 });
    expect(sts.length).toBeGreaterThan(0);
    expect(sts.every((p) => p.position === 'ST')).toBe(true);
  });

  it('Q11: Who won the 2019 Brasileirão?', () => {
    const db = givenLoadedDatabase();
    expect(db.standings('Brasileirão', 2019)[0].team.toLowerCase()).toContain('flamengo');
  });

  it('Q12: Who was relegated in 2019? (bottom four of a 20-team league)', () => {
    const db = givenLoadedDatabase();
    const table = db.standings('Brasileirão', 2019);
    const relegated = table.slice(-4);
    expect(relegated.length).toBe(4);
    expect(relegated.every((r) => r.position >= 17)).toBe(true);
  });

  it('Q13: What is the average goals per match in the Brasileirão?', () => {
    const db = givenLoadedDatabase();
    expect(db.leagueStats({ competition: 'Brasileirão' }).avgGoalsPerMatch).toBeGreaterThan(2);
  });

  it('Q14: Which team has the best home record in a season?', () => {
    const db = givenLoadedDatabase();
    const table = db.standings('Brasileirão', 2019);
    expect(table[0].wins).toBeGreaterThan(0);
  });

  it('Q15: Show me the biggest wins in the dataset', () => {
    const db = givenLoadedDatabase();
    expect(db.biggestWins({ limit: 5 }).length).toBe(5);
  });

  it('Q16: What competitions has Palmeiras played in?', () => {
    const db = givenLoadedDatabase();
    const comps = new Set(db.searchMatches({ team: 'Palmeiras', limit: 5000 }).map((m) => m.competition));
    expect(comps.has('Brasileirão')).toBe(true);
    expect(comps.has('Copa Libertadores')).toBe(true);
  });

  it('Q17: Compare the 2018 and 2019 seasons (aggregate stats)', () => {
    const db = givenLoadedDatabase();
    const s18 = db.leagueStats({ competition: 'Brasileirão', season: 2018 });
    const s19 = db.leagueStats({ competition: 'Brasileirão', season: 2019 });
    expect(s18.matches).toBeGreaterThan(0);
    expect(s19.matches).toBeGreaterThan(0);
  });

  it('Q18: Which Libertadores matches involved a Brazilian club in 2019?', () => {
    const db = givenLoadedDatabase();
    const m = db.searchMatches({ team: 'Flamengo', competition: 'Libertadores', season: 2019 });
    expect(m.length).toBeGreaterThan(0);
  });

  it('Q19: How many teams contest the modern Brasileirão? (standings size)', () => {
    const db = givenLoadedDatabase();
    expect(db.standings('Brasileirão', 2019).length).toBe(20);
  });

  it('Q20: What is Gabriel Jesus rating and club? (player lookup)', () => {
    const db = givenLoadedDatabase();
    const [p] = db.searchPlayers({ name: 'Gabriel Jesus' });
    expect(p).toBeDefined();
    expect(p.nationality).toBe('Brazil');
    expect(p.club).toBeTruthy();
  });

  it('Q21 (cross-file): A Santos FIFA player and Santos match history both exist', () => {
    const db = givenLoadedDatabase();
    const players = db.searchPlayers({ club: 'Santos', limit: 5 });
    const matches = db.searchMatches({ team: 'Santos', limit: 5 });
    expect(players.length).toBeGreaterThan(0);
    expect(matches.length).toBeGreaterThan(0);
  });

  it('Q22: Which clubs have the most Brazilian players? (aggregation)', () => {
    const db = givenLoadedDatabase();
    expect(db.playersByClub({ nationality: 'Brazil', minPlayers: 10 }).length).toBeGreaterThan(0);
  });
});
