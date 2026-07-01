/**
 * Match-centric queries: find matches by criteria, head-to-head records, and
 * "when did X last play Y" lookups.
 */
import { teamMatches } from "../normalize.js";
import type { Match } from "../types.js";
import { filterMatches, sortByDate, type MatchFilter } from "./filters.js";

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

/** Find matches matching a filter, sorted chronologically (default ascending). */
export function findMatches(
  all: Match[],
  filter: MatchFilter,
  options: { direction?: "asc" | "desc"; limit?: number } = {},
): Match[] {
  const filtered = filterMatches(all, filter);
  const sorted = sortByDate(filtered, options.direction ?? "asc");
  return options.limit ? sorted.slice(0, options.limit) : sorted;
}

/**
 * Compute the head-to-head record between two teams across all played matches
 * (in every competition present in the data unless a filter narrows it).
 */
export function headToHead(
  all: Match[],
  teamA: string,
  teamB: string,
  extra: Omit<MatchFilter, "team" | "opponent"> = {},
): { record: HeadToHead; matches: Match[] } {
  const matches = filterMatches(all, {
    ...extra,
    team: teamA,
    opponent: teamB,
    playedOnly: true,
  });

  const record: HeadToHead = {
    teamA,
    teamB,
    matches: matches.length,
    teamAWins: 0,
    teamBWins: 0,
    draws: 0,
    teamAGoals: 0,
    teamBGoals: 0,
  };

  for (const m of matches) {
    const { aGoals, bGoals } = orientGoals(m, teamA);
    record.teamAGoals += aGoals;
    record.teamBGoals += bGoals;
    if (aGoals > bGoals) record.teamAWins += 1;
    else if (bGoals > aGoals) record.teamBWins += 1;
    else record.draws += 1;
  }

  return { record, matches: sortByDate(matches, "desc") };
}

/** The most recent played match between two teams, or null if none exist. */
export function lastMeeting(all: Match[], teamA: string, teamB: string): Match | null {
  const { matches } = headToHead(all, teamA, teamB);
  return matches.length > 0 ? matches[0] : null;
}

/**
 * Orient a match's goals relative to `teamA`, so callers get (aGoals, bGoals)
 * regardless of whether teamA played home or away. Assumes the match has a
 * recorded score.
 */
export function orientGoals(match: Match, teamA: string): { aGoals: number; bGoals: number } {
  const home = match.homeGoals ?? 0;
  const away = match.awayGoals ?? 0;
  // teamA counts as the home side whenever it matches the home team name.
  const teamAIsHome = teamMatches(match.homeTeam, teamA);
  return teamAIsHome ? { aGoals: home, bGoals: away } : { aGoals: away, bGoals: home };
}
