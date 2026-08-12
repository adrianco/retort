import type { Match, Player, StandingRow, TeamStats } from "./types.js";

export function formatMatch(match: Match): string {
  const context = match.stage ? `, ${match.stage}` : match.round ? `, round ${match.round}` : "";
  return `${match.date}: ${match.homeTeam} ${match.homeGoals}-${match.awayGoals} ${match.awayTeam} (${match.competition}${context})`;
}

export function formatMatches(matches: Match[], total = matches.length): string {
  if (!matches.length) return "No matching matches were found in the provided datasets.";
  const lines = matches.map((match) => `- ${formatMatch(match)}`);
  if (total > matches.length) lines.push(`… ${total - matches.length} more matching matches (use offset to continue)`);
  return lines.join("\n");
}

export function formatTeamStats(stats: TeamStats): string {
  return `${stats.team}: ${stats.matches} matches — ${stats.wins} wins, ${stats.draws} draws, ${stats.losses} losses; ` +
    `${stats.goalsFor} goals for, ${stats.goalsAgainst} against (${stats.goalDifference >= 0 ? "+" : ""}${stats.goalDifference}); ` +
    `${stats.points} points, ${stats.winRate}% win rate.`;
}

export function formatStandings(rows: StandingRow[]): string {
  if (!rows.length) return "No standings could be calculated for that competition and season.";
  return rows.map((row) => `${row.position}. ${row.team} — ${row.points} pts (${row.wins}W, ${row.draws}D, ${row.losses}L, GD ${row.goalDifference >= 0 ? "+" : ""}${row.goalDifference})`).join("\n");
}

export function formatPlayers(players: Player[], total = players.length): string {
  if (!players.length) return "No matching players were found in the FIFA dataset.";
  const lines = players.map((player, index) => `${index + 1}. ${player.name} — overall ${player.overall ?? "unknown"}, ${player.position || "position unknown"}, ${player.club || "club unknown"}, ${player.nationality}`);
  if (total > players.length) lines.push(`… ${total - players.length} more matching players (use offset to continue)`);
  return lines.join("\n");
}
