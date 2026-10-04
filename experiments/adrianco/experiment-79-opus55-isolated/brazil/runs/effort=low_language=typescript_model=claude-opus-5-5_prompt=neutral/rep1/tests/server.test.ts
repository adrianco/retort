import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { InMemoryTransport } from '@modelcontextprotocol/sdk/inMemory.js';
import { afterAll, beforeAll, describe, expect, it } from 'vitest';
import { createServer } from '../src/server.js';
import { tools } from '../src/tools.js';
import { ask, kb } from './helpers.js';

describe('Feature: MCP server', () => {
  const client = new Client({ name: 'test-client', version: '1.0.0' });
  const text = async (name: string, args: Record<string, unknown> = {}) => {
    const res = await client.callTool({ name, arguments: args });
    return { text: (res.content as { text: string }[])[0].text, isError: res.isError };
  };

  beforeAll(async () => {
    const [clientSide, serverSide] = InMemoryTransport.createLinkedPair();
    await createServer(kb).connect(serverSide);
    await client.connect(clientSide);
  });
  afterAll(() => client.close());

  it('Scenario: the server advertises every tool with a description and input schema', async () => {
    const listed = (await client.listTools()).tools;
    expect(listed.map((t) => t.name).sort()).toEqual(tools.map((t) => t.name).sort());
    for (const t of listed) {
      expect(t.description!.length).toBeGreaterThan(20);
      expect(t.inputSchema.type).toBe('object');
    }
  });

  it('Scenario: a tool call over the protocol returns formatted text', async () => {
    const r = await text('head_to_head', { team_a: 'Flamengo', team_b: 'Fluminense' });
    expect(r.isError).toBeFalsy();
    expect(r.text).toMatch(/^Flamengo vs Fluminense \(Fla-Flu\)/);
    expect(r.text).toMatch(/Head-to-head in dataset \(\d+ matches\): Flamengo \d+ wins, Fluminense \d+ wins, \d+ draws/);
  });

  it('Scenario: unknown teams and invalid arguments are reported as errors, not crashes', async () => {
    const unknown = await text('team_stats', { team: 'Nonexistent United XYZ' });
    expect(unknown.isError).toBe(true);
    expect(unknown.text).toMatch(/No team matching/);
    const invalid = await text('search_matches', { date_from: '01/02/2020' });
    expect(invalid.isError).toBe(true);
  });
});

