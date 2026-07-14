import { teamKeyMatchesQuery } from "../normalize.js";
import type { Dataset } from "../types.js";
import { competitionMatches } from "./shared.js";

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
  winRatePct: number;
}

/** Aggregate win/draw/loss and goal record for a team, optionally scoped to
 * a competition, season and/or home/away venue. */
export function teamRecord(dataset: Dataset, team: string, opts: TeamRecordOptions = {}): TeamRecord {
  const venue = opts.venue ?? "all";

  let matches = dataset.matches.filter((m) => {
    const isHome = teamKeyMatchesQuery(m.homeTeam, team);
    const isAway = teamKeyMatchesQuery(m.awayTeam, team);
    if (venue === "home") return isHome;
    if (venue === "away") return isAway;
    return isHome || isAway;
  });

  if (opts.competition) matches = matches.filter((m) => competitionMatches(m, opts.competition!));
  if (opts.season !== undefined) matches = matches.filter((m) => m.season === opts.season);

  let wins = 0;
  let draws = 0;
  let losses = 0;
  let goalsFor = 0;
  let goalsAgainst = 0;
  let played = 0;

  for (const m of matches) {
    if (m.homeGoals === null || m.awayGoals === null) continue;
    const isHome = teamKeyMatchesQuery(m.homeTeam, team);
    const forGoals = isHome ? m.homeGoals : m.awayGoals;
    const againstGoals = isHome ? m.awayGoals : m.homeGoals;
    played += 1;
    goalsFor += forGoals;
    goalsAgainst += againstGoals;
    if (forGoals > againstGoals) wins += 1;
    else if (forGoals < againstGoals) losses += 1;
    else draws += 1;
  }

  return {
    team,
    matchesPlayed: played,
    wins,
    draws,
    losses,
    goalsFor,
    goalsAgainst,
    winRatePct: played > 0 ? (wins / played) * 100 : 0,
  };
}

export interface TeamCompetitionsResult {
  team: string;
  competitions: { competition: string; matches: number; seasons: number[] }[];
}

/** Which competitions/datasets a team appears in, and across which seasons. */
export function teamCompetitions(dataset: Dataset, team: string): TeamCompetitionsResult {
  const matches = dataset.matches.filter(
    (m) => teamKeyMatchesQuery(m.homeTeam, team) || teamKeyMatchesQuery(m.awayTeam, team),
  );

  const byCompetition = new Map<string, { matches: number; seasons: Set<number> }>();
  for (const m of matches) {
    let entry = byCompetition.get(m.competition);
    if (!entry) {
      entry = { matches: 0, seasons: new Set() };
      byCompetition.set(m.competition, entry);
    }
    entry.matches += 1;
    if (m.season !== null) entry.seasons.add(m.season);
  }

  const competitions = [...byCompetition.entries()]
    .map(([competition, entry]) => ({
      competition,
      matches: entry.matches,
      seasons: [...entry.seasons].sort((a, b) => a - b),
    }))
    .sort((a, b) => b.matches - a.matches);

  return { team, competitions };
}
