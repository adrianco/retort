/**
 * The specification's own sample questions, end to end.
 *
 * Each case names the natural-language question, the tool an LLM would pick,
 * the arguments, and an assertion on the answer. Together they satisfy the
 * "at least 20 sample questions can be answered" and "cross-file queries work"
 * criteria, and they double as the worked examples in the README.
 */

import { describe, expect, it } from 'vitest';
import { getGraph } from '../src/graph/graph.js';
import { toolByName } from '../src/tools/index.js';

const graph = getGraph();

interface Case {
  question: string;
  tool: string;
  args: Record<string, unknown>;
  expect: (text: string, data: Record<string, unknown>) => void;
}

function ask(tool: string, args: Record<string, unknown>) {
  const definition = toolByName(tool);
  if (!definition) throw new Error(`No tool named ${tool}`);
  const parsed = definition.schema.parse(args);
  return definition.handler(graph, parsed as never);
}

const CASES: Case[] = [
  // --- Simple lookups ----------------------------------------------------
  {
    question: 'When did Flamengo last play Corinthians, and what was the score?',
    tool: 'head_to_head',
    args: { teamA: 'Flamengo', teamB: 'Corinthians', limit: 1 },
    expect: (text, data) => {
      expect(text).toContain('Most recent meeting');
      expect(Number(data['meetings'])).toBeGreaterThan(10);
    },
  },
  {
    question: 'Who is Alisson?',
    tool: 'player_profile',
    args: { name: 'Alisson' },
    expect: (text) => {
      expect(text).toContain('Nationality: Brazil');
      expect(text).toMatch(/Overall: \d+/);
    },
  },
  {
    question: 'Show me all Flamengo vs Fluminense matches.',
    tool: 'search_matches',
    args: { team: 'Flamengo', opponent: 'Fluminense', limit: 100 },
    expect: (_text, data) => {
      expect(Number(data['total'])).toBeGreaterThanOrEqual(15);
    },
  },
  {
    question: 'What matches did Palmeiras play in 2023?',
    tool: 'search_matches',
    args: { team: 'Palmeiras', season: 2023, limit: 100 },
    expect: (_text, data) => {
      expect(Number(data['total'])).toBeGreaterThanOrEqual(38);
    },
  },
  {
    question: 'Find all Copa do Brasil finals.',
    tool: 'search_matches',
    args: { competition: 'copa-do-brasil', stage: 'final', limit: 100 },
    expect: (text, data) => {
      expect(Number(data['total'])).toBeGreaterThanOrEqual(10);
      expect(text).not.toContain('Quarterfinals');
    },
  },

  // --- Team queries ------------------------------------------------------
  {
    question: "What is Corinthians' home record in 2022?",
    tool: 'team_stats',
    args: { team: 'Corinthians', season: 2022, competition: 'serie-a', venue: 'home' },
    expect: (text, data) => {
      const record = data['record'] as Record<string, number>;
      expect(record['played']).toBe(19);
      expect(record['wins'] + record['draws'] + record['losses']).toBe(19);
      expect(text).toContain('Win rate');
    },
  },
  {
    question: 'Which team scored the most goals in Série A 2023?',
    tool: 'team_rankings',
    args: { metric: 'goalsFor', competition: 'serie-a', season: 2023, limit: 3 },
    expect: (_text, data) => {
      const rankings = data['rankings'] as Array<Record<string, unknown>>;
      expect(rankings.length).toBe(3);
      expect(Number(rankings[0]!['goalsFor'])).toBeGreaterThanOrEqual(
        Number(rankings[1]!['goalsFor']),
      );
    },
  },
  {
    question: 'Compare Palmeiras and Santos head-to-head.',
    tool: 'head_to_head',
    args: { teamA: 'Palmeiras', teamB: 'Santos' },
    expect: (text, data) => {
      expect(text).toContain('Head-to-head in dataset');
      const total =
        Number(data['aWins']) + Number(data['bWins']) + Number(data['draws']) + Number(data['withoutScore']);
      expect(total).toBe(Number(data['meetings']));
    },
  },
  {
    question: 'Which team has the best home record in Série A 2019?',
    tool: 'team_rankings',
    args: { metric: 'points', venue: 'home', competition: 'serie-a', season: 2019, limit: 1 },
    expect: (_text, data) => {
      const rankings = data['rankings'] as Array<Record<string, unknown>>;
      expect(rankings[0]!['team']).toBe('Flamengo');
    },
  },
  {
    question: 'Which team has the best away record in Série A 2019?',
    tool: 'team_rankings',
    args: { metric: 'points', venue: 'away', competition: 'serie-a', season: 2019, limit: 1 },
    expect: (_text, data) => {
      const rankings = data['rankings'] as Array<Record<string, unknown>>;
      expect(Number(rankings[0]!['played'])).toBe(19);
    },
  },
  {
    question: 'What competitions has Palmeiras played in?',
    tool: 'team_profile',
    args: { team: 'Palmeiras' },
    expect: (text, data) => {
      const competitions = data['competitions'] as Array<Record<string, unknown>>;
      expect(competitions.length).toBeGreaterThanOrEqual(2);
      expect(text).toContain('Copa Libertadores');
    },
  },
  {
    question: 'Which clubs played in Série A in 2019?',
    tool: 'list_teams',
    args: { competition: 'serie-a', season: 2019, limit: 100 },
    expect: (_text, data) => {
      expect(Number(data['total'])).toBe(20);
    },
  },

  // --- Player queries ----------------------------------------------------
  {
    question: 'Find all Brazilian players in the dataset.',
    tool: 'search_players',
    args: { nationality: 'Brazil', limit: 5 },
    expect: (_text, data) => {
      expect(Number(data['total'])).toBe(827);
    },
  },
  {
    question: 'Who are the top-rated Brazilian players?',
    tool: 'search_players',
    args: { nationality: 'Brazil', sortBy: 'overall', limit: 3 },
    expect: (_text, data) => {
      const players = data['players'] as Array<Record<string, unknown>>;
      expect(players[0]!['name']).toBe('Neymar Jr');
      expect(Number(players[0]!['overall'])).toBeGreaterThanOrEqual(Number(players[1]!['overall']));
    },
  },
  {
    question: 'Who are the highest-rated players at Fluminense?',
    tool: 'search_players',
    args: { club: 'Fluminense', sortBy: 'overall', limit: 5 },
    expect: (_text, data) => {
      const players = data['players'] as Array<Record<string, unknown>>;
      expect(players.length).toBe(5);
      expect(players[0]!['clubTeamId']).toBe('fluminense-rj');
    },
  },
  {
    question: 'Show me all forwards from Santos.',
    tool: 'search_players',
    args: { club: 'Santos', positionGroup: 'Forward', limit: 20 },
    expect: (_text, data) => {
      const players = data['players'] as Array<Record<string, unknown>>;
      expect(players.length).toBeGreaterThan(0);
      for (const player of players) expect(player['positionGroup']).toBe('Forward');
    },
  },
  {
    question: 'Which Brazilian clubs have squads in the player data, and how strong are they?',
    tool: 'club_squad',
    args: {},
    expect: (text, data) => {
      const clubs = data['clubs'] as Array<Record<string, unknown>>;
      expect(clubs.length).toBeGreaterThanOrEqual(10);
      expect(text).toContain('avg rating');
    },
  },

  // --- Cross-file (player + match) ---------------------------------------
  {
    question: "What is Internacional's squad, and how has the club done in the matches?",
    tool: 'club_squad',
    args: { team: 'Internacional' },
    expect: (text, data) => {
      expect(Number(data['squadSize'])).toBe(20);
      const record = data['record'] as Record<string, number>;
      expect(record['played']).toBeGreaterThan(100);
      expect(text).toContain('match record in the dataset');
    },
  },

  // --- Competition queries -----------------------------------------------
  {
    question: 'Who won the 2019 Brasileirão?',
    tool: 'competition_standings',
    args: { competition: 'serie-a', season: 2019 },
    expect: (text, data) => {
      const champion = data['champion'] as Record<string, unknown>;
      expect(champion['team']).toBe('Flamengo');
      expect(champion['points']).toBe(90);
      expect(text).toContain('Champion');
    },
  },
  {
    question: 'Which teams were relegated from Série A in 2020?',
    tool: 'competition_standings',
    args: { competition: 'serie-a', season: 2020 },
    expect: (_text, data) => {
      const relegated = data['relegated'] as Array<Record<string, unknown>>;
      expect(relegated.length).toBe(4);
      expect(relegated.map((r) => r['team'])).toContain('Botafogo');
    },
  },
  {
    question: 'Show the 2018 Copa Libertadores bracket.',
    tool: 'competition_bracket',
    args: { competition: 'libertadores', season: 2018 },
    expect: (text, data) => {
      const winner = data['winner'] as Record<string, unknown>;
      expect(winner['name']).toBe('River Plate');
      expect(text).toContain('Group Stage');
      expect(text).toContain('Semifinals');
    },
  },
  {
    question: 'Which seasons of the Copa do Brasil are covered?',
    tool: 'list_seasons',
    args: { competition: 'copa-do-brasil' },
    expect: (_text, data) => {
      const seasons = data['seasons'] as Array<Record<string, unknown>>;
      expect(seasons.length).toBeGreaterThanOrEqual(10);
    },
  },

  // --- Statistical analysis ----------------------------------------------
  {
    question: "What's the average goals per match in the Brasileirão?",
    tool: 'match_statistics',
    args: { competition: 'serie-a' },
    expect: (_text, data) => {
      const goalsPerMatch = Number(data['goalsPerMatch']);
      expect(goalsPerMatch).toBeGreaterThan(2);
      expect(goalsPerMatch).toBeLessThan(3);
    },
  },
  {
    question: 'How often does the home team win in the Brasileirão?',
    tool: 'match_statistics',
    args: { competition: 'serie-a' },
    expect: (_text, data) => {
      const rate = Number(data['homeWinRate']);
      expect(rate).toBeGreaterThan(0.4);
      expect(rate).toBeLessThan(0.6);
      expect(rate).toBeGreaterThan(Number(data['awayWinRate']));
    },
  },
  {
    question: 'Show me the biggest wins in the dataset.',
    tool: 'record_extremes',
    args: { kind: 'biggest-margin', limit: 5 },
    expect: (_text, data) => {
      const matches = data['matches'] as Array<Record<string, unknown>>;
      expect(matches.length).toBe(5);
      expect(Number(matches[0]!['margin'])).toBeGreaterThanOrEqual(Number(matches[4]!['margin']));
    },
  },
  {
    question: 'Compare the 2018 and 2019 Série A seasons.',
    tool: 'compare_seasons',
    args: { competition: 'serie-a', seasons: [2018, 2019] },
    expect: (text, data) => {
      const seasons = data['seasons'] as Array<Record<string, unknown>>;
      expect(seasons.length).toBe(2);
      expect(text).toContain('Goals per match moved');
    },
  },
  {
    question: 'Show me all the derbies played in 2023.',
    tool: 'find_derbies',
    args: { season: 2023 },
    expect: (text, data) => {
      expect(Number(data['total'])).toBeGreaterThan(5);
      expect(text).toMatch(/Fla-Flu|Derby Paulista|Grenal/);
    },
  },
  {
    question: 'What is in this dataset?',
    tool: 'dataset_info',
    args: {},
    expect: (text) => {
      expect(text).toContain('Merged fixtures');
      expect(text).toContain('Competitions:');
    },
  },
];

describe('specification sample questions', () => {
  it('covers at least the 20 questions the specification asks for', () => {
    expect(CASES.length).toBeGreaterThanOrEqual(20);
  });

  it.each(CASES.map((testCase) => [testCase.question, testCase] as const))(
    '%s',
    (_question, testCase) => {
      const result = ask(testCase.tool, testCase.args);
      expect(result.text.length).toBeGreaterThan(0);
      testCase.expect(result.text, result.data);
    },
  );
});
