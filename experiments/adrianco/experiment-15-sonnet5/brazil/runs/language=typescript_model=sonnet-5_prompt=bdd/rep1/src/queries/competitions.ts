import type { SoccerDataStore } from "../data/store.js";
import type { Competition, StandingsRow } from "../types.js";
import { filterMatches, resultForTeam } from "./helpers.js";

const POINTS_FOR_WIN = 3;
const POINTS_FOR_DRAW = 1;

/**
 * Calculates a league table for a competition/season from the raw match
 * results (Competition Queries §4). Standings are derived, not sourced
 * from a pre-computed table, so they reflect only the matches present in
 * the dataset for that season.
 */
export function calculateStandings(store: SoccerDataStore, competition: Competition, season: number): StandingsRow[] {
  const matches = filterMatches(store.matches, { competition, season });

  const teamKeys = new Set<string>();
  for (const match of matches) {
    teamKeys.add(match.homeTeamKey);
    teamKeys.add(match.awayTeamKey);
  }

  const rows: StandingsRow[] = [];
  for (const teamKey of teamKeys) {
    let wins = 0;
    let draws = 0;
    let losses = 0;
    let goalsFor = 0;
    let goalsAgainst = 0;
    let played = 0;
    for (const match of matches) {
      const result = resultForTeam(match, teamKey);
      if (!result) continue;
      played += 1;
      goalsFor += result.goalsFor;
      goalsAgainst += result.goalsAgainst;
      if (result.outcome === "win") wins += 1;
      else if (result.outcome === "draw") draws += 1;
      else losses += 1;
    }
    if (played === 0) continue;
    rows.push({
      team: store.displayNameFor(teamKey),
      matches: played,
      wins,
      draws,
      losses,
      goalsFor,
      goalsAgainst,
      winRate: played > 0 ? wins / played : 0,
      points: wins * POINTS_FOR_WIN + draws * POINTS_FOR_DRAW,
      position: 0,
    });
  }

  // Tie-break order follows CBF regulations: points, then wins, then goal
  // difference, then goals scored.
  rows.sort((a, b) => {
    if (b.points !== a.points) return b.points - a.points;
    if (b.wins !== a.wins) return b.wins - a.wins;
    const goalDiffA = a.goalsFor - a.goalsAgainst;
    const goalDiffB = b.goalsFor - b.goalsAgainst;
    if (goalDiffB !== goalDiffA) return goalDiffB - goalDiffA;
    return b.goalsFor - a.goalsFor;
  });
  rows.forEach((row, index) => {
    row.position = index + 1;
  });

  return rows;
}

/** Returns the bottom N teams of a calculated table, a proxy for relegation (exact relegation rules varied by year and aren't encoded in the match data). */
export function bottomOfTable(store: SoccerDataStore, competition: Competition, season: number, count = 4): StandingsRow[] {
  const standings = calculateStandings(store, competition, season);
  return standings.slice(Math.max(0, standings.length - count));
}

/** Lists the seasons for which a competition has match data. */
export function seasonsForCompetition(store: SoccerDataStore, competition: Competition): number[] {
  const seasons = new Set<number>();
  for (const match of store.matches) {
    if (match.competition === competition && match.season !== null) {
      seasons.add(match.season);
    }
  }
  return [...seasons].sort((a, b) => a - b);
}
