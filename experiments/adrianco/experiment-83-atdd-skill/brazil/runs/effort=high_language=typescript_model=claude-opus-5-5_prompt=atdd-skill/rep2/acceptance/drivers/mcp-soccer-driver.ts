/**
 * Protocol driver: talks to the soccer knowledge system through its natural
 * interface – the Model Context Protocol over stdio, exactly as an LLM
 * client would. This is the only layer of the test infrastructure that
 * knows tool names, argument shapes and result structures.
 *
 * Every method passes or fails the test with a domain-language message.
 */
import { Client } from '@modelcontextprotocol/sdk/client/index.js';
import { StdioClientTransport } from '@modelcontextprotocol/sdk/client/stdio.js';
import { expect } from 'vitest';
import { SERVER_ENTRY } from './paths.js';
import type {
  MatchCriteria,
  PlayerCriteria,
  RankingMeasure,
  RecordCriteria,
  SoccerSystemDriver,
  StatisticsScope,
  SummaryExpectation,
  TeamProfileExpectation,
  TeamRecordExpectation,
} from './soccer-system-driver.js';

interface MatchView {
  date: string;
  competition: string;
  season: number;
  round?: number;
  stage?: string;
  homeTeam: string;
  awayTeam: string;
  homeGoals: number;
  awayGoals: number;
  derby?: string;
}

interface ToolAnswer<T> {
  data: T;
  text: string;
}

function line(m: MatchView): string {
  return `${m.date}: ${score(m)}`;
}

function score(m: MatchView): string {
  return `${m.homeTeam} ${m.homeGoals}-${m.awayGoals} ${m.awayTeam}`;
}

function defined<T extends object>(value: T): Partial<T> {
  return Object.fromEntries(Object.entries(value).filter(([, v]) => v !== undefined)) as Partial<T>;
}

function matchArguments(c: MatchCriteria) {
  return defined({
    team: c.team,
    opponent: c.opponent,
    venue: c.venue,
    competition: c.competition,
    season: c.season,
    date_from: c.from,
    date_to: c.to,
    stage: c.stage,
  });
}

function playerArguments(c: PlayerCriteria) {
  return defined({ name: c.name, nationality: c.nationality, club: c.club, position: c.position, limit: c.limit });
}

export class McpSoccerDriver implements SoccerSystemDriver {
  private client: Client | undefined;
  private transport: StdioClientTransport | undefined;
  private stderr = '';

  constructor(private readonly dataDirectory: string) {}

  async start(): Promise<void> {
    this.transport = new StdioClientTransport({
      command: process.execPath,
      args: [SERVER_ENTRY],
      env: { ...(process.env as Record<string, string>), SOCCER_DATA_DIR: this.dataDirectory },
      stderr: 'pipe',
    });
    this.transport.stderr?.on('data', (chunk: Buffer) => (this.stderr += String(chunk)));
    this.client = new Client({ name: 'acceptance-tests', version: '1.0.0' });
    try {
      await this.client.connect(this.transport);
    } catch (error) {
      throw new Error(`The soccer knowledge system did not start: ${String(error)}\n${this.stderr}`);
    }
  }

  async stop(): Promise<void> {
    await this.client?.close();
    this.client = undefined;
  }

  // ---- Matches -------------------------------------------------------------

  async confirmMatchesFound(criteria: MatchCriteria, expected: string[]): Promise<void> {
    const { data } = await this.ask<{ matches: MatchView[] }>('find_matches', { ...matchArguments(criteria), limit: 500 });
    expect(data.matches.map(line), `matches found for ${JSON.stringify(criteria)}`).toEqual(expected);
  }

  async confirmMatchesFoundAtLeast(criteria: MatchCriteria, count: number, involving: string[]): Promise<void> {
    const { data } = await this.ask<{ total: number; matches: MatchView[] }>('find_matches', { ...matchArguments(criteria), limit: 500 });
    expect(data.total, `number of matches found for ${JSON.stringify(criteria)}`).toBeGreaterThanOrEqual(count);
    for (const team of involving) {
      expect(
        data.matches.some((m) => m.homeTeam === team || m.awayTeam === team),
        `${team} should be involved in the matches found for ${JSON.stringify(criteria)}`,
      ).toBe(true);
    }
  }

  async confirmLastMeeting(team: string, opponent: string, expected?: string): Promise<void> {
    const { data } = await this.ask<{ matches: MatchView[] }>('find_matches', { team, opponent, limit: 1 });
    expect(data.matches.length, `${team} and ${opponent} should have met`).toBe(1);
    if (expected) expect(line(data.matches[0]), `last meeting of ${team} and ${opponent}`).toBe(expected);
  }

