/**
 * Protocol driver: talks to the Brazilian Soccer MCP server exactly as an
 * LLM host would — launching it over stdio and calling its tools.
 *
 * This is the only place in the acceptance tests that knows the system is an
 * MCP server, what its tools are called, and the shape of their answers.
 * Assertions live here, failing with messages in domain language.
 */
import { existsSync, rmSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { join, resolve } from 'node:path';
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import type {
  ExpectedMatch, ExpectedStandingsRow, ExpectedTie, MatchCriteria, MatchRecord, PlayerCriteria, PlayerRecord,
  RankingCriteria, RecordCriteria, SoccerDriver,
} from '../soccer-driver.js';
import { writeDatasets } from './dataset-writer.js';

const PROJECT_ROOT = resolve(fileURLToPath(new URL('../../../../', import.meta.url)));
const SERVER_ENTRY = join(PROJECT_ROOT, 'dist', 'src', 'index.js');
const PROVIDED_DATA = join(PROJECT_ROOT, 'data', 'kaggle');

/* eslint-disable @typescript-eslint/no-explicit-any */
type Json = any;

interface Answer {
  tool: string;
  text: string;
  data: Json;
  isError: boolean;
}

function fail(message: string): never {
  throw new Error(message);
}

function pct(rate: number): string {
  return `${rate.toFixed(1)}%`;
}

function describeMatch(m: Json): string {
  return `${m.date} ${m.home} ${m.homeGoals}-${m.awayGoals} ${m.away}`;
}

function describeExpected(m: ExpectedMatch): string {
  return `${m.date} ${m.home} ${m.homeGoals}-${m.awayGoals} ${m.away}`;
}

function checkFigures(what: string, actual: Json, expected: Record<string, unknown>): void {
  const wrong = Object.entries(expected)
    .filter(([, v]) => v !== undefined)
    .filter(([k, v]) => actual?.[k] !== v)
    .map(([k, v]) => `${k}: expected ${JSON.stringify(v)} but was ${JSON.stringify(actual?.[k])}`);
  if (wrong.length) fail(`${what} was not as expected —\n  ${wrong.join('\n  ')}`);
}

export class McpSoccerDriver implements SoccerDriver {
  private readonly matches: MatchRecord[] = [];
  private readonly players: PlayerRecord[] = [];
  private client: Client | undefined;
  private dataDir: string | undefined;
  private answer: Answer | undefined;

  private constructor(private readonly useProvidedData: boolean) {}

  static withSyntheticData(): McpSoccerDriver {
    return new McpSoccerDriver(false);
  }

  static withProvidedData(): McpSoccerDriver {
    return new McpSoccerDriver(true);
  }

  // ---------------------------------------------------------------- world

  recordMatch(match: MatchRecord): void {
    this.ensureWorldIsOpen();
    this.matches.push(match);
  }

  recordPlayer(player: PlayerRecord): void {
    this.ensureWorldIsOpen();
    this.players.push(player);
  }

  private ensureWorldIsOpen(): void {
    if (this.useProvidedData) fail('Specs using the provided datasets cannot add their own matches or players');
    if (this.client) fail('Matches and players must be described before the first question is asked');
  }

  async start(): Promise<void> {
    if (this.client) return;
    if (!existsSync(SERVER_ENTRY)) fail(`The server has not been built — run "npm run build" (missing ${SERVER_ENTRY})`);
    this.dataDir = this.useProvidedData ? PROVIDED_DATA : writeDatasets(this.matches, this.players);
    const transport = new StdioClientTransport({
      command: process.execPath,
      args: [SERVER_ENTRY, '--data-dir', this.dataDir],
      stderr: 'pipe',
    });
    const client = new Client({ name: 'acceptance-tests', version: '1.0.0' });
    await client.connect(transport);
    this.client = client;
  }

  async close(): Promise<void> {
    await this.client?.close();
    this.client = undefined;
    if (!this.useProvidedData && this.dataDir) rmSync(this.dataDir, { recursive: true, force: true });
  }

  private async ask(tool: string, args: Record<string, unknown>): Promise<void> {
    await this.start();
    const cleanArgs = Object.fromEntries(Object.entries(args).filter(([, v]) => v !== undefined));
    const result: Json = await this.client!.callTool({ name: tool, arguments: cleanArgs });
    const text = (result.content ?? []).filter((c: Json) => c.type === 'text').map((c: Json) => c.text).join('\n');
    this.answer = { tool, text, data: result.structuredContent ?? {}, isError: Boolean(result.isError) };
  }

  private answered(): Answer {
    if (!this.answer) fail('No question has been asked yet');
    if (this.answer.isError) fail(`The question was not answered: ${this.answer.text}`);
    return this.answer;
  }

  // -------------------------------------------------------------- matches

  async findMatches(criteria: MatchCriteria): Promise<void> {
    await this.ask('search_matches', { ...criteria, date_from: criteria.from, date_to: criteria.to, from: undefined, to: undefined, limit: 500 });
  }

  async findLastMeeting(team: string, opponent: string): Promise<void> {
    await this.ask('search_matches', { team, opponent, limit: 1 });
  }

  async findFinals(competition: string, season?: number): Promise<void> {
    await this.ask('cup_finals', { competition, season });
  }

  async findDerbies(season?: number): Promise<void> {
    await this.ask('find_derbies', { season });
  }

  confirmMatchesFound(expected: ExpectedMatch[]): void {
    const found: Json[] = this.answered().data.matches ?? [];
    const actual = found.map(describeMatch);
    const wanted = expected.map(describeExpected);
    if (JSON.stringify(actual) !== JSON.stringify(wanted)) {
      fail(`Expected to find these matches:\n  ${wanted.join('\n  ') || '(none)'}\nbut found:\n  ${actual.join('\n  ') || '(none)'}`);
    }
  }

  confirmMatchPresentedAs(line: string): void {
    const { text } = this.answered();
    if (!text.includes(line)) fail(`Expected the answer to present "${line}" but it said:\n${text}`);
  }

  confirmMatchStatistics(expected: { corners?: [number, number]; shots?: [number, number] }): void {
    const match = this.answered().data.matches?.[0];
    if (!match) fail('Expected a match with statistics but no match was found');
    for (const [stat, value] of Object.entries(expected)) {
      if (!value) continue;
      const actual = match.stats?.[stat];
      if (actual?.home !== value[0] || actual?.away !== value[1]) {
        fail(`Expected ${stat} ${value[0]}-${value[1]} but the answer gave ${actual ? `${actual.home}-${actual.away}` : 'none'}`);
      }
    }
  }

  confirmFinals(expected: ExpectedTie[]): void {
    const finals: Json[] = this.answered().data.finals ?? [];
    const describe = (t: { season?: number; winner: string; loser: string; winnerGoals: number; loserGoals: number }) =>
      `${t.season}: ${t.winner} beat ${t.loser} ${t.winnerGoals}-${t.loserGoals} on aggregate`;
    const actual = finals.map((f) => describe({ season: f.season, winner: f.winner, loser: f.runnerUp, winnerGoals: f.winnerGoals, loserGoals: f.runnerUpGoals }));
    const wanted = expected.map(describe);
    if (JSON.stringify(actual) !== JSON.stringify(wanted)) {
      fail(`Expected these finals:\n  ${wanted.join('\n  ')}\nbut found:\n  ${actual.join('\n  ') || '(none)'}`);
    }
  }

  confirmDerbyNamed(name: string): void {
    const derbies = (this.answered().data.matches ?? []).map((m: Json) => m.derby);
    if (!derbies.includes(name)) fail(`Expected one of the derbies to be the ${name}, but they were: ${derbies.join(', ') || '(none)'}`);
  }

  confirmTeamNotRecognised(name: string): void {
    const answer = this.answer ?? fail('No question has been asked yet');
    if (!answer.isError) fail(`Expected "${name}" not to be recognised as a team, but the answer was:\n${answer.text}`);
    if (!answer.text.includes(name)) fail(`Expected the answer to say it did not recognise "${name}", but it said: ${answer.text}`);
  }

  // ---------------------------------------------------------------- teams

  async requestRecord(criteria: RecordCriteria): Promise<void> {
    await this.ask('team_record', { ...criteria });
  }

  confirmRecord(expected: Record<string, number | string | undefined>): void {
    const record = this.answered().data;
    const { winRate, ...figures } = expected;
    checkFigures(`${record.team}'s record`, record, figures);
    if (winRate !== undefined && pct(record.winRate) !== winRate) fail(`Expected a win rate of ${winRate} but it was ${pct(record.winRate)}`);
  }

  async compareHeadToHead(team: string, opponent: string): Promise<void> {
    await this.ask('head_to_head', { team, opponent });
  }

  confirmHeadToHead(expected: Record<string, number | undefined>): void {
    const h2h = this.answered().data;
    checkFigures(`The head-to-head between ${h2h.team} and ${h2h.opponent}`, h2h, expected);
  }

  async requestCompetitions(team: string): Promise<void> {
    await this.ask('team_competitions', { team });
  }

  confirmCompetitions(expected: string[]): void {
    const actual: string[] = (this.answered().data.competitions ?? []).map((c: Json) => c.competition);
    if (JSON.stringify([...actual].sort()) !== JSON.stringify([...expected].sort())) {
      fail(`Expected competitions ${expected.join(', ')} but found ${actual.join(', ') || '(none)'}`);
    }
  }

  confirmCompetitionRecord(expected: { competition: string } & Record<string, unknown>): void {
    const { competition, ...figures } = expected;
    const record = (this.answered().data.competitions ?? []).find((c: Json) => c.competition === competition);
    if (!record) fail(`Expected a record in the ${competition} but there was none`);
    checkFigures(`The record in the ${competition}`, record, figures);
  }

  async rankTeams(criteria: RankingCriteria): Promise<void> {
    await this.ask('team_rankings', { ...criteria });
  }

  confirmLeader(expected: { team: string; goalsFor?: number; winRate?: string }): void {
    const leader = this.answered().data.rankings?.[0];
    if (!leader) fail('Expected a ranking of teams but none was given');
    if (leader.team !== expected.team) fail(`Expected ${expected.team} to be top of the ranking but it was ${leader.team}`);
    if (expected.goalsFor !== undefined && leader.goalsFor !== expected.goalsFor) {
      fail(`Expected ${expected.team} to have scored ${expected.goalsFor} goals but they scored ${leader.goalsFor}`);
    }
    if (expected.winRate !== undefined && pct(leader.winRate) !== expected.winRate) {
      fail(`Expected ${expected.team} to have a win rate of ${expected.winRate} but it was ${pct(leader.winRate)}`);
    }
  }

  // -------------------------------------------------------------- players

  async lookUpPlayer(name: string): Promise<void> {
    await this.ask('get_player', { name });
  }

  private foundPlayer(): Json {
    const data = this.answered().data;
    if (!data.found) fail(`Expected to find the player but the answer was: ${this.answer!.text}`);
    return data.player;
  }

  confirmPlayer(expected: Record<string, unknown>): void {
    const player = this.foundPlayer();
    checkFigures(`The player found (${player.name})`, player, expected);
  }

  confirmSkills(expected: Record<string, number>): void {
    const player = this.foundPlayer();
    checkFigures(`${player.name}'s skills`, player.skills, expected);
  }

  confirmPlayerNotFound(suggesting: string): void {
    const data = this.answered().data;
    if (data.found) fail(`Expected no player to be found but found ${data.player.name}`);
    if (!(data.suggestions ?? []).includes(suggesting)) {
      fail(`Expected ${suggesting} to be suggested but the suggestions were: ${(data.suggestions ?? []).join(', ') || '(none)'}`);
    }
  }

  async searchPlayers(criteria: PlayerCriteria): Promise<void> {
    await this.ask('search_players', { ...criteria });
  }

  confirmPlayersListed(expected: string[], inAnyOrder: boolean): void {
    const actual: string[] = (this.answered().data.players ?? []).map((p: Json) => p.name);
    const same = inAnyOrder
      ? JSON.stringify([...actual].sort()) === JSON.stringify([...expected].sort())
      : JSON.stringify(actual) === JSON.stringify(expected);
    if (!same) fail(`Expected players ${expected.join(', ')} but found ${actual.join(', ') || '(none)'}`);
  }

  async summariseClubsForNationality(nationality: string): Promise<void> {
    await this.ask('brazilian_club_squads', { nationality });
  }

  confirmClubSummary(expected: { club: string; players?: number; averageRating?: number }): void {
    const { club, ...figures } = expected;
    const summary = (this.answered().data.clubs ?? []).find((c: Json) => c.club === club);
    if (!summary) fail(`Expected ${club} in the summary of Brazilian clubs but it was missing`);
    checkFigures(`The summary for ${club}`, summary, figures);
  }

  confirmClubNotInSummary(club: string): void {
    const clubs: string[] = (this.answered().data.clubs ?? []).map((c: Json) => c.club);
    if (clubs.includes(club)) fail(`Expected ${club} not to be summarised as a Brazilian club`);
  }

  // --------------------------------------------------------- competitions

  async requestStandings(competition: string, season: number): Promise<void> {
    await this.ask('standings', { competition, season });
  }

  confirmStandings(expected: ExpectedStandingsRow[], wholeTable: boolean): void {
    const table: Json[] = this.answered().data.table ?? [];
    const describe = (r: ExpectedStandingsRow) => `${r.position}. ${r.team} - ${r.points} pts (${r.won}W, ${r.drawn}D, ${r.lost}L)`;
    const actual = (wholeTable ? table : table.slice(0, expected.length)).map(describe);
    const wanted = expected.map(describe);
    if (JSON.stringify(actual) !== JSON.stringify(wanted)) {
      fail(`Expected the table to read:\n  ${wanted.join('\n  ')}\nbut it read:\n  ${actual.join('\n  ') || '(empty)'}`);
    }
  }

  confirmChampion(team: string): void {
    const champion = this.answered().data.champion;
    if (champion !== team) fail(`Expected ${team} to be champion but it was ${champion ?? 'nobody'}`);
  }

  confirmTeamsInTable(teams: string[]): void {
    const actual: string[] = (this.answered().data.table ?? []).map((r: Json) => r.team);
    if (JSON.stringify(actual) !== JSON.stringify(teams)) fail(`Expected the table to list ${teams.join(', ')} but it listed ${actual.join(', ')}`);
  }

  confirmSeasonIncomplete(matchesMissing: number): void {
    const standings = this.answered().data;
    if (standings.complete !== false) fail('Expected the season to be reported as incomplete but it was reported as complete');
    if (standings.missingMatches !== matchesMissing) {
      fail(`Expected ${matchesMissing} matches to be reported missing but ${standings.missingMatches} were`);
    }
    if (standings.champion) fail(`Expected no champion for an incomplete season but ${standings.champion} was named`);
  }

  confirmRelegated(teams: string[]): void {
    const relegated: string[] = this.answered().data.relegated ?? [];
    if (JSON.stringify(relegated) !== JSON.stringify(teams)) {
      fail(`Expected ${teams.join(', ')} to be relegated but it was ${relegated.join(', ') || 'nobody'}`);
    }
  }

  async requestBracket(competition: string, season: number): Promise<void> {
    await this.ask('knockout_bracket', { competition, season });
  }

  confirmTie(stage: string, expected: ExpectedTie): void {
    const round = (this.answered().data.stages ?? []).find((s: Json) => s.stage === stage);
    if (!round) fail(`Expected the bracket to include the ${stage} but it did not`);
    const tie = round.ties.find((t: Json) => t.winner === expected.winner && t.loser === expected.loser);
    if (!tie) fail(`Expected ${expected.winner} to beat ${expected.loser} in the ${stage}`);
    if (tie.winnerGoals !== expected.winnerGoals || tie.loserGoals !== expected.loserGoals) {
      fail(`Expected ${expected.winner} to win ${expected.winnerGoals}-${expected.loserGoals} on aggregate but it was ${tie.winnerGoals}-${tie.loserGoals}`);
    }
  }

  // ----------------------------------------------------------- statistics

  async summariseCompetition(competition?: string, season?: number): Promise<void> {
    await this.ask('competition_stats', { competition, season });
  }

  confirmSummary(expected: { matches?: number; averageGoals?: number; homeWinRate?: string; drawRate?: string; awayWinRate?: string }): void {
    const stats = this.answered().data;
    const { matches, averageGoals, ...rates } = expected;
    checkFigures('The competition summary', stats, { matches, averageGoals });
    for (const [rate, value] of Object.entries(rates)) {
      if (value !== undefined && pct(stats[rate]) !== value) fail(`Expected ${rate} of ${value} but it was ${pct(stats[rate])}`);
    }
  }

  async findBiggestWins(limit: number, competition?: string): Promise<void> {
    await this.ask('biggest_wins', { limit, competition });
  }

  confirmBiggestWins(expected: ExpectedMatch[]): void {
    this.confirmMatchesFound(expected);
  }

  async compareSeasons(seasons: number[], competition: string): Promise<void> {
    await this.ask('compare_seasons', { seasons, competition });
  }

  confirmSeason(expected: { season: number; matches?: number; averageGoals?: number; champion?: string }): void {
    const { season, ...figures } = expected;
    const summary = (this.answered().data.seasons ?? []).find((s: Json) => s.season === season);
    if (!summary) fail(`Expected a summary of the ${season} season but there was none`);
    checkFigures(`The ${season} season`, summary, figures);
  }

  async profileTeam(team: string): Promise<void> {
    await this.ask('team_profile', { team });
  }

  confirmProfile(expected: { team?: string; played?: number; won?: number; squadSize?: number; bestPlayer?: string }): void {
    const profile = this.answered().data;
    checkFigures(`The profile of ${profile.team}`, {
      team: profile.team,
      played: profile.record?.played,
      won: profile.record?.won,
      squadSize: profile.squad?.size,
      bestPlayer: profile.squad?.players?.[0]?.name,
    }, expected);
  }

  // ---------------------------------------------------------- the datasets

  async requestDatasetOverview(): Promise<void> {
    await this.ask('dataset_info', {});
  }

  confirmDatasetLoaded(name: string, records: number): void {
    const dataset = (this.answered().data.datasets ?? []).find((d: Json) => d.name === name);
    if (!dataset) fail(`Expected the ${name} dataset to be loaded but it was not`);
    if (dataset.records !== records) fail(`Expected ${records} records in the ${name} dataset but there were ${dataset.records}`);
  }

  confirmLastQuestionAnswered(): void {
    const answer = this.answered();
    if (!answer.text.trim()) fail(`The ${answer.tool} answer was empty`);
  }
}
