/**
 * ============================================================================
 * Context
 * ----------------------------------------------------------------------------
 * Module:  src/queries/matches.ts
 * Purpose: Match-centric queries — searching matches by team / competition /
 *          season / date range, and computing head-to-head records between two
 *          teams.
 *
 * Backs the MCP tools `search_matches` and `head_to_head`. Searches return the
 * raw (non-deduplicated) match list so users see every record; head-to-head
 * deduplicates first so win/draw/loss tallies are accurate.
 * ============================================================================
 */

import type { Dataset, Match } from "../data/types.js";
import { displayTeamName, teamMatches } from "../data/normalize.js";
import {
  MatchFilter,
  dedupeMatches,
  filterMatches,
  formatMatch,
  outcomeFor,
  sortByDateDesc,
} from "./common.js";

export interface MatchSearchResult {
  count: number;
  matches: Match[];
  text: string;
}

/** Search matches by the given filter; returns up to `limit` most-recent. */
export function searchMatches(
  ds: Dataset,
  filter: MatchFilter,
  limit = 25
): MatchSearchResult {
  const all = sortByDateDesc(dedupeMatches(filterMatches(ds.matches, filter)));
  const shown = all.slice(0, limit);

  const header = describeFilter(filter, all.length);
  const lines = shown.map((m) => `- ${formatMatch(m)}`);
  let text = `${header}\n${lines.join("\n")}`;
  if (all.length > shown.length) {
    text += `\n... (${all.length - shown.length} more not shown)`;
  }
  if (all.length === 0) text = `${header}\n(no matches found)`;

  return { count: all.length, matches: shown, text };
}

function describeFilter(f: MatchFilter, total: number): string {
  const parts: string[] = [];
  if (f.team) parts.push(`team "${displayTeamName(f.team)}"`);
  if (f.opponent) parts.push(`vs "${displayTeamName(f.opponent)}"`);
  if (f.competition) parts.push(f.competition);
  if (f.season != null) parts.push(`season ${f.season}`);
  if (f.from || f.to) parts.push(`${f.from ?? "…"} → ${f.to ?? "…"}`);
  const scope = parts.length ? parts.join(", ") : "all competitions";
  return `Found ${total} match(es) for ${scope}:`;
}

export interface HeadToHead {
  teamA: string;
  teamB: string;
  total: number;
  teamAWins: number;
  teamBWins: number;
  draws: number;
  teamAGoals: number;
  teamBGoals: number;
  matches: Match[];
  text: string;
}

/** Compute the head-to-head record between two teams across all competitions. */
export function headToHead(
  ds: Dataset,
  teamA: string,
  teamB: string,
  filter: Omit<MatchFilter, "team" | "opponent"> = {}
): HeadToHead {
  const games = dedupeMatches(
    filterMatches(ds.matches, { ...filter, team: teamA, opponent: teamB })
  );

  let aWins = 0,
    bWins = 0,
    draws = 0,
    aGoals = 0,
    bGoals = 0;

  for (const m of games) {
    if (m.homeGoal == null || m.awayGoal == null) continue;
    const res = outcomeFor(m, teamA);
    if (res === "win") aWins++;
    else if (res === "loss") bWins++;
    else if (res === "draw") draws++;

    // Goal tallies from team A's perspective.
    const aIsHome = teamMatches(teamA, m.homeKey);
    if (aIsHome) {
      aGoals += m.homeGoal;
      bGoals += m.awayGoal;
    } else {
      aGoals += m.awayGoal;
      bGoals += m.homeGoal;
    }
  }

  const nameA = displayTeamName(teamA);
  const nameB = displayTeamName(teamB);
  const sorted = sortByDateDesc(games);

  const recent = sorted.slice(0, 10).map((m) => `- ${formatMatch(m)}`);
  const text =
    `Head-to-head: ${nameA} vs ${nameB}\n` +
    `Total matches: ${games.length}\n` +
    `${nameA} wins: ${aWins}, ${nameB} wins: ${bWins}, draws: ${draws}\n` +
    `Goals: ${nameA} ${aGoals} - ${bGoals} ${nameB}\n` +
    (recent.length ? `\nMost recent meetings:\n${recent.join("\n")}` : "");

  return {
    teamA: nameA,
    teamB: nameB,
    total: games.length,
    teamAWins: aWins,
    teamBWins: bWins,
    draws,
    teamAGoals: aGoals,
    teamBGoals: bGoals,
    matches: sorted,
    text,
  };
}
