import { normalizeTeamName } from "../data/normalize.js";
import type { Match, MatchResultForTeam, TeamRecord } from "../types.js";
import type { Competition } from "../types.js";

export interface MatchFilter {
  teamKey?: string;
  opponentKey?: string;
  competition?: Competition;
  season?: number;
  dateFrom?: Date;
  dateTo?: Date;
}

/** Resolves a free-text team name into its lookup key. */
export function resolveTeamKey(name: string): string {
  return normalizeTeamName(name).teamKey;
}

/** Filters a match list by any combination of team, opponent, competition, season, and date range. */
export function filterMatches(matches: Match[], filter: MatchFilter): Match[] {
  return matches.filter((match) => {
    if (filter.teamKey && match.homeTeamKey !== filter.teamKey && match.awayTeamKey !== filter.teamKey) {
      return false;
    }
    if (filter.opponentKey) {
      const involvesOpponent = match.homeTeamKey === filter.opponentKey || match.awayTeamKey === filter.opponentKey;
      if (!involvesOpponent) return false;
      // When both a team and an opponent are given, they must be on opposite sides of the same match.
      if (filter.teamKey && filter.teamKey === filter.opponentKey) return false;
    }
    if (filter.competition && match.competition !== filter.competition) return false;
    if (filter.season !== undefined && match.season !== filter.season) return false;
    if (filter.dateFrom && (!match.date || match.date < filter.dateFrom)) return false;
    if (filter.dateTo && (!match.date || match.date > filter.dateTo)) return false;
    return true;
  });
}

/** Sorts matches most-recent first; matches with unknown dates sort last. */
export function sortByDateDesc(matches: Match[]): Match[] {
  return [...matches].sort((a, b) => {
    if (!a.date && !b.date) return 0;
    if (!a.date) return 1;
    if (!b.date) return -1;
    return b.date.getTime() - a.date.getTime();
  });
}

/** Returns the outcome (win/loss/draw) and goal tally for a specific team within a match, or null if the team wasn't involved or the score is unknown. */
export function resultForTeam(match: Match, teamKey: string): MatchResultForTeam | null {
  if (match.homeGoals === null || match.awayGoals === null) return null;
  let venue: "home" | "away";
  let goalsFor: number;
  let goalsAgainst: number;
  if (match.homeTeamKey === teamKey) {
    venue = "home";
    goalsFor = match.homeGoals;
    goalsAgainst = match.awayGoals;
  } else if (match.awayTeamKey === teamKey) {
    venue = "away";
    goalsFor = match.awayGoals;
    goalsAgainst = match.homeGoals;
  } else {
    return null;
  }
  const outcome = goalsFor > goalsAgainst ? "win" : goalsFor < goalsAgainst ? "loss" : "draw";
  return { match, outcome, goalsFor, goalsAgainst, venue };
}

/** Aggregates a team's win/draw/loss record and goal tallies across a set of matches. */
export function computeTeamRecord(matches: Match[], teamKey: string, displayName: string): TeamRecord {
  let wins = 0;
  let draws = 0;
  let losses = 0;
  let goalsFor = 0;
  let goalsAgainst = 0;
  let counted = 0;
  for (const match of matches) {
    const result = resultForTeam(match, teamKey);
    if (!result) continue;
    counted += 1;
    goalsFor += result.goalsFor;
    goalsAgainst += result.goalsAgainst;
    if (result.outcome === "win") wins += 1;
    else if (result.outcome === "draw") draws += 1;
    else losses += 1;
  }
  return {
    team: displayName,
    matches: counted,
    wins,
    draws,
    losses,
    goalsFor,
    goalsAgainst,
    winRate: counted > 0 ? wins / counted : 0,
  };
}
