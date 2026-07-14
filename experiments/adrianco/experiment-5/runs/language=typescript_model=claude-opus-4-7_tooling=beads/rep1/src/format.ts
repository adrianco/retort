import type { Match, Player, TeamRecord, HeadToHead } from './types.js';
import type { StandingRow, GoalsStat, AggregateStats, PlayerClubSummary } from './queries.js';

export function formatMatch(m: Match): string {
  const parts = [`${m.date}: ${m.homeTeamRaw} ${m.homeGoals}-${m.awayGoals} ${m.awayTeamRaw}`];
  const meta: string[] = [m.competition];
  if (m.round !== undefined && m.round !== '') meta.push(`Round ${m.round}`);
  if (m.stage) meta.push(m.stage);
  if (m.arena) meta.push(m.arena);
  parts.push(`(${meta.join(', ')})`);
  return parts.join(' ');
}

export function formatMatchList(matches: Match[], maxLines = 25): string {
  if (matches.length === 0) return 'No matches found.';
  const lines = matches.slice(0, maxLines).map(m => `- ${formatMatch(m)}`);
  const trailer = matches.length > maxLines ? `\n... and ${matches.length - maxLines} more` : '';
  return `Found ${matches.length} match(es):\n${lines.join('\n')}${trailer}`;
}

export function formatTeamRecord(r: TeamRecord, label = ''): string {
  const heading = label ? `${label}` : `Record for ${r.team}`;
  const rate = r.matches ? ((r.wins / r.matches) * 100).toFixed(1) : '0.0';
  return [
    heading,
    `- Matches: ${r.matches}`,
    `- Wins: ${r.wins}, Draws: ${r.draws}, Losses: ${r.losses}`,
    `- Goals For: ${r.goalsFor}, Goals Against: ${r.goalsAgainst} (Diff: ${r.goalDifference >= 0 ? '+' : ''}${r.goalDifference})`,
    `- Points: ${r.points}`,
    `- Win rate: ${rate}%`,
  ].join('\n');
}

export function formatHeadToHead(h: HeadToHead, maxMatches = 10): string {
  const lines = [
    `Head-to-head: ${h.teamA} vs ${h.teamB}`,
    `- Matches: ${h.matches}`,
    `- ${h.teamA} wins: ${h.teamAWins}, ${h.teamB} wins: ${h.teamBWins}, Draws: ${h.draws}`,
    `- Goals: ${h.teamA} ${h.teamAGoals}, ${h.teamB} ${h.teamBGoals}`,
  ];
  if (h.history.length) {
    lines.push('', `Most recent ${Math.min(maxMatches, h.history.length)} match(es):`);
    for (const m of h.history.slice(0, maxMatches)) lines.push(`- ${formatMatch(m)}`);
    if (h.history.length > maxMatches) {
      lines.push(`... and ${h.history.length - maxMatches} more`);
    }
  }
  return lines.join('\n');
}

export function formatStandings(rows: StandingRow[], maxRows = 30): string {
  if (rows.length === 0) return 'No standings available.';
  const lines = rows.slice(0, maxRows).map(r =>
    `${String(r.rank).padStart(2, ' ')}. ${r.team} - ${r.points} pts (${r.wins}W, ${r.draws}D, ${r.losses}L) GD ${r.goalDifference >= 0 ? '+' : ''}${r.goalDifference}`,
  );
  const trailer = rows.length > maxRows ? `\n... ${rows.length - maxRows} more rows` : '';
  return lines.join('\n') + trailer;
}

export function formatPlayers(players: Player[], maxRows = 25): string {
  if (players.length === 0) return 'No players found.';
  const lines = players.slice(0, maxRows).map((p, i) => {
    const bits = [`${i + 1}. ${p.name}`];
    if (p.overall !== undefined) bits.push(`Overall: ${p.overall}`);
    if (p.position) bits.push(`Pos: ${p.position}`);
    if (p.club) bits.push(`Club: ${p.club}`);
    if (p.nationality) bits.push(`Nat: ${p.nationality}`);
    if (p.age !== undefined) bits.push(`Age: ${p.age}`);
    return bits.join(' - ');
  });
  const trailer = players.length > maxRows ? `\n... and ${players.length - maxRows} more` : '';
  return `Found ${players.length} player(s):\n${lines.join('\n')}${trailer}`;
}

export function formatScoringStats(rows: GoalsStat[], maxRows = 15): string {
  if (rows.length === 0) return 'No data.';
  const lines = rows.slice(0, maxRows).map((r, i) =>
    `${i + 1}. ${r.team}: ${r.goals} goals (${r.matches} matches, avg ${(r.goals / Math.max(1, r.matches)).toFixed(2)})`,
  );
  return lines.join('\n');
}

export function formatAggregate(stats: AggregateStats): string {
  return [
    `Matches: ${stats.totalMatches}`,
    `Total goals: ${stats.totalGoals}`,
    `Average goals per match: ${stats.averageGoalsPerMatch}`,
    `Home wins: ${stats.homeWins} (${(stats.homeWinRate * 100).toFixed(1)}%)`,
    `Away wins: ${stats.awayWins} (${(stats.awayWinRate * 100).toFixed(1)}%)`,
    `Draws: ${stats.draws} (${(stats.drawRate * 100).toFixed(1)}%)`,
  ].join('\n');
}

export function formatPlayerClubSummary(rows: PlayerClubSummary[], maxRows = 20): string {
  if (rows.length === 0) return 'No data.';
  const lines = rows.slice(0, maxRows).map(r =>
    `- ${r.club}: ${r.count} player(s), avg rating ${r.averageOverall.toFixed(1)}`,
  );
  return lines.join('\n');
}
