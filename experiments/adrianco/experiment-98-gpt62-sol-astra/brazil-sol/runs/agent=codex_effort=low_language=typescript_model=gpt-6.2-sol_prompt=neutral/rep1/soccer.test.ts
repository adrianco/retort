import assert from 'node:assert/strict';
import { fileURLToPath } from 'node:url';
import { after, before, describe, it } from 'node:test';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { CallToolResultSchema } from '@modelcontextprotocol/sdk/types.js';
import { dateOnly, teamName } from './data.js';
import type { SoccerGraph } from './soccer.js';

const client = new Client({ name: 'soccer-test', version: '1.0.0' });
const transport = new StdioClientTransport({
  command: process.execPath,
  args: [fileURLToPath(new URL('./index.js', import.meta.url))],
});
const tools = {
  data_coverage: 'coverage',
  search_matches: 'matches',
  team_stats: 'teamStats',
  head_to_head: 'headToHead',
  search_players: 'players',
  standings: 'standings',
  competition_results: 'competitionResults',
  match_statistics: 'statistics',
  club_profile: 'clubProfile',
} as const satisfies Record<string, keyof SoccerGraph>;

async function ask<T extends keyof typeof tools>(name: T, args: Record<string, unknown> = {}, timeout = 2000) {
  const start = performance.now();
  const result = await client.callTool({ name, arguments: args }, CallToolResultSchema, { timeout });
  assert.ok(performance.now() - start < timeout, `${name} exceeded ${timeout} ms`);
  const [content] = CallToolResultSchema.parse(result).content;
  assert.equal(content?.type, 'text');
  assert.ok(!result.isError, content.text);
  return JSON.parse(content.text) as ReturnType<SoccerGraph[(typeof tools)[T]]>;
}

