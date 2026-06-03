import type { Match, TeamRecord } from "../types.js";

export interface StandingsFilter {
  competition: string;
  season: number;
}

export function standings(matches: Match[], filter: StandingsFilter): TeamRecord[] {
  const compNeedle = filter.competition.toLowerCase();
  const tally = new Map<string, TeamRecord & { displayName: string }>();

  function getRow(displayName: string): TeamRecord & { displayName: string } {
    const key = displayName.toLowerCase();
    let r = tally.get(key);
    if (!r) {
      r = {
        team: displayName,
        displayName,
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
      tally.set(key, r);
    }
    return r;
  }

  for (const m of matches) {
    if (m.season !== filter.season) continue;
    if (!String(m.competition).toLowerCase().includes(compNeedle)) continue;
    if (m.homeGoal === null || m.awayGoal === null) continue;

    const home = getRow(m.homeTeam);
    const away = getRow(m.awayTeam);

    home.matches++; away.matches++;
    home.goalsFor += m.homeGoal; home.goalsAgainst += m.awayGoal;
    away.goalsFor += m.awayGoal; away.goalsAgainst += m.homeGoal;

    if (m.homeGoal > m.awayGoal) { home.wins++; away.losses++; }
    else if (m.homeGoal < m.awayGoal) { away.wins++; home.losses++; }
    else { home.draws++; away.draws++; }
  }

  const rows = Array.from(tally.values()).map((r) => {
    r.points = r.wins * 3 + r.draws;
    r.goalDifference = r.goalsFor - r.goalsAgainst;
    r.winRate = r.matches > 0 ? r.wins / r.matches : 0;
    return r;
  });

  rows.sort((a, b) => {
    if (b.points !== a.points) return b.points - a.points;
    if (b.wins !== a.wins) return b.wins - a.wins;
    if (b.goalDifference !== a.goalDifference) return b.goalDifference - a.goalDifference;
    if (b.goalsFor !== a.goalsFor) return b.goalsFor - a.goalsFor;
    return a.team.localeCompare(b.team);
  });

  return rows;
}

export function champion(matches: Match[], filter: StandingsFilter): TeamRecord | null {
  const s = standings(matches, filter);
  return s.length > 0 ? s[0] : null;
}

export function relegated(matches: Match[], filter: StandingsFilter, count = 4): TeamRecord[] {
  const s = standings(matches, filter);
  return s.slice(Math.max(0, s.length - count));
}

export function listCompetitions(matches: Match[]): string[] {
  const set = new Set<string>();
  for (const m of matches) {
    set.add(String(m.competition));
  }
  return Array.from(set).sort();
}

export function listSeasons(matches: Match[], competition?: string): number[] {
  const needle = competition?.toLowerCase();
  const set = new Set<number>();
  for (const m of matches) {
    if (needle && !String(m.competition).toLowerCase().includes(needle)) continue;
    if (m.season !== null) set.add(m.season);
  }
  return Array.from(set).sort((a, b) => a - b);
}
