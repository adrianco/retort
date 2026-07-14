/**
 * ============================================================================
 * Context
 * ----------------------------------------------------------------------------
 * Module:  src/queries/common.ts
 * Purpose: Shared filtering / aggregation primitives used by every query
 *          module (matches, teams, competitions, stats).
 *
 * The provided datasets overlap (e.g. Serie A appears in three files), so
 * `dedupeMatches` is critical: any aggregation that counts matches must run on
 * a deduplicated set, otherwise standings and statistics double- or
 * triple-count the same game. Plain searches, by contrast, are allowed to show
 * every record so users see full coverage.
 * ============================================================================
 */

import type { Match, Outcome } from "../data/types.js";
import { teamMatches } from "../data/normalize.js";

/** Criteria for filtering matches. All fields are optional / ANDed together. */
export interface MatchFilter {
  /** Team that must appear (home OR away). */
  team?: string;
  /** Restrict the `team` above to home or away only. */
  teamSide?: "home" | "away" | "either";
  /** Second team — when set with `team`, restricts to head-to-head games. */
  opponent?: string;
  competition?: string;
  season?: number;
  /** Inclusive ISO date lower bound (YYYY-MM-DD). */
  from?: string;
  /** Inclusive ISO date upper bound (YYYY-MM-DD). */
  to?: string;
}

function involvesTeam(
  m: Match,
  team: string,
  side: "home" | "away" | "either"
): boolean {
  const home = teamMatches(team, m.homeKey);
  const away = teamMatches(team, m.awayKey);
  if (side === "home") return home;
  if (side === "away") return away;
  return home || away;
}

/** Apply a MatchFilter to a list of matches. */
export function filterMatches(matches: Match[], f: MatchFilter): Match[] {
  const fromD = f.from ? new Date(f.from + "T00:00:00Z") : null;
  const toD = f.to ? new Date(f.to + "T23:59:59Z") : null;

  return matches.filter((m) => {
    if (f.competition && m.competition !== f.competition) return false;
    if (f.season != null && m.season !== f.season) return false;
    if (f.team && !involvesTeam(m, f.team, f.teamSide ?? "either")) return false;
    if (f.opponent && !involvesTeam(m, f.opponent, "either")) return false;
    if (fromD && (!m.date || m.date < fromD)) return false;
    if (toD && (!m.date || m.date > toD)) return false;
    return true;
  });
}

/**
 * Stable key identifying a unique match regardless of source file.
 *
 * The same game often appears in multiple source files with slightly different
 * recorded dates (kick-off vs scheduled, timezone shifts), so a date-based key
 * misses cross-source duplicates. Within a single competition and season a
 * given home/away pairing occurs at most once (league round-robins and cup
 * legs are each played once per venue), so `competition|season|home|away` is a
 * reliable identity. When the season is unknown we fall back to the date so
 * undated/season-less records are not collapsed together.
 */
function matchIdentity(m: Match): string {
  if (m.season != null) {
    return `${m.competition}|${m.season}|${m.homeKey}|${m.awayKey}`;
  }
  const d = m.date ? m.date.toISOString().slice(0, 10) : m.rawDate;
  return `${m.competition}|${d}|${m.homeKey}|${m.awayKey}|${m.homeGoal}-${m.awayGoal}`;
}

/**
 * Remove duplicate matches that appear in more than one source file.
 * The first occurrence wins. Essential before any aggregation.
 */
export function dedupeMatches(matches: Match[]): Match[] {
  const seen = new Set<string>();
  const out: Match[] = [];
  for (const m of matches) {
    // A team cannot play itself; identical home/away keys signal a
    // mis-normalized name (e.g. an ambiguous "Atletico"), so drop the record.
    if (m.homeKey && m.homeKey === m.awayKey) continue;
    const id = matchIdentity(m);
    if (seen.has(id)) continue;
    seen.add(id);
    out.push(m);
  }
  return out;
}

/** Determine outcome of a match from a given team's perspective. */
export function outcomeFor(m: Match, teamQuery: string): Outcome | null {
  if (m.homeGoal == null || m.awayGoal == null) return null;
  const isHome = teamMatches(teamQuery, m.homeKey);
  const isAway = teamMatches(teamQuery, m.awayKey);
  if (!isHome && !isAway) return null;

  const gf = isHome ? m.homeGoal : m.awayGoal;
  const ga = isHome ? m.awayGoal : m.homeGoal;
  if (gf > ga) return "win";
  if (gf < ga) return "loss";
  return "draw";
}

/** Sort matches most-recent first (undated records sort last). */
export function sortByDateDesc(matches: Match[]): Match[] {
  return [...matches].sort((a, b) => {
    const ta = a.date ? a.date.getTime() : -Infinity;
    const tb = b.date ? b.date.getTime() : -Infinity;
    return tb - ta;
  });
}

/** Format a match for human-readable output. */
export function formatMatch(m: Match): string {
  const date = m.date ? m.date.toISOString().slice(0, 10) : m.rawDate || "????";
  const score =
    m.homeGoal != null && m.awayGoal != null
      ? `${m.homeGoal}-${m.awayGoal}`
      : "vs";
  const ctx: string[] = [m.competition];
  if (m.season != null) ctx.push(String(m.season));
  if (m.round != null) ctx.push(`Round ${m.round}`);
  if (m.stage) ctx.push(m.stage);
  return `${date}: ${m.homeTeam} ${score} ${m.awayTeam} (${ctx.join(", ")})`;
}
