/**
 * Executable specification: competition standings, champions, relegation and
 * knockout brackets, all calculated from match results.
 */
import { describe, it } from 'vitest';
import { useSoccerDsl } from '../dsl/soccer-dsl.js';

describe('Competition standings', () => {
  const { given, competitions } = useSoccerDsl();

  it('should name the champion of a league season', async () => {
    await given.brasileiraoSeasonFinishingInOrder({ season: 2019, teams: ['Flamengo', 'Santos', 'Palmeiras', 'Grêmio'] });

    await competitions.confirmChampion({ season: 2019, team: 'Flamengo', points: 18 });
  });

  it('should rank teams by points, then wins, then goal difference', async () => {
    await given.brasileiraoMatch({ home: 'Santos', away: 'Bahia', score: '1-0', season: 2018 });
    await given.brasileiraoMatch({ home: 'Palmeiras', away: 'Bahia', score: '5-0', season: 2018 });
    await given.brasileiraoMatch({ home: 'Santos', away: 'Palmeiras', score: '0-0', season: 2018 });

    await competitions.confirmStandings({ season: 2018, order: ['Palmeiras', 'Santos', 'Bahia'] });
  });

  it('should identify the teams relegated at the end of a season', async () => {
    await given.brasileiraoSeasonFinishingInOrder({
      season: 2020,
      teams: ['Flamengo', 'Internacional', 'Atlético Mineiro', 'São Paulo', 'Vasco da Gama', 'Goiás', 'Coritiba', 'Botafogo'],
    });

    await competitions.confirmRelegated({ season: 2020, teams: ['Vasco da Gama', 'Goiás', 'Coritiba', 'Botafogo'] });
  });

  it('should show the knockout bracket of a cup season', async () => {
    await given.libertadoresTie({ season: 2018, stage: 'final', home: 'Boca Juniors', away: 'River Plate', firstLeg: '2-2', secondLeg: '3-1', dates: ['2018-11-11', '2018-12-09'] });
    await given.libertadoresTie({ season: 2018, stage: 'semifinals', home: 'Palmeiras', away: 'Boca Juniors', firstLeg: '0-2', secondLeg: '2-2', dates: ['2018-10-24', '2018-10-31'] });
    await given.libertadoresMatch({ home: 'Palmeiras', away: 'Junior de Barranquilla', date: '2018-04-04' });

    await competitions.confirmBracket({
      competition: 'Copa Libertadores',
      season: 2018,
      stages: {
        semifinals: ['Palmeiras 0-2 Boca Juniors', 'Boca Juniors 2-2 Palmeiras'],
        final: ['Boca Juniors 2-2 River Plate', 'River Plate 3-1 Boca Juniors'],
      },
    });
  });
});
