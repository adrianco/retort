import { teamsMatch } from "./normalize.js";
import { isWithinDateRange } from "./dates.js";
import type { Match } from "./types.js";

export interface MatchSearchOptions {
  opponent?: string;
  competition?: string;
  season?: number;
  startDate?: string;
  endDate?: string;
}

function matchesOptions(match: Match, options: MatchSearchOptions): boolean {
  if (options.opponent) {
    const opponentPlayed = teamsMatch(match.homeTeam, options.opponent) || teamsMatch(match.awayTeam, options.opponent);
    if (!opponentPlayed) return false;
  }
  if (options.competition && match.competition.toLowerCase() !== options.competition.toLowerCase()) {
    return false;
  }
  if (options.season !== undefined && match.season !== options.season) {
    return false;
  }
  if (!isWithinDateRange(match.date, options.startDate, options.endDate)) {
    return false;
  }
  return true;
}

export function findMatchesByTeam(
  matches: Match[],
  team: string,
  options: MatchSearchOptions = {},
): Match[] {
  return matches
    .filter((m) => teamsMatch(m.homeTeam, team) || teamsMatch(m.awayTeam, team))
    .filter((m) => matchesOptions(m, options))
    .sort((a, b) => b.date.getTime() - a.date.getTime());
}

export interface HeadToHeadResult {
  teamA: string;
  teamB: string;
  teamAWins: number;
  teamBWins: number;
  draws: number;
  matches: Match[];
}

export function headToHead(matches: Match[], teamA: string, teamB: string): HeadToHeadResult {
  const relevant = matches
    .filter(
      (m) =>
        (teamsMatch(m.homeTeam, teamA) && teamsMatch(m.awayTeam, teamB)) ||
        (teamsMatch(m.homeTeam, teamB) && teamsMatch(m.awayTeam, teamA)),
    )
    .sort((a, b) => b.date.getTime() - a.date.getTime());

  let teamAWins = 0;
  let teamBWins = 0;
  let draws = 0;

  for (const m of relevant) {
    if (m.homeGoals === m.awayGoals) {
      draws++;
      continue;
    }
    const winner = m.homeGoals > m.awayGoals ? m.homeTeam : m.awayTeam;
    if (teamsMatch(winner, teamA)) teamAWins++;
    else teamBWins++;
  }

  return { teamA, teamB, teamAWins, teamBWins, draws, matches: relevant };
}

function normalizedCompetitionKey(competition: string): string {
  const lower = competition.toLowerCase();
  if (lower === "serie a" || lower.includes("brasileir")) return "brasileirao";
  if (lower.includes("copa do brasil")) return "copa do brasil";
  return lower;
}

export function canonicalMatches(matches: Match[]): Match[] {
  const covered = new Set<string>();

  for (const m of matches) {
    if (m.source === "Brasileirao_Matches.csv") {
      covered.add(`brasileirao|${m.season}`);
    } else if (m.source === "Brazilian_Cup_Matches.csv") {
      covered.add(`copa do brasil|${m.season}`);
    }
  }

  return matches.filter((m) => {
    if (m.source === "novo_campeonato_brasileiro.csv" && m.season >= 2012) {
      return false;
    }
    if (m.source === "BR-Football-Dataset.csv") {
      const key = `${normalizedCompetitionKey(m.competition)}|${m.season}`;
      return !covered.has(key);
    }
    return true;
  });
}
