/**
 * The contract every protocol driver for the soccer knowledge system fulfils.
 *
 * Methods are at the same level of abstraction as the DSL. Each one either
 * passes or fails the test with a message in the language of the domain.
 */
export type Venue = 'home' | 'away' | 'any';

export interface MatchCriteria {
  team?: string;
  opponent?: string;
  venue?: Venue;
  competition?: string;
  season?: number;
  from?: string;
  to?: string;
  stage?: string;
}

export interface RecordCriteria {
  team: string;
  season?: number;
  competition?: string;
  venue?: Venue;
  from?: string;
  to?: string;
}

export interface TeamRecordExpectation {
  played?: number;
  wins?: number;
  draws?: number;
  losses?: number;
  goalsFor?: number;
  goalsAgainst?: number;
  winRate?: number;
}

export type RankingMeasure = 'goals_scored' | 'goals_conceded' | 'points' | 'wins' | 'win_rate' | 'home_win_rate' | 'away_win_rate';

export interface StatisticsScope {
  competition?: string;
  season?: number;
  team?: string;
}

export interface SummaryExpectation {
  matches?: number;
  averageGoals?: number;
  homeWinRate?: number;
  drawRate?: number;
  awayWinRate?: number;
  averageCorners?: number;
}

export interface PlayerCriteria {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  limit?: number;
}

export interface TeamProfileExpectation {
  squadSize?: number;
  bestPlayer?: string;
  played?: number;
  wins?: number;
  hasSquad?: boolean;
  hasMatches?: boolean;
}

export interface SoccerSystemDriver {
  start(): Promise<void>;
  stop(): Promise<void>;

  confirmMatchesFound(criteria: MatchCriteria, expected: string[]): Promise<void>;
  confirmMatchesFoundAtLeast(criteria: MatchCriteria, count: number, involving: string[]): Promise<void>;
  confirmLastMeeting(team: string, opponent: string, expected?: string): Promise<void>;
  confirmDerbies(criteria: { season?: number }, expected: string[]): Promise<void>;
  confirmDerbiesInclude(criteria: { season?: number }, derbyNames: string[]): Promise<void>;
  confirmMatchAnswerMentions(criteria: MatchCriteria, mentions: string[]): Promise<void>;

  confirmTeamRecord(criteria: RecordCriteria, expected: TeamRecordExpectation): Promise<void>;
  confirmHeadToHead(team: string, opponent: string, expected: TeamRecordExpectation): Promise<void>;
  confirmHeadToHeadPlayedAtLeast(team: string, opponent: string, matches: number): Promise<void>;
  confirmCompetitions(team: string, competitions: string[]): Promise<void>;
  confirmTopRanked(measure: RankingMeasure, scope: StatisticsScope, team: string, value?: number): Promise<void>;
  confirmRankingAvailable(measure: RankingMeasure, scope: StatisticsScope): Promise<void>;
  confirmTeamProfile(team: string, expected: TeamProfileExpectation): Promise<void>;

  confirmPlayerProfile(name: string, expected: { club?: string; position?: string; overall?: number; nationality?: string }): Promise<void>;
  confirmPlayerUnknown(name: string, suggestions: string[]): Promise<void>;
  confirmPlayersFound(criteria: PlayerCriteria, expectedNames: string[]): Promise<void>;
  confirmPlayersFoundAtLeast(criteria: PlayerCriteria, count: number): Promise<void>;
  confirmNoPlayersFound(criteria: PlayerCriteria): Promise<void>;
  confirmClubSummary(nationality: string | undefined, clubs: Array<{ club: string; players: number; averageOverall: number }>): Promise<void>;
  confirmClubSummaryIncludes(nationality: string | undefined, clubs: string[]): Promise<void>;

  confirmChampion(season: number, competition: string, expected: { team: string; points?: number; wins?: number; draws?: number; losses?: number }): Promise<void>;
  confirmStandingsOrder(season: number, competition: string, order: string[]): Promise<void>;
  confirmRelegated(season: number, competition: string, teams: string[]): Promise<void>;
  confirmBracket(competition: string, season: number, stages: Record<string, string[]>): Promise<void>;
  confirmBracketIncludes(competition: string, season: number, stage: string, teams: string[]): Promise<void>;

  confirmSummary(scope: StatisticsScope, expected: SummaryExpectation): Promise<void>;
  confirmSummaryBetween(scope: StatisticsScope, ranges: Record<string, [number, number]>): Promise<void>;
  confirmBiggestWins(scope: StatisticsScope, limit: number, expected: string[]): Promise<void>;
  confirmBiggestWinsMarginAtLeast(scope: StatisticsScope, limit: number, margin: number): Promise<void>;
  confirmSeasonComparison(competition: string, seasons: Record<number, { matches?: number; averageGoals?: number; champion?: string }>): Promise<void>;

  confirmDatasetsLoaded(recordsByFile: Record<string, number>): Promise<void>;
  confirmSimpleLookupsWithin(seconds: number): Promise<void>;
  confirmAggregateQueriesWithin(seconds: number): Promise<void>;
}
