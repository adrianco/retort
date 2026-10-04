/**
 * Executable specification: the system answers questions from the six
 * provided Kaggle datasets, accurately and promptly.
 *
 * Unlike the other specs, these run against the real provided data (shared,
 * read-only), because what they specify is coverage of that data and the
 * response times of real-sized queries.
 */
import { providedDataSpec as spec, type QuestionAreas } from './dsl/spec.js';

spec('should load all six provided datasets', async ({ datasets }) => {
  await datasets.requestOverview();

  datasets.confirmLoaded({ dataset: 'Brasileirão Serie A matches', records: 4180 });
  datasets.confirmLoaded({ dataset: 'Copa do Brasil matches', records: 1337 });
  datasets.confirmLoaded({ dataset: 'Copa Libertadores matches', records: 1255 });
  datasets.confirmLoaded({ dataset: 'Extended match statistics', records: 10296 });
  datasets.confirmLoaded({ dataset: 'Historical Brasileirão 2003-2019', records: 6886 });
  datasets.confirmLoaded({ dataset: 'FIFA player database', records: 18207 });
});

spec('should calculate the real 2019 Brasileirão champion', async ({ competitions }) => {
  await competitions.requestStandings({ competition: 'Brasileirão', season: 2019 });

  competitions.confirmStandingsStartWith(['1. Flamengo - 90 pts (28W, 6D, 4L)']);
});

spec('should find the real 2020 Copa do Brasil final', async ({ matches }) => {
  await matches.findFinals({ competition: 'Copa do Brasil', season: 2020 });

  matches.confirmFinals(['2020: Palmeiras beat Grêmio 3-0 on aggregate']);
});

spec('should find the top-rated Brazilian player', async ({ players }) => {
  await players.search({ nationality: 'Brazil', limit: 1 });

  players.confirmListed(['Neymar Jr']);
});

spec('should combine match results and squad data for a real club', async ({ statistics }) => {
  await statistics.profileTeam({ team: 'Grêmio' });

  statistics.confirmProfile({ team: 'Grêmio', squadSize: 20 });
});

type SampleQuestion = { question: string; aggregate?: boolean; ask: (dsl: QuestionAreas) => Promise<void> };

const sampleQuestions: SampleQuestion[] = [
  { question: 'Show me all Flamengo vs Fluminense matches', ask: ({ matches }) => matches.findBetween({ team: 'Flamengo', opponent: 'Fluminense' }) },
  { question: 'What matches did Palmeiras play in 2023?', ask: ({ matches }) => matches.findForTeam({ team: 'Palmeiras', season: 2023 }) },
  { question: 'Find all Copa do Brasil finals', ask: ({ matches }) => matches.findFinals({ competition: 'Copa do Brasil' }) },
  { question: 'When did Flamengo last play Corinthians?', ask: ({ matches }) => matches.findLastMeeting({ team: 'Flamengo', opponent: 'Corinthians' }) },
  { question: 'Show me all derbies in 2023', ask: ({ matches }) => matches.findDerbies({ season: 2023 }) },
  { question: "What is Corinthians' home record in 2022?", ask: ({ teams }) => teams.requestRecord({ team: 'Corinthians', season: 2022, venue: 'home' }) },
  { question: 'Which team scored the most goals in Serie A 2023?', aggregate: true, ask: ({ teams }) => teams.rank({ by: 'goals scored', season: 2023, competition: 'Brasileirão' }) },
  { question: 'Compare Palmeiras and Santos head-to-head', ask: ({ teams }) => teams.compareHeadToHead({ team: 'Palmeiras', opponent: 'Santos' }) },
  { question: 'What competitions has Palmeiras played in?', ask: ({ teams }) => teams.requestCompetitions({ team: 'Palmeiras' }) },
  { question: 'Find all Brazilian players in the dataset', ask: ({ players }) => players.search({ nationality: 'Brazil' }) },
  { question: 'Who are the highest-rated players at Grêmio?', ask: ({ players }) => players.search({ club: 'Grêmio' }) },
  { question: 'Show me all forwards from Santos', ask: ({ players }) => players.search({ club: 'Santos', position: 'forward' }) },
  { question: 'Who is Neymar?', ask: ({ players }) => players.lookUp({ name: 'Neymar' }) },
  { question: 'How many Brazilian players play at each Brazilian club?', aggregate: true, ask: ({ players }) => players.summariseByBrazilianClub({ nationality: 'Brazil' }) },
  { question: 'Who won the 2019 Brasileirão?', aggregate: true, ask: ({ competitions }) => competitions.requestStandings({ season: 2019 }) },
  { question: 'Show the 2018 Copa Libertadores bracket', ask: ({ competitions }) => competitions.requestBracket({ competition: 'Libertadores', season: 2018 }) },
  { question: 'Which teams were relegated in 2020?', aggregate: true, ask: ({ competitions }) => competitions.requestStandings({ season: 2020 }) },
  { question: "What's the average goals per match in the Brasileirão?", aggregate: true, ask: ({ statistics }) => statistics.summariseCompetition({ competition: 'Brasileirão' }) },
  { question: 'Which team has the best home record?', aggregate: true, ask: ({ statistics }) => statistics.rankTeams({ by: 'home record' }) },
  { question: 'Which team has the best away record?', aggregate: true, ask: ({ statistics }) => statistics.rankTeams({ by: 'away record' }) },
  { question: 'Show me the biggest wins in the dataset', aggregate: true, ask: ({ statistics }) => statistics.findBiggestWins({}) },
  { question: 'Compare the 2018 and 2019 seasons', aggregate: true, ask: ({ statistics }) => statistics.compareSeasons({ seasons: [2018, 2019] }) },
  { question: 'Tell me about Flamengo, its results and its players', aggregate: true, ask: ({ statistics }) => statistics.profileTeam({ team: 'Flamengo' }) },
];

for (const { question, aggregate, ask } of sampleQuestions) {
  const seconds = aggregate ? 5 : 2;
  spec(`should answer "${question}" within ${seconds} seconds`, async ({ answers, matches, teams, players, competitions, statistics }) => {
    await answers.timeAnswerTo(() => ask({ matches, teams, players, competitions, statistics }));

    answers.confirmAnsweredWithin({ seconds });
  });
}
