import { normalizeTeamName, teamsMatch } from './teamNormalizer.js';

describe('normalizeTeamName', () => {
  it('strips state suffix from team name', () => {
    expect(normalizeTeamName('Palmeiras-SP')).toBe('Palmeiras');
    expect(normalizeTeamName('Flamengo-RJ')).toBe('Flamengo');
    expect(normalizeTeamName('Sport-PE')).toBe('Sport');
    expect(normalizeTeamName('Portuguesa-SP')).toBe('Portuguesa');
  });

  it('returns name unchanged when no state suffix', () => {
    expect(normalizeTeamName('Flamengo')).toBe('Flamengo');
    expect(normalizeTeamName('Palmeiras')).toBe('Palmeiras');
  });

  it('handles known full-name aliases', () => {
    expect(normalizeTeamName('Sport Club Corinthians Paulista')).toBe('Corinthians');
    expect(normalizeTeamName('Athletico-PR')).toBe('Athletico');
    expect(normalizeTeamName('Atlético-MG')).toBe('Atlético');
  });

  it('trims whitespace', () => {
    expect(normalizeTeamName('  Flamengo  ')).toBe('Flamengo');
    expect(normalizeTeamName('  Palmeiras-SP  ')).toBe('Palmeiras');
  });
});

describe('teamsMatch', () => {
  it('matches teams with same normalized name', () => {
    expect(teamsMatch('Palmeiras-SP', 'Palmeiras')).toBe(true);
    expect(teamsMatch('Flamengo-RJ', 'Flamengo')).toBe(true);
    expect(teamsMatch('Sport-PE', 'Sport')).toBe(true);
  });

  it('matches case-insensitively', () => {
    expect(teamsMatch('flamengo', 'Flamengo')).toBe(true);
    expect(teamsMatch('PALMEIRAS', 'palmeiras')).toBe(true);
  });

  it('does not match different teams', () => {
    expect(teamsMatch('Flamengo', 'Fluminense')).toBe(false);
    expect(teamsMatch('Palmeiras', 'Santos')).toBe(false);
  });

  it('matches partial names (search-friendly)', () => {
    expect(teamsMatch('Flamengo-RJ', 'flamengo')).toBe(true);
    expect(teamsMatch('São Paulo', 'sao paulo')).toBe(true);
  });
});