describe('Given the six soccer datasets and a connected MCP client', () => {
  before(() => client.connect(transport));
  after(() => client.close());

  it('lists every tool and reports all six source counts', async () => {
    const { tools: registered } = await client.listTools();
    assert.deepEqual(registered.map(tool => tool.name).sort(), Object.keys(tools).sort());
    const coverage = await ask('data_coverage');
    assert.deepEqual(coverage.sources.map(({ rows }) => rows), [4180, 6886, 1337, 1255, 10296, 18207]);
    assert.equal(coverage.competitions.find(c => c.key === 'league')?.seasons[0], 2003);
  });

  it('answers “Show me Flamengo vs Fluminense” with both venues, scores and records', async () => {
    const result = await ask('head_to_head', { team: 'Flamengo-RJ', opponent: 'Fluminense Football Club' });
    assert.ok(result.total > 20);
    assert.deepEqual(result.teams.map(row => row.team).sort(), ['Flamengo', 'Fluminense']);
    assert.equal(result.teams[0].wins, result.teams[1].losses);
    assert.equal(result.teams[0].draws, result.teams[1].draws);
    assert.ok(result.items.some(match => match.home === 'Flamengo'));
    assert.ok(result.items.some(match => match.home === 'Fluminense'));
    assert.ok(result.items.every(match => match.date && match.competition && match.homeGoals !== null && match.awayGoals !== null));
  });

  it('answers “What matches did Palmeiras play in 2023?”', async () => {
    const result = await ask('search_matches', { team: 'Sociedade Esportiva Palmeiras', season: 2023 });
    assert.ok(result.total >= 37);
    assert.ok(result.items.every(match => match.season === 2023 && [match.home, match.away].includes('Palmeiras')));
  });

  it('answers “When did Flamengo last play Corinthians and what was the score?”', async () => {
    const { items: [match] } = await ask('search_matches', {
      team: 'Flamengo', opponent: 'Sport Club Corinthians Paulista', limit: 1,
    });
    assert.deepEqual([match.date, match.homeGoals, match.awayGoals], ['2023-10-08', 1, 1]);
  });

  it('answers “Find all Copa do Brasil finals” without counting semifinals as finals', async () => {
    const result = await ask('search_matches', { competition: 'Copa do Brasil', stage: 'finals', limit: 100 });
    assert.equal(result.total, 24);
    assert.equal(result.items.filter(match => match.season === 2021).length, 2);
    assert.equal(result.items.filter(match => match.season === 2020 && match.date?.startsWith('2021')).length, 2);
    assert.ok(result.items.every(match => match.stage === 'final'));
  });

  it('finds historical games by inclusive Brazilian and ISO dates and includes stadiums', async () => {
    const { items } = await ask('search_matches', { source: 'historical', from: '29/03/2003', to: '2003-03-29' });
    assert.equal(items.length, 2);
    assert.ok(items.every(match => match.date === '2003-03-29' && match.stadium));
  });

  it('finds shot and corner statistics in the extended feed', async () => {
    const { items: [match] } = await ask('search_matches', {
      source: 'extended', competition: 'Copa do Brasil', from: '2023-09-24', to: '2023-09-24',
    });
    assert.equal(match.statistics?.home_shots, 8);
    assert.equal(match.statistics?.total_corners, 6);
  });

  it('finds round one in the standalone Série A file', async () => {
    const result = await ask('search_matches', { source: 'league', season: 2012, round: 1 });
    assert.equal(result.total, 10);
    assert.ok(result.items.every(match => match.round === 1 && match.sources.join() === 'league'));
  });

  it('returns unscored cup fixtures as null scores', async () => {
    const result = await ask('search_matches', { source: 'cup', season: 2021, status: 'unscored' });
    assert.ok(result.total > 0);
    assert.ok(result.items.every(match => match.homeGoals === null && match.awayGoals === null));
  });

  it('answers “Show me all derbies in 2023” with stable pagination', async () => {
    const filters = { derby: true, season: 2023, limit: 2 };
    const first = await ask('search_matches', filters);
    const second = await ask('search_matches', { ...filters, offset: first.nextOffset });
    assert.equal(first.total, second.total);
    assert.ok(first.total > 20);
    assert.equal(second.offset, 2);
    assert.notDeepEqual(first.items, second.items);
  });

  it('answers “What is Corinthians’ Série A home record in 2022?”', async () => {
    const result = await ask('team_stats', { team: 'Corinthians-SP', competition: 'Série A', season: 2022, venue: 'home' }, 5000);
    const { played, wins, draws, losses, goalsFor, goalsAgainst } = result.overall;
    assert.deepEqual([played, wins, draws, losses, goalsFor, goalsAgainst], [19, 12, 4, 3, 24, 11]);
    assert.equal(result.away.played, 0);
    assert.equal(result.home.winRate, 0.6316);
  });

  it('answers “What competitions has Palmeiras played in?”', async () => {
    const result = await ask('team_stats', { team: 'Palmeiras' }, 5000);
    assert.deepEqual(result.competitions.map(row => row.competition).sort(), ['cup', 'league', 'libertadores']);
    assert.equal(result.overall.goalsFor, result.home.goalsFor + result.away.goalsFor);
    assert.equal(result.seasons.length, 20);
  });

  it('answers “Compare Palmeiras and Santos head-to-head”', async () => {
    const result = await ask('head_to_head', { team: 'Palmeiras', opponent: 'Santos FC', season: 2022 });
    assert.equal(result.total, 2);
    assert.equal(result.teams.find(row => row.team === 'Palmeiras')?.wins, 2);
  });

  it('answers “Who are the top Brazilian players?” and exposes FIFA skills', async () => {
    const result = await ask('search_players', { nationality: 'Brazilian', limit: 3 });
    assert.equal(result.total, 827);
    assert.equal(result.items[0].name, 'Neymar Jr');
    assert.equal(result.items[0].overall, 92);
    assert.ok(result.items[0].attributes.Dribbling);
    assert.ok(result.items.every(player => player.nationality === 'Brazil'));
  });

  it('finds a player by name regardless of accents and case', async () => {
    const result = await ask('search_players', { name: 'jOsUe Chiamulera' });
    assert.equal(result.total, 1);
    assert.equal(result.items[0].name, 'Josué Chiamulera');
  });

  it('returns an empty search for Gabriel Barbosa and clubs missing from the FIFA file', async () => {
    assert.equal((await ask('search_players', { name: 'Gabriel Barbosa' })).total, 0);
    assert.equal((await ask('search_players', { club: 'Flamengo-RJ' })).total, 0);
    assert.equal((await ask('search_players', { club: 'São Paulo FC', position: 'forwards' })).total, 0);
  });

  it('answers “Show forwards at Grêmio” using the FIFA positional codes', async () => {
    const result = await ask('search_players', { club: 'Gremio-RS', position: 'forwards' });
    assert.ok(result.total > 0);
    assert.ok(result.items.every(player => player.club === 'Grêmio' && ['CF', 'ST', 'LW', 'RW', 'LF', 'RF', 'LS', 'RS'].includes(player.position)));
  });

  it('groups Brazilian players at Brazilian clubs and calculates average ratings', async () => {
    const result = await ask('search_players', { nationality: 'Brasil', brazilianClub: true, limit: 100 });
    const club = result.byClub.items.find(row => row.club === 'Grêmio');
    assert.equal(club?.players, 20);
    assert.ok(club.averageOverall && club.averageOverall > 60);
    assert.ok(result.items.every(player => player.club !== 'Paris Saint-Germain'));
  });

  it('joins a club’s match history with its FIFA roster', async () => {
    const result = await ask('club_profile', { team: 'Gremio-RS', season: 2023, nationality: 'Brazil' }, 5000);
    assert.equal(result.fifaRoster.total, 20);
    assert.ok(result.recentMatches.items.every(match => match.season === 2023));
    assert.ok(result.recentMatches.items.length > 0);
    assert.ok(result.fifaRoster.items.every(p => p.club === 'Grêmio'));
  });

  it('answers “Who won the 2019 Brasileirão?” using 380 distinct fixtures', async () => {
    const result = await ask('standings', { competition: 'Brasileirão', season: 2019 }, 5000);
    assert.equal(result.scoredMatches, 380);
    assert.equal(result.completeDoubleRoundRobin, true);
    assert.equal(result.calculatedWinner, 'Flamengo');
    const { points, wins, draws, losses } = result.standings[0];
    assert.deepEqual([points, wins, draws, losses], [90, 28, 6, 4]);
  });

  it('answers “Which teams were relegated in 2020?”', async () => {
    const result = await ask('standings', { competition: 'league', season: 2020 }, 5000);
    assert.deepEqual(result.relegationPlaces, ['Vasco da Gama', 'Goiás', 'Coritiba', 'Botafogo-RJ']);
  });

  it('flags incomplete standings and ranks 2023 goals from recorded matches', async () => {
    const table = await ask('standings', { competition: 'league', season: 2023 }, 5000);
    assert.equal(table.scoredMatches, 377);
    assert.equal(table.expectedMatches, 380);
    assert.equal(table.calculatedWinner, null);
    const { rankings } = await ask('match_statistics', { competition: 'league', season: 2023, rankBy: 'goalsFor' }, 5000);
    assert.equal(rankings.items[0].team, 'Grêmio');
    assert.equal(rankings.items[0].goalsFor, 63);
  });

  it('answers “Show the 2018 Libertadores bracket” and reports scorer availability', async () => {
    const result = await ask('competition_results', { competition: 'Libertadores', season: 2018, stage: 'knockout' });
    assert.deepEqual(result.stages.map(row => row.fixtures), [16, 8, 4, 2]);
    assert.equal(result.items.length, 30);
    assert.equal(result.topScorersAvailable, false);
    assert.ok(result.items.every(match => match.sources.includes('libertadores')));
  });

  it('exposes the undated 2022 Libertadores final without inventing its score', async () => {
    const { items } = await ask('competition_results', { competition: 'Libertadores', season: 2022, stage: 'final' });
    assert.equal(items.length, 1);
    assert.deepEqual([items[0].home, items[0].away, items[0].date, items[0].homeGoals],
      ['Flamengo', 'Athletico Paranaense', null, null]);
  });

  it('keeps Santos and Santos Laguna rosters distinct', async () => {
    const brazilian = await ask('search_players', { club: 'Santos FC', limit: 100 });
    const mexican = await ask('search_players', { club: 'Santos Laguna', limit: 100 });
    assert.ok(brazilian.total > 0);
    assert.ok(mexican.total > 0);
    assert.ok(brazilian.items.every(player => player.club === 'Santos'));
    assert.ok(mexican.items.every(player => player.club === 'Santos Laguna'));
  });

  it('answers “Compare the 2018 and 2019 seasons” with goals per match', async () => {
    const result = await ask('match_statistics', { competition: 'Brasileirão', seasons: [2018, 2019] }, 5000);
    assert.deepEqual(result.seasons.map(row => [row.season, row.played]), [[2018, 380], [2019, 380]]);
    assert.equal(result.homeWins + result.awayWins + result.draws, 760);
    assert.equal(result.averageGoals, Number((result.goals / 760).toFixed(4)));
  });

  it('ranks home and away performance and finds the biggest wins', async () => {
    const home = await ask('match_statistics', { rankVenue: 'home', minMatches: 19, limit: 3 }, 5000);
    const away = await ask('match_statistics', { rankVenue: 'away', minMatches: 19, limit: 3 }, 5000);
    assert.ok(home.homeWinRate! > away.awayWinRate!);
    assert.ok(away.rankings.items.every(row => row.played >= 19));
    assert.ok(home.biggestWins.items[0].margin >= 7);
    assert.ok(home.biggestWins.items[0].margin >= home.biggestWins.items[1].margin);
  });

  it('returns tool errors for invalid dates, venue filters and page sizes', async () => {
    for (const args of [{ from: '31/02/2023' }, { venue: 'home' }, { limit: 0 }]) {
      const result = await client.callTool({ name: 'search_matches', arguments: args }, CallToolResultSchema);
      assert.equal(result.isError, true);
    }
  });
});

it('preserves distinct clubs with the same base name and validates dates', () => {
  assert.equal(teamName('Atletico - MG'), 'Atlético Mineiro');
  assert.equal(teamName('Atlético-PR'), 'Athletico Paranaense');
  assert.notEqual(teamName('Botafogo - PB'), teamName('Botafogo - RJ'));
  assert.notEqual(teamName('América - RN'), teamName('América - MG'));
  assert.equal(dateOnly('2012-05-19 18:30:00'), '2012-05-19');
  assert.equal(dateOnly('29/02/2020'), '2020-02-29');
  assert.equal(dateOnly('29/02/2021'), null);
});
