/**
 * Executable specification: finding matches.
 *
 * Layer 1 of the four-layer model (test cases). Written in the language of
 * Brazilian football only — nothing here knows about MCP, CSV files or
 * processes. Each test creates the matches it needs (synthetic data), so
 * tests are isolated from one another and from the provided Kaggle data.
 */
import { spec } from './dsl/spec.js';

spec('should find every meeting between two teams, whichever was at home', async ({ given, matches }) => {
  given.match({ home: 'Flamengo', away: 'Fluminense', score: '2-1', date: '2023-09-03' });
  given.match({ home: 'Fluminense', away: 'Flamengo', score: '1-0', date: '2023-05-28' });
  given.match({ home: 'Flamengo', away: 'Vasco' });

  await matches.findBetween({ team: 'Flamengo', opponent: 'Fluminense' });

  matches.confirmFound(['2023-09-03 Flamengo 2-1 Fluminense', '2023-05-28 Fluminense 1-0 Flamengo']);
});

spec('should present each match with its date, score, competition and round', async ({ given, matches }) => {
  given.match({ home: 'Flamengo', away: 'Fluminense', score: '2-1', date: '2023-09-03', round: 22 });

  await matches.findBetween({ team: 'Flamengo', opponent: 'Fluminense' });

  matches.confirmPresentedAs('2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Round 22)');
});

spec("should find a team's matches in a season across every competition", async ({ given, matches }) => {
  given.match({ home: 'Palmeiras', away: 'Santos', competition: 'Brasileirão', date: '2023-06-10' });
  given.match({ home: 'Bolívar', away: 'Palmeiras', competition: 'Libertadores', date: '2023-04-05' });
  given.match({ home: 'Palmeiras', away: 'Tombense', competition: 'Copa do Brasil', date: '2023-04-26' });
  given.match({ home: 'Palmeiras', away: 'Santos', competition: 'Brasileirão', date: '2022-06-10' });

  await matches.findForTeam({ team: 'Palmeiras', season: 2023 });

  matches.confirmFound(['2023-06-10 Palmeiras 1-0 Santos', '2023-04-26 Palmeiras 1-0 Tombense', '2023-04-05 Bolívar 1-0 Palmeiras']);
});

spec('should find only the matches a team played at home', async ({ given, matches }) => {
  given.match({ home: 'Grêmio', away: 'Bahia', date: '2021-08-01' });
  given.match({ home: 'Bahia', away: 'Grêmio', date: '2021-11-01' });

  await matches.findForTeam({ team: 'Grêmio', venue: 'home' });

  matches.confirmFound(['2021-08-01 Grêmio 1-0 Bahia']);
});

spec('should find matches played within a date range', async ({ given, matches }) => {
  given.match({ home: 'Santos', away: 'Ceará', date: '2018-03-31' });
  given.match({ home: 'Santos', away: 'Vitória', date: '2018-04-15' });
  given.match({ home: 'Santos', away: 'Sport', date: '2018-05-02' });

  await matches.findForTeam({ team: 'Santos', from: '2018-04-01', to: '2018-04-30' });

  matches.confirmFound(['2018-04-15 Santos 1-0 Vitória']);
});

spec('should find matches from a single competition', async ({ given, matches }) => {
  given.match({ home: 'Cruzeiro', away: 'Atlético-MG', competition: 'Copa do Brasil', date: '2014-11-26' });
  given.match({ home: 'Cruzeiro', away: 'Atlético-MG', competition: 'Brasileirão', date: '2014-09-07' });

  await matches.findInCompetition({ competition: 'Copa do Brasil' });

  matches.confirmFound(['2014-11-26 Cruzeiro 1-0 Atlético-MG']);
});

spec('should report the most recent meeting between two teams', async ({ given, matches }) => {
  given.match({ home: 'Flamengo', away: 'Corinthians', score: '3-0', date: '2021-06-01' });
  given.match({ home: 'Corinthians', away: 'Flamengo', score: '1-1', date: '2022-10-12' });
  given.match({ home: 'Flamengo', away: 'Corinthians', score: '2-0', date: '2022-03-01' });

  await matches.findLastMeeting({ team: 'Flamengo', opponent: 'Corinthians' });

  matches.confirmFound(['2022-10-12 Corinthians 1-1 Flamengo']);
});

