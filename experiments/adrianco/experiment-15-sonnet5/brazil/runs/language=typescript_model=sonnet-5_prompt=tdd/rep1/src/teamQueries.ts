import { teamsMatch } from "./normalize.js";
import { headToHead, type HeadToHeadResult } from "./matchQueries.js";
import type { Match } from "./types.js";

export interface TeamRecordOptions {
  competition?: string;
  season?: number;
  venue?: "home" | "away" | "all";
}

export interface TeamRecord {
  team: string;
  matchesPlayed: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  winRate: number;
}

export function teamRecord(matches: Match[], team: string, options: TeamRecordOptions = {}): TeamRecord {
  const venue = options.venue ?? "all";

  const relevant = matches.filter((m) => {
    const isHome = teamsMatch(m.homeTeam, team);
    const isAway = teamsMatch(m.awayTeam, team);
    if (venue === "home" && !isHome) return false;
    if (venue === "away" && !isAway) return false;
    if (venue === "all" && !isHome && !isAway) return false;
    if (options.competition && m.competition.toLowerCase() !== options.competition.toLowerCase()) return false;
    if (options.season !== undefined && m.season !== options.season) return false;
    return true;
  });

  let wins = 0;
  let draws = 0;
  let losses = 0;
  let goalsFor = 0;
  let goalsAgainst = 0;

  for (const m of relevant) {
    const isHome = teamsMatch(m.homeTeam, team);
    const teamGoals = isHome ? m.homeGoals : m.awayGoals;
    const opponentGoals = isHome ? m.awayGoals : m.homeGoals;
    goalsFor += teamGoals;
    goalsAgainst += opponentGoals;
    if (teamGoals > opponentGoals) wins++;
    else if (teamGoals === opponentGoals) draws++;
    else losses++;
  }

  const matchesPlayed = relevant.length;
  const winRate = matchesPlayed === 0 ? 0 : (wins / matchesPlayed) * 100;

  return { team, matchesPlayed, wins, draws, losses, goalsFor, goalsAgainst, winRate };
}

export interface TeamComparison {
  teamA: TeamRecord;
  teamB: TeamRecord;
  headToHead: HeadToHeadResult;
}

export function compareTeams(
  matches: Match[],
  teamA: string,
  teamB: string,
  options: TeamRecordOptions = {},
): TeamComparison {
  return {
    teamA: teamRecord(matches, teamA, options),
    teamB: teamRecord(matches, teamB, options),
    headToHead: headToHead(matches, teamA, teamB),
  };
}
