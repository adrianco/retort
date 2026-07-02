import type { SoccerDataStore } from "../data/store.js";
import type { Competition, Match } from "../types.js";
import { filterMatches, resolveTeamKey, resultForTeam, sortByDateDesc } from "./helpers.js";

export interface MatchSearchOptions {
  team?: string;
  opponent?: string;
  competition?: Competition;
  season?: number;
  dateFrom?: string;
  dateTo?: string;
  limit?: number;
}

export interface MatchSearchResult {
  matches: Match[];
  totalMatches: number;
}

/** Finds matches by team, opponent, competition, season, and/or date range (Match Queries §1). */
export function searchMatches(store: SoccerDataStore, options: MatchSearchOptions): MatchSearchResult {
  const filtered = filterMatches(store.matches, {
    teamKey: options.team ? resolveTeamKey(options.team) : undefined,
    opponentKey: options.opponent ? resolveTeamKey(options.opponent) : undefined,
    competition: options.competition,
    season: options.season,
    dateFrom: options.dateFrom ? new Date(options.dateFrom) : undefined,
    dateTo: options.dateTo ? new Date(options.dateTo) : undefined,
  });
  const sorted = sortByDateDesc(filtered);
  const limit = options.limit ?? 25;
  return { matches: sorted.slice(0, limit), totalMatches: sorted.length };
}

export interface HeadToHeadResult {
  teamA: string;
  teamB: string;
  matches: Match[];
  totalMatches: number;
  teamAWins: number;
  teamBWins: number;
  draws: number;
}

/** Finds every match between two teams and tallies the head-to-head record. */
export function headToHead(store: SoccerDataStore, teamA: string, teamB: string, options: { competition?: Competition; season?: number; limit?: number } = {}): HeadToHeadResult {
  const teamAKey = resolveTeamKey(teamA);
  const teamBKey = resolveTeamKey(teamB);
  const all = filterMatches(store.matches, {
    teamKey: teamAKey,
    opponentKey: teamBKey,
    competition: options.competition,
    season: options.season,
  });
  const sorted = sortByDateDesc(all);

  let teamAWins = 0;
  let teamBWins = 0;
  let draws = 0;
  for (const match of all) {
    const result = resultForTeam(match, teamAKey);
    if (!result) continue;
    if (result.outcome === "win") teamAWins += 1;
    else if (result.outcome === "loss") teamBWins += 1;
    else draws += 1;
  }

  return {
    teamA: store.displayNameFor(teamAKey),
    teamB: store.displayNameFor(teamBKey),
    matches: sorted.slice(0, options.limit ?? sorted.length),
    totalMatches: sorted.length,
    teamAWins,
    teamBWins,
    draws,
  };
}

/** Finds the most recent match between two teams, across all competitions and datasets. */
export function mostRecentMatch(store: SoccerDataStore, teamA: string, teamB: string): Match | null {
  const result = headToHead(store, teamA, teamB, { limit: 1 });
  return result.matches[0] ?? null;
}
