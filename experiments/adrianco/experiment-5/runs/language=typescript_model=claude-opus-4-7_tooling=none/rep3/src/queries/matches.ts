import { Match, Competition } from '../types.js';
import { keyMatches, normalizeTeam } from '../normalize.js';

export interface MatchFilter {
  team?: string;
  opponent?: string;
  /** If team is set, restricts to matches where they were the home side. */
  homeOnly?: boolean;
  /** If team is set, restricts to matches where they were the away side. */
  awayOnly?: boolean;
  competition?: Competition;
  season?: number;
  /** ISO YYYY-MM-DD lower bound (inclusive). */
  dateFrom?: string;
  /** ISO YYYY-MM-DD upper bound (inclusive). */
  dateTo?: string;
  /** Substring of round / stage. */
  round?: string;
  /** Cap the number of results returned. */
  limit?: number;
}

export interface HeadToHead {
  teamA: string;
  teamB: string;
  matches: Match[];
  teamAWins: number;
  teamBWins: number;
  draws: number;
  teamAGoals: number;
  teamBGoals: number;
}

function matchHasTeam(m: Match, teamKey: string): 'home' | 'away' | null {
  if (keyMatches(m.homeKey, teamKey)) return 'home';
  if (keyMatches(m.awayKey, teamKey)) return 'away';
  return null;
}

export function findMatches(matches: Match[], filter: MatchFilter): Match[] {
  const teamKey = filter.team ? normalizeTeam(filter.team) : '';
  const oppKey = filter.opponent ? normalizeTeam(filter.opponent) : '';

  let out = matches.filter((m) => {
    if (filter.competition && m.competition !== filter.competition) return false;
    if (filter.season != null && m.season !== filter.season) return false;
    if (filter.dateFrom && m.date < filter.dateFrom) return false;
    if (filter.dateTo && m.date > filter.dateTo) return false;
    if (filter.round) {
      const r = (m.round ?? '').toLowerCase();
      const s = (m.stage ?? '').toLowerCase();
      const needle = filter.round.toLowerCase();
      if (!r.includes(needle) && !s.includes(needle)) return false;
    }
    if (teamKey) {
      const side = matchHasTeam(m, teamKey);
      if (!side) return false;
      if (filter.homeOnly && side !== 'home') return false;
      if (filter.awayOnly && side !== 'away') return false;
    }
    if (oppKey) {
      const oppSide = matchHasTeam(m, oppKey);
      if (!oppSide) return false;
      if (teamKey) {
        // Make sure team and opponent are on different sides.
        const teamSide = matchHasTeam(m, teamKey);
        if (teamSide === oppSide) return false;
      }
    }
    return true;
  });

  // Newest first
  out.sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : 0));
  if (filter.limit != null && filter.limit > 0) out = out.slice(0, filter.limit);
  return out;
}

export function headToHead(
  matches: Match[],
  teamA: string,
  teamB: string,
): HeadToHead {
  const keyA = normalizeTeam(teamA);
  const keyB = normalizeTeam(teamB);
  const ms = findMatches(matches, { team: teamA, opponent: teamB });

  let aWins = 0;
  let bWins = 0;
  let draws = 0;
  let aGoals = 0;
  let bGoals = 0;
  for (const m of ms) {
    const aIsHome = keyMatches(m.homeKey, keyA);
    const aGoalsThis = aIsHome ? m.homeGoals : m.awayGoals;
    const bGoalsThis = aIsHome ? m.awayGoals : m.homeGoals;
    aGoals += aGoalsThis;
    bGoals += bGoalsThis;
    if (aGoalsThis > bGoalsThis) aWins++;
    else if (bGoalsThis > aGoalsThis) bWins++;
    else draws++;
  }

  return {
    teamA,
    teamB,
    matches: ms,
    teamAWins: aWins,
    teamBWins: bWins,
    draws,
    teamAGoals: aGoals,
    teamBGoals: bGoals,
  };
}

export function biggestWins(
  matches: Match[],
  opts: { competition?: Competition; limit?: number } = {},
): Match[] {
  const limit = opts.limit ?? 10;
  return [...matches]
    .filter((m) => (opts.competition ? m.competition === opts.competition : true))
    .filter((m) => m.homeGoals !== m.awayGoals)
    .sort(
      (a, b) =>
        Math.abs(b.homeGoals - b.awayGoals) -
        Math.abs(a.homeGoals - a.awayGoals),
    )
    .slice(0, limit);
}
