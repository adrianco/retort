import { getTeamRecord, getStandings, getTopScoringTeams } from './teamQueries.js';
import type { AllData, BrazileiraoMatch } from './dataLoader.js';

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
  round: 1,
  competition: 'Brasileirao',
  ...overrides,
});

const makeData = (brasileirao: BrazileiraoMatch[]): AllData => ({
  brasileirao,
  copaBrasil: [],
  libertadores: [],
  brFootball: [],
  historical: [],
  fifaPlayers: [],
});

describe('getTeamRecord', () => {
  const data = makeData([
    makeBrasileiraoMatch({ home_goal: 2, away_goal: 1 }),    // Flamengo wins
    makeBrasileiraoMatch({ home_team: 'Fluminense-RJ', home_team_normalized: 'Fluminense', away_team: 'Flamengo-RJ', away_team_normalized: 'Flamengo', home_goal: 1, away_goal: 0 }), // Flamengo loses
    makeBrasileiraoMatch({ home_goal: 1, away_goal: 1,
      away_team: 'Flamengo-RJ', away_team_normalized: 'Flamengo',
      home_team: 'Palmeiras-SP', home_team_normalized: 'Palmeiras' }), // Flamengo draws
    makeBrasileiraoMatch({ home_goal: 3, away_goal: 0, season: 2022 }), // Flamengo 2022 win
  ]);

  it('calculates overall wins losses draws', () => {
    const record = getTeamRecord(data, 'Flamengo', {});
    expect(record.wins).toBe(2); // match1(2023) + match4(2022)
    expect(record.losses).toBe(1);
    expect(record.draws).toBe(1);
    expect(record.played).toBe(4);
  });

  it('filters by season', () => {
    const record = getTeamRecord(data, 'Flamengo', { season: 2023 });
    expect(record.played).toBe(3);
    expect(record.wins).toBe(1);
  });

  it('filters by home only', () => {
    const record = getTeamRecord(data, 'Flamengo', { homeOnly: true });
    expect(record.played).toBe(2); // 2 home matches in 2023+2022
  });

  it('calculates goals scored and conceded', () => {
    const record = getTeamRecord(data, 'Flamengo', {});
    expect(record.goalsFor).toBe(6);  // 2+0+1+3
    expect(record.goalsAgainst).toBe(3); // 1+1+1+0
  });
});

describe('getStandings', () => {
  const data = makeData([
    // Flamengo wins 3-0 at home (defaults already have Flamengo-RJ vs Fluminense-RJ)
    makeBrasileiraoMatch({ home_goal: 3, away_goal: 0, round: 1 }),
    // Palmeiras wins 2-1 at home
    makeBrasileiraoMatch({ home_team: 'Palmeiras-SP', home_team_normalized: 'Palmeiras', away_team: 'Santos-SP', away_team_normalized: 'Santos', home_goal: 2, away_goal: 1, round: 1 }),
    // Flamengo wins again
    makeBrasileiraoMatch({ home_team: 'Flamengo-RJ', home_team_normalized: 'Flamengo', away_team: 'Santos-SP', away_team_normalized: 'Santos', home_goal: 1, away_goal: 0, round: 2 }),
  ]);

  it('returns teams sorted by points descending', () => {
    const standings = getStandings(data, { season: 2023, competition: 'Brasileirao' });
    expect(standings[0].team).toBe('Flamengo');
    expect(standings[0].points).toBe(6);
    expect(standings[1].points).toBe(3);
  });

  it('calculates win/draw/loss correctly', () => {
    const standings = getStandings(data, { season: 2023, competition: 'Brasileirao' });
    const flamengo = standings.find(s => s.team === 'Flamengo');
    expect(flamengo?.wins).toBe(2);
    expect(flamengo?.draws).toBe(0);
    expect(flamengo?.losses).toBe(0);
  });

  it('includes all teams that participated', () => {
    const standings = getStandings(data, { season: 2023, competition: 'Brasileirao' });
    const teams = standings.map(s => s.team);
    expect(teams).toContain('Flamengo');
    expect(teams).toContain('Fluminense');
    expect(teams).toContain('Palmeiras');
    expect(teams).toContain('Santos');
  });
});

describe('getTopScoringTeams', () => {
  const data = makeData([
    makeBrasileiraoMatch({ home_goal: 5, away_goal: 0 }),  // Flamengo-RJ scores 5
    makeBrasileiraoMatch({ home_team: 'Palmeiras-SP', home_team_normalized: 'Palmeiras', home_goal: 2, away_goal: 1 }),
    makeBrasileiraoMatch({ home_team: 'Flamengo-RJ', home_team_normalized: 'Flamengo', away_team: 'Palmeiras-SP', away_team_normalized: 'Palmeiras', home_goal: 3, away_goal: 1 }),
  ]);

  it('ranks teams by total goals scored', () => {
    const top = getTopScoringTeams(data, { season: 2023, competition: 'Brasileirao' }, 5);
    expect(top[0].team).toBe('Flamengo');
    expect(top[0].goals).toBe(8); // 5+3
  });

  it('limits result count', () => {
    const top = getTopScoringTeams(data, {}, 1);
    expect(top.length).toBe(1);
  });
});
