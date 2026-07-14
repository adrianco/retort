/**
 * ============================================================================
 * Context Block — File: test/normalize.test.ts
 * Project: Brazilian Soccer MCP Server
 * Purpose: Unit-level BDD specs for the name/date normalization layer that the
 *          whole knowledge graph depends on. Verifies team-name variants
 *          collapse correctly WITHOUT over-merging distinct same-base clubs,
 *          and that the several date formats parse to ISO.
 * ============================================================================
 */

import { describe, it, expect } from 'vitest';
import {
  teamKey,
  teamBaseKey,
  teamKeyMatches,
  displayTeamName,
  parseDate,
  parseGoals,
} from '../src/normalize.js';

describe('Feature: Team-name normalization', () => {
  it('Scenario: accent and suffix variants of one club collapse together', () => {
    // Given several spellings of the same club
    // When normalized to keys
    // Then the base names agree
    expect(teamBaseKey(teamKey('Palmeiras-SP'))).toBe('palmeiras');
    expect(teamBaseKey(teamKey('Palmeiras'))).toBe('palmeiras');
    expect(teamKey('São Paulo')).toBe('sao paulo');
    expect(teamKey('Sao Paulo')).toBe('sao paulo');
    expect(teamKey('Grêmio')).toBe('gremio');
  });

  it('Scenario: clubs sharing a base name but different states stay distinct', () => {
    // Given two different clubs that share the "Atlético" base
    // Then their full keys differ
    expect(teamKey('Atlético-MG')).toBe('atletico mg');
    expect(teamKey('Atletico-PR')).toBe('atletico pr');
    expect(teamKey('Atlético-MG')).not.toBe(teamKey('Atletico-PR'));
  });

  it('Scenario: a stateless query matches any state, a stateful query is exact', () => {
    // "Atletico" (no state) is ambiguous and matches both
    expect(teamKeyMatches('atletico mg', teamKey('Atletico'))).toBe(true);
    expect(teamKeyMatches('atletico pr', teamKey('Atletico'))).toBe(true);
    // "Palmeiras" matches "Palmeiras-SP"
    expect(teamKeyMatches('palmeiras sp', teamKey('Palmeiras'))).toBe(true);
    // but a specific state does not cross-match
    expect(teamKeyMatches('atletico pr', teamKey('Atletico-MG'))).toBe(false);
  });

  it('Scenario: parenthetical country codes are dropped', () => {
    expect(teamKey('Nacional (URU)')).toBe('nacional');
  });

  it('Scenario: display names keep the state suffix for disambiguation', () => {
    expect(displayTeamName('Atlético - MG')).toBe('Atlético-MG');
    expect(displayTeamName('Palmeiras-SP')).toBe('Palmeiras-SP');
  });
});

describe('Feature: Date and goal parsing', () => {
  it('Scenario: multiple date formats parse to ISO YYYY-MM-DD', () => {
    expect(parseDate('2023-09-24')).toBe('2023-09-24');
    expect(parseDate('2012-05-19 18:30:00')).toBe('2012-05-19');
    expect(parseDate('29/03/2003')).toBe('2003-03-29');
    expect(parseDate('')).toBeNull();
  });

  it('Scenario: goals encoded as floats or quoted strings parse to integers', () => {
    expect(parseGoals('1.0')).toBe(1);
    expect(parseGoals('"2"')).toBe(2);
    expect(parseGoals('')).toBeNull();
    expect(parseGoals('nan')).toBeNull();
  });
});
