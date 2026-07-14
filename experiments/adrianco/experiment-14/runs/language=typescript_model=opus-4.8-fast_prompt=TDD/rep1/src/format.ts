/**
 * Human-readable formatters that render query results into the answer styles
 * shown in the specification. The MCP tools return these strings so that an LLM
 * (or a human reading the tool output) receives ready-to-present prose.
 */

import type { Match, Player, TeamRecord } from "./types.js";
import { formatDate } from "./normalize.js";
import type { Statistics } from "./database.js";

/** Render the competition context suffix: "(Brasileirão Série A Round 22)". */
function context(m: Match): string {
  const parts: string[] = [m.competition];
  if (m.round) parts.push(`Round ${m.round}`);
  if (m.stage) return `(${m.competition}, ${m.stage})`;
  return `(${parts.join(" ")})`;
}

/** Render a single match: "2023-09-03: Flamengo 2-1 Fluminense (...)". */
export function formatMatch(m: Match): string {
  return `${formatDate(m.date)}: ${m.homeTeam} ${m.homeGoals}-${m.awayGoals} ${m.awayTeam} ${context(m)}`;
}

function pct(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

/** Render a header followed by a bullet list of matches (capped, with a note). */
export function formatMatchList(
  matches: Match[],
  header: string,
  max = 25
): string {
  if (matches.length === 0) {
    return `${header}\nNo matches found.`;
  }
  const shown = matches.slice(0, max);
  const lines = shown.map((m) => `- ${formatMatch(m)}`);
  let out = `${header}\n${lines.join("\n")}`;
  if (matches.length > shown.length) {
    out += `\n- ... (${matches.length - shown.length} more matches in dataset)`;
  }
  return out;
}

export interface HeadToHead {
  teamA: string;
  teamB: string;
  matches: number;
  teamAWins: number;
  teamBWins: number;
  draws: number;
  games: Match[];
}

function plural(n: number, word: string): string {
  return `${n} ${word}${n === 1 ? "" : "s"}`;
}

/** Summarise a head-to-head record. */
export function formatHeadToHead(h: HeadToHead): string {
  return (
    `Head-to-head (${h.matches} matches): ` +
    `${h.teamA} ${plural(h.teamAWins, "win")}, ` +
    `${h.teamB} ${plural(h.teamBWins, "win")}, ` +
    `${plural(h.draws, "draw")}`
  );
}

/** Render a team's win/draw/loss record block. */
export function formatTeamRecord(rec: TeamRecord, header: string): string {
  const winRate = rec.matches ? rec.wins / rec.matches : 0;
  return [
    `${header}:`,
    `- Matches: ${rec.matches}`,
    `- Wins: ${rec.wins}, Draws: ${rec.draws}, Losses: ${rec.losses}`,
    `- Goals For: ${rec.goalsFor}, Goals Against: ${rec.goalsAgainst}`,
    `- Points: ${rec.points}`,
    `- Win rate: ${pct(winRate)}`,
  ].join("\n");
}

/** Render a numbered standings table. */
export function formatStandings(table: TeamRecord[], header: string): string {
  if (table.length === 0) return `${header}\nNo data available.`;
  const lines = table.map(
    (r, i) =>
      `${i + 1}. ${r.team} - ${r.points} pts (${r.wins}W, ${r.draws}D, ${r.losses}L)` +
      ` GF:${r.goalsFor} GA:${r.goalsAgainst}`
  );
  return `${header}\n${lines.join("\n")}`;
}

/** Render a descriptive statistics block. */
export function formatStatistics(s: Statistics, header: string): string {
  return [
    `${header}:`,
    `- Matches: ${s.totalMatches}`,
    `- Total goals: ${s.totalGoals}`,
    `- Average goals per match: ${s.averageGoals.toFixed(2)}`,
    `- Home win rate: ${pct(s.homeWinRate)}`,
    `- Away win rate: ${pct(s.awayWinRate)}`,
    `- Draw rate: ${pct(s.drawRate)}`,
  ].join("\n");
}

/** Render a single player line. */
export function formatPlayer(p: Player): string {
  return `${p.name} - Overall: ${p.overall ?? "?"}, Position: ${p.position}, Club: ${p.club}`;
}

/** Render a numbered player list under a header. */
export function formatPlayerList(
  players: Player[],
  header: string,
  max = 25
): string {
  if (players.length === 0) {
    return `${header}\nNo players found.`;
  }
  const shown = players.slice(0, max);
  const lines = shown.map((p, i) => `${i + 1}. ${formatPlayer(p)}`);
  let out = `${header}\n${lines.join("\n")}`;
  if (players.length > shown.length) {
    out += `\n... (${players.length - shown.length} more players in dataset)`;
  }
  return out;
}
