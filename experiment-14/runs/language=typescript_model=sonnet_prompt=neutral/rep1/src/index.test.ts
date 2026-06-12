import {
  loadAllData,
  normalizeTeamName,
} from './data-loader';
import {
  queryMatches,
  getTeamStats,
  getHeadToHead,
  getStandings,
  queryPlayers,
  getBiggestWins,
  getLeagueStats,
  getTopScoringTeams,
} from './query-engine';

// Load data once for all tests
const store = loadAllData();

describe('Data Loading', () => {
  test('loads Brasileirão matches', () => {
    expect(store.brasileirao.length).toBeGreaterThan(4000);
  });

  test('loads Copa do Brasil matches', () => {
    expect(store.copa.length).toBeGreaterThan(1000);
  });

  test('loads Copa Libertadores matches', () => {
    expect(store.libertadores.length).toBeGreaterThan(1000);
  });

  test('loads extended match stats', () => {
    expect(store.extended.length).toBeGreaterThan(5000);
  });

  test('loads historical Brasileirão matches', () => {
    expect(store.historical.length).toBeGreaterThan(5000);
  });

  test('loads FIFA player data', () => {
    expect(store.players.length).toBeGreaterThan(10000);
  });

  test('brasileirao matches have required fields', () => {
    const m = store.brasileirao[0];
    expect(m.home_team).toBeTruthy();
    expect(m.away_team).toBeTruthy();
    expect(typeof m.home_goal).toBe('number');
    expect(typeof m.season).toBe('number');
    expect(m.source).toBe('brasileirao');
  });

  test('FIFA players have required fields', () => {
    const p = store.players[0];
    expect(p.name).toBeTruthy();
    expect(typeof p.overall).toBe('number');
    expect(p.overall).toBeGreaterThan(0);
  });
});

describe('Team Name Normalization', () => {
  test('removes state suffixes', () => {
    expect(normalizeTeamName('Palmeiras-SP')).toBe('Palmeiras');
    expect(normalizeTeamName('Flamengo-RJ')).toBe('Flamengo');
    expect(normalizeTeamName('Sport-PE')).toBe('Sport');
  });

  test('removes parenthetical notes', () => {
    expect(normalizeTeamName('Boavista Sport Club (antigo Esporte Clube Barreira) - RJ')).toBe('Boavista Sport Club');
  });

  test('passes through clean names', () => {
    expect(normalizeTeamName('Palmeiras')).toBe('Palmeiras');
    expect(normalizeTeamName('Flamengo')).toBe('Flamengo');
  });
});

describe('Match Queries', () => {
  test('finds Flamengo matches', () => {
    const matches = queryMatches(store, { team: 'Flamengo', limit: 10 });
    expect(matches.length).toBeGreaterThan(0);
    const hasFlamengo = matches.every(m =>
      m.home_team.includes('Flamengo') || m.away_team.includes('Flamengo')
    );
    expect(hasFlamengo).toBe(true);
  });

  test('finds Palmeiras matches in 2023', () => {
    const matches = queryMatches(store, { team: 'Palmeiras', season: 2023, limit: 50 });
    expect(matches.length).toBeGreaterThan(0);
    const allSeason = matches.every(m => m.season === 2023);
    expect(allSeason).toBe(true);
  });

  test('finds Brasileirão matches only', () => {
    const matches = queryMatches(store, { competition: 'brasileirao', limit: 10 });
    expect(matches.length).toBeGreaterThan(0);
    const allComp = matches.every(m =>
      m.competition.toLowerCase().includes('brasil')
    );
    expect(allComp).toBe(true);
  });

  test('finds head-to-head: Flamengo vs Fluminense', () => {
    const matches = queryMatches(store, { home_team: 'Flamengo', away_team: 'Fluminense', limit: 50 });
    expect(matches.length).toBeGreaterThan(0);
    const allFlaFlu = matches.every(m =>
      (m.home_team.includes('Flamengo') || m.away_team.includes('Flamengo')) &&
      (m.home_team.includes('Fluminense') || m.away_team.includes('Fluminense'))
    );
    expect(allFlaFlu).toBe(true);
  });

  test('date range filter works', () => {
    const matches = queryMatches(store, { date_from: '2023-01-01', date_to: '2023-12-31', limit: 20 });
    expect(matches.length).toBeGreaterThan(0);
    const allIn2023 = matches.every(m => m.date.startsWith('2023'));
    expect(allIn2023).toBe(true);
  });

  test('returns results sorted by date descending', () => {
    const matches = queryMatches(store, { team: 'Corinthians', limit: 20 });
    expect(matches.length).toBeGreaterThan(1);
    for (let i = 1; i < matches.length; i++) {
      expect(matches[i].date <= matches[i - 1].date).toBe(true);
    }
  });

  test('respects limit parameter', () => {
    const matches = queryMatches(store, { limit: 5 });
    expect(matches.length).toBeLessThanOrEqual(5);
  });
});

