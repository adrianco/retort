export type Competition =
  | "Brasileirão"
  | "Copa do Brasil"
  | "Copa Libertadores"
  | "Brasileirão (historical)"
  | "Other";

export interface Match {
  source: string;
  competition: Competition | string;
  date: string | null;
  season: number | null;
  round: string | null;
  stage: string | null;
  homeTeam: string;
  homeTeamNormalized: string;
  homeState: string | null;
  awayTeam: string;
  awayTeamNormalized: string;
  awayState: string | null;
  homeGoal: number | null;
  awayGoal: number | null;
  arena: string | null;
  extras?: Record<string, unknown>;
}

export interface Player {
  id: number;
  name: string;
  age: number | null;
  nationality: string;
  overall: number | null;
  potential: number | null;
  club: string;
  clubNormalized: string;
  position: string | null;
  jerseyNumber: number | null;
  height: string | null;
  weight: string | null;
  preferredFoot: string | null;
}

export interface TeamRecord {
  team: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDifference: number;
  points: number;
  winRate: number;
}

export interface HeadToHead {
  teamA: string;
  teamB: string;
  matches: number;
  teamAWins: number;
  teamBWins: number;
  draws: number;
  teamAGoals: number;
  teamBGoals: number;
}
