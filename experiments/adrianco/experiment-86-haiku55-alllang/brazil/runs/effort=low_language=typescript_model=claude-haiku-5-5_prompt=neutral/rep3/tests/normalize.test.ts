/*
 * Context: Feature tests for team-name normalization. Covers the naming variations called
 * out in TASK.md ("Palmeiras-SP", "Sociedade Esportiva Palmeiras", accents) and the
 * state-qualified collisions (Atlético-MG vs Atlético-PR) that would otherwise merge clubs.
 * Related: src/normalize.ts.
 */
import { describe, expect, it } from 'vitest';
import { matchesText, foldText, stateOf, teamDisplayName, teamKey } from '../src/normalize.js';

describe('Feature: Team name normalization', () => {
  it('Scenario: state suffix is ignored when matching a team', () => {
    // Given a team written with a state suffix
    // When its key is computed
    // Then it matches the bare name
    expect(teamKey('Palmeiras-SP')).toBe(teamKey('Palmeiras'));
    expect(teamKey('Flamengo - RJ')).toBe('flamengo');
  });

  it('Scenario: full club names resolve to the short name', () => {
    expect(teamKey('Sociedade Esportiva Palmeiras')).toBe('palmeiras');
    expect(teamKey('Sport Club Corinthians Paulista')).toBe('corinthians');
    expect(teamKey('Vasco da Gama-RJ')).toBe(teamKey('Vasco'));
  });

  it('Scenario: accents and case do not affect matching', () => {
    expect(teamKey('São Paulo')).toBe(teamKey('Sao Paulo'));
    expect(teamKey('GRÊMIO')).toBe(teamKey('Gremio'));
    expect(foldText('  Avaí  ')).toBe('avai');
  });

  it('Scenario: clubs sharing a base name stay distinct by state', () => {
    // Given Atlético-MG and Atlético-PR appear in the data
    // Then they are different clubs
    expect(teamKey('Atlético-MG')).toBe('atletico mineiro');
    expect(teamKey('Atletico-PR')).toBe('athletico pr');
    expect(teamKey('Atletico-PR')).not.toBe(teamKey('Atletico-MG'));
    expect(teamKey('América RN')).not.toBe(teamKey('América-MG'));
  });

  it('Scenario: parenthetical and country suffixes are removed', () => {
    expect(teamKey('Nacional (URU)')).toBe('nacional');
    expect(teamKey('Barcelona-EQU')).toBe('barcelona');
    expect(teamKey('Boavista Sport Club (antigo Esporte Clube Barreira) - RJ')).toBe('boavista sport club');
  });

  it('Scenario: display names drop the suffix but keep accents', () => {
    expect(teamDisplayName('Palmeiras-SP')).toBe('Palmeiras');
    expect(teamDisplayName('Grêmio')).toBe('Grêmio');
  });

  it('Scenario: state codes are detected from suffixes', () => {
    expect(stateOf('Botafogo - PB')).toBe('PB');
    expect(stateOf('Sport RJ')).toBe('RJ');
    expect(stateOf('Libertad')).toBeNull();
  });

  it('Scenario: word-start matching for search text', () => {
    // Given a player named "Neymar Jr"
    expect(matchesText('Neymar Jr', 'neymar')).toBe(true);
    expect(matchesText('Neymar Jr', 'jr neymar')).toBe(true);
    // And "a" must not match the word "Série B"
    expect(matchesText('Brasileirão Série B', 'Série A')).toBe(false);
    expect(matchesText('Brasileirão Série A', 'Série A')).toBe(true);
  });
});
