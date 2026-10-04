/**
 * Executable specification: team records, head-to-head comparisons and
 * consistent recognition of a team whatever name a dataset gives it.
 */
import { describe, it } from 'vitest';
import { useSoccerDsl } from '../dsl/soccer-dsl.js';

describe('Team records', () => {
  const { given, teams } = useSoccerDsl();

  it("should report a team's home record for a season", async () => {
    await given.brasileiraoMatch({ home: 'Corinthians', away: 'Santos', score: '2-0', season: 2022 });
    await given.brasileiraoMatch({ home: 'Corinthians', away: 'Palmeiras', score: '1-1', season: 2022 });
    await given.brasileiraoMatch({ home: 'Corinthians', away: 'Grêmio', score: '0-1', season: 2022 });
    await given.brasileiraoMatch({ home: 'Santos', away: 'Corinthians', score: '3-0', season: 2022 });

    await teams.confirmRecord({
      team: 'Corinthians', season: 2022, venue: 'home',
      played: 3, wins: 1, draws: 1, losses: 1, goalsFor: 3, goalsAgainst: 2, winRate: 33.3,
    });
  });

  it('should compare two teams head-to-head', async () => {
    await given.brasileiraoMatch({ home: 'Palmeiras', away: 'Santos', score: '3-1' });
    await given.brasileiraoMatch({ home: 'Santos', away: 'Palmeiras', score: '2-2' });
    await given.copaDoBrasilMatch({ home: 'Santos', away: 'Palmeiras', score: '1-0' });
    await given.libertadoresMatch({ home: 'Palmeiras', away: 'Santos', score: '1-0' });

    await teams.confirmHeadToHead({ team: 'Palmeiras', opponent: 'Santos', wins: 2, draws: 1, losses: 1, goalsFor: 6, goalsAgainst: 4 });
  });

  it('should list the competitions a team has played in', async () => {
    await given.brasileiraoMatch({ home: 'Palmeiras', away: 'Santos' });
    await given.copaDoBrasilMatch({ home: 'Palmeiras', away: 'Bahia' });
    await given.libertadoresMatch({ home: 'Boca Juniors', away: 'Palmeiras' });
    await given.brasileiraoMatch({ home: 'Flamengo', away: 'Bahia' });
    await given.leagueMatch({ division: 'Serie B', home: 'Vasco da Gama', away: 'Bahia' });

    await teams.confirmCompetitions({ team: 'Palmeiras', competitions: ['Brasileirão Série A', 'Copa do Brasil', 'Copa Libertadores'] });
  });

  it('should find the team that scored the most goals in a season', async () => {
    await given.brasileiraoMatch({ home: 'Palmeiras', away: 'Santos', score: '4-0', season: 2023 });
    await given.brasileiraoMatch({ home: 'Botafogo', away: 'Palmeiras', score: '3-2', season: 2023 });
    await given.brasileiraoMatch({ home: 'Santos', away: 'Botafogo', score: '1-0', season: 2023 });

    await teams.confirmTopRanked({ measure: 'goals scored', season: 2023, team: 'Palmeiras', value: 6 });
  });

  it('should find the team with the best away record', async () => {
    await given.brasileiraoMatch({ home: 'Santos', away: 'Grêmio', score: '0-1' });
    await given.brasileiraoMatch({ home: 'Bahia', away: 'Grêmio', score: '0-2' });
    await given.brasileiraoMatch({ home: 'Grêmio', away: 'Santos', score: '0-3' });
    await given.brasileiraoMatch({ home: 'Bahia', away: 'Santos', score: '1-1' });

    await teams.confirmTopRanked({ measure: 'away win rate', team: 'Grêmio', value: 100 });
  });

  it('should combine a club squad with its match record', async () => {
    await given.player({ name: 'Everton', club: 'Grêmio', overall: 82 });
    await given.player({ name: 'Geromel', club: 'Grêmio', overall: 80 });
    await given.player({ name: 'Paolo Guerrero', nationality: 'Peru', club: 'Internacional', overall: 78 });
    await given.brasileiraoMatch({ home: 'Gremio', away: 'Internacional', score: '2-0' });

    await teams.confirmProfile({ team: 'Grêmio', squadSize: 2, bestPlayer: 'Everton', played: 1, wins: 1 });
  });
});

describe('Recognising teams whatever their name', () => {
  const { given, teams } = useSoccerDsl();

  it('should treat state-suffixed, accent-free and full club names as the same team', async () => {
    await given.brasileiraoMatch({ home: 'São Paulo', away: 'Santos', score: '1-0', date: '2015-05-10', recordedIn: 'serie-a-dataset' });
    await given.brasileiraoMatch({ home: 'Santos', away: 'São Paulo', score: '1-1', date: '2013-08-04', recordedIn: 'historical-dataset' });
    await given.leagueMatch({ division: 'Serie A', home: 'São Paulo', away: 'Santos', score: '2-0', date: '2023-07-09' });

    await teams.confirmRecord({ team: 'Sao Paulo FC', played: 3, wins: 2, draws: 1, losses: 0 });
  });

  it('should tell apart clubs that share a name but come from different states', async () => {
    await given.brasileiraoMatch({ home: 'Atlético Mineiro', away: 'Atlético Goianiense', score: '2-0' });
    await given.brasileiraoMatch({ home: 'Athletico Paranaense', away: 'Atlético Mineiro', score: '1-1' });

    await teams.confirmRecord({ team: 'Atletico-MG', played: 2, wins: 1, draws: 1, losses: 0 });
  });

  it('should count a match once even when several datasets record it', async () => {
    await given.brasileiraoMatch({ home: 'Cruzeiro', away: 'Bahia', score: '2-1', date: '2017-06-11', recordedIn: 'serie-a-dataset' });
    await given.brasileiraoMatch({ home: 'Cruzeiro', away: 'Bahia', score: '2-1', date: '2017-06-11', recordedIn: 'historical-dataset' });
    await given.brasileiraoMatch({ home: 'Cruzeiro', away: 'Bahia', score: '2-1', date: '2017-06-11', recordedIn: 'extended-stats-dataset' });

    await teams.confirmRecord({ team: 'Cruzeiro', played: 1, wins: 1, goalsFor: 2, goalsAgainst: 1 });
  });

  it('should understand Brazilian dates in historical records', async () => {
    await given.brasileiraoMatch({ home: 'Vitória', away: 'Bahia', score: '2-2', date: '2008-08-31', recordedIn: 'historical-dataset' });

    await teams.confirmRecord({ team: 'Vitória', from: '2008-08-01', to: '2008-08-31', played: 1, draws: 1 });
  });
});
