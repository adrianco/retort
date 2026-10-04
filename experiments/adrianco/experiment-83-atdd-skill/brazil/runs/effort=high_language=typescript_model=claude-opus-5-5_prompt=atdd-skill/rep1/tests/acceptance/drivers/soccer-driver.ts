/**
 * The protocol driver contract (layer 3 of the four-layer model).
 *
 * The DSL talks to the system under test only through this interface, at the
 * same level of abstraction as the test cases. Implementations are the only
 * code that knows how the system works (today: an MCP client talking to the
 * server over stdio, fed by datasets written in the Kaggle file formats).
 *
 * Every method either succeeds or fails the test with a message in the
 * language of the problem domain. "confirm…" methods assert against the
 * answer to the most recent question.
 */

export type Dataset = 'brasileirao' | 'cup' | 'libertadores' | 'extended' | 'historical';

export interface MatchRecord {
  home: string;
  away: string;
  homeGoals: number;
  awayGoals: number;
  date: string; // ISO yyyy-mm-dd
  season: number;
  competition: string;
  round: number;
  stage: string;
  dataset: Dataset;
  corners?: [number, number];
  shots?: [number, number];
}

export interface PlayerRecord {
  name: string;
  club: string;
  nationality: string;
  overall: number;
  potential: number;
  position: string;
  age: number;
  jerseyNumber: number;
  skills: Record<string, number>;
}

export interface ExpectedMatch {
  date: string;
  home: string;
  homeGoals: number;
  awayGoals: number;
  away: string;
}

export interface ExpectedTie {
  season?: number;
  winner: string;
  loser: string;
  winnerGoals: number;
  loserGoals: number;
}

export interface ExpectedStandingsRow {
  position: number;
  team: string;
  points: number;
  won: number;
  drawn: number;
  lost: number;
}

export interface MatchCriteria {
  team?: string;
  opponent?: string;
  venue?: 'home' | 'away';
  competition?: string;
  season?: number;
  from?: string;
  to?: string;
}

export interface RecordCriteria {
  team: string;
  season?: number;
  competition?: string;
  venue?: 'home' | 'away';
}

export interface RankingCriteria {
  metric: 'goals_for' | 'win_rate';
  venue?: 'home' | 'away';
  season?: number;
  competition?: string;
}

export interface PlayerCriteria {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  limit?: number;
}

export interface SoccerDriver {
  // The world the system knows about
  recordMatch(match: MatchRecord): void;
  recordPlayer(player: PlayerRecord): void;
  start(): Promise<void>;
  close(): Promise<void>;

  // Matches
  findMatches(criteria: MatchCriteria): Promise<void>;
  findLastMeeting(team: string, opponent: string): Promise<void>;
  findFinals(competition: string, season?: number): Promise<void>;
  findDerbies(season?: number): Promise<void>;
  confirmMatchesFound(expected: ExpectedMatch[]): void;
  confirmMatchPresentedAs(line: string): void;
  confirmMatchStatistics(expected: { corners?: [number, number]; shots?: [number, number] }): void;
  confirmFinals(expected: ExpectedTie[]): void;
  confirmDerbyNamed(name: string): void;
  confirmTeamNotRecognised(name: string): void;

  // Teams
  requestRecord(criteria: RecordCriteria): Promise<void>;
  confirmRecord(expected: Partial<Record<'played' | 'won' | 'drawn' | 'lost' | 'goalsFor' | 'goalsAgainst', number>> & { winRate?: string }): void;
  compareHeadToHead(team: string, opponent: string): Promise<void>;
  confirmHeadToHead(expected: Partial<Record<'played' | 'teamWins' | 'opponentWins' | 'draws' | 'teamGoals' | 'opponentGoals', number>>): void;
  requestCompetitions(team: string): Promise<void>;
  confirmCompetitions(expected: string[]): void;
  confirmCompetitionRecord(expected: { competition: string } & Partial<Record<'played' | 'won' | 'drawn' | 'lost' | 'goalsFor' | 'goalsAgainst', number>>): void;
  rankTeams(criteria: RankingCriteria): Promise<void>;
  confirmLeader(expected: { team: string; goalsFor?: number; winRate?: string }): void;

  // Players
  lookUpPlayer(name: string): Promise<void>;
  confirmPlayer(expected: Partial<Pick<PlayerRecord, 'name' | 'club' | 'overall' | 'position' | 'nationality'>>): void;
  confirmSkills(expected: Record<string, number>): void;
  confirmPlayerNotFound(suggesting: string): void;
  searchPlayers(criteria: PlayerCriteria): Promise<void>;
  confirmPlayersListed(expected: string[], inAnyOrder: boolean): void;
  summariseClubsForNationality(nationality: string): Promise<void>;
  confirmClubSummary(expected: { club: string; players?: number; averageRating?: number }): void;
  confirmClubNotInSummary(club: string): void;

  // Competitions
  requestStandings(competition: string, season: number): Promise<void>;
  confirmStandings(expected: ExpectedStandingsRow[], wholeTable: boolean): void;
  confirmChampion(team: string): void;
  confirmRelegated(teams: string[]): void;
  confirmSeasonIncomplete(matchesMissing: number): void;
  confirmTeamsInTable(teams: string[]): void;
  requestBracket(competition: string, season: number): Promise<void>;
  confirmTie(stage: string, expected: ExpectedTie): void;

  // Statistics
  summariseCompetition(competition?: string, season?: number): Promise<void>;
  confirmSummary(expected: { matches?: number; averageGoals?: number; homeWinRate?: string; drawRate?: string; awayWinRate?: string }): void;
  findBiggestWins(limit: number, competition?: string): Promise<void>;
  confirmBiggestWins(expected: ExpectedMatch[]): void;
  compareSeasons(seasons: number[], competition: string): Promise<void>;
  confirmSeason(expected: { season: number; matches?: number; averageGoals?: number; champion?: string }): void;
  profileTeam(team: string): Promise<void>;
  confirmProfile(expected: { team?: string; played?: number; won?: number; squadSize?: number; bestPlayer?: string }): void;

  // The provided data
  requestDatasetOverview(): Promise<void>;
  confirmDatasetLoaded(name: string, records: number): void;
  confirmLastQuestionAnswered(): void;
}
