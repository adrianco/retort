/**
 * ============================================================================
 * Context Block
 * ----------------------------------------------------------------------------
 * File:    src/format.ts
 * Project: Brazilian Soccer MCP Server
 * Purpose: Render query results into the human-readable text shown in the
 *          specification's "Example answer format" blocks. The MCP tools return
 *          these strings so an LLM/end-user gets nicely formatted answers, while
 *          also returning structured JSON for programmatic use.
 * ============================================================================
 */

import type { Match, Player, StandingRow, TeamRecord } from './types.js';

function comp(m: Match): string {
  const parts = [m.competition];
  if (m.round != null) parts.push(`Round ${m.round}`);
  else if (m.stage) parts.push(m.stage);
  return parts.join(' ');
}

export function formatMatchLine(m: Match): string {
  const date = m.date ?? `${m.season}`;
  return `${date}: ${m.homeTeam} ${m.homeGoal}-${m.awayGoal} ${m.awayTeam} (${comp(m)})`;
}

export function formatMatches(matches: Match[], heading?: string, shownLimit = 20): string {
  if (matches.length === 0) return heading ? `${heading}\nNo matches found.` : 'No matches found.';
  const lines: string[] = [];
  if (heading) lines.push(heading);
  const shown = matches.slice(0, shownLimit);
  for (const m of shown) lines.push(`- ${formatMatchLine(m)}`);
  if (matches.length > shown.length) {
    lines.push(`- ... (${matches.length - shown.length} more matches)`);
  }
  return lines.join('\n');
}

export function formatHeadToHead(h2h: {
  team1: string;
  team2: string;
  competition: string;
  totalMatches: number;
  team1Wins: number;
  team2Wins: number;
  draws: number;
  team1Goals: number;
  team2Goals: number;
  matches: Match[];
}): string {
  const lines: string[] = [];
  lines.push(`${h2h.team1} vs ${h2h.team2} (${h2h.competition}):`);
  lines.push(formatMatches(h2h.matches, undefined, 15));
  lines.push('');
  lines.push(
    `Head-to-head in dataset: ${h2h.team1} ${h2h.team1Wins} wins, ` +
      `${h2h.team2} ${h2h.team2Wins} wins, ${h2h.draws} draws ` +
      `(goals ${h2h.team1Goals}-${h2h.team2Goals})`,
  );
  return lines.join('\n');
}

export function formatTeamRecord(
  rec: TeamRecord,
  context: { season?: number; competition?: string; venue?: string } = {},
): string {
  const ctxParts: string[] = [];
  if (context.venue) ctxParts.push(`${context.venue} record`);
  else ctxParts.push('record');
  const ctx: string[] = [];
  if (context.season != null) ctx.push(String(context.season));
  if (context.competition) ctx.push(context.competition);
  const ctxStr = ctx.length ? ` (${ctx.join(' ')})` : '';
  return [
    `${rec.team} ${ctxParts.join(' ')}${ctxStr}:`,
    `- Matches: ${rec.matches}`,
    `- Wins: ${rec.wins}, Draws: ${rec.draws}, Losses: ${rec.losses}`,
    `- Goals For: ${rec.goalsFor}, Goals Against: ${rec.goalsAgainst}`,
    `- Points: ${rec.points}`,
    `- Win rate: ${rec.winRate}%`,
  ].join('\n');
}

export function formatStandings(
  rows: StandingRow[],
  competition: string,
  season: number,
  limit = 20,
): string {
  if (rows.length === 0) {
    return `No standings available for ${competition} ${season}.`;
  }
  const lines: string[] = [];
  lines.push(`${season} ${competition} Standings (calculated from matches):`);
  const shown = rows.slice(0, limit);
  for (const r of shown) {
    const tag = r.position === 1 ? ' - Champion' : '';
    lines.push(
      `${r.position}. ${r.team} - ${r.points} pts ` +
        `(${r.wins}W, ${r.draws}D, ${r.losses}L, GD ${r.goalDifference >= 0 ? '+' : ''}${r.goalDifference})${tag}`,
    );
  }
  if (rows.length > shown.length) {
    lines.push(`... (${rows.length - shown.length} more teams)`);
  }
  return lines.join('\n');
}

export function formatPlayer(p: Player, index?: number): string {
  const prefix = index != null ? `${index}. ` : '';
  const rating = p.overall != null ? `Overall: ${p.overall}` : 'Overall: n/a';
  return `${prefix}${p.name} - ${rating}, Position: ${p.position || 'n/a'}, Club: ${p.club || 'n/a'}, Nationality: ${p.nationality || 'n/a'}`;
}

export function formatPlayers(players: Player[], heading?: string, limit = 25): string {
  if (players.length === 0) return heading ? `${heading}\nNo players found.` : 'No players found.';
  const lines: string[] = [];
  if (heading) lines.push(heading);
  const shown = players.slice(0, limit);
  shown.forEach((p, i) => lines.push(formatPlayer(p, i + 1)));
  if (players.length > shown.length) {
    lines.push(`... (${players.length - shown.length} more players)`);
  }
  return lines.join('\n');
}