  async confirmDerbies(criteria: { season?: number }, expected: string[]): Promise<void> {
    const { data } = await this.ask<{ matches: MatchView[] }>('derbies', defined(criteria));
    expect(data.matches.map((m) => `${line(m)} (${m.derby})`), 'derbies found').toEqual(expected);
  }

  async confirmDerbiesInclude(criteria: { season?: number }, derbyNames: string[]): Promise<void> {
    const { data } = await this.ask<{ matches: MatchView[] }>('derbies', defined(criteria));
    const names = new Set(data.matches.map((m) => m.derby));
    for (const derby of derbyNames) expect(names.has(derby), `the ${derby} should have been played`).toBe(true);
  }

  async confirmMatchAnswerMentions(criteria: MatchCriteria, mentions: string[]): Promise<void> {
    const { text } = await this.ask('find_matches', matchArguments(criteria));
    for (const mention of mentions) expect(text, 'the readable answer').toContain(mention);
  }

  // ---- Teams ---------------------------------------------------------------

  async confirmTeamRecord(criteria: RecordCriteria, expected: TeamRecordExpectation): Promise<void> {
    const { data } = await this.ask<TeamRecordExpectation>(
      'team_record',
      defined({
        team: criteria.team,
        season: criteria.season,
        competition: criteria.competition,
        venue: criteria.venue,
        date_from: criteria.from,
        date_to: criteria.to,
      }),
    );
    expect(data, `record of ${criteria.team}`).toMatchObject(expected);
  }

  async confirmHeadToHead(team: string, opponent: string, expected: TeamRecordExpectation): Promise<void> {
    const { data } = await this.ask<TeamRecordExpectation>('head_to_head', { team, opponent });
    expect(data, `${team} against ${opponent}`).toMatchObject(expected);
  }

  async confirmHeadToHeadPlayedAtLeast(team: string, opponent: string, matches: number): Promise<void> {
    const { data } = await this.ask<{ played: number }>('head_to_head', { team, opponent });
    expect(data.played, `meetings of ${team} and ${opponent}`).toBeGreaterThanOrEqual(matches);
  }

  async confirmCompetitions(team: string, competitions: string[]): Promise<void> {
    const { data } = await this.ask<{ competitions: Array<{ competition: string }> }>('team_competitions', { team });
    expect(data.competitions.map((c) => c.competition).sort(), `competitions ${team} played in`).toEqual([...competitions].sort());
  }

  async confirmTopRanked(measure: RankingMeasure, scope: StatisticsScope, team: string, value?: number): Promise<void> {
    const { data } = await this.ask<{ rankings: Array<{ team: string; value: number }> }>('team_rankings', { measure, ...defined(scope) });
    expect(data.rankings[0]?.team, `best team by ${measure}`).toBe(team);
    if (value !== undefined) expect(data.rankings[0].value, `${team}'s ${measure}`).toBeCloseTo(value, 1);
  }

  async confirmRankingAvailable(measure: RankingMeasure, scope: StatisticsScope): Promise<void> {
    const { data } = await this.ask<{ rankings: Array<{ team: string; value: number }> }>('team_rankings', { measure, ...defined(scope) });
    expect(data.rankings.length, `teams ranked by ${measure}`).toBeGreaterThan(0);
  }

  async confirmTeamProfile(team: string, expected: TeamProfileExpectation): Promise<void> {
    const { data } = await this.ask<{
      squad: { size: number; players: Array<{ name: string }> };
      record: { played: number; wins: number };
    }>('team_profile', { team });
    if (expected.squadSize !== undefined) expect(data.squad.size, `squad size of ${team}`).toBe(expected.squadSize);
    if (expected.bestPlayer !== undefined) expect(data.squad.players[0]?.name, `best player at ${team}`).toBe(expected.bestPlayer);
    if (expected.played !== undefined) expect(data.record.played, `matches played by ${team}`).toBe(expected.played);
    if (expected.wins !== undefined) expect(data.record.wins, `matches won by ${team}`).toBe(expected.wins);
    if (expected.hasSquad) expect(data.squad.size, `squad of ${team}`).toBeGreaterThan(0);
    if (expected.hasMatches) expect(data.record.played, `matches of ${team}`).toBeGreaterThan(0);
  }

  // ---- Players -------------------------------------------------------------

  async confirmPlayerProfile(name: string, expected: { club?: string; position?: string; overall?: number; nationality?: string }): Promise<void> {
    const { data } = await this.ask<{ player: Record<string, unknown> | null }>('player_profile', { name });
    expect(data.player, `${name} should be in the player data`).not.toBeNull();
    expect(data.player, `profile of ${name}`).toMatchObject(expected);
  }

  async confirmPlayerUnknown(name: string, suggestions: string[]): Promise<void> {
    const { data, text } = await this.ask<{ player: unknown; suggestions: Array<{ name: string }> }>('player_profile', { name });
    expect(data.player, `${name} should not be in the player data`).toBeNull();
    expect(text, 'the answer should say the player was not found').toMatch(/no player/i);
    const suggested = data.suggestions.map((s) => s.name);
    for (const s of suggestions) expect(suggested, `players suggested instead of ${name}`).toContain(s);
  }