spec('should recognise a team whichever way a dataset writes its name', async ({ given, matches }) => {
  given.match({ home: 'Palmeiras-SP', away: 'Sao Paulo-SP', dataset: 'brasileirao', date: '2015-09-13' });
  given.match({ home: 'Palmeiras - SP', away: 'Grêmio - RS', dataset: 'cup', date: '2020-12-16' });
  given.match({ home: 'Palmeiras', away: 'Boca Juniors', dataset: 'libertadores', date: '2018-10-31' });
  given.match({ home: 'Palmeiras', away: 'Botafogo RJ', dataset: 'extended', date: '2023-11-01' });

  await matches.findForTeam({ team: 'Sociedade Esportiva Palmeiras' });

  matches.confirmFound([
    '2023-11-01 Palmeiras 1-0 Botafogo-RJ',
    '2020-12-16 Palmeiras 1-0 Grêmio',
    '2018-10-31 Palmeiras 1-0 Boca Juniors',
    '2015-09-13 Palmeiras 1-0 São Paulo',
  ]);
});

spec('should not confuse a foreign club with a Brazilian club of the same name', async ({ given, matches }) => {
  given.match({ home: 'River Plate', away: 'Boca Juniors', dataset: 'libertadores', date: '2018-12-09' });
  given.match({ home: 'River Plate - SE', away: 'Bahia - BA', dataset: 'cup', date: '2016-02-17' });

  await matches.findForTeam({ team: 'River Plate-SE' });

  matches.confirmFound(['2016-02-17 River Plate-SE 1-0 Bahia']);
});

spec('should list a match only once when several datasets record it', async ({ given, matches }) => {
  given.match({ home: 'Flamengo-RJ', away: 'Gremio-RS', score: '5-0', date: '2019-10-27', dataset: 'brasileirao' });
  given.match({ home: 'Flamengo', away: 'Grêmio', score: '5-0', date: '2019-10-27', dataset: 'historical' });
  given.match({ home: 'Flamengo', away: 'Gremio', score: '5-0', date: '2019-10-27', dataset: 'extended' });

  await matches.findBetween({ team: 'Flamengo', opponent: 'Grêmio' });

  matches.confirmFound(['2019-10-27 Flamengo 5-0 Grêmio']);
});

spec('should understand dates written in the Brazilian day/month/year style', async ({ given, matches }) => {
  given.match({ home: 'Guarani', away: 'Vasco', score: '4-2', date: '2003-03-29', dataset: 'historical' });

  await matches.findForTeam({ team: 'Guarani', from: '2003-03-01', to: '2003-03-31' });

  matches.confirmFound(['2003-03-29 Guarani 4-2 Vasco']);
});

spec('should report corners and shots where the data records them', async ({ given, matches }) => {
  given.match({ home: 'Sao Paulo', away: 'Flamengo', score: '1-1', dataset: 'extended', corners: '2-4', shots: '8-13' });

  await matches.findBetween({ team: 'São Paulo', opponent: 'Flamengo' });

  matches.confirmMatchStatistics({ corners: '2-4', shots: '8-13' });
});

spec('should find every Copa do Brasil final and who won it', async ({ given, matches }) => {
  given.match({ home: 'Grêmio', away: 'Palmeiras', score: '0-1', competition: 'Copa do Brasil', season: 2020, round: 8 });
  given.match({ home: 'Palmeiras', away: 'Grêmio', score: '2-0', competition: 'Copa do Brasil', season: 2020, round: 8 });
  given.match({ home: 'Palmeiras', away: 'América-MG', score: '2-0', competition: 'Copa do Brasil', season: 2020, round: 7 });
  given.match({ home: 'Athletico-PR', away: 'Internacional', score: '1-0', competition: 'Copa do Brasil', season: 2019, round: 8 });
  given.match({ home: 'Internacional', away: 'Athletico-PR', score: '1-2', competition: 'Copa do Brasil', season: 2019, round: 8 });

  await matches.findFinals({ competition: 'Copa do Brasil' });

  matches.confirmFinals(['2020: Palmeiras beat Grêmio 3-0 on aggregate', '2019: Athletico-PR beat Internacional 3-1 on aggregate']);
});

spec('should find the derbies played in a season', async ({ given, matches }) => {
  given.match({ home: 'Corinthians', away: 'Palmeiras', score: '2-0', date: '2023-07-09' });
  given.match({ home: 'Fluminense', away: 'Flamengo', score: '1-0', date: '2023-05-28' });
  given.match({ home: 'Flamengo', away: 'Santos', date: '2023-06-01' });
  given.match({ home: 'Grêmio', away: 'Internacional', date: '2022-06-01' });

  await matches.findDerbies({ season: 2023 });

  matches.confirmFound(['2023-07-09 Corinthians 2-0 Palmeiras', '2023-05-28 Fluminense 1-0 Flamengo']);
  matches.confirmDerbyNamed('Fla-Flu');
});

spec('should say so when it does not recognise a team', async ({ given, matches }) => {
  given.match({ home: 'Flamengo', away: 'Vasco' });

  await matches.findForTeam({ team: 'Atlantis United' });

  matches.confirmTeamNotRecognised('Atlantis United');
});
