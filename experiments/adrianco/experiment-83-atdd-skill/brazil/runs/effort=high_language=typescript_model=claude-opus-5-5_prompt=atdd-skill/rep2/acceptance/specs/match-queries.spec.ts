/**
 * Executable specification: finding matches.
 *
 * Capability: a fan (via an LLM) can find matches by team, opponent, venue,
 * competition, season and date range, across every provided match dataset.
 */
import { describe, it } from 'vitest';
import { useSoccerDsl } from '../dsl/soccer-dsl.js';

describe('Finding matches', () => {
  const { given, matches } = useSoccerDsl();

  it('should list every meeting between two rivals, most recent first', async () => {
    await given.brasileiraoMatch({ home: 'Fluminense', away: 'Flamengo', score: '1-0', date: '2023-05-28' });
    await given.brasileiraoMatch({ home: 'Flamengo', away: 'Fluminense', score: '2-1', date: '2023-09-03' });
    await given.brasileiraoMatch({ home: 'Flamengo', away: 'Palmeiras', score: '3-0', date: '2023-07-01' });

    await matches.confirmMeetings({
      team: 'Flamengo',
      opponent: 'Fluminense',
      expected: ['2023-09-03: Flamengo 2-1 Fluminense', '2023-05-28: Fluminense 1-0 Flamengo'],
    });
  });

  it('should find the matches a team played in a season', async () => {
    await given.brasileiraoMatch({ home: 'Palmeiras', away: 'Santos', score: '2-0', date: '2023-04-16' });
    await given.copaDoBrasilMatch({ home: 'Botafogo', away: 'Palmeiras', score: '1-1', date: '2023-05-10' });
    await given.brasileiraoMatch({ home: 'Palmeiras', away: 'Santos', score: '0-0', date: '2022-04-16' });

    await matches.confirmFound({
      team: 'Palmeiras',
      season: 2023,
      expected: ['2023-05-10: Botafogo 1-1 Palmeiras', '2023-04-16: Palmeiras 2-0 Santos'],
    });
  });

  it('should find only the home matches of a team when asked', async () => {
    await given.brasileiraoMatch({ home: 'Corinthians', away: 'Santos', score: '1-0', date: '2022-05-01' });
    await given.brasileiraoMatch({ home: 'Santos', away: 'Corinthians', score: '1-0', date: '2022-09-01' });

    await matches.confirmFound({ team: 'Corinthians', venue: 'home', expected: ['2022-05-01: Corinthians 1-0 Santos'] });
  });

  it('should find matches within a date range', async () => {
    await given.brasileiraoMatch({ home: 'Grêmio', away: 'Internacional', date: '2019-03-01' });
    await given.brasileiraoMatch({ home: 'Internacional', away: 'Grêmio', score: '1-0', date: '2019-08-01' });
    await given.brasileiraoMatch({ home: 'Grêmio', away: 'Internacional', date: '2019-11-01' });

    await matches.confirmFound({
      team: 'Grêmio',
      from: '2019-07-01',
      to: '2019-09-30',
      expected: ['2019-08-01: Internacional 1-0 Grêmio'],
    });
  });

  it('should find matches by competition', async () => {
    await given.brasileiraoMatch({ home: 'Santos', away: 'Vasco da Gama', date: '2018-06-01' });
    await given.libertadoresMatch({ home: 'Santos', away: 'Boca Juniors', score: '0-0', date: '2018-08-28' });

    await matches.confirmFound({
      team: 'Santos',
      competition: 'Copa Libertadores',
      expected: ['2018-08-28: Santos 0-0 Boca Juniors'],
    });
  });

  it('should find the finals of a cup competition', async () => {
    await given.copaDoBrasilTie({ season: 2019, stage: 'final', home: 'Internacional', away: 'Athletico Paranaense', firstLeg: '0-1', secondLeg: '1-1', dates: ['2019-09-11', '2019-09-18'] });
    await given.copaDoBrasilTie({ season: 2019, stage: 'semifinals', home: 'Grêmio', away: 'Athletico Paranaense', firstLeg: '2-0', secondLeg: '0-2', dates: ['2019-08-14', '2019-09-04'] });

    await matches.confirmFound({
      competition: 'Copa do Brasil',
      stage: 'final',
      expected: ['2019-09-18: Athletico Paranaense 1-1 Internacional', '2019-09-11: Internacional 0-1 Athletico Paranaense'],
    });
  });

  it('should tell when two teams last met', async () => {
    await given.brasileiraoMatch({ home: 'Flamengo', away: 'Corinthians', score: '1-0', date: '2021-06-01' });
    await given.copaDoBrasilMatch({ home: 'Corinthians', away: 'Flamengo', score: '2-2', date: '2022-10-19' });
    await given.brasileiraoMatch({ home: 'Corinthians', away: 'Flamengo', score: '1-2', date: '2020-02-01' });

    await matches.confirmLastMeeting({ team: 'Flamengo', opponent: 'Corinthians', expected: '2022-10-19: Corinthians 2-2 Flamengo' });
  });

  it('should find the traditional derbies played in a season', async () => {
    await given.brasileiraoMatch({ home: 'Flamengo', away: 'Fluminense', score: '2-1', date: '2023-09-03' });
    await given.brasileiraoMatch({ home: 'Grêmio', away: 'Internacional', score: '0-0', date: '2023-06-18' });
    await given.brasileiraoMatch({ home: 'Flamengo', away: 'Bahia', score: '3-0', date: '2023-07-01' });

    await matches.confirmDerbies({
      season: 2023,
      expected: ['2023-09-03: Flamengo 2-1 Fluminense (Fla-Flu)', '2023-06-18: Grêmio 0-0 Internacional (Grenal)'],
    });
  });

  it('should present matches as a readable answer with a head-to-head summary', async () => {
    await given.brasileiraoMatch({ home: 'Flamengo', away: 'Fluminense', score: '2-1', date: '2023-09-03', round: 22 });

    await matches.confirmReadableAnswer({
      team: 'Flamengo',
      opponent: 'Fluminense',
      mentions: ['2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Round 22)', 'Flamengo 1 wins, Fluminense 0 wins, 0 draws'],
    });
  });
});
