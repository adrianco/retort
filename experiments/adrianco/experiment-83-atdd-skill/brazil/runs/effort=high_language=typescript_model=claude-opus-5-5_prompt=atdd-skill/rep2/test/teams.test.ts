import { describe, expect, it } from 'vitest';
import { identifyTeam, TeamRegistry } from '../src/teams.js';

describe('identifyTeam', () => {
  it.each([
    ['Palmeiras-SP', 'Palmeiras'],
    ['Palmeiras - SP', 'Palmeiras'],
    ['Sociedade Esportiva Palmeiras', 'Palmeiras'],
    ['Sao Paulo-SP', 'São Paulo'],
    ['Sao Paulo', 'São Paulo'],
    ['São Paulo - SP', 'São Paulo'],
    ['Sport Club Corinthians Paulista', 'Corinthians'],
    ['Atletico-MG', 'Atlético Mineiro'],
    ['Atlético - MG', 'Atlético Mineiro'],
    ['Atletico Mineiro', 'Atlético Mineiro'],
    ['Atletico-PR', 'Athletico Paranaense'],
    ['Athletico-PR', 'Athletico Paranaense'],
    ['Athletico', 'Athletico Paranaense'],
    ['Atlético Paranaense', 'Athletico Paranaense'],
    ['Atletico-GO', 'Atlético Goianiense'],
    ['America-MG', 'América Mineiro'],
    ['América FC (Minas Gerais)', 'América Mineiro'],
    ['America RN', 'América de Natal'],
    ['Vasco', 'Vasco da Gama'],
    ['Vasco Da Gama RJ', 'Vasco da Gama'],
    ['Gremio RS', 'Grêmio'],
    ['EC Bahia', 'Bahia'],
    ['Sport Recife', 'Sport'],
    ['Sport Club do Recife', 'Sport'],
    ['Ceará Sporting Club', 'Ceará'],
    ['Csa-AL', 'CSA'],
    ['C.s.a. - AL', 'CSA'],
    ['Bragantino', 'Red Bull Bragantino'],
  ])('recognises "%s" as %s', (raw, name) => {
    expect(identifyTeam(raw)).toMatchObject({ name, canonical: true });
  });

  it.each([
    ['Botafogo - PB', 'Botafogo-RJ'],
    ['Flamengo - PI', 'Flamengo'],
    ['Santos AP', 'Santos'],
    ['Santos Laguna', 'Santos'],
    ['Nacional (URU)', 'Nacional (PAR)'],
    ['River Plate-URU', 'River Plate'],
    ['Atletico - ES', 'Atletico-MG'],
  ])('keeps "%s" apart from "%s"', (a, b) => {
    expect(identifyTeam(a).key).not.toBe(identifyTeam(b).key);
  });

  it.each([
    ['Nacional (URU)', 'Nacional-URU'],
    ['Guaraní (PAR)', 'Guaraní-PAR'],
    ['Ceilândia - DF', 'Ceilandia'],
    ['Independiente del Valle', 'Independiente Del Valle'],
  ])('treats "%s" and "%s" as the same team', (a, b) => {
    expect(identifyTeam(a).key).toBe(identifyTeam(b).key);
  });
});

describe('TeamRegistry', () => {
  it('prefers the accented spelling of a team it does not know', () => {
    const registry = new TeamRegistry();
    const key = registry.register('Ceilandia');
    registry.register('Ceilândia - DF');
    expect(registry.name(key)).toBe('Ceilândia');
  });

  it('resolves partial names to the team that appears most', () => {
    const registry = new TeamRegistry();
    registry.register('Athletico-PR');
    registry.register('Athletico-PR');
    registry.register('Atlético Cearense - CE');
    expect(registry.name(registry.resolve('paranaense')!)).toBe('Athletico Paranaense');
  });

  it('returns null for a team it has never seen', () => {
    expect(new TeamRegistry().resolve('Real Madrid')).toBeNull();
  });
});
