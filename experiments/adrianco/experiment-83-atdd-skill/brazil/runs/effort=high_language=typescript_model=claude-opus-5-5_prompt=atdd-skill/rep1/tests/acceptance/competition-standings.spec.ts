/**
 * Executable specification: competition standings, champions, relegation
 * and knockout brackets — all calculated from match results.
 *
 * Layer 1 (test cases) — domain language only.
 */
import { spec } from './dsl/spec.js';

spec("should calculate a season's final standings from its results", async ({ given, competitions }) => {
  given.match({ home: 'Flamengo', away: 'Santos', score: '3-1', season: 2019 });
  given.match({ home: 'Santos', away: 'Flamengo', score: '0-0', season: 2019 });
  given.match({ home: 'Palmeiras', away: 'Flamengo', score: '0-2', season: 2019 });
  given.match({ home: 'Santos', away: 'Palmeiras', score: '2-1', season: 2019 });

  await competitions.requestStandings({ competition: 'Brasileirão', season: 2019 });

  competitions.confirmStandings([
    '1. Flamengo - 7 pts (2W, 1D, 0L)',
    '2. Santos - 4 pts (1W, 1D, 1L)',
    '3. Palmeiras - 0 pts (0W, 0D, 2L)',
  ]);
});

spec('should name the champion as the team top of the table', async ({ given, competitions }) => {
  given.leagueSeason({ season: 2019, finishingOrder: ['Flamengo', 'Santos', 'Palmeiras', 'Grêmio'] });

  await competitions.requestStandings({ season: 2019 });

  competitions.confirmChampion('Flamengo');
});

spec('should separate teams level on points by wins, then goal difference', async ({ given, competitions }) => {
  given.match({ home: 'Bahia', away: 'Ceará', score: '1-0', season: 2021 });
  given.match({ home: 'Ceará', away: 'Bahia', score: '3-0', season: 2021 });
  given.match({ home: 'Sport', away: 'Bahia', score: '1-1', season: 2021 });
  given.match({ home: 'Ceará', away: 'Sport', score: '1-1', season: 2021 });

  await competitions.requestStandings({ season: 2021 });

  competitions.confirmStandings([
    '1. Ceará - 4 pts (1W, 1D, 1L)',
    '2. Bahia - 4 pts (1W, 1D, 1L)',
    '3. Sport - 2 pts (0W, 2D, 0L)',
  ]);
});

spec('should name the four teams relegated from the bottom of the table', async ({ given, competitions }) => {
  given.leagueSeason({
    season: 2020,
    finishingOrder: ['Flamengo', 'Internacional', 'Atlético-MG', 'São Paulo', 'Vasco', 'Goiás', 'Coritiba', 'Botafogo-RJ'],
  });

  await competitions.requestStandings({ season: 2020 });

  competitions.confirmRelegated(['Vasco', 'Goiás', 'Coritiba', 'Botafogo-RJ']);
});

spec('should leave matches from other competitions out of the league table', async ({ given, competitions }) => {
  given.match({ home: 'Grêmio', away: 'Internacional', score: '1-0', season: 2018, competition: 'Brasileirão' });
  given.match({ home: 'Internacional', away: 'Grêmio', score: '0-0', season: 2018, competition: 'Brasileirão' });
  given.match({ home: 'Internacional', away: 'Grêmio', score: '5-0', season: 2018, competition: 'Copa do Brasil' });

  await competitions.requestStandings({ competition: 'Brasileirão', season: 2018 });

  competitions.confirmChampion('Grêmio');
});

spec('should leave a stray one-off match out of the league table', async ({ given, competitions }) => {
  given.leagueSeason({ season: 2016, finishingOrder: ['Palmeiras', 'Santos', 'Flamengo', 'Atlético-MG'] });
  given.match({ home: 'Brasília', away: 'Taguatinga', score: '9-0', season: 2016, dataset: 'extended' });

  await competitions.requestStandings({ season: 2016 });

  competitions.confirmChampion('Palmeiras');
  competitions.confirmTeamsInTable(['Palmeiras', 'Santos', 'Flamengo', 'Atlético-MG']);
});

spec('should warn that a season is incomplete rather than crown a champion', async ({ given, competitions }) => {
  given.match({ home: 'Grêmio', away: 'Palmeiras', score: '1-0', season: 2023 });
  given.match({ home: 'Palmeiras', away: 'Grêmio', score: '1-1', season: 2023 });
  given.match({ home: 'Grêmio', away: 'Santos', score: '2-0', season: 2023 });
  given.match({ home: 'Santos', away: 'Grêmio', score: '0-0', season: 2023 });
  given.match({ home: 'Palmeiras', away: 'Santos', score: '3-0', season: 2023 });

  await competitions.requestStandings({ season: 2023 });

  competitions.confirmIncomplete({ matchesMissing: 1 });
});

spec('should show the knockout bracket of a Libertadores season', async ({ given, competitions }) => {
  given.match({ home: 'Boca Juniors', away: 'River Plate', score: '2-2', competition: 'Libertadores', season: 2018, stage: 'final' });
  given.match({ home: 'River Plate', away: 'Boca Juniors', score: '3-1', competition: 'Libertadores', season: 2018, stage: 'final' });
  given.match({ home: 'Palmeiras', away: 'Boca Juniors', score: '2-2', competition: 'Libertadores', season: 2018, stage: 'semifinals' });
  given.match({ home: 'Boca Juniors', away: 'Palmeiras', score: '2-0', competition: 'Libertadores', season: 2018, stage: 'semifinals' });
  given.match({ home: 'Grêmio', away: 'River Plate', score: '1-2', competition: 'Libertadores', season: 2018, stage: 'semifinals' });
  given.match({ home: 'River Plate', away: 'Grêmio', score: '0-1', competition: 'Libertadores', season: 2018, stage: 'semifinals' });

  await competitions.requestBracket({ competition: 'Libertadores', season: 2018 });

  competitions.confirmTie({ stage: 'semifinals', result: 'Boca Juniors beat Palmeiras 4-2 on aggregate' });
  competitions.confirmTie({ stage: 'final', result: 'River Plate beat Boca Juniors 5-3 on aggregate' });
});
