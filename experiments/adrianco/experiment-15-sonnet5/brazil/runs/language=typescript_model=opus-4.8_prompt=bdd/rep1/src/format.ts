/**
 * Human-readable formatting of query results, mirroring the answer formats in
 * the specification. Each MCP tool returns one of these strings as its text
 * content so an LLM (or a person) sees a clean, self-describing answer.
 */
import { formatDate } from "./normalize.js";
import type { Match, Player, StandingsRow } from "./types.js";
import type { HeadToHead } from "./queries/matches.js";
import type { TeamStats } from "./queries/teams.js";
import type { MatchAggregate, BiggestWin, TeamGoalTotal } from "./queries/stats.js";
import type { ClubSummary } from "./queries/players.js";

/** Format a competition/round tag like "(Brasileirão Série A Round 22)". */
function contextTag(match: Match): string {
  const parts = [match.competition];
  if (match.round) parts.push(`Round ${match.round}`);
  else if (match.stage) parts.push(match.stage);
  return `(${parts.join(" ")})`;
}

/** One-line scoreline, e.g. "2023-09-03: Flamengo 2-1 Fluminense (Brasileirão Round 22)". */
export function formatMatchLine(match: Match): string {
  const score =
    match.homeGoals === null || match.awayGoals === null
      ? "vs"
      : `${match.homeGoals}-${match.awayGoals}`;
  return `${formatDate(match.date)}: ${match.homeTeam} ${score} ${match.awayTeam} ${contextTag(match)}`;
}

export function formatMatchList(matches: Match[], heading: string, limit = 25): string {
  if (matches.length === 0) return `${heading}\nNo matches found.`;
  const shown = matches.slice(0, limit).map((m) => `- ${formatMatchLine(m)}`);
  const lines = [heading, ...shown];
  if (matches.length > limit) {
    lines.push(`- ... (${matches.length - limit} more matches in dataset)`);
  }
  return lines.join("\n");
}

export function formatHeadToHead(record: HeadToHead, matches: Match[], limit = 10): string {
  const heading = `${record.teamA} vs ${record.teamB} head-to-head:`;
  const recent = matches.slice(0, limit).map((m) => `- ${formatMatchLine(m)}`);
  const summary =
    `\nHead-to-head in dataset (${record.matches} matches): ` +
    `${record.teamA} ${record.teamAWins} wins, ${record.teamB} ${record.teamBWins} wins, ${record.draws} draws.` +
    `\nGoals: ${record.teamA} ${record.teamAGoals}, ${record.teamB} ${record.teamBGoals}.`;
  if (matches.length === 0) {
    return `${heading}\nNo matches found between these teams in the dataset.`;
  }
  const extra = matches.length > limit ? `\n- ... (${matches.length - limit} more)` : "";
  return `${heading}\n${recent.join("\n")}${extra}${summary}`;
}

function pct(rate: number): string {
  return `${(rate * 100).toFixed(1)}%`;
}

export function formatTeamStats(stats: TeamStats, scopeLabel: string): string {
  return [
    `${stats.team} record (${scopeLabel}):`,
    `- Matches: ${stats.played}`,
    `- Wins: ${stats.wins}, Draws: ${stats.draws}, Losses: ${stats.losses}`,
    `- Goals For: ${stats.goalsFor}, Goals Against: ${stats.goalsAgainst} (GD ${signed(stats.goalDifference)})`,
    `- Points: ${stats.points}`,
    `- Win rate: ${pct(stats.winRate)}`,
    `- Home: ${stats.home.wins}W ${stats.home.draws}D ${stats.home.losses}L | ` +
      `Away: ${stats.away.wins}W ${stats.away.draws}D ${stats.away.losses}L`,
    `- Competitions: ${stats.competitions.join(", ") || "none"}`,
  ].join("\n");
}

function signed(n: number): string {
  return n > 0 ? `+${n}` : `${n}`;
}

export function formatStandings(rows: StandingsRow[], heading: string, limit = 20): string {
  if (rows.length === 0) return `${heading}\nNo matches available to build the table.`;
  const lines = rows.slice(0, limit).map((r) => {
    const tag = r.position === 1 ? " - Champion" : "";
    return `${r.position}. ${r.team} - ${r.points} pts (${r.wins}W, ${r.draws}D, ${r.losses}L, GD ${signed(r.goalDifference)})${tag}`;
  });
  return [heading, ...lines].join("\n");
}

export function formatPlayer(player: Player): string {
  const rating = player.overall !== null ? `Overall: ${player.overall}` : "Overall: n/a";
  const pos = player.position || "?";
  const club = player.club || "Free agent";
  return `${player.name} - ${rating}, Position: ${pos}, Club: ${club}, Nationality: ${player.nationality}`;
}

export function formatPlayerList(players: Player[], heading: string, limit = 25): string {
  if (players.length === 0) return `${heading}\nNo players found.`;
  const lines = players.slice(0, limit).map((p, i) => `${i + 1}. ${formatPlayer(p)}`);
  if (players.length > limit) {
    lines.push(`... (${players.length - limit} more players)`);
  }
  return [heading, ...lines].join("\n");
}

export function formatClubSummaries(summaries: ClubSummary[], heading: string, limit = 15): string {
  if (summaries.length === 0) return `${heading}\nNo clubs found.`;
  const lines = summaries
    .slice(0, limit)
    .map(
      (s) =>
        `- ${s.club}: ${s.playerCount} players (avg rating: ${s.averageOverall}, top: ${s.topPlayer})`,
    );
  return [heading, ...lines].join("\n");
}

export function formatAggregate(agg: MatchAggregate, scopeLabel: string): string {
  return [
    `Match statistics (${scopeLabel}):`,
    `- Matches: ${agg.matches}`,
    `- Total goals: ${agg.totalGoals}`,
    `- Average goals per match: ${agg.averageGoalsPerMatch}`,
    `- Home wins: ${agg.homeWins} (${pct(agg.homeWinRate)})`,
    `- Away wins: ${agg.awayWins} (${pct(agg.awayWinRate)})`,
    `- Draws: ${agg.draws} (${pct(agg.drawRate)})`,
  ].join("\n");
}

export function formatBiggestWins(wins: BiggestWin[], heading: string): string {
  if (wins.length === 0) return `${heading}\nNo matches found.`;
  const lines = wins.map((w, i) => `${i + 1}. ${formatMatchLine(w.match)} [margin ${w.margin}]`);
  return [heading, ...lines].join("\n");
}

export function formatTopScoringTeams(totals: TeamGoalTotal[], heading: string): string {
  if (totals.length === 0) return `${heading}\nNo matches found.`;
  const lines = totals.map(
    (t, i) => `${i + 1}. ${t.team} - ${t.goalsFor} goals in ${t.matches} matches`,
  );
  return [heading, ...lines].join("\n");
}
