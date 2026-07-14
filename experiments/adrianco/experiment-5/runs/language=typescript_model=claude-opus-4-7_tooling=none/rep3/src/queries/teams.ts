import { Match, Competition } from '../types.js';
import { keyMatches, normalizeTeam } from '../normalize.js';
import { findMatches } from './matches.js';

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

function emptyRecord(team: string): TeamRecord {
  return {
    team,
    matches: 0,
    wins: 0,
    draws: 0,
    losses: 0,
    goalsFor: 0,
    goalsAgainst: 0,
    goalDifference: 0,
    points: 0,
    winRate: 0,
  };
}

function finalize(r: TeamRecord): TeamRecord {
  r.goalDifference = r.goalsFor - r.goalsAgainst;
  r.points = r.wins * 3 + r.draws;
  r.winRate = r.matches > 0 ? r.wins / r.matches : 0;
  return r;
}

export interface TeamRecordOptions {
  competition?: Competition;
  season?: number;
  /** Restrict to matches played at home. */
  homeOnly?: boolean;
  /** Restrict to matches played away. */
  awayOnly?: boolean;
}

/**
 * Compute a team's win/draw/loss record from a match list.
 *
 * Note: deliberately runs through findMatches so the team-name normalization
 * stays consistent with the rest of the surface.
 */
export function teamRecord(
  matches: Match[],
  team: string,
  opts: TeamRecordOptions = {},
): TeamRecord {
  const ms = findMatches(matches, {
    team,
    competition: opts.competition,
    season: opts.season,
    homeOnly: opts.homeOnly,
    awayOnly: opts.awayOnly,
  });
  const teamKey = normalizeTeam(team);
  const rec = emptyRecord(team);
  for (const m of ms) {
    const isHome = keyMatches(m.homeKey, teamKey);
    const gf = isHome ? m.homeGoals : m.awayGoals;
    const ga = isHome ? m.awayGoals : m.homeGoals;
    rec.matches++;
    rec.goalsFor += gf;
    rec.goalsAgainst += ga;
    if (gf > ga) rec.wins++;
    else if (gf < ga) rec.losses++;
    else rec.draws++;
  }
  return finalize(rec);
}

/**
 * Compute records for every team that appears in the supplied match list.
 *
 * Returned records use the most common display name for each normalized
 * team key (so "Palmeiras-SP" and "Palmeiras" merge correctly).
 */
export function allTeamRecords(
  matches: Match[],
  opts: TeamRecordOptions = {},
): TeamRecord[] {
  const filtered = matches.filter((m) => {
    if (opts.competition && m.competition !== opts.competition) return false;
    if (opts.season != null && m.season !== opts.season) return false;
    return true;
  });

  const byKey = new Map<
    string,
    {
      rec: TeamRecord;
      nameCounts: Map<string, number>;
    }
  >();

  const addAppearance = (key: string, name: string) => {
    let entry = byKey.get(key);
    if (!entry) {
      entry = { rec: emptyRecord(name), nameCounts: new Map() };
      byKey.set(key, entry);
    }
    entry.nameCounts.set(name, (entry.nameCounts.get(name) ?? 0) + 1);
    return entry;
  };

  for (const m of filtered) {
    if (!m.homeKey || !m.awayKey) continue;

    const homeEntry = addAppearance(m.homeKey, m.homeTeam);
    const awayEntry = addAppearance(m.awayKey, m.awayTeam);

    if (!opts.awayOnly) {
      homeEntry.rec.matches++;
      homeEntry.rec.goalsFor += m.homeGoals;
      homeEntry.rec.goalsAgainst += m.awayGoals;
      if (m.homeGoals > m.awayGoals) homeEntry.rec.wins++;
      else if (m.homeGoals < m.awayGoals) homeEntry.rec.losses++;
      else homeEntry.rec.draws++;
    }

    if (!opts.homeOnly) {
      awayEntry.rec.matches++;
      awayEntry.rec.goalsFor += m.awayGoals;
      awayEntry.rec.goalsAgainst += m.homeGoals;
      if (m.awayGoals > m.homeGoals) awayEntry.rec.wins++;
      else if (m.awayGoals < m.homeGoals) awayEntry.rec.losses++;
      else awayEntry.rec.draws++;
    }
  }

  const out: TeamRecord[] = [];
  for (const { rec, nameCounts } of byKey.values()) {
    if (rec.matches === 0) continue;
    let bestName = rec.team;
    let bestCount = -1;
    for (const [name, count] of nameCounts) {
      if (count > bestCount) {
        bestCount = count;
        bestName = name;
      }
    }
    rec.team = bestName;
    finalize(rec);
    out.push(rec);
  }
  return out;
}

/**
 * League-style standings sorted by points, then goal difference, then GF.
 */
export function standings(
  matches: Match[],
  opts: TeamRecordOptions = {},
): TeamRecord[] {
  return allTeamRecords(matches, opts).sort((a, b) => {
    if (b.points !== a.points) return b.points - a.points;
    if (b.goalDifference !== a.goalDifference)
      return b.goalDifference - a.goalDifference;
    if (b.goalsFor !== a.goalsFor) return b.goalsFor - a.goalsFor;
    return a.team.localeCompare(b.team);
  });
}

export function topScoringTeams(
  matches: Match[],
  opts: TeamRecordOptions & { limit?: number } = {},
): TeamRecord[] {
  const limit = opts.limit ?? 10;
  return allTeamRecords(matches, opts)
    .sort((a, b) => b.goalsFor - a.goalsFor || b.points - a.points)
    .slice(0, limit);
}
