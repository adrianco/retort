/**
 * Executable specification: aggregated statistics across matches, seasons
 * and datasets.
 *
 * Layer 1 (test cases) — domain language only.
 */
import { spec } from './dsl/spec.js';

spec('should calculate the average goals per match and how often each side wins', async ({ given, statistics }) => {
  given.match({ home: 'Flamengo', away: 'Vasco', score: '2-1' });
  given.match({ home: 'Santos', away: 'Ceará', score: '0-0' });
  given.match({ home: 'Bahia', away: 'Sport', score: '1-3' });
  given.match({ home: 'Grêmio', away: 'Goiás', score: '3-0' });

  await statistics.summariseCompetition({ competition: 'Brasileirão' });

  statistics.confirmSummary({ matches: 4, averageGoals: 2.5, homeWinRate: '50.0%', drawRate: '25.0%', awayWinRate: '25.0%' });
});

spec('should find the team with the best home record', async ({ given, statistics }) => {
  given.match({ home: 'Palmeiras', away: 'Santos', score: '2-0' });
  given.match({ home: 'Palmeiras', away: 'Bahia', score: '1-0' });
  given.match({ home: 'Santos', away: 'Palmeiras', score: '1-0' });
  given.match({ home: 'Santos', away: 'Bahia', score: '1-1' });
  given.match({ home: 'Bahia', away: 'Palmeiras', score: '2-2' });

  await statistics.rankTeams({ by: 'home record' });

  statistics.confirmBest({ team: 'Palmeiras', winRate: '100.0%' });
});

spec('should find the team with the best away record', async ({ given, statistics }) => {
  given.match({ home: 'Palmeiras', away: 'Santos', score: '2-0' });
  given.match({ home: 'Bahia', away: 'Santos', score: '1-1' });
  given.match({ home: 'Santos', away: 'Palmeiras', score: '1-2' });
  given.match({ home: 'Bahia', away: 'Palmeiras', score: '0-0' });

  await statistics.rankTeams({ by: 'away record' });

  statistics.confirmBest({ team: 'Palmeiras', winRate: '50.0%' });
});

spec('should list the biggest wins, largest margin first', async ({ given, statistics }) => {
  given.match({ home: 'Santos', away: 'Bolívar', score: '8-0', competition: 'Libertadores', date: '2012-05-27' });
  given.match({ home: 'Palmeiras', away: 'São Paulo', score: '6-0', date: '2015-09-13' });
  given.match({ home: 'Flamengo', away: 'Grêmio', score: '5-0', date: '2019-10-27' });
  given.match({ home: 'Vasco', away: 'Botafogo-RJ', score: '2-1', date: '2019-11-03' });

  await statistics.findBiggestWins({ limit: 3 });

  statistics.confirmBiggestWins([
    '2012-05-27 Santos 8-0 Bolívar',
    '2015-09-13 Palmeiras 6-0 São Paulo',
    '2019-10-27 Flamengo 5-0 Grêmio',
  ]);
});

spec('should compare two seasons side by side', async ({ given, statistics }) => {
  given.leagueSeason({ season: 2018, finishingOrder: ['Palmeiras', 'Santos'] });
  given.leagueSeason({ season: 2019, finishingOrder: ['Flamengo', 'Santos', 'Palmeiras'] });
  given.match({ home: 'Flamengo', away: 'Santos', score: '4-0', season: 2019, competition: 'Copa do Brasil' });

  await statistics.compareSeasons({ seasons: [2018, 2019] });

  statistics.confirmSeason({ season: 2018, matches: 2, averageGoals: 2, champion: 'Palmeiras' });
  statistics.confirmSeason({ season: 2019, matches: 6, averageGoals: 2, champion: 'Flamengo' });
});

spec("should profile a team from both its results and its squad", async ({ given, statistics }) => {
  given.match({ home: 'Grêmio-RS', away: 'Internacional-RS', score: '2-1', competition: 'Brasileirão' });
  given.match({ home: 'Grêmio', away: 'River Plate', score: '1-0', competition: 'Libertadores' });
  given.player({ name: 'Luan', club: 'Grêmio', overall: 80 });
  given.player({ name: 'Geromel', club: 'Grêmio', overall: 82 });

  await statistics.profileTeam({ team: 'Gremio' });

  statistics.confirmProfile({ team: 'Grêmio', played: 2, won: 2, squadSize: 2, bestPlayer: 'Geromel' });
});
