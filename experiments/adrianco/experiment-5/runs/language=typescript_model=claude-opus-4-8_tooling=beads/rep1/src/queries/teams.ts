/**
 * ============================================================================
 * Context
 * ----------------------------------------------------------------------------
 * Module:  src/queries/teams.ts
 * Purpose: Team-centric statistics — overall and home/away win/draw/loss
 *          records, goals for/against, and win rate, optionally scoped by
 *          competition and season.
 *
 * Backs the MCP tool `team_stats`. All tallies run on deduplicated matches
 * (see common.ts) so overlapping source files do not inflate the numbers.
 * ============================================================================
 */

import type { Dataset, Match } from "../data/types.js";
import { displayTeamName, teamMatches } from "../data/normalize.js";
import {
  MatchFilter,
  dedupeMatches,
  filterMatches,
} from "./common.js";

export interface Record3 {
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  winRate: number;
}

export interface TeamStats {
  team: string;
  scope: string;
  overall: Record3;
  home: Record3;
  away: Record3;
  text: string;
}

function emptyRecord(): Record3 {
  return {
    matches: 0,
    wins: 0,
    draws: 0,
    losses: 0,
    goalsFor: 0,
    goalsAgainst: 0,
    winRate: 0,
  };
}

function tally(rec: Record3, gf: number, ga: number): void {
  rec.matches++;
  rec.goalsFor += gf;
  rec.goalsAgainst += ga;
  if (gf > ga) rec.wins++;
  else if (gf < ga) rec.losses++;
  else rec.draws++;
}

function finalize(rec: Record3): void {
  rec.winRate = rec.matches > 0 ? (rec.wins / rec.matches) * 100 : 0;
}

/** Compute win/draw/loss and goal records for a team. */
export function teamStats(
  ds: Dataset,
  team: string,
  filter: Omit<MatchFilter, "team" | "teamSide"> = {}
): TeamStats {
  const games = dedupeMatches(
    filterMatches(ds.matches, { ...filter, team, teamSide: "either" })
  );

  const overall = emptyRecord();
  const home = emptyRecord();
  const away = emptyRecord();

  for (const m of games) {
    if (m.homeGoal == null || m.awayGoal == null) continue;
    const isHome = teamMatches(team, m.homeKey);
    const gf = isHome ? m.homeGoal : m.awayGoal;
    const ga = isHome ? m.awayGoal : m.homeGoal;
    tally(overall, gf, ga);
    tally(isHome ? home : away, gf, ga);
  }
  [overall, home, away].forEach(finalize);

  const name = displayTeamName(team);
  const scopeParts: string[] = [];
  if (filter.competition) scopeParts.push(filter.competition);
  if (filter.season != null) scopeParts.push(String(filter.season));
  const scope = scopeParts.length ? scopeParts.join(" ") : "all competitions";

  const fmt = (label: string, r: Record3) =>
    `${label}: ${r.matches} matches — ${r.wins}W ${r.draws}D ${r.losses}L, ` +
    `GF ${r.goalsFor} GA ${r.goalsAgainst}, win rate ${r.winRate.toFixed(1)}%`;

  const text =
    `${name} (${scope}):\n` +
    `${fmt("Overall", overall)}\n` +
    `${fmt("Home", home)}\n` +
    `${fmt("Away", away)}`;

  return { team: name, scope, overall, home, away, text };
}
