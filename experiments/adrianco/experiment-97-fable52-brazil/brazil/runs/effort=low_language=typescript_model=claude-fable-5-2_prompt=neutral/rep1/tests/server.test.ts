import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { connectClient } from './helpers.js';

let ask: Awaited<ReturnType<typeof connectClient>>['ask'];
let client: Awaited<ReturnType<typeof connectClient>>['client'];

beforeAll(async () => {
  ({ ask, client } = await connectClient());
});
afterAll(async () => {
  await client.close();
});

describe('Feature: MCP server', () => {
  it('Scenario: The server advertises its tools with schemas', async () => {
    const { tools } = await client.listTools();
    expect(tools.map((t) => t.name).sort()).toEqual(
      [
        'biggest_wins', 'club_player_summary', 'compare_seasons', 'competition_stats', 'cup_summary',
        'dataset_info', 'extended_match_stats', 'find_derbies', 'head_to_head', 'list_teams',
        'player_details', 'rank_teams', 'search_matches', 'search_players', 'standings',
        'team_profile', 'team_stats',
      ].sort(),
    );
    for (const t of tools) {
      expect(t.description).toBeTruthy();
      expect(t.inputSchema.type).toBe('object');
    }
  });

  it('Scenario: Invalid arguments and unknown teams are reported as errors, not crashes', async () => {
    const bad = await ask('team_stats', { team: 'Nonexistent United' });
    expect(bad.isError).toBe(true);
    expect(bad.text).toMatch(/No team matching/);
    const invalid = await ask('standings', { season: 'twenty-nineteen' });
    expect(invalid.isError).toBe(true);
  });
});

