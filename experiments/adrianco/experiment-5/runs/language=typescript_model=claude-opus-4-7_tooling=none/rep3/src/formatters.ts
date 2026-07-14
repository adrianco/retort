import { Match } from './types.js';
import { TeamRecord } from './queries/teams.js';
import { ClubSummary } from './queries/players.js';
import { Player } from './types.js';
import { HeadToHead } from './queries/matches.js';
import { OverallStats } from './queries/stats.js';

export function formatMatchLine(m: Match): string {
  const round = m.round ? ` Round ${m.round}` : '';
  const stage = m.stage ? ` ${m.stage}` : '';
  return `${m.date}: ${m.homeTeam} ${m.homeGoals}-${m.awayGoals} ${m.awayTeam} (${m.competition}${round}${stage})`;
}

export function formatMatches(matches: Match[], cap = 20): string {
  if (matches.length === 0) return 'No matches found.';
  const shown = matches.slice(0, cap);
  const lines = shown.map((m) => '- ' + formatMatchLine(m));
  const more = matches.length > cap ? `\n... (${matches.length - cap} more)` : '';
  return lines.join('\n') + more;
}

export function formatTeamRecord(r: TeamRecord): string {
  const winRatePct = (r.winRate * 100).toFixed(1);
  return [
    `${r.team}`,
    `- Matches: ${r.matches}`,
    `- Wins: ${r.wins}, Draws: ${r.draws}, Losses: ${r.losses}`,
    `- Goals For: ${r.goalsFor}, Goals Against: ${r.goalsAgainst} (GD ${r.goalDifference >= 0 ? '+' : ''}${r.goalDifference})`,
    `- Points: ${r.points}, Win rate: ${winRatePct}%`,
  ].join('\n');
}

export function formatStandings(rows: TeamRecord[], cap = 20): string {
  if (rows.length === 0) return 'No matches found for standings.';
  return rows
    .slice(0, cap)
    .map(
      (r, i) =>
        `${String(i + 1).padStart(2, ' ')}. ${r.team} - ${r.points} pts (${r.wins}W ${r.draws}D ${r.losses}L) GD ${r.goalDifference >= 0 ? '+' : ''}${r.goalDifference}`,
    )
    .join('\n');
}

export function formatHeadToHead(h: HeadToHead): string {
  const lines: string[] = [];
  lines.push(`${h.teamA} vs ${h.teamB}`);
  lines.push(
    `Head-to-head: ${h.teamA} ${h.teamAWins} wins, ${h.teamB} ${h.teamBWins} wins, ${h.draws} draws`,
  );
  lines.push(
    `Goals: ${h.teamA} ${h.teamAGoals} - ${h.teamBGoals} ${h.teamB}`,
  );
  lines.push('');
  lines.push(formatMatches(h.matches, 15));
  return lines.join('\n');
}

export function formatPlayer(p: Player): string {
  const parts = [p.name];
  if (p.overall != null) parts.push(`Overall: ${p.overall}`);
  if (p.position) parts.push(`Position: ${p.position}`);
  if (p.club) parts.push(`Club: ${p.club}`);
  if (p.nationality) parts.push(`Nationality: ${p.nationality}`);
  if (p.age != null) parts.push(`Age: ${p.age}`);
  return parts.join(' | ');
}

export function formatPlayers(players: Player[], cap = 25): string {
  if (players.length === 0) return 'No players found.';
  const shown = players.slice(0, cap);
  const lines = shown.map((p, i) => `${i + 1}. ${formatPlayer(p)}`);
  const more = players.length > cap ? `\n... (${players.length - cap} more)` : '';
  return lines.join('\n') + more;
}

export function formatClubSummaries(rows: ClubSummary[], cap = 20): string {
  if (rows.length === 0) return 'No clubs found.';
  return rows
    .slice(0, cap)
    .map(
      (r) =>
        `- ${r.club}: ${r.count} players (avg rating: ${r.averageOverall.toFixed(1)})`,
    )
    .join('\n');
}

export function formatOverallStats(s: OverallStats): string {
  return [
    `Matches: ${s.matches}`,
    `Total goals: ${s.totalGoals}`,
    `Average goals/match: ${s.averageGoals.toFixed(2)}`,
    `Home wins: ${s.homeWins} (${(s.homeWinRate * 100).toFixed(1)}%)`,
    `Away wins: ${s.awayWins} (${(s.awayWinRate * 100).toFixed(1)}%)`,
    `Draws: ${s.draws} (${(s.drawRate * 100).toFixed(1)}%)`,
  ].join('\n');
}
