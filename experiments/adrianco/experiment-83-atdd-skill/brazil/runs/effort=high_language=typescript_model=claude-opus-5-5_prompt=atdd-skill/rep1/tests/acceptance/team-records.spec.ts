/**
 * Executable specification: team records and head-to-head comparisons.
 *
 * Layer 1 (test cases) — domain language only.
 */
import { spec } from './dsl/spec.js';

spec("should report a team's home record for a season", async ({ given, teams }) => {
  given.match({ home: 'Corinthians', away: 'Santos', score: '2-0', season: 2022 });
  given.match({ home: 'Corinthians', away: 'Goiás', score: '1-1', season: 2022 });
  given.match({ home: 'Corinthians', away: 'Ceará', score: '0-1', season: 2022 });
  given.match({ home: 'Fortaleza', away: 'Corinthians', score: '0-3', season: 2022 });
  given.match({ home: 'Corinthians', away: 'Bahia', score: '4-0', season: 2021 });

  await teams.requestRecord({ team: 'Corinthians', season: 2022, venue: 'home' });

  teams.confirmRecord({ played: 3, won: 1, drawn: 1, lost: 1, goalsFor: 3, goalsAgainst: 2, winRate: '33.3%' });
});

spec("should report a team's away record", async ({ given, teams }) => {
  given.match({ home: 'Fortaleza', away: 'Corinthians', score: '0-3' });
  given.match({ home: 'Bahia', away: 'Corinthians', score: '2-2' });
  given.match({ home: 'Corinthians', away: 'Santos', score: '2-0' });

  await teams.requestRecord({ team: 'Corinthians', venue: 'away' });

  teams.confirmRecord({ played: 2, won: 1, drawn: 1, lost: 0, goalsFor: 5, goalsAgainst: 2, winRate: '50.0%' });
});

spec("should only count the competition asked about in a team's record", async ({ given, teams }) => {
  given.match({ home: 'Internacional', away: 'Grêmio', score: '1-0', competition: 'Brasileirão' });
  given.match({ home: 'Internacional', away: 'Athletico-PR', score: '1-2', competition: 'Copa do Brasil' });

  await teams.requestRecord({ team: 'Internacional', competition: 'Copa do Brasil' });

  teams.confirmRecord({ played: 1, won: 0, drawn: 0, lost: 1 });
});

spec('should compare two teams head-to-head', async ({ given, teams }) => {
  given.match({ home: 'Palmeiras', away: 'Santos', score: '3-0' });
  given.match({ home: 'Santos', away: 'Palmeiras', score: '1-2' });
  given.match({ home: 'Palmeiras', away: 'Santos', score: '0-1' });
  given.match({ home: 'Santos', away: 'Palmeiras', score: '1-1' });
  given.match({ home: 'Palmeiras', away: 'Flamengo', score: '0-4' });

  await teams.compareHeadToHead({ team: 'Palmeiras', opponent: 'Santos' });

  teams.confirmHeadToHead({ played: 4, teamWins: 2, opponentWins: 1, draws: 1, teamGoals: 6, opponentGoals: 3 });
});

spec('should list the competitions a team has played in', async ({ given, teams }) => {
  given.match({ home: 'Palmeiras', away: 'Santos', competition: 'Brasileirão' });
  given.match({ home: 'Palmeiras', away: 'Boca Juniors', competition: 'Libertadores' });
  given.match({ home: 'Palmeiras', away: 'Tombense', competition: 'Copa do Brasil' });
  given.match({ home: 'Flamengo', away: 'Ponte Preta', competition: 'Serie B' });

  await teams.requestCompetitions({ team: 'Palmeiras' });

  teams.confirmCompetitions(['Brasileirão', 'Copa do Brasil', 'Libertadores']);
});

spec("should break down a team's performance by competition", async ({ given, teams }) => {
  given.match({ home: 'Palmeiras', away: 'Santos', score: '2-0', competition: 'Brasileirão' });
  given.match({ home: 'Palmeiras', away: 'Boca Juniors', score: '1-1', competition: 'Libertadores' });
  given.match({ home: 'River Plate', away: 'Palmeiras', score: '0-3', competition: 'Libertadores' });

  await teams.requestCompetitions({ team: 'Palmeiras' });

  teams.confirmCompetitionRecord({ competition: 'Libertadores', played: 2, won: 1, drawn: 1, lost: 0, goalsFor: 4, goalsAgainst: 1 });
});

spec('should find the team that scored the most goals in a season', async ({ given, teams }) => {
  given.match({ home: 'Palmeiras', away: 'Santos', score: '4-0', season: 2023 });
  given.match({ home: 'Botafogo-RJ', away: 'Palmeiras', score: '3-4', season: 2023 });
  given.match({ home: 'Botafogo-RJ', away: 'Santos', score: '3-0', season: 2023 });
  given.match({ home: 'Santos', away: 'Grêmio', score: '9-0', season: 2022 });

  await teams.rank({ by: 'goals scored', season: 2023 });

  teams.confirmLeader({ team: 'Palmeiras', goalsFor: 8 });
});