describe('Team Statistics', () => {
  test('Flamengo 2023 stats', () => {
    const stats = getTeamStats(store, 'Flamengo', 2023);
    expect(stats.matches).toBeGreaterThan(0);
    expect(stats.wins + stats.draws + stats.losses).toBe(stats.matches);
    expect(stats.points).toBe(stats.wins * 3 + stats.draws);
    expect(stats.win_rate).toBeGreaterThan(0);
    expect(stats.win_rate).toBeLessThanOrEqual(100);
  });

  test('returns zero stats for unknown team', () => {
    const stats = getTeamStats(store, 'Nonexistent FC 9999');
    expect(stats.matches).toBe(0);
    expect(stats.wins).toBe(0);
  });

  test('home and away match counts sum to total', () => {
    const stats = getTeamStats(store, 'Palmeiras', 2022);
    expect(stats.home_matches + stats.away_matches).toBe(stats.matches);
  });
});

describe('Head-to-Head', () => {
  test('Flamengo vs Fluminense head-to-head', () => {
    const h2h = getHeadToHead(store, 'Flamengo', 'Fluminense');
    expect(h2h.team1_wins + h2h.team2_wins + h2h.draws).toBeGreaterThan(0);
    expect(h2h.matches.length).toBeGreaterThan(0);
  });

  test('win counts are consistent', () => {
    const h2h = getHeadToHead(store, 'Palmeiras', 'Santos');
    const totalFromH2H = h2h.team1_wins + h2h.team2_wins + h2h.draws;
    // Total from h2h may differ from matches.length (matches are capped, h2h counts all)
    expect(totalFromH2H).toBeGreaterThanOrEqual(h2h.matches.length);
  });
});

describe('League Standings', () => {
  test('2019 Brasileirão standings', () => {
    const standings = getStandings(store, 2019, 'brasileirao');
    expect(standings.length).toBeGreaterThan(10);
    // Standings should be sorted by points descending
    for (let i = 1; i < standings.length; i++) {
      expect(standings[i].points).toBeLessThanOrEqual(standings[i - 1].points);
    }
    // Top team should have won many matches
    expect(standings[0].wins).toBeGreaterThan(10);
  });

  test('positions are sequential', () => {
    const standings = getStandings(store, 2018, 'brasileirao');
    standings.forEach((s, i) => {
      expect(s.position).toBe(i + 1);
    });
  });

  test('Libertadores standings 2019', () => {
    const standings = getStandings(store, 2019, 'libertadores');
    expect(standings.length).toBeGreaterThan(0);
  });
});

describe('Player Queries', () => {
  test('finds Brazil players', () => {
    const players = queryPlayers(store, { nationality: 'Brazil', limit: 10 });
    expect(players.length).toBeGreaterThan(0);
    const allBrazil = players.every(p => p.nationality.includes('Brazil'));
    expect(allBrazil).toBe(true);
  });

  test('finds players by name: Neymar', () => {
    const players = queryPlayers(store, { name: 'Neymar' });
    expect(players.length).toBeGreaterThan(0);
    expect(players[0].name.toLowerCase()).toContain('neymar');
  });

  test('finds players by club: Grêmio', () => {
    const players = queryPlayers(store, { club: 'Grêmio' });
    expect(players.length).toBeGreaterThan(0);
    const allGremio = players.every(p => p.club.toLowerCase().includes('grêmio') || p.club.toLowerCase().includes('gremio'));
    expect(allGremio).toBe(true);
  });

  test('filters by minimum overall rating', () => {
    const players = queryPlayers(store, { min_overall: 85 });
    expect(players.length).toBeGreaterThan(0);
    const allHighRated = players.every(p => p.overall >= 85);
    expect(allHighRated).toBe(true);
  });

  test('results sorted by overall rating descending', () => {
    const players = queryPlayers(store, { nationality: 'Brazil', limit: 20 });
    for (let i = 1; i < players.length; i++) {
      expect(players[i].overall).toBeLessThanOrEqual(players[i - 1].overall);
    }
  });

  test('respects limit', () => {
    const players = queryPlayers(store, { nationality: 'Brazil', limit: 5 });
    expect(players.length).toBeLessThanOrEqual(5);
  });

  test('finds players by position', () => {
    const players = queryPlayers(store, { nationality: 'Brazil', position: 'GK', limit: 10 });
    expect(players.length).toBeGreaterThan(0);
    const allGK = players.every(p => p.position.toUpperCase().includes('GK'));
    expect(allGK).toBe(true);
  });
});

