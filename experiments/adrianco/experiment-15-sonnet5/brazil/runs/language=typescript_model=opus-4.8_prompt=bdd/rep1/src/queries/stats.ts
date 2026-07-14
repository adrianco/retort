/**
 * Aggregate statistical analysis across matches: goals-per-match averages,
 * home-win rates, biggest victories, and top-scoring teams.
 */
import { teamKey } from "../normalize.js";
import type { Match } from "../types.js";
import { filterMatches, type MatchFilter } from "./filters.js";

export interface MatchAggregate {
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

/** Aggregate goal / result statistics over the played matches matching a filter. */
export function aggregateStats(all: Match[], filter: MatchFilter = {}): MatchAggregate {
  const matches = filterMatches(all, { ...filter, playedOnly: true });
  let totalGoals = 0;
  let homeWins = 0;
  let awayWins = 0;
  let draws = 0;

  for (const m of matches) {
    const home = m.homeGoals as number;
    const away = m.awayGoals as number;
    totalGoals += home + away;
    if (home > away) homeWins += 1;
    else if (away > home) awayWins += 1;
    else draws += 1;
  }

  const n = matches.length;
  return {
    matches: n,
    totalGoals,
    averageGoalsPerMatch: n > 0 ? Math.round((totalGoals / n) * 100) / 100 : 0,
    homeWins,
    awayWins,
    draws,
    homeWinRate: n > 0 ? homeWins / n : 0,
    awayWinRate: n > 0 ? awayWins / n : 0,
    drawRate: n > 0 ? draws / n : 0,
  };
}

export interface BiggestWin {
  match: Match;
  margin: number;
}

/** The matches with the largest goal margins, matching a filter. */
export function biggestWins(all: Match[], filter: MatchFilter = {}, limit = 10): BiggestWin[] {
  const matches = filterMatches(all, { ...filter, playedOnly: true });
  return matches
    .map((match) => ({
      match,
      margin: Math.abs((match.homeGoals as number) - (match.awayGoals as number)),
    }))
    .sort((a, b) => {
      if (b.margin !== a.margin) return b.margin - a.margin;
      const bTotal = (b.match.homeGoals as number) + (b.match.awayGoals as number);
      const aTotal = (a.match.homeGoals as number) + (a.match.awayGoals as number);
      return bTotal - aTotal;
    })
    .slice(0, limit);
}

export interface TeamGoalTotal {
  team: string;
  goalsFor: number;
  matches: number;
}

/**
 * Rank teams by total goals scored over the matches matching a filter.
 * Answers "which team scored the most goals in Serie A 2023?".
 */
export function topScoringTeams(all: Match[], filter: MatchFilter = {}, limit = 10): TeamGoalTotal[] {
  const matches = filterMatches(all, { ...filter, playedOnly: true });
  const totals = new Map<string, TeamGoalTotal>();

  const bump = (team: string, goals: number) => {
    const key = teamKey(team);
    const entry = totals.get(key) ?? { team, goalsFor: 0, matches: 0 };
    entry.goalsFor += goals;
    entry.matches += 1;
    totals.set(key, entry);
  };

  for (const m of matches) {
    bump(m.homeTeam, m.homeGoals as number);
    bump(m.awayTeam, m.awayGoals as number);
  }

  return [...totals.values()]
    .sort((a, b) => b.goalsFor - a.goalsFor || a.team.localeCompare(b.team))
    .slice(0, limit);
}
