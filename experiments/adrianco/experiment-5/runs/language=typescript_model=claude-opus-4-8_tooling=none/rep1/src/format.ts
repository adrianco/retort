/**
 * Context
 * -------
 * Presentation layer. Converts the structured results from `queries.ts` into
 * the human-readable text blocks shown in the spec's "Example answer format"
 * sections. The MCP tools return these strings as their textual content so an
 * LLM client gets a ready-to-read answer, while the same data is also returned
 * as structured JSON.
 */

import type { Match, Player } from "./types.js";
import type {
  CompetitionStats,
  HeadToHead,
  StandingRow,
  TeamStats,
} from "./queries.js";

function score(m: Match): string {
  const h = m.homeGoal ?? "?";
  const a = m.awayGoal ?? "?";
  return `${h}-${a}`;
}

function context(m: Match): string {
  const parts: string[] = [m.competition];
  if (m.round != null) parts.push(`Round ${m.round}`);
  if (m.stage) parts.push(m.stage);
  if (m.season != null && m.round == null && !m.stage) parts.push(String(m.season));
  return parts.join(", ");
}

/** One match as a single line: "2023-09-03: Flamengo 2-1 Fluminense (Brasileirão ...)". */
export function formatMatchLine(m: Match): string {
  const date = m.date ?? "date unknown";
  return `${date}: ${m.homeTeam} ${score(m)} ${m.awayTeam} (${context(m)})`;
}

export function formatMatchList(matches: Match[], opts: { max?: number; title?: string } = {}): string {
  if (matches.length === 0) return opts.title ? `${opts.title}\nNo matches found.` : "No matches found.";
  const max = opts.max ?? 25;
  const shown = matches.slice(0, max);
  const lines = shown.map((m) => `- ${formatMatchLine(m)}`);
  let out = opts.title ? `${opts.title}\n` : "";
  out += lines.join("\n");
  if (matches.length > max) {
    out += `\n- ... (${matches.length - max} more matches in dataset)`;
  }
  return out;
}

export function formatHeadToHead(h: HeadToHead): string {
  const header = `${h.teamA} vs ${h.teamB} — head-to-head (${h.matches.length} matches in dataset):`;
  const lines = h.matches.slice(0, 20).map((m) => `- ${formatMatchLine(m)}`);
  const more =
    h.matches.length > 20 ? `\n- ... (${h.matches.length - 20} more matches in dataset)` : "";
  const summary =
    `\n\nHead-to-head: ${h.teamA} ${h.teamAWins} wins, ${h.teamB} ${h.teamBWins} wins, ${h.draws} draws` +
    `\nGoals: ${h.teamA} ${h.teamAGoals}, ${h.teamB} ${h.teamBGoals}`;
  if (h.matches.length === 0) {
    return `${header}\nNo matches with recorded scores found between these teams.`;
  }
  return header + "\n" + lines.join("\n") + more + summary;
}

export function formatTeamStats(s: TeamStats): string {
  const scope = [
    s.season != null ? String(s.season) : null,
    s.competition ?? null,
  ]
    .filter(Boolean)
    .join(" ");
  const title = `${s.team} record${scope ? ` (${scope})` : ""}:`;
  const r = s.overall;
  return (
    `${title}\n` +
    `- Matches: ${r.played}\n` +
    `- Wins: ${r.wins}, Draws: ${r.draws}, Losses: ${r.losses}\n` +
    `- Goals For: ${r.goalsFor}, Goals Against: ${r.goalsAgainst}\n` +
    `- Win rate: ${s.winRate.toFixed(1)}%\n` +
    `- Home: ${s.home.wins}W ${s.home.draws}D ${s.home.losses}L (${s.home.goalsFor}-${s.home.goalsAgainst})\n` +
    `- Away: ${s.away.wins}W ${s.away.draws}D ${s.away.losses}L (${s.away.goalsFor}-${s.away.goalsAgainst})`
  );
}

export function formatStandings(
  rows: StandingRow[],
  competition: string,
  season: number,
  opts: { max?: number } = {},
): string {
  if (rows.length === 0) {
    return `No ${competition} standings could be computed for ${season}.`;
  }
  const max = opts.max ?? rows.length;
  const title = `${season} ${competition} standings (calculated from matches):`;
  const lines = rows.slice(0, max).map((r, i) => {
    const champion = i === 0 ? " - Champion" : "";
    return `${i + 1}. ${r.team} - ${r.points} pts (${r.wins}W, ${r.draws}D, ${r.losses}L) GD ${r.goalDifference >= 0 ? "+" : ""}${r.goalDifference}${champion}`;
  });
  return `${title}\n` + lines.join("\n");
}

export function formatPlayerLine(p: Player, index?: number): string {
  const prefix = index != null ? `${index}. ` : "";
  const overall = p.overall != null ? `Overall: ${p.overall}` : "Overall: N/A";
  const pos = p.position ? `, Position: ${p.position}` : "";
  const club = p.club ? `, Club: ${p.club}` : "";
  return `${prefix}${p.name} - ${overall}${pos}${club}`;
}

export function formatPlayerList(players: Player[], opts: { max?: number; title?: string } = {}): string {
  if (players.length === 0) return opts.title ? `${opts.title}\nNo players found.` : "No players found.";
  const max = opts.max ?? 25;
  const shown = players.slice(0, max);
  const lines = shown.map((p, i) => formatPlayerLine(p, i + 1));
  let out = opts.title ? `${opts.title}\n` : "";
  out += lines.join("\n");
  if (players.length > max) out += `\n... (${players.length - max} more players in dataset)`;
  return out;
}

export function formatPlayerDetail(p: Player): string {
  return (
    `${p.name}\n` +
    `- Nationality: ${p.nationality || "Unknown"}\n` +
    `- Age: ${p.age ?? "?"}\n` +
    `- Club: ${p.club || "Unknown"}\n` +
    `- Position: ${p.position || "?"}${p.jerseyNumber ? ` (#${p.jerseyNumber})` : ""}\n` +
    `- Overall: ${p.overall ?? "?"}, Potential: ${p.potential ?? "?"}\n` +
    `- Height: ${p.height || "?"}, Weight: ${p.weight || "?"}, Preferred foot: ${p.preferredFoot || "?"}\n` +
    `- Value: ${p.value || "?"}, Wage: ${p.wage || "?"}`
  );
}

export function formatCompetitionStats(s: CompetitionStats): string {
  const scope = [s.season != null ? String(s.season) : null, s.competition ?? "all competitions"]
    .filter(Boolean)
    .join(" ");
  return (
    `Statistics for ${scope}:\n` +
    `- Matches: ${s.totalMatches} (${s.matchesWithScores} with recorded scores)\n` +
    `- Total goals: ${s.totalGoals}\n` +
    `- Average goals per match: ${s.averageGoalsPerMatch.toFixed(2)}\n` +
    `- Home wins: ${s.homeWins}, Away wins: ${s.awayWins}, Draws: ${s.draws}\n` +
    `- Home win rate: ${s.homeWinRate.toFixed(1)}%`
  );
}
