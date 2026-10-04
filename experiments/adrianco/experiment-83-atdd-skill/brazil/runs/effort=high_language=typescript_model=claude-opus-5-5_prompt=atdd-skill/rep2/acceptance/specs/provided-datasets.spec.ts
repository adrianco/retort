/**
 * Executable specification: answering the sample questions from the brief
 * against the real, provided Kaggle datasets.
 *
 * Unlike the other specs, which create synthetic data, these exercise the
 * system with the data it ships with, to prove data coverage and that
 * answers come back fast enough. Expectations are well-known football facts
 * rather than values read back from the files.
 */
import { describe, it } from 'vitest';
import { useSoccerDsl } from '../dsl/soccer-dsl.js';

describe('Answering questions from the provided datasets', () => {
  const { datasets, matches, teams, players, competitions, statistics, performance } = useSoccerDsl({ datasets: 'provided' });

  it('should load all six provided datasets', async () => {
    await datasets.confirmLoaded({
      'Brasileirao_Matches.csv': 4180,
      'Brazilian_Cup_Matches.csv': 1337,
      'Libertadores_Matches.csv': 1255,
      'BR-Football-Dataset.csv': 10296,
      'novo_campeonato_brasileiro.csv': 6886,
      'fifa_data.csv': 18207,
    });
  });

  // Competition queries
  it('should know who won the 2019 Brasileirão', async () => {
    await competitions.confirmChampion({ season: 2019, team: 'Flamengo', points: 90, wins: 28, draws: 6, losses: 4 });
  });

  it('should calculate the top of the 2019 table', async () => {
    await competitions.confirmStandings({ season: 2019, order: ['Flamengo', 'Santos', 'Palmeiras'] });
  });

  it('should know which teams were relegated in 2019', async () => {
    await competitions.confirmRelegated({ season: 2019, teams: ['Cruzeiro', 'CSA', 'Chapecoense', 'Avaí'] });
  });

  it('should treat the pandemic-delayed 2020 season as one season', async () => {
    await competitions.confirmChampion({ season: 2020, team: 'Flamengo', points: 71 });
  });

  it('should know the 2003 champion from the historical records', async () => {
    await competitions.confirmChampion({ season: 2003, team: 'Cruzeiro' });
  });

  it('should show the 2018 Copa Libertadores final', async () => {
    await competitions.confirmBracketIncludes({ competition: 'Copa Libertadores', season: 2018, stage: 'final', teams: ['Boca Juniors', 'River Plate'] });
  });

  it('should find the 2019 Copa do Brasil final', async () => {
    await matches.confirmFoundAtLeast({ competition: 'Copa do Brasil', season: 2019, stage: 'final', count: 2, involving: ['Athletico Paranaense', 'Internacional'] });
  });

  // Match queries
  it('should show Flamengo vs Fluminense matches', async () => {
    await matches.confirmFoundAtLeast({ team: 'Flamengo', opponent: 'Fluminense', count: 20 });
  });

  it('should find the matches Palmeiras played in 2022', async () => {
    await matches.confirmFoundAtLeast({ team: 'Palmeiras', season: 2022, count: 38 });
  });

  it('should tell when Flamengo last played Corinthians', async () => {
    await matches.confirmLastMeetingFound({ team: 'Flamengo', opponent: 'Corinthians' });
  });

  it('should find the derbies played in 2023', async () => {
    await matches.confirmDerbiesFound({ season: 2023, including: ['Fla-Flu', 'Grenal', 'Derby Paulista'] });
  });

  // Team queries
  it("should report Corinthians' home record in 2022", async () => {
    await teams.confirmRecord({ team: 'Corinthians', season: 2022, venue: 'home', competition: 'Brasileirão', played: 19 });
  });

  it('should compare Palmeiras and Santos head-to-head', async () => {
    await teams.confirmHeadToHeadPlayedAtLeast({ team: 'Palmeiras', opponent: 'Santos', matches: 30 });
  });

  it('should know every competition Palmeiras has played in', async () => {
    await teams.confirmCompetitions({ team: 'Palmeiras', competitions: ['Brasileirão Série A', 'Copa do Brasil', 'Copa Libertadores'] });
  });

  it('should find the team with the best home record', async () => {
    await teams.confirmRankingAvailable({ measure: 'home win rate', competition: 'Brasileirão' });
  });

  it('should combine a club squad with its match record', async () => {
    await teams.confirmProfileHasSquadAndMatches({ team: 'Grêmio' });
  });

  // Player queries
  it('should list the top Brazilian players with Neymar first', async () => {
    await players.confirmFound({ nationality: 'Brazil', limit: 1, expected: ['Neymar Jr'] });
  });

  it('should explain that Gabriel Barbosa is not in the FIFA data and suggest similar names', async () => {
    await players.confirmUnknown({ name: 'Gabriel Barbosa', suggesting: ['Gabriel Jesus'] });
  });

  it('should find the players at a Brazilian club', async () => {
    await players.confirmFoundAtLeast({ club: 'Santos', count: 20 });
  });

  it('should summarise Brazilian players by Brazilian club', async () => {
    await players.confirmClubSummaryIncludes({ nationality: 'Brazil', clubs: ['Grêmio', 'Cruzeiro', 'Santos'] });
  });

  // Statistical analysis
  it('should calculate the average goals per Brasileirão match', async () => {
    await statistics.confirmSummaryBetween({ competition: 'Brasileirão', averageGoals: [2.2, 2.8], homeWinRate: [40, 55] });
  });

  it('should list the biggest wins in the dataset', async () => {
    await statistics.confirmBiggestWinsMarginAtLeast({ limit: 5, margin: 5 });
  });

  it('should compare the 2018 and 2019 seasons', async () => {
    await statistics.confirmSeasonComparison({
      competition: 'Brasileirão',
      seasons: { 2018: { matches: 380, champion: 'Palmeiras' }, 2019: { matches: 380, champion: 'Flamengo' } },
    });
  });

  // Query performance
  it('should answer simple lookups in under 2 seconds', async () => {
    await performance.confirmSimpleLookupsWithin({ seconds: 2 });
  });

  it('should answer aggregate queries in under 5 seconds', async () => {
    await performance.confirmAggregateQueriesWithin({ seconds: 5 });
  });
});
