/**
 * ============================================================================
 * File: src/format.ts
 * Project: Brazilian Soccer MCP Server
 * ----------------------------------------------------------------------------
 * Context:
 *   Pure formatting helpers that turn the knowledge graph's structured query
 *   results into the human-readable text blocks shown in the specification's
 *   "Example answer format" sections. Kept separate from query logic so the
 *   same data can be rendered for the MCP text response while remaining
 *   directly assertable in tests.
 * ============================================================================
 */

import type {
  CompetitionStats,
  HeadToHead,
  StandingRow,
} from "./knowledgeGraph.js";
import type { Match, Player, Record as TeamRecord } from "./types.js";

function score(m: Match): string {
  const h = m.homeGoals ?? "?";
  const a = m.awayGoals ?? "?";
  return `${m.homeTeam} ${h}-${a} ${m.awayTeam}`;
}

function context(m: Match): string {
  const parts: string[] = [m.competition];
  if (m.round) parts.push(`Round ${m.round}`);
  if (m.stage) parts.push(m.stage);
  return parts.join(", ");
}

export function formatMatch(m: Match): string {
  const date = m.date ?? "date unknown";
  return `- ${date}: ${score(m)} (${context(m)})`;
}

export function formatMatchList(matches: Match[], heading?: string): string {
  if (matches.length === 0) return heading ? `${heading}\n(no matches found)` : "No matches found.";
  const lines = matches.map(formatMatch);
  return heading ? `${heading}\n${lines.join("\n")}` : lines.join("\n");
}

function pct(n: number): string {
  return `${(n * 100).toFixed(1)}%`;
}

export function formatRecord(team: string, rec: TeamRecord, label?: string): string {
  const head = label ? `${team} record (${label}):` : `${team} record:`;
  const winRate = rec.matches ? rec.wins / rec.matches : 0;
  return [
    head,
    `- Matches: ${rec.matches}`,
    `- Wins: ${rec.wins}, Draws: ${rec.draws}, Losses: ${rec.losses}`,
    `- Goals For: ${rec.goalsFor}, Goals Against: ${rec.goalsAgainst}`,
    `- Win rate: ${pct(winRate)}`,
  ].join("\n");
}

export function formatHeadToHead(h: HeadToHead, sampleLimit = 10): string {
  const lines = [
    `${h.teamA} vs ${h.teamB} — head-to-head (dataset):`,
    `- Matches: ${h.totalMatches}`,
    `- ${h.teamA} wins: ${h.teamAWins}, ${h.teamB} wins: ${h.teamBWins}, Draws: ${h.draws}`,
    `- Goals: ${h.teamA} ${h.teamAGoals}, ${h.teamB} ${h.teamBGoals}`,
  ];
  if (h.matches.length) {
    lines.push("", "Most recent meetings:");
    for (const m of h.matches.slice(0, sampleLimit)) lines.push(formatMatch(m));
    if (h.matches.length > sampleLimit) {
      lines.push(`- ... (${h.matches.length - sampleLimit} more)`);
    }
  }
  return lines.join("\n");
}

export function formatPlayer(p: Player, index?: number): string {
  const prefix = index !== undefined ? `${index}. ` : "- ";
  const rating = p.overall ?? "?";
  const club = p.club || "Free agent";
  return `${prefix}${p.name} - Overall: ${rating}, Position: ${p.position || "?"}, Club: ${club}`;
}

export function formatPlayerList(players: Player[], heading?: string): string {
  if (players.length === 0) return heading ? `${heading}\n(no players found)` : "No players found.";
  const lines = players.map((p, i) => formatPlayer(p, i + 1));
  return heading ? `${heading}\n${lines.join("\n")}` : lines.join("\n");
}

export function formatStandings(
  competition: string,
  season: number,
  rows: StandingRow[],
  limit?: number,
): string {
  if (rows.length === 0) {
    return `No standings available for ${competition} ${season}.`;
  }
  const shown = limit ? rows.slice(0, limit) : rows;
  const lines = shown.map((r, i) => {
    const pos = i + 1;
    const tag = pos === 1 ? " - Champion" : "";
    return `${pos}. ${r.team} - ${r.points} pts (${r.wins}W, ${r.draws}D, ${r.losses}L, GD ${r.goalDifference >= 0 ? "+" : ""}${r.goalDifference})${tag}`;
  });
  return `${competition} ${season} standings (calculated from matches):\n${lines.join("\n")}`;
}

export function formatCompetitionStats(s: CompetitionStats): string {
  const label = s.season !== undefined ? `${s.competition} ${s.season}` : s.competition;
  return [
    `${label} — statistics:`,
    `- Matches: ${s.matches} (${s.matchesWithScores} with recorded scores)`,
    `- Total goals: ${s.totalGoals}`,
    `- Average goals per match: ${s.averageGoalsPerMatch.toFixed(2)}`,
    `- Home wins: ${s.homeWins} (${pct(s.homeWinRate)})`,
    `- Away wins: ${s.awayWins} (${pct(s.awayWinRate)})`,
    `- Draws: ${s.draws} (${pct(s.drawRate)})`,
  ].join("\n");
}
