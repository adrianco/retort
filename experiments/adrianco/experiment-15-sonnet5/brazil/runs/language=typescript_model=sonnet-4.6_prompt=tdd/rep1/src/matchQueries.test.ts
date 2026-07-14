import { findMatches, getHeadToHead, getBiggestWins, getAverageGoals } from './matchQueries.js';
import type { BrazileiraoMatch, CupMatch, LibertadoresMatch, AllData } from './dataLoader.js';

const makeBrasileiraoMatch = (overrides: Partial<BrazileiraoMatch> = {}): BrazileiraoMatch => ({
  datetime: '2023-09-03 16:00:00',
  home_team: 'Flamengo-RJ',
  home_team_normalized: 'Flamengo',
  home_team_state: 'RJ',
  away_team: 'Fluminense-RJ',
  away_team_normalized: 'Fluminense',
  away_team_state: 'RJ',
  home_goal: 2,
  away_goal: 1,
  season: 2023,
  round: 22,
  competition: 'Brasileirao',
  ...overrides,
});

const makeCupMatch = (overrides: Partial<CupMatch> = {}): CupMatch => ({
  round: 'Final',
  datetime: '2023-10-01 16:00:00',
  home_team: 'Flamengo',
  home_team_normalized: 'Flamengo',
  away_team: 'São Paulo',
  away_team_normalized: 'São Paulo',
  home_goal: 1,
  away_goal: 0,
  season: 2023,
  competition: 'Copa do Brasil',
  ...overrides,
});

const makeLibertadoresMatch = (overrides: Partial<LibertadoresMatch> = {}): LibertadoresMatch => ({
  datetime: '2023-08-01 20:00:00',
  home_team: 'Flamengo',
  home_team_normalized: 'Flamengo',
  away_team: 'Olimpia',
  away_team_normalized: 'Olimpia',
  home_goal: 3,
  away_goal: 0,
  season: 2023,
  stage: 'group stage',
  competition: 'Libertadores',
  ...overrides,
});

const makeData = (overrides: Partial<AllData> = {}): AllData => ({
  brasileirao: [
    makeBrasileiraoMatch(),
    makeBrasileiraoMatch({
      home_team: 'Fluminense-RJ', home_team_normalized: 'Fluminense',
      away_team: 'Flamengo-RJ', away_team_normalized: 'Flamengo',
      home_goal: 1, away_goal: 0,
      datetime: '2023-05-28 16:00:00', season: 2023, round: 8,
    }),
    makeBrasileiraoMatch({
      home_team: 'Palmeiras-SP', home_team_normalized: 'Palmeiras',
      away_team: 'Santos-SP', away_team_normalized: 'Santos',
      home_goal: 3, away_goal: 0, season: 2022,
    }),
  ],
  copaBrasil: [makeCupMatch()],
  libertadores: [makeLibertadoresMatch()],
  brFootball: [],
  historical: [],
  fifaPlayers: [],
  ...overrides,
});

describe('findMatches', () => {
  const data = makeData();

  it('finds matches by team name in brasileirao', () => {
    const results = findMatches(data, { team: 'Flamengo' });
    expect(results.length).toBe(4); // 2 brasileirao + 1 copa + 1 lib
  });

  it('finds matches by specific competition', () => {
    const results = findMatches(data, { competition: 'Brasileirao' });
    expect(results.length).toBe(3);
  });

  it('finds matches by copa do brasil competition', () => {
    const results = findMatches(data, { competition: 'Copa do Brasil' });
    expect(results.length).toBe(1);
    expect(results[0].competition).toBe('Copa do Brasil');
  });

  it('finds matches by season', () => {
    const results = findMatches(data, { season: 2023 });
    expect(results.length).toBe(4); // 2 brasileirao + 1 copa + 1 lib
  });

  it('finds matches between two specific teams', () => {
    const results = findMatches(data, { team: 'Flamengo', opponent: 'Fluminense' });
    expect(results.length).toBe(2);
  });

  it('combines filters', () => {
    const results = findMatches(data, { team: 'Flamengo', season: 2023, competition: 'Brasileirao' });
    expect(results.length).toBe(2);
  });

  it('returns empty array when no matches found', () => {
    const results = findMatches(data, { team: 'Botafogo' });
    expect(results.length).toBe(0);
  });
});

describe('getHeadToHead', () => {
  const data = makeData();

  it('calculates head-to-head record between two teams', () => {
    const h2h = getHeadToHead(data, 'Flamengo', 'Fluminense');
    expect(h2h.total).toBe(2);
    expect(h2h.teamAWins).toBe(1); // Flamengo 2-1
    expect(h2h.teamBWins).toBe(1); // Fluminense 1-0
    expect(h2h.draws).toBe(0);
  });

  it('returns zeros when teams have not played', () => {
    const h2h = getHeadToHead(data, 'Botafogo', 'Cruzeiro');
    expect(h2h.total).toBe(0);
    expect(h2h.teamAWins).toBe(0);
    expect(h2h.teamBWins).toBe(0);
  });
});

describe('getBiggestWins', () => {
  const data = makeData({
    brasileirao: [
      makeBrasileiraoMatch({ home_goal: 6, away_goal: 0 }),
      makeBrasileiraoMatch({ home_goal: 3, away_goal: 0 }),
      makeBrasileiraoMatch({ home_goal: 1, away_goal: 1 }),
    ],
  });

  it('returns matches sorted by goal difference descending', () => {
    const wins = getBiggestWins(data, { competition: 'Brasileirao' }, 3);
    expect(wins[0].goalDiff).toBe(6);
    expect(wins[1].goalDiff).toBe(3);
    expect(wins[2].goalDiff).toBe(0);
  });

  it('limits results', () => {
    const wins = getBiggestWins(data, {}, 2);
    expect(wins.length).toBe(2);
  });
});

describe('getAverageGoals', () => {
  const data = makeData({
    brasileirao: [
      makeBrasileiraoMatch({ home_goal: 2, away_goal: 1 }),
      makeBrasileiraoMatch({ home_goal: 0, away_goal: 0 }),
      makeBrasileiraoMatch({ home_goal: 3, away_goal: 2 }),
    ],
    copaBrasil: [],
    libertadores: [],
    brFootball: [],
    historical: [],
    fifaPlayers: [],
  });

  it('calculates average goals per match', () => {
    const avg = getAverageGoals(data, { competition: 'Brasileirao' });
    expect(avg).toBeCloseTo(8 / 3, 2);
  });
});
