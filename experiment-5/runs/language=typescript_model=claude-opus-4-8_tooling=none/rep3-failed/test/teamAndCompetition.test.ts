/**
 * ============================================================================
 * Context Block — File: test/teamAndCompetition.test.ts
 * Project: Brazilian Soccer MCP Server
 * Purpose: BDD specs for capability areas #2 (Team Queries) and #4 (Competition
 *          Queries): team records, computed standings, and known historical
 *          champions used as ground-truth assertions.
 * ============================================================================
 */

import { describe, it, expect } from 'vitest';
import { givenLoadedDatabase } from './helpers.js';

describe('Feature: Team Queries', () => {
  it('Scenario: Get a team home record for a season', () => {
    // Given the match data is loaded
    const db = givenLoadedDatabase();
    // When I request Corinthians' 2022 Brasileirão home record
    const rec = db.teamStats('Corinthians', { season: 2022, competition: 'Brasileirão', venue: 'home' });
    // Then I receive wins, losses, draws, and goals
    expect(rec.matches).toBe(19); // 19 home games in a 20-team league
    expect(rec.wins + rec.draws + rec.losses).toBe(19);
    expect(rec.goalsFor).toBeGreaterThan(0);
    expect(rec.winRate).toBeGreaterThan(0);
    expect(rec.points).toBe(rec.wins * 3 + rec.draws);
  });

  it('Scenario: A full-season record splits into home and away', () => {
    const db = givenLoadedDatabase();
    const all = db.teamStats('Palmeiras', { season: 2019, competition: 'Brasileirão' });
    const home = db.teamStats('Palmeiras', { season: 2019, competition: 'Brasileirão', venue: 'home' });
    const away = db.teamStats('Palmeiras', { season: 2019, competition: 'Brasileirão', venue: 'away' });
    expect(home.matches + away.matches).toBe(all.matches);
    expect(all.matches).toBe(38);
  });
});

describe('Feature: Competition Queries (standings)', () => {
  it('Scenario: A computed standings table is well-formed', () => {
    const db = givenLoadedDatabase();
    const table = db.standings('Brasileirão', 2019);
    expect(table.length).toBe(20);
    // positions are 1..N
    table.forEach((r, i) => expect(r.position).toBe(i + 1));
    // ordered by points descending
    for (let i = 1; i < table.length; i++) {
      expect(table[i - 1].points).toBeGreaterThanOrEqual(table[i].points);
    }
    // every team played a full double round-robin (38 games)
    for (const r of table) expect(r.matches).toBe(38);
  });

  it.each([
    [2019, 'Flamengo'],
    [2018, 'Palmeiras'],
    [2017, 'Corinthians'],
    [2016, 'Palmeiras'],
    [2014, 'Cruzeiro'],
    [2009, 'Flamengo'],
  ])('Scenario: %i Brasileirão champion is %s', (season, champion) => {
    const db = givenLoadedDatabase();
    const table = db.standings('Brasileirão', season as number);
    expect(table[0].team.toLowerCase()).toContain((champion as string).toLowerCase());
  });

  it('Scenario: List the available competitions', () => {
    const db = givenLoadedDatabase();
    const comps = db.listCompetitions().map((c) => c.name);
    expect(comps).toContain('Brasileirão');
    expect(comps).toContain('Copa do Brasil');
    expect(comps).toContain('Copa Libertadores');
  });
});
