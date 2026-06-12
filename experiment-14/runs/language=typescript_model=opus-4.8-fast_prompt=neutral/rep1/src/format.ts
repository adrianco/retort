/**
 * Brazilian Soccer MCP — Response formatting
 * ------------------------------------------
 * Context: Turns the structured results from `SoccerStore` into the
 * human-readable text blocks shown in the specification's "Example answer
 * format" sections. Keeping formatting separate from querying means the store
 * stays purely analytical and these helpers stay purely presentational, so both
 * are easy to test in isolation.
 */

import type { Match, Player } from "./types.js";
import type { StandingRow, TeamRecord } from "./store.js";

const pct = (x: number) => `${(x * 100).toFixed(1)}%`;

function score(m: Match): string {
  if (m.homeGoals === null || m.awayGoals === null) return "vs";
  return `${m.homeGoals}-${m.awayGoals}`;
}

function context(m: Match): string {
  const bits: string[] = [m.competition];
  if (m.round) bits.push(`Round ${m.round}`);
  if (m.stage) bits.push(m.stage);
  return bits.join(", ");
}

/** One match as a single line: "2023-09-03: Flamengo 2-1 Fluminense (Brasileirão …)". */
export function formatMatchLine(m: Match): string {
  const date = m.date ?? "date unknown";
  return `${date}: ${m.homeTeam} ${score(m)} ${m.awayTeam} (${context(m)})`;
}

export function formatMatches(matches: Match[], title: string, limit = 25): string {
  if (matches.length === 0) return `${title}\nNo matches found.`;
  const shown = matches.slice(0, limit).map((m) => `- ${formatMatchLine(m)}`);
  const more =
    matches.length > limit ? `\n... (${matches.length - limit} more matches)` : "";
  return `${title} (${matches.length} match${matches.length === 1 ? "" : "es"}):\n${shown.join("\n")}${more}`;
}

export function formatHeadToHead(h: {
  teamA: { display: string } | null;
  teamB: { display: string } | null;
  matches: Match[];
  aWins: number;
  bWins: number;
  draws: number;
  aGoals: number;
  bGoals: number;
}): string {
  if (!h.teamA || !h.teamB) {
    const missing = !h.teamA ? "first" : "second";
    return `Could not resolve the ${missing} team name.`;
  }
  const header = `${h.teamA.display} vs ${h.teamB.display} — head-to-head`;
  const summary =
    `Played: ${h.matches.length} | ${h.teamA.display} ${h.aWins} wins, ` +
    `${h.teamB.display} ${h.bWins} wins, ${h.draws} draws | ` +
    `Goals: ${h.teamA.display} ${h.aGoals}, ${h.teamB.display} ${h.bGoals}`;
  const recent = h.matches.slice(-10).reverse().map((m) => `- ${formatMatchLine(m)}`);
  const body = recent.length ? `\nMost recent meetings:\n${recent.join("\n")}` : "";
  return `${header}\n${summary}${body}`;
}

export function formatTeamRecord(rec: TeamRecord, scope: string): string {
  return (
    `${rec.team} record (${scope}):\n` +
    `- Matches: ${rec.played}\n` +
    `- Wins: ${rec.wins}, Draws: ${rec.draws}, Losses: ${rec.losses}\n` +
    `- Goals For: ${rec.goalsFor}, Goals Against: ${rec.goalsAgainst} ` +
    `(diff ${rec.goalsFor - rec.goalsAgainst >= 0 ? "+" : ""}${rec.goalsFor - rec.goalsAgainst})\n` +
    `- Points: ${rec.points}\n` +
    `- Win rate: ${pct(rec.winRate)}`
  );
}

export function formatStandings(rows: StandingRow[], title: string, limit = 30): string {
  if (rows.length === 0) return `${title}\nNo data available for that competition/season.`;
  const lines = rows.slice(0, limit).map((r) => {
    const champ = r.rank === 1 ? " — Champion" : "";
    return (
      `${String(r.rank).padStart(2)}. ${r.team} — ${r.points} pts ` +
      `(${r.wins}W ${r.draws}D ${r.losses}L, GF ${r.goalsFor} GA ${r.goalsAgainst}, ` +
      `GD ${r.goalDiff >= 0 ? "+" : ""}${r.goalDiff})${champ}`
    );
  });
  return `${title}:\n${lines.join("\n")}`;
}

export function formatCompetitionStats(
  stats: {
    matches: number;
    decided: number;
    totalGoals: number;
    avgGoals: number;
    homeWins: number;
    awayWins: number;
    draws: number;
    homeWinRate: number;
    biggestMargins: Match[];
  },
  title: string,
): string {
  if (stats.decided === 0) return `${title}\nNo decided matches found for that scope.`;
  const big = stats.biggestMargins
    .slice(0, 5)
    .map((m, i) => `${i + 1}. ${formatMatchLine(m)}`)
    .join("\n");
  return (
    `${title}:\n` +
    `- Matches: ${stats.matches} (${stats.decided} with recorded scores)\n` +
    `- Total goals: ${stats.totalGoals}\n` +
    `- Average goals per match: ${stats.avgGoals.toFixed(2)}\n` +
    `- Home wins: ${stats.homeWins} (${pct(stats.homeWinRate)}), ` +
    `Away wins: ${stats.awayWins}, Draws: ${stats.draws}\n` +
    `\nBiggest victories:\n${big}`
  );
}

export function formatPlayerLine(p: Player, idx?: number): string {
  const prefix = idx !== undefined ? `${idx + 1}. ` : "";
  const rating = p.overall !== null ? `Overall: ${p.overall}` : "Overall: ?";
  const pos = p.position || "?";
  const club = p.club || "Free agent";
  return `${prefix}${p.name} — ${rating}, Position: ${pos}, Club: ${club} (${p.nationality}, age ${p.age ?? "?"})`;
}

export function formatPlayers(players: Player[], title: string, limit = 20): string {
  if (players.length === 0) return `${title}\nNo players found.`;
  const lines = players.slice(0, limit).map((p, i) => formatPlayerLine(p, i));
  const more = players.length > limit ? `\n... (${players.length - limit} more players)` : "";
  return `${title} (${players.length} found):\n${lines.join("\n")}${more}`;
}