/** The sample questions from the specification, each answered through an MCP tool call. */
describe('Feature: Sample questions are answered through MCP tools', () => {
  const questions: [string, string, Record<string, unknown>, RegExp[]][] = [
    ['Show me all Flamengo vs Fluminense matches', 'search_matches', { team: 'Flamengo', opponent: 'Fluminense' },
      [/Flamengo vs Fluminense - \d+ matches found/, /\d{4}-\d{2}-\d{2}: (Flamengo|Fluminense) \d+-\d+ (Flamengo|Fluminense) \(/, /Head-to-head in dataset: Flamengo \d+ wins, Fluminense \d+ wins, \d+ draws/, /more matches in dataset/]],
    ['What matches did Palmeiras play in 2023?', 'search_matches', { team: 'Palmeiras', season: 2023, limit: 100 },
      [/Palmeiras - \d+ matches found/, /2023-\d{2}-\d{2}: /]],
    ['Find all Copa do Brasil finals', 'search_matches', { competition: 'Copa do Brasil', stage: 'final', limit: 50 },
      [/Copa do Brasil 2019, final/, /Athletico-PR 1-0 Internacional/, /Copa do Brasil 2012, final/]],
    ['When did Flamengo last play Corinthians? What was the score?', 'search_matches', { team: 'Flamengo', opponent: 'Corinthians', limit: 1 },
      [/- \d{4}-\d{2}-\d{2}: \S+ \d+-\d+ \S+/]],
    ["What is Corinthians' home record in 2022?", 'team_stats', { team: 'Corinthians', venue: 'home', season: 2022, competition: 'Brasileirão' },
      [/Corinthians home record \(Brasileirão, 2022\)/, /- Matches: \d+/, /- Wins: \d+, Draws: \d+, Losses: \d+/, /Goals For: \d+, Goals Against: \d+/, /Win rate: \d+\.\d%/]],
    ['Which team scored the most goals in Serie A 2023?', 'rank_teams', { metric: 'goals_for', competition: 'Serie A', season: 2023 },
      [/1\. .+ - goals_for: \d+/]],
    ['Compare Palmeiras and Santos head-to-head', 'head_to_head', { team_a: 'Palmeiras', team_b: 'Santos' },
      [/Palmeiras vs Santos \(Clássico da Saudade\)/, /Palmeiras \d+ wins, Santos \d+ wins, \d+ draws/, /Most recent meetings/]],
    ['What competitions has Palmeiras played in?', 'team_profile', { team: 'Palmeiras' },
      [/Brasileirão Série A: seasons 2004-2023/, /Copa do Brasil: seasons/, /Copa Libertadores: seasons/]],
    ['Find all Brazilian players in the dataset', 'search_players', { nationality: 'Brazil', limit: 5 },
      [/827 players found/, /1\. Neymar Jr - Overall: 92, Position: LW, Club: Paris Saint-Germain/, /more players in dataset/]],
    ['Who are the top Brazilian players? (goalkeepers)', 'search_players', { nationality: 'Brazil', position: 'goalkeeper', limit: 3 },
      [/1\. Ederson - Overall: 86, Position: GK, Club: Manchester City/, /2\. Alisson - Overall: \d+, Position: GK, Club: Liverpool/]],
    ['Who are the highest-rated players at Grêmio?', 'search_players', { club: 'Grêmio', limit: 5 },
      [/20 players found/, /Club: Grêmio/]],
    ['Which players play for Flamengo? (club absent from FIFA file)', 'search_players', { club: 'Flamengo' },
      [/No players found/, /does not include every Brazilian club/]],
    ['Show me all forwards from Santos', 'search_players', { club: 'Santos', position: 'forward' },
      [/Position: (ST|CF|LW|RW|LF|RF|LS|RS), Club: Santos/]],
    ['Who is Neymar?', 'player_details', { name: 'Neymar' },
      [/Neymar Jr \(id 190871\)/, /Overall: 92, Potential: 93/, /Dribbling 96/]],
    ['Who is Gabriel Barbosa?', 'search_players', { name: 'Gabriel Barbosa' },
      [/partial matches/, /Gabriel/]],
    ['Brazilian players at Brazilian clubs', 'club_player_summary', { nationality: 'Brazil', brazilian_clubs_only: true },
      [/- Grêmio: \d+ players \(avg rating: \d+\.\d/, /- Santos: \d+ players/]],
    ['Who won the 2019 Brasileirão?', 'standings', { season: 2019 },
      [/2019 Brasileirão Série A Final Standings \(calculated from matches\)/, /1\. Flamengo - 90 pts \(28W, 6D, 4L\).* - Champion/, /2\. Santos - 74 pts \(22W, 8D, 8L\)/, /3\. Palmeiras - 74 pts \(21W, 11D, 6L\)/]],
    ['Which teams were relegated in 2019?', 'standings', { season: 2019 },
      [/Bottom four.*Cruzeiro, CSA, Chapecoense, Avaí/, /20\. Avaí .* - Relegation zone/]],
    ['Show the 2018 Copa Libertadores bracket', 'cup_summary', { competition: 'Libertadores', season: 2018 },
      [/round of 16 \(16 matches\)/, /quarterfinals/, /semifinals/, /Champion: River Plate/]],
    ["What's the average goals per match in the Brasileirão?", 'competition_stats', { competition: 'Brasileirão' },
      [/Average goals per match: \d\.\d{2}/, /Home win rate: \d+\.\d%/]],
    ['Which team has the best away record?', 'rank_teams', { metric: 'win_rate', venue: 'away', competition: 'Serie A', min_matches: 100 },
      [/ranked by win_rate in away matches/, /1\. .+ - win_rate: \d+\.\d%/]],
    ['Which team has the best home record?', 'rank_teams', { metric: 'win_rate', venue: 'home', competition: 'Serie A', min_matches: 100 },
      [/ranked by win_rate in home matches/, /1\. /]],
    ['Show me the biggest wins in the dataset', 'biggest_wins', { limit: 5 },
      [/Biggest victories/, /1\. \d{4}-\d{2}-\d{2}: .+ \d+-\d+ .+ \(/, /5\. /]],
    ['Show me all derbies in 2023', 'find_derbies', { season: 2023 },
      [/derby matches found \(2023\)/, /\[Fla-Flu\] 2023-/]],
    ['Compare the 2018 and 2019 seasons', 'compare_seasons', { season_a: 2018, season_b: 2019 },
      [/2018 Brasileirão Série A:/, /Champion: Palmeiras/, /Champion: Flamengo/, /Change in goals per match: \+0\.1\d/]],
    ['How many corners does Flamengo average?', 'extended_match_stats', { team: 'Flamengo' },
      [/Corners: \d+\.\d{2} for, \d+\.\d{2} against per match/, /Shots: /]],
    ['Which teams are in the data?', 'list_teams', { search: 'atletico' },
      [/Atlético-MG: \d+ matches/, /Atlético-GO: \d+ matches/]],
    ['What data is available?', 'dataset_info', {},
      [/fifa_data\.csv: 18207 rows/, /Copa Libertadores: 1255 matches, seasons 2013-2022/]],
  ];

  it('Scenario: At least 20 sample questions are covered', () => {
    expect(questions.length).toBeGreaterThanOrEqual(20);
  });

  it.each(questions)('Question: %s', async (_q, tool, args, patterns) => {
    const start = performance.now();
    const r = await ask(tool, args);
    expect(r.isError, r.text).toBe(false);
    for (const p of patterns) expect(r.text).toMatch(p);
    expect(performance.now() - start).toBeLessThan(2000);
  });
});
