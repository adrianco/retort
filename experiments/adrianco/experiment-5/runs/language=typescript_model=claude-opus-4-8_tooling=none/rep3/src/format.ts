/**
 * ============================================================================
 * Context: Brazilian Soccer MCP Server — Output Formatting
 * ----------------------------------------------------------------------------
 * Purpose : Render query results as compact, human-readable text matching the
 *           answer formats in the spec (match lists, team records, standings,
 *           player rankings). These strings are what the MCP tools return to
 *           the LLM, so they are kept terse and information-dense.
 * Consumers: server.ts.
 * ============================================================================
 */

import type { Match, Player, StandingRow, TeamRecord } from "./types.js";
import type { AggregateStats, HeadToHead, TeamRanking } from "./queries.js";

function score(m: Match): string {
  const h = m.homeGoals === null ? "?" : m.homeGoals;
  const a = m.awayGoals === null ? "?" : m.awayGoals;
  return `${h}-${a}`;
}

function context(m: Match): string {
  const bits = [m.competition];
  if (m.round) bits.push(`Round ${m.round}`);
  if (m.stage) bits.push(m.stage);
  return bits.join(", ");
}

/** Format a single match line: `2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Série A, Round 22)`. */
export function formatMatch(m: Match): string {
  const date = m.date ?? "date unknown";
  return `${date}: ${m.homeTeam} ${score(m)} ${m.awayTeam} (${context(m)})`;
}

export function formatMatchList(matches: Match[], limit = 25): string {
  if (matches.length === 0) return "No matches found.";
  const shown = matches.slice(0, limit).map((m) => `- ${formatMatch(m)}`);
  let out = shown.join("\n");
  if (matches.length > limit) {
    out += `\n- ... (${matches.length - limit} more match${matches.length - limit === 1 ? "" : "es"})`;
  }
  out = `Found ${matches.length} match${matches.length === 1 ? "" : "es"}:\n${out}`;
  return out;
}

export function formatTeamRecord(r: TeamRecord, heading?: string): string {
  const head = heading ?? `${r.team} record`;
  return [
    `${head}:`,
    `- Matches: ${r.matches}`,
    `- Wins: ${r.wins}, Draws: ${r.draws}, Losses: ${r.losses}`,
    `- Goals For: ${r.goalsFor}, Goals Against: ${r.goalsAgainst} (GD ${r.goalsFor - r.goalsAgainst})`,
    `- Points: ${r.points}`,
    `- Win rate: ${(r.winRate * 100).toFixed(1)}%`,
  ].join("\n");
}

export function formatHeadToHead(h: HeadToHead): string {
  const lines = [
    `Head-to-head: ${h.teamA} vs ${h.teamB} (${h.matches.length} meetings in dataset)`,
    `- ${h.teamA} wins: ${h.teamAWins}`,
    `- ${h.teamB} wins: ${h.teamBWins}`,
    `- Draws: ${h.draws}`,
    `- Goals: ${h.teamA} ${h.teamAGoals} — ${h.teamBGoals} ${h.teamB}`,
  ];
  if (h.matches.length > 0) {
    lines.push("", "Recent meetings:");
    for (const m of h.matches.slice(0, 10)) lines.push(`- ${formatMatch(m)}`);
  }
  return lines.join("\n");
}

export function formatPlayer(p: Player, index?: number): string {
  const prefix = index !== undefined ? `${index}. ` : "";
  const rating = p.overall ?? "?";
  const parts = [`${prefix}${p.name} — Overall: ${rating}`];
  if (p.position) parts.push(`Position: ${p.position}`);
  if (p.club) parts.push(`Club: ${p.club}`);
  if (p.nationality) parts.push(`Nationality: ${p.nationality}`);
  if (p.age !== null) parts.push(`Age: ${p.age}`);
  return parts.join(", ");
}

export function formatPlayerList(players: Player[], total?: number): string {
  if (players.length === 0) return "No players found.";
  const header = `Found ${total ?? players.length} player${(total ?? players.length) === 1 ? "" : "s"}${
    total && total > players.length ? ` (showing top ${players.length})` : ""
  }:`;
  const lines = players.map((p, i) => formatPlayer(p, i + 1));
  return [header, ...lines].join("\n");
}

export function formatStandings(rows: StandingRow[], title: string, limit = 30): string {
  if (rows.length === 0) return `No standings could be calculated for ${title}.`;
  const lines = rows.slice(0, limit).map((r) => {
    const marker = r.position === 1 ? " — Champion" : "";
    return `${r.position}. ${r.team} — ${r.points} pts (${r.wins}W ${r.draws}D ${r.losses}L, GF ${r.goalsFor} GA ${r.goalsAgainst}, GD ${r.goalDifference >= 0 ? "+" : ""}${r.goalDifference})${marker}`;
  });
  return [`${title} (calculated from matches):`, ...lines].join("\n");
}

export function formatAggregate(stats: AggregateStats, label: string): string {
  return [
    `${label}:`,
    `- Matches (with score): ${stats.matchesWithScore} / ${stats.matches}`,
    `- Total goals: ${stats.totalGoals}`,
    `- Average goals per match: ${stats.goalsPerMatch.toFixed(2)}`,
    `- Home win rate: ${(stats.homeWinRate * 100).toFixed(1)}%`,
    `- Away win rate: ${(stats.awayWinRate * 100).toFixed(1)}%`,
    `- Draw rate: ${(stats.drawRate * 100).toFixed(1)}%`,
  ].join("\n");
}

export function formatTeamRankings(rankings: TeamRanking[], label: string, asPercent = false): string {
  if (rankings.length === 0) return `No teams found for ${label}.`;
  const lines = rankings.map((r, i) => {
    const v = asPercent ? `${(r.value * 100).toFixed(1)}%` : `${r.value}`;
    return `${i + 1}. ${r.team} — ${v} (${r.record.wins}W ${r.record.draws}D ${r.record.losses}L over ${r.record.matches} matches)`;
  });
  return [`${label}:`, ...lines].join("\n");
}
