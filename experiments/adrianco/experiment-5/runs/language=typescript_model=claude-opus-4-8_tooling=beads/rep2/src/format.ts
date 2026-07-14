/**
 * format.ts
 * -----------------------------------------------------------------------------
 * CONTEXT
 *   Presentation layer: converts the structured results returned by the query
 *   services into the human-readable, "properly formatted responses" shown in
 *   the spec's examples (match lists with head-to-head tallies, team records,
 *   player rankings, league tables, stat summaries).
 *
 *   Kept separate from the services so the same data can be unit-tested
 *   structurally while the MCP tools return formatted text. Pure string helpers,
 *   no I/O.
 * -----------------------------------------------------------------------------
 */

import type { Match, Player } from "./types.js";
import type { HeadToHead } from "./services/matches.js";
import type { TeamRecord } from "./services/teams.js";
import type { StandingRow } from "./services/competitions.js";
import type { AggregateStats, BiggestWin } from "./services/stats.js";
import type { ClubBreakdownRow } from "./services/players.js";

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

function pct(fraction: number): string {
  return `${(fraction * 100).toFixed(1)}%`;
}

/** Format a single match line: "2023-09-03: Flamengo 2-1 Fluminense (...)". */
export function formatMatchLine(m: Match): string {
  const date = m.date ?? "unknown date";
  return `${date}: ${score(m)} (${context(m)})`;
}

/** Format a list of matches with an optional cap and "N more" footer. */
export function formatMatchList(matches: Match[], shown = 15): string {
  if (matches.length === 0) return "No matches found.";
  const lines = matches.slice(0, shown).map((m) => `- ${formatMatchLine(m)}`);
  if (matches.length > shown) {
    lines.push(`- ... (${matches.length - shown} more matches in dataset)`);
  }
  return lines.join("\n");
}

/** Format a head-to-head summary block. */
export function formatHeadToHead(h: HeadToHead): string {
  const header = `${h.teamA} vs ${h.teamB} (${h.totalMatches} matches in dataset):`;
  const list = formatMatchList(h.matches);
  const tally =
    `\n\nHead-to-head: ${h.teamA} ${h.teamAWins} wins, ` +
    `${h.teamB} ${h.teamBWins} wins, ${h.draws} draws ` +
    `(goals ${h.teamAGoals}-${h.teamBGoals}).`;
  return `${header}\n${list}${tally}`;
}

/** Format a team record block. */
export function formatTeamRecord(r: TeamRecord): string {
  const scope: string[] = [];
  if (r.season !== undefined) scope.push(String(r.season));
  if (r.competition) scope.push(r.competition);
  if (r.venue !== "any") scope.push(`${r.venue} matches`);
  const scopeStr = scope.length ? ` (${scope.join(" ")})` : "";
  return [
    `${r.team} record${scopeStr}:`,
    `- Matches: ${r.matches}`,
    `- Wins: ${r.wins}, Draws: ${r.draws}, Losses: ${r.losses}`,
    `- Goals For: ${r.goalsFor}, Goals Against: ${r.goalsAgainst} (GD ${r.goalDifference >= 0 ? "+" : ""}${r.goalDifference})`,
    `- Points: ${r.points}`,
    `- Win rate: ${pct(r.winRate)}`,
  ].join("\n");
}

/** Format a single player line. */
export function formatPlayerLine(p: Player): string {
  const bits = [
    p.overall !== null ? `Overall: ${p.overall}` : null,
    p.position ? `Position: ${p.position}` : null,
    p.club ? `Club: ${p.club}` : null,
    p.nationality ? `Nationality: ${p.nationality}` : null,
  ].filter(Boolean);
  return `${p.name} - ${bits.join(", ")}`;
}

/** Format a ranked player list. */
export function formatPlayerList(players: Player[], shown = 20): string {
  if (players.length === 0) return "No players found.";
  const lines = players
    .slice(0, shown)
    .map((p, i) => `${i + 1}. ${formatPlayerLine(p)}`);
  if (players.length > shown) {
    lines.push(`... (${players.length - shown} more players)`);
  }
  return lines.join("\n");
}

/** Format a per-club breakdown block. */
export function formatClubBreakdown(rows: ClubBreakdownRow[], shown = 15): string {
  if (rows.length === 0) return "No clubs found.";
  return rows
    .slice(0, shown)
    .map(
      (r) =>
        `- ${r.club}: ${r.count} player${r.count === 1 ? "" : "s"} (avg rating: ${r.averageOverall}, top: ${r.topPlayer})`,
    )
    .join("\n");
}

/** Format a standings table. */
export function formatStandings(
  rows: StandingRow[],
  competition: string,
  season: number,
  shown = 20,
): string {
  if (rows.length === 0) {
    return `No standings available for ${competition} ${season}.`;
  }
  const header = `${season} ${competition} Standings (calculated from matches):`;
  const lines = rows.slice(0, shown).map((r) => {
    const tag =
      r.position === 1
        ? " - Champion"
        : "";
    return `${r.position}. ${r.team} - ${r.points} pts (${r.wins}W ${r.draws}D ${r.losses}L, GF ${r.goalsFor} GA ${r.goalsAgainst})${tag}`;
  });
  return `${header}\n${lines.join("\n")}`;
}

/** Format an aggregate-statistics block. */
export function formatAggregateStats(s: AggregateStats, label = "Matches"): string {
  return [
    `${label} analysed: ${s.matches} (${s.matchesWithScores} with scores)`,
    `Total goals: ${s.totalGoals}`,
    `Average goals per match: ${s.averageGoalsPerMatch.toFixed(2)}`,
    `Home win rate: ${pct(s.homeWinRate)}`,
    `Draw rate: ${pct(s.drawRate)}`,
    `Away win rate: ${pct(s.awayWinRate)}`,
  ].join("\n");
}

/** Format a biggest-wins list. */
export function formatBiggestWins(wins: BiggestWin[]): string {
  if (wins.length === 0) return "No decisive matches found.";
  return wins
    .map((w, i) => {
      const date = w.match.date ?? "unknown date";
      return `${i + 1}. ${date}: ${w.scoreline} (${w.match.competition}, margin ${w.margin})`;
    })
    .join("\n");
}

/** Format a best-records ranking. */
export function formatTeamRankings(records: TeamRecord[], shown = 10): string {
  if (records.length === 0) return "No teams found.";
  return records
    .slice(0, shown)
    .map(
      (r, i) =>
        `${i + 1}. ${r.team} - ${pct(r.winRate)} win rate (${r.wins}W ${r.draws}D ${r.losses}L, ${r.points} pts, GD ${r.goalDifference >= 0 ? "+" : ""}${r.goalDifference})`,
    )
    .join("\n");
}
