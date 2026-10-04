/**
 * Executable specification: aggregate statistics calculated from match results.
 */
import { describe, it } from 'vitest';
import { useSoccerDsl } from '../dsl/soccer-dsl.js';

describe('Statistical analysis', () => {
  const { given, statistics } = useSoccerDsl();

  it('should calculate the average goals per match of a competition', async () => {
    await given.brasileiraoMatch({ home: 'Santos', away: 'Bahia', score: '3-1' });
    await given.brasileiraoMatch({ home: 'Bahia', away: 'Ceará', score: '0-0' });
    await given.brasileiraoMatch({ home: 'Ceará', away: 'Santos', score: '1-1' });
    await given.copaDoBrasilMatch({ home: 'Santos', away: 'Ceará', score: '9-0' });

    await statistics.confirmSummary({ competition: 'Brasileirão', matches: 3, averageGoals: 2.0 });
  });

  it('should calculate how often the home side wins', async () => {
    await given.brasileiraoMatch({ home: 'Santos', away: 'Bahia', score: '3-1' });
    await given.brasileiraoMatch({ home: 'Bahia', away: 'Ceará', score: '0-0' });
    await given.brasileiraoMatch({ home: 'Ceará', away: 'Santos', score: '2-1' });
    await given.brasileiraoMatch({ home: 'Santos', away: 'Ceará', score: '0-1' });

    await statistics.confirmSummary({ competition: 'Brasileirão', homeWinRate: 50.0, drawRate: 25.0, awayWinRate: 25.0 });
  });

  it('should list the biggest wins, largest margin first', async () => {
    await given.brasileiraoMatch({ home: 'Palmeiras', away: 'São Paulo', score: '6-0', date: '2015-09-13' });
    await given.libertadoresMatch({ home: 'Santos', away: 'Bolívar', score: '8-0', date: '2012-05-27' });
    await given.brasileiraoMatch({ home: 'Flamengo', away: 'Grêmio', score: '5-0', date: '2019-10-27' });
    await given.brasileiraoMatch({ home: 'Bahia', away: 'Vitória', score: '1-0', date: '2019-10-28' });

    await statistics.confirmBiggestWins({
      limit: 3,
      expected: [
        '2012-05-27: Santos 8-0 Bolívar (Copa Libertadores)',
        '2015-09-13: Palmeiras 6-0 São Paulo (Brasileirão Série A)',
        '2019-10-27: Flamengo 5-0 Grêmio (Brasileirão Série A)',
      ],
    });
  });

  it('should compare two seasons side by side', async () => {
    await given.brasileiraoMatch({ home: 'Santos', away: 'Bahia', score: '4-0', season: 2018 });
    await given.brasileiraoMatch({ home: 'Bahia', away: 'Santos', score: '1-1', season: 2019 });
    await given.brasileiraoMatch({ home: 'Santos', away: 'Bahia', score: '0-1', season: 2019 });

    await statistics.confirmSeasonComparison({
      competition: 'Brasileirão',
      seasons: { 2018: { matches: 1, averageGoals: 4.0 }, 2019: { matches: 2, averageGoals: 1.5 } },
    });
  });

  it('should report match statistics such as corners and shots where recorded', async () => {
    await given.leagueMatch({ division: 'Serie A', home: 'Fortaleza', away: 'Ceará', score: '1-0', corners: '7-3', shots: '15-6' });

    await statistics.confirmSummary({ competition: 'Brasileirão', averageCorners: 10.0 });
  });
});
