import type { Match, HeadToHead } from "../types.js";
import { normalizeTeam } from "../normalize.js";

export interface MatchFilter {
  team?: string;
  homeTeam?: string;
  awayTeam?: string;
  opponent?: string;
  competition?: string;
  season?: number;
  seasonFrom?: number;
  seasonTo?: number;
  dateFrom?: string;
  dateTo?: string;
  round?: string;
  stage?: string;
  hasResult?: boolean;
  limit?: number;
}

function matchesText(value: string | null, query: string | undefined): boolean {
  if (!query) return true;
  if (!value) return false;
  return value.toLowerCase().includes(query.toLowerCase());
}

export function findMatches(matches: Match[], filter: MatchFilter): Match[] {
  const team = filter.team ? normalizeTeam(filter.team) : undefined;
  const home = filter.homeTeam ? normalizeTeam(filter.homeTeam) : undefined;
  const away = filter.awayTeam ? normalizeTeam(filter.awayTeam) : undefined;
  const opponent = filter.opponent ? normalizeTeam(filter.opponent) : undefined;

  const out: Match[] = [];
  for (const m of matches) {
    if (filter.competition && !matchesText(String(m.competition), filter.competition)) continue;
    if (filter.season !== undefined && m.season !== filter.season) continue;
    if (filter.seasonFrom !== undefined && (m.season ?? -Infinity) < filter.seasonFrom) continue;
    if (filter.seasonTo !== undefined && (m.season ?? Infinity) > filter.seasonTo) continue;
    if (filter.dateFrom && (m.date ?? "") < filter.dateFrom) continue;
    if (filter.dateTo && (m.date ?? "9999") > filter.dateTo) continue;
    if (filter.round && !matchesText(m.round, filter.round)) continue;
    if (filter.stage && !matchesText(m.stage, filter.stage)) continue;
    if (filter.hasResult && (m.homeGoal === null || m.awayGoal === null)) continue;

    if (team) {
      if (m.homeTeamNormalized !== team && m.awayTeamNormalized !== team) continue;
    }
    if (home && m.homeTeamNormalized !== home) continue;
    if (away && m.awayTeamNormalized !== away) continue;
    if (opponent && team) {
      // Either team @ opponent, or opponent @ team
      const okA = m.homeTeamNormalized === team && m.awayTeamNormalized === opponent;
      const okB = m.homeTeamNormalized === opponent && m.awayTeamNormalized === team;
      if (!okA && !okB) continue;
    }

    out.push(m);
  }

  out.sort((a, b) => (b.date ?? "").localeCompare(a.date ?? ""));

  if (filter.limit && filter.limit > 0) return out.slice(0, filter.limit);
  return out;
}

export function headToHead(matches: Match[], teamA: string, teamB: string, opts?: {
  competition?: string;
  seasonFrom?: number;
  seasonTo?: number;
}): { matches: Match[]; summary: HeadToHead } {
  const a = normalizeTeam(teamA);
  const b = normalizeTeam(teamB);
  const filtered = findMatches(matches, {
    team: teamA,
    opponent: teamB,
    competition: opts?.competition,
    seasonFrom: opts?.seasonFrom,
    seasonTo: opts?.seasonTo,
    hasResult: true,
  });

  let aWins = 0, bWins = 0, draws = 0, aGoals = 0, bGoals = 0;
  for (const m of filtered) {
    if (m.homeGoal === null || m.awayGoal === null) continue;
    const aIsHome = m.homeTeamNormalized === a;
    const aScore = aIsHome ? m.homeGoal : m.awayGoal;
    const bScore = aIsHome ? m.awayGoal : m.homeGoal;
    aGoals += aScore;
    bGoals += bScore;
    if (aScore > bScore) aWins++;
    else if (bScore > aScore) bWins++;
    else draws++;
  }

  return {
    matches: filtered,
    summary: {
      teamA,
      teamB,
      matches: filtered.length,
      teamAWins: aWins,
      teamBWins: bWins,
      draws,
      teamAGoals: aGoals,
      teamBGoals: bGoals,
    },
  };
}

export function lastMatchBetween(matches: Match[], teamA: string, teamB: string): Match | null {
  const { matches: list } = headToHead(matches, teamA, teamB);
  return list.length > 0 ? list[0] : null;
}