/** The sample questions from the specification, each answered through a tool. */
describe('Feature: Sample questions', () => {
  const cases: [question: string, tool: string, args: Record<string, unknown>, expected: RegExp][] = [
    ['Show me all Flamengo vs Fluminense matches', 'search_matches', { team: 'Flamengo', opponent: 'Fluminense' }, /Found \d+ matches:\n- \d{4}-\d{2}-\d{2}: (Flamengo|Fluminense) \d+-\d+ (Flamengo|Fluminense) \(/],
    ['What matches did Palmeiras play in 2023?', 'search_matches', { team: 'Palmeiras', season: 2023 }, /Found \d+ matches:[\s\S]*Palmeiras/],
    ['Find all Copa do Brasil finals', 'search_matches', { competition: 'Copa do Brasil', stage: 'final', limit: 50 }, /2015-12-02: Palmeiras 2-1 Santos \(Copa do Brasil 2015, final\)/],
    ["What is Corinthians' home record in 2022?", 'team_stats', { team: 'Corinthians', season: 2022, competition: 'Brasileirão', venue: 'home' }, /Corinthians home record \(2022 Brasileirão Série A\):\n- Matches: 19\n- Wins: \d+, Draws: \d+, Losses: \d+\n- Goals For: \d+, Goals Against: \d+[^\n]*\n- Points: \d+\n- Win rate: \d+\.\d%/],
    ['Which team scored the most goals in Serie A 2019?', 'rank_teams', { metric: 'goalsFor', competition: 'Serie A', season: 2019 }, /1\. Flamengo .* goals 86-37/],
    ['Compare Palmeiras and Santos head-to-head', 'head_to_head', { team_a: 'Palmeiras', team_b: 'Santos' }, /Palmeiras vs Santos \(Clássico da Saudade\)[\s\S]*Palmeiras \d+ wins, Santos \d+ wins, \d+ draws/],
    ['Find all Brazilian players in the dataset', 'search_players', { nationality: 'Brazil' }, /Found 827 players[\s\S]*1\. Neymar Jr - Overall: 92, Potential: 93, Position: LW/],
    ['Who are the highest-rated players at Grêmio?', 'search_players', { club: 'Grêmio', limit: 5 }, /Found 20 players[\s\S]*Club: Grêmio/],
    ['Show me all forwards from São Paulo FC', 'search_players', { club: 'São Paulo FC', position: 'forward' }, /No players found.*absent/],
    ['Show me all forwards from Santos', 'search_players', { club: 'Santos', position: 'forward' }, /Position: ST.*Club: Santos,/],
    ['Brazilian players at Brazilian clubs', 'brazilian_club_squads', { nationality: 'Brazil' }, /- Santos: \d+ players \(avg rating: \d+\.\d\)/],
    ['Who won the 2019 Brasileirão?', 'standings', { season: 2019 }, /2019 Brasileirão Série A Final Standings \(calculated from matches\):\n1\. Flamengo - 90 pts \(28W, 6D, 4L\).* - Champion\n2\. Santos - 74 pts \(22W, 8D, 8L\)/],
    ['Show the 2018 Copa Libertadores bracket', 'competition_knockout', { competition: 'Libertadores', season: 2018 }, /semifinals \(4 matches\)[\s\S]*Champion: River Plate \(5-3 on aggregate/],
    ['Which teams were relegated in 2020?', 'standings', { season: 2020 }, /17\. Vasco .* - Relegated\n18\. Goiás .* - Relegated\n19\. Coritiba .* - Relegated\n20\. Botafogo .* - Relegated/],
    ['Who won the 2021 Copa do Brasil?', 'competition_knockout', { competition: 'Copa do Brasil', season: 2021 }, /Champion: Atlético-MG \(6-1 on aggregate/],
    ["What's the average goals per match in the Brasileirão?", 'league_stats', { competition: 'Brasileirão' }, /Average goals per match: 2\.\d\d\n- Home win rate: \d\d\.\d%/],
    ['Which team has the best away record?', 'rank_teams', { venue: 'away', competition: 'Brasileirão', min_matches: 100 }, /Teams ranked by away win rate[\s\S]*\n1\. .+ - \d+\.\d% wins/],
    ['Which team has the best home record?', 'rank_teams', { venue: 'home', competition: 'Brasileirão', season: 2019 }, /Teams ranked by home win rate[\s\S]*\n1\. Flamengo/],
    ['Show me the biggest wins in the dataset', 'biggest_wins', {}, /Biggest victories \(all competitions\):\n1\. 2021-06-08: São Paulo 9-1 4 de Julho/],
    ['When did Flamengo last play Corinthians? What was the score?', 'search_matches', { team: 'Flamengo', opponent: 'Corinthians', limit: 1 }, /- 2023-10-08: Corinthians 1-1 Flamengo/],
    ['Who is Neymar?', 'player_profile', { name: 'Neymar' }, /Neymar Jr \(FIFA ID 190871\)[\s\S]*Overall: 92, Potential: 93[\s\S]*Best skills: /],
    ['Who is Gabriel Barbosa? (not in the FIFA file)', 'player_profile', { name: 'Gabriel Barbosa' }, /No player matching "Gabriel Barbosa".*Closest by partial name: Gabriel Jesus/],
    ['Which players play for Fluminense?', 'search_players', { club: 'Fluminense' }, /Found 20 players/],
    ['Show me all derbies in 2023', 'find_derbies', { season: 2023 }, /Derbies \(2023\): \d+ matches\n- .+: 2023-/],
    ['What competitions has Palmeiras played in?', 'team_overview', { team: 'Palmeiras' }, /Brasileirão Série A \([\d, -]+\): \d+ matches[\s\S]*Copa do Brasil[\s\S]*Copa Libertadores/],
    ['Tell me about Santos and its players (cross-file)', 'team_overview', { team: 'Santos' }, /Copa Libertadores[\s\S]*FIFA squad: 20 players \(avg rating: \d+\.\d\)/],
    ['Who are the top Brazilian players?', 'search_players', { nationality: 'Brazil', limit: 3 }, /1\. Neymar Jr[\s\S]*\.\.\. \(824 more players\)/],
    ['Compare the 2018 and 2019 seasons', 'compare_seasons', { season_a: 2018, season_b: 2019 }, /2018:[\s\S]*Most points: Palmeiras \(80 pts[\s\S]*2019:[\s\S]*Most points: Flamengo \(90 pts/],
    ['What data is available?', 'dataset_info', {}, /fifa_data\.csv: 18207[\s\S]*Copa Libertadores: \d+ matches, seasons 2013-2022/],
  ];

  it('covers at least 20 questions', () => expect(cases.length).toBeGreaterThanOrEqual(20));

  it.each(cases)('Scenario: %s', (_question, tool, args, expected) => {
    expect(ask(tool, args)).toMatch(expected);
  });

  it('Scenario: nothing found is reported plainly', () => {
    expect(ask('search_matches', { team: 'Flamengo', season: 1950 })).toBe('No matches found for those criteria in the dataset.');
    expect(ask('standings', { season: 1999 })).toMatch(/No Brasileirão Série A matches for 1999.*Seasons available: 2003-2023/);
  });

  it('Scenario: long result lists are truncated with a count of the remainder', () => {
    const out = ask('search_matches', { team: 'Flamengo', limit: 2 });
    expect(out.split('\n')).toHaveLength(4);
    expect(out).toMatch(/\.\.\. \(\d+ more matches in dataset\)$/);
  });
});

describe('Feature: Query performance', () => {
  const timed = (fn: () => unknown) => {
    const start = performance.now();
    fn();
    return performance.now() - start;
  };

  it('Scenario: simple lookups respond in under 2 seconds', () => {
    expect(timed(() => ask('search_matches', { team: 'Flamengo', opponent: 'Corinthians' }))).toBeLessThan(2000);
    expect(timed(() => ask('player_profile', { name: 'Neymar' }))).toBeLessThan(2000);
  });

  it('Scenario: aggregate queries respond in under 5 seconds', () => {
    expect(timed(() => ask('rank_teams', { venue: 'away' }))).toBeLessThan(5000);
    expect(timed(() => ask('standings', { season: 2019 }))).toBeLessThan(5000);
    expect(timed(() => ask('biggest_wins', {}))).toBeLessThan(5000);
  });
});
