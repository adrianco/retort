/**
 * ============================================================================
 * Context
 * ----------------------------------------------------------------------------
 * Module:  src/queries/stats.ts
 * Purpose: Aggregated statistical analysis across the match data — average
 *          goals per match, home-win rate, biggest victories, and a ranking of
 *          teams by goals scored.
 *
 * Backs the MCP tools `aggregate_stats`, `biggest_wins` and `top_scoring_teams`.
 * Everything operates on deduplicated matches so cross-file overlap does not
 * skew the averages.
 * ============================================================================
 */

import type { Dataset, Match } from "../data/types.js";
import {
  MatchFilter,
  dedupeMatches,
  filterMatches,
  formatMatch,
} from "./common.js";

export interface AggregateStats {
  matches: number;
  totalGoals: number;
  avgGoalsPerMatch: number;
  homeWins: number;
  awayWins: number;
  draws: number;
  homeWinRate: number;
  awayWinRate: number;
  drawRate: number;
  text: string;
}

/** Compute headline aggregate statistics for a filtered slice of matches. */
export function aggregateStats(
  ds: Dataset,
  filter: MatchFilter = {}
): AggregateStats {
  const games = dedupeMatches(filterMatches(ds.matches, filter)).filter(
    (m) => m.homeGoal != null && m.awayGoal != null
  );

  let totalGoals = 0,
    homeWins = 0,
    awayWins = 0,
    draws = 0;
  for (const m of games) {
    totalGoals += m.homeGoal! + m.awayGoal!;
    if (m.homeGoal! > m.awayGoal!) homeWins++;
    else if (m.homeGoal! < m.awayGoal!) awayWins++;
    else draws++;
  }
  const n = games.length;
  const pct = (x: number) => (n > 0 ? (x / n) * 100 : 0);

  const scope = describeScope(filter);
  const text =
    `Aggregate statistics (${scope}, ${n} matches):\n` +
    `Total goals: ${totalGoals}\n` +
    `Average goals per match: ${(n > 0 ? totalGoals / n : 0).toFixed(2)}\n` +
    `Home wins: ${homeWins} (${pct(homeWins).toFixed(1)}%)\n` +
    `Away wins: ${awayWins} (${pct(awayWins).toFixed(1)}%)\n` +
    `Draws: ${draws} (${pct(draws).toFixed(1)}%)`;

  return {
    matches: n,
    totalGoals,
    avgGoalsPerMatch: n > 0 ? totalGoals / n : 0,
    homeWins,
    awayWins,
    draws,
    homeWinRate: pct(homeWins),
    awayWinRate: pct(awayWins),
    drawRate: pct(draws),
    text,
  };
}

function describeScope(f: MatchFilter): string {
  const parts: string[] = [];
  if (f.competition) parts.push(f.competition);
  if (f.season != null) parts.push(String(f.season));
  if (f.team) parts.push(`team ${f.team}`);
  return parts.length ? parts.join(" ") : "all data";
}

export interface BiggestWinsResult {
  matches: Match[];
  text: string;
}

/** Find the matches with the largest goal margins. */
export function biggestWins(
  ds: Dataset,
  filter: MatchFilter = {},
  limit = 10
): BiggestWinsResult {
  const games = dedupeMatches(filterMatches(ds.matches, filter))
    .filter((m) => m.homeGoal != null && m.awayGoal != null)
    .map((m) => ({ m, margin: Math.abs(m.homeGoal! - m.awayGoal!) }))
    .sort(
      (a, b) =>
        b.margin - a.margin ||
        b.m.homeGoal! + b.m.awayGoal! - (a.m.homeGoal! + a.m.awayGoal!)
    )
    .slice(0, limit)
    .map((x) => x.m);

  const lines = games.map(
    (m, i) => `${i + 1}. ${formatMatch(m)} [margin ${Math.abs(m.homeGoal! - m.awayGoal!)}]`
  );
  const text =
    `Biggest victories (${describeScope(filter)}):\n` +
    (lines.length ? lines.join("\n") : "(no matches found)");

  return { matches: games, text };
}

export interface TeamGoalRow {
  team: string;
  goals: number;
  matches: number;
}

export interface TopScoringResult {
  rows: TeamGoalRow[];
  text: string;
}

/** Rank teams by total goals scored within a filtered slice. */
export function topScoringTeams(
  ds: Dataset,
  filter: MatchFilter = {},
  limit = 10
): TopScoringResult {
  const games = dedupeMatches(filterMatches(ds.matches, filter)).filter(
    (m) => m.homeGoal != null && m.awayGoal != null
  );

  // Key by normalized team key so differing spellings merge; keep a display name.
  const goals = new Map<string, { team: string; goals: number; matches: number }>();
  const add = (key: string, display: string, g: number) => {
    const cur = goals.get(key) ?? { team: display, goals: 0, matches: 0 };
    cur.goals += g;
    cur.matches += 1;
    goals.set(key, cur);
  };
  for (const m of games) {
    add(m.homeKey, m.homeTeam, m.homeGoal!);
    add(m.awayKey, m.awayTeam, m.awayGoal!);
  }

  const rows = [...goals.values()]
    .map((v) => ({ team: v.team, goals: v.goals, matches: v.matches }))
    .sort((a, b) => b.goals - a.goals || b.matches - a.matches)
    .slice(0, limit);

  const lines = rows.map(
    (r, i) => `${i + 1}. ${r.team} — ${r.goals} goals in ${r.matches} matches`
  );
  const text =
    `Top scoring teams (${describeScope(filter)}):\n` +
    (lines.length ? lines.join("\n") : "(no matches found)");

  return { rows, text };
}
