import { teamMatches } from "../normalize.js";
import type { Competition, Dataset, Match } from "../types.js";

export interface MatchFilter {
  team?: string;
  team2?: string;
  homeTeam?: string;
  awayTeam?: string;
  season?: number;
  seasonFrom?: number;
  seasonTo?: number;
  dateFrom?: string;
  dateTo?: string;
  competition?: Competition | string;
  stage?: string;
  round?: string;
  limit?: number;
}

function withinDate(d: string, from?: string, to?: string): boolean {
  if (!d) return !from && !to;
  if (from && d < from) return false;
  if (to && d > to) return false;
  return true;
}

function competitionMatches(filter: string, m: Match): boolean {
  const f = filter.toLowerCase();
  if (m.competition.toLowerCase() === f) return true;
  return m.competitionLabel.toLowerCase().includes(f);
}

export function findMatches(dataset: Dataset, filter: MatchFilter): Match[] {
  const result: Match[] = [];
  for (const m of dataset.matches) {
    if (filter.team && !(teamMatches(filter.team, m.homeTeamRaw) || teamMatches(filter.team, m.awayTeamRaw))) continue;
    if (filter.team2 && !(teamMatches(filter.team2, m.homeTeamRaw) || teamMatches(filter.team2, m.awayTeamRaw))) continue;
    if (filter.homeTeam && !teamMatches(filter.homeTeam, m.homeTeamRaw)) continue;
    if (filter.awayTeam && !teamMatches(filter.awayTeam, m.awayTeamRaw)) continue;
    if (filter.season !== undefined && m.season !== filter.season) continue;
    if (filter.seasonFrom !== undefined && (m.season ?? -Infinity) < filter.seasonFrom) continue;
    if (filter.seasonTo !== undefined && (m.season ?? Infinity) > filter.seasonTo) continue;
    if (!withinDate(m.date, filter.dateFrom, filter.dateTo)) continue;
    if (filter.competition && !competitionMatches(String(filter.competition), m)) continue;
    if (filter.stage && (m.stage ?? "").toLowerCase().indexOf(filter.stage.toLowerCase()) === -1) continue;
    if (filter.round && String(m.round ?? "") !== String(filter.round)) continue;
    result.push(m);
  }
  result.sort((a, b) => (a.date || "").localeCompare(b.date || ""));
  if (filter.limit && filter.limit > 0) return result.slice(0, filter.limit);
  return result;
}

export function findMatchesBetween(dataset: Dataset, teamA: string, teamB: string, opts: Omit<MatchFilter, "team" | "team2"> = {}): Match[] {
  return findMatches(dataset, { ...opts, team: teamA, team2: teamB }).filter(
    (m) => !teamMatches(teamA, m.homeTeamRaw) || !teamMatches(teamA, m.awayTeamRaw)
      ? teamMatches(teamA, m.homeTeamRaw) !== teamMatches(teamB, m.homeTeamRaw)
      : false,
  );
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
  recentMatches: Match[];
}

export function headToHead(
  dataset: Dataset,
  teamA: string,
  teamB: string,
  opts: { competition?: string; seasonFrom?: number; seasonTo?: number } = {},
): HeadToHead {
  const matches = findMatches(dataset, {
    team: teamA,
    team2: teamB,
    competition: opts.competition,
    seasonFrom: opts.seasonFrom,
    seasonTo: opts.seasonTo,
  }).filter((m) => {
    const aIsHome = teamMatches(teamA, m.homeTeamRaw);
    const bIsHome = teamMatches(teamB, m.homeTeamRaw);
    const aIsAway = teamMatches(teamA, m.awayTeamRaw);
    const bIsAway = teamMatches(teamB, m.awayTeamRaw);
    return (aIsHome && bIsAway) || (bIsHome && aIsAway);
  });

  let teamAWins = 0;
  let teamBWins = 0;
  let draws = 0;
  let teamAGoals = 0;
  let teamBGoals = 0;

  for (const m of matches) {
    if (m.homeGoals === null || m.awayGoals === null) continue;
    const aIsHome = teamMatches(teamA, m.homeTeamRaw);
    const aGoals = aIsHome ? m.homeGoals : m.awayGoals;
    const bGoals = aIsHome ? m.awayGoals : m.homeGoals;
    teamAGoals += aGoals;
    teamBGoals += bGoals;
    if (aGoals > bGoals) teamAWins++;
    else if (bGoals > aGoals) teamBWins++;
    else draws++;
  }

  // most recent first
  const sorted = [...matches].sort((a, b) => (b.date || "").localeCompare(a.date || ""));

  return {
    teamA,
    teamB,
    matches: matches.length,
    teamAWins,
    teamBWins,
    draws,
    teamAGoals,
    teamBGoals,
    recentMatches: sorted.slice(0, 10),
  };
}
