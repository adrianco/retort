import { teamKeyMatchesQuery } from "../normalize.js";
import type { Dataset, Match } from "../types.js";
import { byDateDesc, competitionMatches, DEFAULT_LIMIT } from "./shared.js";

export interface MatchFilter {
  team?: string;
  opponent?: string;
  competition?: string;
  season?: number;
  dateFrom?: string;
  dateTo?: string;
  limit?: number;
}

export interface MatchQueryResult {
  total: number;
  matches: Match[];
}

function inTeamAndOpponent(match: Match, team: string, opponent: string): boolean {
  return (
    (teamKeyMatchesQuery(match.homeTeam, team) && teamKeyMatchesQuery(match.awayTeam, opponent)) ||
    (teamKeyMatchesQuery(match.homeTeam, opponent) && teamKeyMatchesQuery(match.awayTeam, team))
  );
}

/** Finds matches across all datasets by team, opponent, competition, season
 * and/or date range. Returns the full matching total alongside a
 * most-recent-first page (capped by `limit`, default 25). */
export function findMatches(dataset: Dataset, filter: MatchFilter): MatchQueryResult {
  let results = dataset.matches;

  if (filter.team && filter.opponent) {
    results = results.filter((m) => inTeamAndOpponent(m, filter.team!, filter.opponent!));
  } else if (filter.team) {
    results = results.filter(
      (m) => teamKeyMatchesQuery(m.homeTeam, filter.team!) || teamKeyMatchesQuery(m.awayTeam, filter.team!),
    );
  } else if (filter.opponent) {
    results = results.filter(
      (m) => teamKeyMatchesQuery(m.homeTeam, filter.opponent!) || teamKeyMatchesQuery(m.awayTeam, filter.opponent!),
    );
  }

  if (filter.competition) {
    results = results.filter((m) => competitionMatches(m, filter.competition!));
  }
  if (filter.season !== undefined) {
    results = results.filter((m) => m.season === filter.season);
  }
  if (filter.dateFrom) {
    const from = new Date(filter.dateFrom);
    results = results.filter((m) => m.date !== null && m.date >= from);
  }
  if (filter.dateTo) {
    const to = new Date(filter.dateTo);
    results = results.filter((m) => m.date !== null && m.date <= to);
  }

  const sorted = [...results].sort(byDateDesc);
  const limit = filter.limit ?? DEFAULT_LIMIT;
  return { total: sorted.length, matches: sorted.slice(0, limit) };
}

export interface HeadToHeadResult {
  teamA: string;
  teamB: string;
  totalMatches: number;
  teamAWins: number;
  teamBWins: number;
  draws: number;
  teamAGoals: number;
  teamBGoals: number;
  matches: Match[];
}

export interface HeadToHeadOptions {
  competition?: string;
  season?: number;
  limit?: number;
}

/** Head-to-head record between two teams: overall W/D/L and goals, plus a
 * most-recent-first page of the underlying matches. */
export function headToHead(
  dataset: Dataset,
  teamA: string,
  teamB: string,
  opts: HeadToHeadOptions = {},
): HeadToHeadResult {
  let matches = dataset.matches.filter((m) => inTeamAndOpponent(m, teamA, teamB));
  if (opts.competition) matches = matches.filter((m) => competitionMatches(m, opts.competition!));
  if (opts.season !== undefined) matches = matches.filter((m) => m.season === opts.season);

  let teamAWins = 0;
  let teamBWins = 0;
  let draws = 0;
  let teamAGoals = 0;
  let teamBGoals = 0;

  for (const m of matches) {
    if (m.homeGoals === null || m.awayGoals === null) continue;
    const homeIsA = teamKeyMatchesQuery(m.homeTeam, teamA);
    const aGoals = homeIsA ? m.homeGoals : m.awayGoals;
    const bGoals = homeIsA ? m.awayGoals : m.homeGoals;
    teamAGoals += aGoals;
    teamBGoals += bGoals;
    if (aGoals > bGoals) teamAWins += 1;
    else if (bGoals > aGoals) teamBWins += 1;
    else draws += 1;
  }

  const sorted = [...matches].sort(byDateDesc);
  const limit = opts.limit ?? DEFAULT_LIMIT;

  return {
    teamA,
    teamB,
    totalMatches: matches.length,
    teamAWins,
    teamBWins,
    draws,
    teamAGoals,
    teamBGoals,
    matches: sorted.slice(0, limit),
  };
}

export function formatMatchLine(match: Match): string {
  const date = match.date ? match.date.toISOString().slice(0, 10) : match.dateRaw || "unknown date";
  const round = match.round ? ` (${match.competition} Round ${match.round})` : ` (${match.competition})`;
  return `${date}: ${match.homeTeam.display} ${match.homeGoals ?? "?"}-${match.awayGoals ?? "?"} ${match.awayTeam.display}${round}`;
}
