/*
 * ============================================================================
 * Context
 * ----------------------------------------------------------------------------
 * Module:  src/format.ts
 * Purpose: Render query results into the human-readable text shown in the spec
 *          ("Flamengo 2-1 Fluminense (Brasileirão Round 22)", standings tables,
 *          player lists, etc.). MCP tools return both this text and structured
 *          JSON; the text is what an LLM/end-user reads.
 * Inputs:  Query-layer result objects.
 * Outputs: Formatted strings.
 * Notes:   Pure formatting only — no data access.
 * ============================================================================
 */

import type { Match, Player, StandingRow } from "./data/types.js";
import type { HeadToHead } from "./queries/matches.js";
import type { TeamRecord } from "./data/types.js";

/** Format a single match as a one-line summary. */
export function formatMatch(m: Match): string {
  const date = m.date ?? "????-??-??";
  const score =
    m.homeGoals != null && m.awayGoals != null
      ? `${m.homeGoals}-${m.awayGoals}`
      : "vs";
  const ctx: string[] = [m.competition];
  if (m.round) ctx.push(`Round ${m.round}`);
  if (m.stage) ctx.push(m.stage);
  return `${date}: ${m.homeTeam} ${score} ${m.awayTeam} (${ctx.join(", ")})`;
}

/** Format a list of matches with an optional cap and "N more" note. */
export function formatMatchList(matches: Match[], cap = 25): string {
  if (matches.length === 0) return "No matches found.";
  const shown = matches.slice(0, cap);
  const lines = shown.map((m) => `- ${formatMatch(m)}`);
  if (matches.length > cap) {
    lines.push(`- ... (${matches.length - cap} more matches in dataset)`);
  }
  return lines.join("\n");
}

/** Format a head-to-head summary block. */
export function formatHeadToHead(h: HeadToHead): string {
  const header = `${h.team1} vs ${h.team2} — head-to-head (dataset):`;
  const record =
    `Total matches: ${h.totalMatches} | ` +
    `${h.team1} ${h.team1Wins} wins, ${h.team2} ${h.team2Wins} wins, ${h.draws} draws | ` +
    `Goals: ${h.team1} ${h.team1Goals} - ${h.team2Goals} ${h.team2}`;
  const list = formatMatchList(h.matches, 10);
  return `${header}\n${record}\n\nRecent meetings:\n${list}`;
}

/** Format a team's W/D/L + goals record. */
export function formatTeamRecord(rec: TeamRecord, scope = ""): string {
  const rate =
    rec.played === 0
      ? "0.0%"
      : `${((rec.wins / rec.played) * 100).toFixed(1)}%`;
  const title = scope ? `${rec.team} record (${scope}):` : `${rec.team} record:`;
  return [
    title,
    `- Matches: ${rec.played}`,
    `- Wins: ${rec.wins}, Draws: ${rec.draws}, Losses: ${rec.losses}`,
    `- Goals For: ${rec.goalsFor}, Goals Against: ${rec.goalsAgainst}`,
    `- Points: ${rec.points}`,
    `- Win rate: ${rate}`,
  ].join("\n");
}

/** Format a league standings table. */
export function formatStandings(
  rows: StandingRow[],
  title: string,
  cap = 30,
): string {
  if (rows.length === 0) return `No data to compute standings for ${title}.`;
  const lines = [`${title} (calculated from matches):`];
  const shown = rows.slice(0, cap);
  for (const r of shown) {
    const tag =
      r.position === 1 ? " - Champion" : "";
    lines.push(
      `${r.position}. ${r.team} - ${r.points} pts ` +
        `(${r.wins}W, ${r.draws}D, ${r.losses}L, GF ${r.goalsFor}, GA ${r.goalsAgainst}, GD ${r.goalDifference >= 0 ? "+" : ""}${r.goalDifference})${tag}`,
    );
  }
  return lines.join("\n");
}

/** Format a single player line. */
export function formatPlayer(p: Player, index?: number): string {
  const prefix = index != null ? `${index}. ` : "";
  const bits = [
    `Overall: ${p.overall ?? "?"}`,
    `Position: ${p.position || "?"}`,
    `Club: ${p.club || "Free agent"}`,
    `Nationality: ${p.nationality || "?"}`,
  ];
  if (p.age != null) bits.push(`Age: ${p.age}`);
  return `${prefix}${p.name} - ${bits.join(", ")}`;
}

/** Format a list of players. */
export function formatPlayerList(players: Player[], cap = 25): string {
  if (players.length === 0) return "No players found.";
  const shown = players.slice(0, cap);
  const lines = shown.map((p, i) => formatPlayer(p, i + 1));
  if (players.length > cap) {
    lines.push(`... (${players.length - cap} more players in dataset)`);
  }
  return lines.join("\n");
}