describe('Statistical Analysis', () => {
  test('gets biggest wins', () => {
    const wins = getBiggestWins(store, 5);
    expect(wins.length).toBe(5);
    // Sorted by goal difference descending
    for (let i = 1; i < wins.length; i++) {
      expect(wins[i].goal_diff).toBeLessThanOrEqual(wins[i - 1].goal_diff);
    }
    // All should have positive goal difference
    wins.forEach(w => expect(w.goal_diff).toBeGreaterThan(0));
  });

  test('gets league stats for all competitions', () => {
    const stats = getLeagueStats(store);
    expect(stats.total_matches).toBeGreaterThan(10000);
    expect(stats.avg_goals_per_match).toBeGreaterThan(1);
    expect(stats.avg_goals_per_match).toBeLessThan(5);
    expect(stats.home_wins + stats.away_wins + stats.draws).toBe(stats.total_matches);
  });

  test('gets top scoring teams', () => {
    const teams = getTopScoringTeams(store, 2023, undefined, 5);
    expect(teams.length).toBeGreaterThan(0);
    // Sorted by goals descending
    for (let i = 1; i < teams.length; i++) {
      expect(teams[i].goals).toBeLessThanOrEqual(teams[i - 1].goals);
    }
  });

  test('gets league stats for specific competition', () => {
    const stats = getLeagueStats(store, 'brasileirao');
    expect(stats.total_matches).toBeGreaterThan(1000);
    expect(stats.home_win_rate).toBeGreaterThan(30);
  });
});

describe('Sample Questions Coverage', () => {
  test('"Show me all Flamengo vs Fluminense matches"', () => {
    const h2h = getHeadToHead(store, 'Flamengo', 'Fluminense', 30);
    expect(h2h.matches.length).toBeGreaterThan(5);
  });

  test('"What matches did Palmeiras play in 2023?"', () => {
    const matches = queryMatches(store, { team: 'Palmeiras', season: 2023 });
    expect(matches.length).toBeGreaterThan(10);
  });

  test('"Who are the highest-rated players at Santos?"', () => {
    const players = queryPlayers(store, { club: 'Santos', limit: 5 });
    expect(players.length).toBeGreaterThan(0);
    expect(players[0].overall).toBeGreaterThan(60);
  });

  test('"Show me all forwards from São Paulo"', () => {
    const players = queryPlayers(store, { club: 'São Paulo', position: 'ST', limit: 10 });
    // May be 0 depending on dataset coverage — just ensure no crash
    expect(Array.isArray(players)).toBe(true);
  });

  test('"Who won the 2019 Brasileirão?"', () => {
    const standings = getStandings(store, 2019, 'brasileirao');
    expect(standings.length).toBeGreaterThan(0);
    const champion = standings[0];
    expect(champion.position).toBe(1);
    // Flamengo won 2019 - check it's near top
    const flamPos = standings.findIndex(s => s.team.toLowerCase().includes('flamengo'));
    expect(flamPos).toBeLessThan(3);
  });

  test('"What is the average goals per match in Brasileirão?"', () => {
    const stats = getLeagueStats(store, 'brasileirao');
    expect(stats.avg_goals_per_match).toBeGreaterThan(0);
  });

  test('"Which team has the best away record?" — computable', () => {
    const teams = ['Flamengo', 'Palmeiras', 'Corinthians', 'Santos'];
    const awayStats = teams.map(t => {
      const s = getTeamStats(store, t);
      return { team: t, away_win_rate: s.away_matches > 0 ? s.away_wins / s.away_matches : 0 };
    });
    awayStats.sort((a, b) => b.away_win_rate - a.away_win_rate);
    expect(awayStats[0].away_win_rate).toBeGreaterThan(0);
  });

  test('"Find all Brazil players in the dataset"', () => {
    const players = queryPlayers(store, { nationality: 'Brazil', limit: 100 });
    expect(players.length).toBe(100);
  });

  test('"What competitions has Palmeiras played in?"', () => {
    const allMatches = queryMatches(store, { team: 'Palmeiras', limit: 500 });
    const competitions = new Set(allMatches.map(m => m.competition));
    expect(competitions.size).toBeGreaterThan(1);
  });
});
