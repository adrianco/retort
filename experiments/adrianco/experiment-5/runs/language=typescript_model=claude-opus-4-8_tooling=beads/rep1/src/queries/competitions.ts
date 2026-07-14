/**
 * ============================================================================
 * Context
 * ----------------------------------------------------------------------------
 * Module:  src/queries/competitions.ts
 * Purpose: Competition-level queries — league standings computed from match
 *          results (3 points for a win, 1 for a draw), and the champion /
 *          relegation picture for a season.
 *
 * Backs the MCP tools `standings` and `season_summary`. Standings are computed
 * from deduplicated matches so the three overlapping Serie A sources do not
 * inflate points. Sorting follows the Brazilian convention: points, then wins,
 * then goal difference, then goals for.
 * ============================================================================
 */

import type { Dataset, Match } from "../data/types.js";
import { dedupeMatches, filterMatches } from "./common.js";

export interface StandingRow {
  rank: number;
  team: string;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDiff: number;
  points: number;
}

export interface StandingsResult {
  competition: string;
  season: number;
  rows: StandingRow[];
  text: string;
}

interface Acc {
  team: string;
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
}

/** Compute a league table for a competition + season from match results. */
export function standings(
  ds: Dataset,
  competition: string,
  season: number
): StandingsResult {
  const games = dedupeMatches(
    filterMatches(ds.matches, { competition, season })
  );

  // Group by normalized key (so differing display spellings of the same club
  // merge into one row), keeping the first-seen display name for output.
  const table = new Map<string, Acc>();
  const get = (key: string, display: string): Acc => {
    let a = table.get(key);
    if (!a) {
      a = {
        team: display,
        played: 0,
        wins: 0,
        draws: 0,
        losses: 0,
        goalsFor: 0,
        goalsAgainst: 0,
      };
      table.set(key, a);
    }
    return a;
  };

  for (const m of games) {
    if (m.homeGoal == null || m.awayGoal == null) continue;
    const h = get(m.homeKey, m.homeTeam);
    const a = get(m.awayKey, m.awayTeam);
    h.played++;
    a.played++;
    h.goalsFor += m.homeGoal;
    h.goalsAgainst += m.awayGoal;
    a.goalsFor += m.awayGoal;
    a.goalsAgainst += m.homeGoal;
    if (m.homeGoal > m.awayGoal) {
      h.wins++;
      a.losses++;
    } else if (m.homeGoal < m.awayGoal) {
      a.wins++;
      h.losses++;
    } else {
      h.draws++;
      a.draws++;
    }
  }

  const rows: StandingRow[] = [...table.values()]
    .map((a) => ({
      rank: 0,
      team: a.team,
      played: a.played,
      wins: a.wins,
      draws: a.draws,
      losses: a.losses,
      goalsFor: a.goalsFor,
      goalsAgainst: a.goalsAgainst,
      goalDiff: a.goalsFor - a.goalsAgainst,
      points: a.wins * 3 + a.draws,
    }))
    .sort(
      (x, y) =>
        y.points - x.points ||
        y.wins - x.wins ||
        y.goalDiff - x.goalDiff ||
        y.goalsFor - x.goalsFor ||
        x.team.localeCompare(y.team)
    );
  rows.forEach((r, i) => (r.rank = i + 1));

  const lines = rows.map(
    (r) =>
      `${String(r.rank).padStart(2)}. ${r.team} — ${r.points} pts ` +
      `(${r.wins}W ${r.draws}D ${r.losses}L, GF ${r.goalsFor} GA ${r.goalsAgainst}, GD ${r.goalDiff >= 0 ? "+" : ""}${r.goalDiff})`
  );
  const header =
    rows.length > 0
      ? `${competition} ${season} — final standings (calculated from ${games.length} matches):`
      : `No matches found for ${competition} ${season}.`;
  const text = `${header}${lines.length ? "\n" + lines.join("\n") : ""}`;

  return { competition, season, rows, text };
}

export interface SeasonSummary {
  competition: string;
  season: number;
  champion: string | null;
  relegated: string[];
  totalTeams: number;
  text: string;
}

/**
 * Summarize a league season: champion (top of table) and the relegation zone
 * (bottom 4, the Brazilian Série A convention) when there are enough teams.
 */
export function seasonSummary(
  ds: Dataset,
  competition: string,
  season: number,
  relegationSpots = 4
): SeasonSummary {
  const { rows } = standings(ds, competition, season);
  const champion = rows[0]?.team ?? null;
  const relegated =
    rows.length > relegationSpots
      ? rows.slice(rows.length - relegationSpots).map((r) => r.team)
      : [];

  const text =
    rows.length === 0
      ? `No data for ${competition} ${season}.`
      : `${competition} ${season}: champion ${champion} (${rows[0].points} pts).` +
        (relegated.length
          ? `\nRelegation zone (bottom ${relegationSpots}): ${relegated.join(", ")}`
          : "");

  return {
    competition,
    season,
    champion,
    relegated,
    totalTeams: rows.length,
    text,
  };
}