  async confirmPlayersFound(criteria: PlayerCriteria, expectedNames: string[]): Promise<void> {
    const { data } = await this.ask<{ players: Array<{ name: string }> }>('search_players', playerArguments(criteria));
    expect(data.players.map((p) => p.name), `players found for ${JSON.stringify(criteria)}`).toEqual(expectedNames);
  }

  async confirmPlayersFoundAtLeast(criteria: PlayerCriteria, count: number): Promise<void> {
    const { data } = await this.ask<{ total: number }>('search_players', playerArguments(criteria));
    expect(data.total, `players found for ${JSON.stringify(criteria)}`).toBeGreaterThanOrEqual(count);
  }

  async confirmNoPlayersFound(criteria: PlayerCriteria): Promise<void> {
    const { data, text } = await this.ask<{ total: number }>('search_players', playerArguments(criteria));
    expect(data.total, `players found for ${JSON.stringify(criteria)}`).toBe(0);
    expect(text, 'the answer should say nothing was found').toMatch(/no players/i);
  }

  async confirmClubSummary(nationality: string | undefined, clubs: Array<{ club: string; players: number; averageOverall: number }>): Promise<void> {
    const { data } = await this.ask<{ clubs: Array<{ club: string; players: number; averageOverall: number }> }>('players_by_club', defined({ nationality }));
    expect(data.clubs.map(({ club, players, averageOverall }) => ({ club, players, averageOverall })), 'players by club').toEqual(clubs);
  }

  async confirmClubSummaryIncludes(nationality: string | undefined, clubs: string[]): Promise<void> {
    const { data } = await this.ask<{ clubs: Array<{ club: string; players: number }> }>('players_by_club', defined({ nationality }));
    const names = data.clubs.map((c) => c.club);
    for (const club of clubs) expect(names, 'clubs with players').toContain(club);
  }

  // ---- Competitions ----------------------------------------------------------

  async confirmChampion(season: number, competition: string, expected: { team: string; points?: number; wins?: number; draws?: number; losses?: number }): Promise<void> {
    const table = await this.standings(season, competition);
    expect(table.champion, `${competition} ${season} champion`).toBe(expected.team);
    const { team, ...rest } = expected;
    expect(table.table[0], `${team}'s ${season} record`).toMatchObject(rest);
  }

  async confirmStandingsOrder(season: number, competition: string, order: string[]): Promise<void> {
    const table = await this.standings(season, competition);
    expect(table.table.slice(0, order.length).map((r) => r.team), `${competition} ${season} standings`).toEqual(order);
  }

  async confirmRelegated(season: number, competition: string, teams: string[]): Promise<void> {
    const table = await this.standings(season, competition);
    expect([...table.relegated].sort(), `teams relegated from ${competition} ${season}`).toEqual([...teams].sort());
  }

  async confirmBracket(competition: string, season: number, stages: Record<string, string[]>): Promise<void> {
    const bracket = await this.bracket(competition, season);
    const actual = Object.fromEntries(
      bracket.stages.filter((s) => s.stage in stages).map((s) => [s.stage, s.matches.map(score)]),
    );
    expect(actual, `${competition} ${season} bracket`).toEqual(stages);
    const order = bracket.stages.map((s) => s.stage).filter((s) => s in stages);
    expect(order, `${competition} ${season} stages in order`).toEqual(Object.keys(stages));
  }

  async confirmBracketIncludes(competition: string, season: number, stage: string, teams: string[]): Promise<void> {
    const bracket = await this.bracket(competition, season);
    const matches = bracket.stages.find((s) => s.stage === stage)?.matches ?? [];
    const involved = new Set(matches.flatMap((m) => [m.homeTeam, m.awayTeam]));
    expect([...involved].sort(), `teams in the ${competition} ${season} ${stage}`).toEqual([...teams].sort());
  }

  // ---- Statistics ------------------------------------------------------------

  async confirmSummary(scope: StatisticsScope, expected: SummaryExpectation): Promise<void> {
    const { data } = await this.ask<Record<string, number>>('match_statistics', defined(scope));
    for (const [key, value] of Object.entries(expected)) {
      expect(data[key], `${key} for ${JSON.stringify(scope)}`).toBeCloseTo(value as number, 1);
    }
  }

  async confirmSummaryBetween(scope: StatisticsScope, ranges: Record<string, [number, number]>): Promise<void> {
    const { data } = await this.ask<Record<string, number>>('match_statistics', defined(scope));
    for (const [key, range] of Object.entries(ranges)) {
      if (!range) continue;
      expect(data[key], `${key} for ${JSON.stringify(scope)}`).toBeGreaterThanOrEqual(range[0]);
      expect(data[key], `${key} for ${JSON.stringify(scope)}`).toBeLessThanOrEqual(range[1]);
    }
  }

