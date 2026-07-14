import type { Match, TeamRecord } from "../types.js";
import { normalizeTeam } from "../normalize.js";
import { findMatches } from "./matches.js";

export type Venue = "home" | "away" | "any";

export interface TeamStatsFilter {
  team: string;
  competition?: string;
  season?: number;
  seasonFrom?: number;
  seasonTo?: number;
  venue?: Venue;
}

export function teamStats(matches: Match[], filter: TeamStatsFilter): TeamRecord {
  const teamN = normalizeTeam(filter.team);
  const venue = filter.venue ?? "any";

  let played = 0, wins = 0, draws = 0, losses = 0, gf = 0, ga = 0;
  for (const m of matches) {
    if (m.homeGoal === null || m.awayGoal === null) continue;
    if (filter.competition && !String(m.competition).toLowerCase().includes(filter.competition.toLowerCase())) continue;
    if (filter.season !== undefined && m.season !== filter.season) continue;
    if (filter.seasonFrom !== undefined && (m.season ?? -Infinity) < filter.seasonFrom) continue;
    if (filter.seasonTo !== undefined && (m.season ?? Infinity) > filter.seasonTo) continue;

    const isHome = m.homeTeamNormalized === teamN;
    const isAway = m.awayTeamNormalized === teamN;
    if (!isHome && !isAway) continue;
    if (venue === "home" && !isHome) continue;
    if (venue === "away" && !isAway) continue;

    const for_ = isHome ? m.homeGoal : m.awayGoal;
    const against = isHome ? m.awayGoal : m.homeGoal;
    gf += for_;
    ga += against;
    played++;
    if (for_ > against) wins++;
    else if (for_ < against) losses++;
    else draws++;
  }

  const points = wins * 3 + draws;
  const winRate = played > 0 ? wins / played : 0;

  return {
    team: filter.team,
    matches: played,
    wins,
    draws,
    losses,
    goalsFor: gf,
    goalsAgainst: ga,
    goalDifference: gf - ga,
    points,
    winRate,
  };
}

export function listTeams(matches: Match[]): string[] {
  const set = new Set<string>();
  for (const m of matches) {
    if (m.homeTeam) set.add(m.homeTeam);
    if (m.awayTeam) set.add(m.awayTeam);
  }
  return Array.from(set).sort();
}

export function teamCompetitions(matches: Match[], team: string): string[] {
  const team_ = normalizeTeam(team);
  const set = new Set<string>();
  for (const m of matches) {
    if (m.homeTeamNormalized === team_ || m.awayTeamNormalized === team_) {
      set.add(String(m.competition));
    }
  }
  return Array.from(set).sort();
}

export function teamRecentMatches(matches: Match[], team: string, limit = 10): Match[] {
  return findMatches(matches, { team, hasResult: true, limit });
}
