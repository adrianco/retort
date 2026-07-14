import type { SoccerDataStore } from "../data/store.js";
import type { Competition, TeamRecord } from "../types.js";
import { computeTeamRecord, filterMatches, resolveTeamKey } from "./helpers.js";

export interface TeamRecordOptions {
  competition?: Competition;
  season?: number;
  venue?: "home" | "away" | "all";
}

/** Computes a team's win/draw/loss record and goal tallies (Team Queries §2), optionally scoped to home/away, a competition, and/or a season. */
export function getTeamRecord(store: SoccerDataStore, team: string, options: TeamRecordOptions = {}): TeamRecord {
  const teamKey = resolveTeamKey(team);
  const venue = options.venue ?? "all";
  let matches = filterMatches(store.matches, {
    teamKey,
    competition: options.competition,
    season: options.season,
  });
  if (venue === "home") {
    matches = matches.filter((m) => m.homeTeamKey === teamKey);
  } else if (venue === "away") {
    matches = matches.filter((m) => m.awayTeamKey === teamKey);
  }
  return computeTeamRecord(matches, teamKey, store.displayNameFor(teamKey));
}

/** Lists the distinct competitions/source datasets a team appears in. */
export function competitionsForTeam(store: SoccerDataStore, team: string): string[] {
  const teamKey = resolveTeamKey(team);
  const labels = new Set<string>();
  for (const match of store.matches) {
    if (match.homeTeamKey === teamKey || match.awayTeamKey === teamKey) {
      labels.add(match.sourceLabel);
    }
  }
  return [...labels].sort();
}

/** Ranks all teams by a computed record within an optional competition/season, requiring at least minMatches to qualify. */
export function rankTeamsByRecord(
  store: SoccerDataStore,
  options: TeamRecordOptions & { minMatches?: number; limit?: number; sortBy?: "winRate" | "goalsFor" | "goalDifference" } = {},
): TeamRecord[] {
  const minMatches = options.minMatches ?? 5;
  const sortBy = options.sortBy ?? "winRate";
  const matches = filterMatches(store.matches, { competition: options.competition, season: options.season });

  const teamKeys = new Set<string>();
  for (const match of matches) {
    if (options.venue === "home") {
      teamKeys.add(match.homeTeamKey);
    } else if (options.venue === "away") {
      teamKeys.add(match.awayTeamKey);
    } else {
      teamKeys.add(match.homeTeamKey);
      teamKeys.add(match.awayTeamKey);
    }
  }

  const records = [...teamKeys]
    .map((teamKey) => getTeamRecord(store, store.displayNameFor(teamKey), options))
    .filter((record) => record.matches >= minMatches);

  records.sort((a, b) => {
    if (sortBy === "goalsFor") return b.goalsFor - a.goalsFor;
    if (sortBy === "goalDifference") return b.goalsFor - b.goalsAgainst - (a.goalsFor - a.goalsAgainst);
    return b.winRate - a.winRate;
  });

  return options.limit ? records.slice(0, options.limit) : records;
}