  async confirmBiggestWins(scope: StatisticsScope, limit: number, expected: string[]): Promise<void> {
    const { data } = await this.ask<{ matches: MatchView[] }>('biggest_wins', { ...defined(scope), limit });
    expect(data.matches.map((m) => `${line(m)} (${m.competition})`), 'biggest wins').toEqual(expected);
  }

  async confirmBiggestWinsMarginAtLeast(scope: StatisticsScope, limit: number, margin: number): Promise<void> {
    const { data } = await this.ask<{ matches: MatchView[] }>('biggest_wins', { ...defined(scope), limit });
    expect(data.matches.length, 'number of biggest wins listed').toBe(limit);
    for (const m of data.matches) expect(Math.abs(m.homeGoals - m.awayGoals), `winning margin of ${line(m)}`).toBeGreaterThanOrEqual(margin);
  }

  async confirmSeasonComparison(competition: string, seasons: Record<number, { matches?: number; averageGoals?: number; champion?: string }>): Promise<void> {
    const { data } = await this.ask<{ seasons: Array<{ season: number; matches: number; averageGoals: number; champion: string | null }> }>('compare_seasons', {
      competition,
      seasons: Object.keys(seasons).map(Number),
    });
    for (const [season, expected] of Object.entries(seasons)) {
      const actual = data.seasons.find((s) => s.season === Number(season));
      expect(actual, `the ${season} season should be compared`).toBeDefined();
      expect(actual, `the ${season} season`).toMatchObject(expected);
    }
  }

  // ---- The system itself -------------------------------------------------------

  async confirmDatasetsLoaded(recordsByFile: Record<string, number>): Promise<void> {
    const { data } = await this.ask<{ datasets: Array<{ file: string; records: number }> }>('dataset_overview', {});
    const actual = Object.fromEntries(data.datasets.map((d) => [d.file, d.records]));
    expect(actual, 'records loaded from each dataset').toEqual(recordsByFile);
  }

  async confirmSimpleLookupsWithin(seconds: number): Promise<void> {
    await this.confirmEachWithin(seconds, [
      ['find_matches', { team: 'Flamengo', opponent: 'Corinthians', limit: 1 }],
      ['player_profile', { name: 'Neymar' }],
      ['search_players', { club: 'Santos' }],
      ['head_to_head', { team: 'Palmeiras', opponent: 'Santos' }],
      ['team_record', { team: 'Corinthians', season: 2022, venue: 'home' }],
    ]);
  }

  async confirmAggregateQueriesWithin(seconds: number): Promise<void> {
    await this.confirmEachWithin(seconds, [
      ['standings', { season: 2019 }],
      ['match_statistics', {}],
      ['team_rankings', { measure: 'home_win_rate' }],
      ['compare_seasons', { seasons: [2018, 2019] }],
      ['biggest_wins', { limit: 10 }],
      ['players_by_club', { nationality: 'Brazil' }],
      ['team_competitions', { team: 'Palmeiras' }],
    ]);
  }

  // ---- Plumbing ------------------------------------------------------------------

  private async confirmEachWithin(seconds: number, questions: Array<[string, Record<string, unknown>]>): Promise<void> {
    for (const [tool, args] of questions) {
      const started = performance.now();
      await this.ask(tool, args);
      const elapsed = (performance.now() - started) / 1000;
      expect(elapsed, `seconds taken to answer ${tool} ${JSON.stringify(args)}`).toBeLessThan(seconds);
    }
  }

  private standings(season: number, competition: string) {
    return this.ask<{ table: Array<{ team: string; points: number }>; champion: string | null; relegated: string[] }>('standings', { season, competition }).then((a) => a.data);
  }

  private bracket(competition: string, season: number) {
    return this.ask<{ stages: Array<{ stage: string; matches: MatchView[] }> }>('knockout_bracket', { competition, season }).then((a) => a.data);
  }

  private async ask<T = unknown>(tool: string, args: Record<string, unknown>): Promise<ToolAnswer<T>> {
    if (!this.client) throw new Error('The soccer knowledge system has not been started');
    const result = await this.client.callTool({ name: tool, arguments: args });
    const text = (result.content as Array<{ type: string; text?: string }>)
      .filter((c) => c.type === 'text')
      .map((c) => c.text)
      .join('\n');
    if (result.isError) throw new Error(`The system could not answer ${tool} ${JSON.stringify(args)}: ${text}`);
    if (!result.structuredContent) throw new Error(`The answer from ${tool} carried no structured data: ${text}`);
    return { data: result.structuredContent as T, text };
  }
}
