import { searchPlayers, getTopRatedPlayers, getPlayersByClub } from './playerQueries.js';
import type { FifaPlayer, AllData } from './dataLoader.js';

const makePlayer = (overrides: Partial<FifaPlayer> = {}): FifaPlayer => ({
  id: '1',
  name: 'Neymar Jr',
  age: 26,
  nationality: 'Brazil',
  overall: 92,
  potential: 93,
  club: 'Paris Saint-Germain',
  position: 'LW',
  jersey_number: '10',
  height: "5'9",
  weight: '150lbs',
  ...overrides,
});

const makeData = (players: FifaPlayer[]): AllData => ({
  brasileirao: [],
  copaBrasil: [],
  libertadores: [],
  brFootball: [],
  historical: [],
  fifaPlayers: players,
});

const samplePlayers = [
  makePlayer({ id: '1', name: 'Neymar Jr', nationality: 'Brazil', overall: 92, club: 'Paris Saint-Germain', position: 'LW' }),
  makePlayer({ id: '2', name: 'Alisson', nationality: 'Brazil', overall: 89, club: 'Liverpool', position: 'GK' }),
  makePlayer({ id: '3', name: 'Casemiro', nationality: 'Brazil', overall: 89, club: 'Real Madrid', position: 'CDM' }),
  makePlayer({ id: '4', name: 'Gabriel Barbosa', nationality: 'Brazil', overall: 80, club: 'Flamengo', position: 'ST' }),
  makePlayer({ id: '5', name: 'L. Messi', nationality: 'Argentina', overall: 94, club: 'FC Barcelona', position: 'RF' }),
  makePlayer({ id: '6', name: 'Rodrigo', nationality: 'Spain', overall: 78, club: 'Real Madrid', position: 'ST' }),
];

describe('searchPlayers', () => {
  const data = makeData(samplePlayers);

  it('searches by name (case-insensitive)', () => {
    const results = searchPlayers(data, { name: 'neymar' });
    expect(results.length).toBe(1);
    expect(results[0].name).toBe('Neymar Jr');
  });

  it('finds player by partial name', () => {
    const results = searchPlayers(data, { name: 'gabriel' });
    expect(results.length).toBe(1);
    expect(results[0].name).toBe('Gabriel Barbosa');
  });

  it('filters by nationality', () => {
    const results = searchPlayers(data, { nationality: 'Brazil' });
    expect(results.length).toBe(4);
  });

  it('filters by club (partial match)', () => {
    const results = searchPlayers(data, { club: 'Real Madrid' });
    expect(results.length).toBe(2);
  });

  it('filters by position', () => {
    const results = searchPlayers(data, { position: 'ST' });
    expect(results.length).toBe(2);
  });

  it('combines name and nationality filters', () => {
    const results = searchPlayers(data, { name: 'alisson', nationality: 'Brazil' });
    expect(results.length).toBe(1);
    expect(results[0].name).toBe('Alisson');
  });

  it('returns empty array when no match', () => {
    const results = searchPlayers(data, { name: 'Ronaldinho' });
    expect(results.length).toBe(0);
  });
});

describe('getTopRatedPlayers', () => {
  const data = makeData(samplePlayers);

  it('returns players sorted by overall rating descending', () => {
    const top = getTopRatedPlayers(data, {}, 3);
    expect(top[0].overall).toBe(94);
    expect(top[1].overall).toBe(92);
    expect(top[2].overall).toBe(89);
  });

  it('filters by nationality before ranking', () => {
    const top = getTopRatedPlayers(data, { nationality: 'Brazil' }, 10);
    expect(top[0].name).toBe('Neymar Jr');
    expect(top.every(p => p.nationality === 'Brazil')).toBe(true);
  });

  it('limits result count', () => {
    const top = getTopRatedPlayers(data, {}, 2);
    expect(top.length).toBe(2);
  });
});

describe('getPlayersByClub', () => {
  const data = makeData(samplePlayers);

  it('groups players by club', () => {
    const clubs = getPlayersByClub(data, { nationality: 'Brazil' });
    expect(clubs['Paris Saint-Germain']).toBeDefined();
    expect(clubs['Paris Saint-Germain'].count).toBe(1);
    expect(clubs['Flamengo'].count).toBe(1);
  });

  it('calculates average rating per club', () => {
    const clubs = getPlayersByClub(data, { nationality: 'Brazil' });
    expect(clubs['Paris Saint-Germain'].avgRating).toBeCloseTo(92, 1);
    expect(clubs['Flamengo'].avgRating).toBeCloseTo(80, 1);
  });

  it('returns all clubs without filter', () => {
    const clubs = getPlayersByClub(data, {});
    const clubNames = Object.keys(clubs);
    expect(clubNames).toContain('Paris Saint-Germain');
    expect(clubNames).toContain('Real Madrid');
    expect(clubNames).toContain('FC Barcelona');
  });
});
