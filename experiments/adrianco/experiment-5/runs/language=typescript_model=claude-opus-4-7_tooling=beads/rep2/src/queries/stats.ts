import type { Match } from "../types.js";

export interface StatsFilter {
  competition?: string;
  season?: number;
  seasonFrom?: number;
  seasonTo?: number;
}

function filterMatches(matches: Match[], filter: StatsFilter): Match[] {
  const needle = filter.competition?.toLowerCase();
  return matches.filter((m) => {
    if (m.homeGoal === null || m.awayGoal === null) return false;
    if (needle && !String(m.competition).toLowerCase().includes(needle)) return false;
    if (filter.season !== undefined && m.season !== filter.season) return false;
    if (filter.seasonFrom !== undefined && (m.season ?? -Infinity) < filter.seasonFrom) return false;
    if (filter.seasonTo !== undefined && (m.season ?? Infinity) > filter.seasonTo) return false;
    return true;
  });
}

export interface AggregateStats {
  matches: number;
  totalGoals: number;
  averageGoalsPerMatch: number;
  homeWins: number;
  awayWins: number;
  draws: number;
  homeWinRate: number;
  awayWinRate: number;
  drawRate: number;
}

export function aggregateStats(matches: Match[], filter: StatsFilter = {}): AggregateStats {
  const list = filterMatches(matches, filter);
  let totalGoals = 0, homeWins = 0, awayWins = 0, draws = 0;
  for (const m of list) {
    totalGoals += (m.homeGoal ?? 0) + (m.awayGoal ?? 0);
    if ((m.homeGoal ?? 0) > (m.awayGoal ?? 0)) homeWins++;
    else if ((m.homeGoal ?? 0) < (m.awayGoal ?? 0)) awayWins++;
    else draws++;
  }
  const n = list.length;
  return {
    matches: n,
    totalGoals,
    averageGoalsPerMatch: n ? totalGoals / n : 0,
    homeWins,
    awayWins,
    draws,
    homeWinRate: n ? homeWins / n : 0,
    awayWinRate: n ? awayWins / n : 0,
    drawRate: n ? draws / n : 0,
  };
}

export function biggestWins(matches: Match[], filter: StatsFilter & { limit?: number } = {}): Match[] {
  const list = filterMatches(matches, filter);
  list.sort((a, b) => {
    const da = Math.abs((a.homeGoal ?? 0) - (a.awayGoal ?? 0));
    const db = Math.abs((b.homeGoal ?? 0) - (b.awayGoal ?? 0));
    if (db !== da) return db - da;
    const ga = (a.homeGoal ?? 0) + (a.awayGoal ?? 0);
    const gb = (b.homeGoal ?? 0) + (b.awayGoal ?? 0);
    return gb - ga;
  });
  return list.slice(0, filter.limit ?? 10);
}

export interface TeamSeasonScore {
  team: string;
  goalsFor: number;
  matches: number;
}

export function topScoringTeams(matches: Match[], filter: StatsFilter & { limit?: number } = {}): TeamSeasonScore[] {
  const list = filterMatches(matches, filter);
  const tally = new Map<string, TeamSeasonScore>();
  for (const m of list) {
    const home = tally.get(m.homeTeam) ?? { team: m.homeTeam, goalsFor: 0, matches: 0 };
    home.goalsFor += m.homeGoal ?? 0; home.matches++; tally.set(m.homeTeam, home);
    const away = tally.get(m.awayTeam) ?? { team: m.awayTeam, goalsFor: 0, matches: 0 };
    away.goalsFor += m.awayGoal ?? 0; away.matches++; tally.set(m.awayTeam, away);
  }
  const rows = Array.from(tally.values()).sort((a, b) => b.goalsFor - a.goalsFor);
  return rows.slice(0, filter.limit ?? 10);
}

export interface TeamVenueRecord {
  team: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  winRate: number;
}

export function bestRecord(
  matches: Match[],
  venue: "home" | "away",
  filter: StatsFilter & { limit?: number; minMatches?: number } = {},
): TeamVenueRecord[] {
  const list = filterMatches(matches, filter);
  const tally = new Map<string, TeamVenueRecord>();
  for (const m of list) {
    const teamName = venue === "home" ? m.homeTeam : m.awayTeam;
    const teamGoals = venue === "home" ? m.homeGoal ?? 0 : m.awayGoal ?? 0;
    const oppGoals = venue === "home" ? m.awayGoal ?? 0 : m.homeGoal ?? 0;
    const row = tally.get(teamName) ?? {
      team: teamName, matches: 0, wins: 0, draws: 0, losses: 0, winRate: 0,
    };
    row.matches++;
    if (teamGoals > oppGoals) row.wins++;
    else if (teamGoals < oppGoals) row.losses++;
    else row.draws++;
    tally.set(teamName, row);
  }
  const minMatches = filter.minMatches ?? 5;
  const rows = Array.from(tally.values())
    .filter((r) => r.matches >= minMatches)
    .map((r) => ({ ...r, winRate: r.wins / r.matches }))
    .sort((a, b) => b.winRate - a.winRate || b.wins - a.wins);
  return rows.slice(0, filter.limit ?? 10);
}
