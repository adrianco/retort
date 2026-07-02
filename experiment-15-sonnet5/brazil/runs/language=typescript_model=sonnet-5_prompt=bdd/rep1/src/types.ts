export type Competition =
  | "Brasileirao"
  | "CopaDoBrasil"
  | "Libertadores"
  | "Other";

export interface Match {
  competition: Competition;
  /** Original competition/tournament label as it appeared in the source file, when available. */
  sourceLabel: string;
  date: Date | null;
  /** Raw date string as it appeared in the source file, kept for display when parsing fails. */
  rawDate: string;
  season: number | null;
  round: string | null;
  stage: string | null;
  homeTeam: string;
  homeTeamKey: string;
  homeTeamState: string | null;
  awayTeam: string;
  awayTeamKey: string;
  awayTeamState: string | null;
  homeGoals: number | null;
  awayGoals: number | null;
  venue: string | null;
  extra: Record<string, string | number | null>;
  sourceFile: string;
}

export interface Player {
  id: number | null;
  name: string;
  age: number | null;
  nationality: string;
  overall: number | null;
  potential: number | null;
  club: string;
  clubKey: string;
  position: string | null;
  jerseyNumber: number | null;
  height: string | null;
  weight: string | null;
  wage: string | null;
  value: string | null;
}

export interface MatchResultForTeam {
  match: Match;
  outcome: "win" | "loss" | "draw";
  goalsFor: number;
  goalsAgainst: number;
  venue: "home" | "away";
}

export interface TeamRecord {
  team: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  winRate: number;
}

export interface StandingsRow extends TeamRecord {
  points: number;
  position: number;
}
