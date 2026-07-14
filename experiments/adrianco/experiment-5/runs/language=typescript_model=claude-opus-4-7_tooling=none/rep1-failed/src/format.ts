import type { Match, Player, TeamRecord } from './types.js';
import type { AggregateStats, HeadToHead } from './queries.js';

export function formatMatch(m: Match): string {
  const compRound = m.round ? `${m.competition} Round ${m.round}` : m.stage ? `${m.competition} ${m.stage}` : m.competition;
  return `- ${m.date}: ${m.homeTeam} ${m.homeGoals}-${m.awayGoals} ${m.awayTeam} (${compRound})`;
}

export function formatMatches(matches: Match[]): string {
  if (matches.length === 0) return 'No matches found.';
  return matches.map(formatMatch).join('\n');
}

export function formatTeamRecord(r: TeamRecord): string {
  const winRate = r.matches ? ((r.wins / r.matches) * 100).toFixed(1) : '0.0';
  return [
    `${r.team}:`,
    `- Matches: ${r.matches}`,
    `- Wins: ${r.wins}, Draws: ${r.draws}, Losses: ${r.losses}`,
    `- Goals For: ${r.goalsFor}, Goals Against: ${r.goalsAgainst}`,
    `- Points: ${r.points}`,
    `- Win rate: ${winRate}%`,
  ].join('\n');
}

export function formatStandings(records: TeamRecord[]): string {
  if (records.length === 0) return 'No standings available.';
  return records
    .map((r, i) => {
      const gd = r.goalsFor - r.goalsAgainst;
      return `${i + 1}. ${r.team} - ${r.points} pts (${r.wins}W, ${r.draws}D, ${r.losses}L) GD:${gd >= 0 ? '+' : ''}${gd}`;
    })
    .join('\n');
}

export function formatPlayer(p: Player): string {
  return `- ${p.name} - Overall: ${p.overall}, Position: ${p.position}, Club: ${p.club}, Nationality: ${p.nationality}`;
}

export function formatPlayers(players: Player[]): string {
  if (players.length === 0) return 'No players found.';
  return players.map(formatPlayer).join('\n');
}

export function formatHeadToHead(h: HeadToHead): string {
  const summary = `${h.teamA} vs ${h.teamB}: ${h.teamAWins} wins, ${h.teamBWins} wins, ${h.draws} draws (${h.teamAGoals}-${h.teamBGoals} goals)`;
  if (h.matches.length === 0) return `${summary}\nNo matches found.`;
  return `${summary}\n\nMatches:\n${formatMatches(h.matches)}`;
}

export function formatAggregate(a: AggregateStats): string {
  return [
    `Total matches: ${a.totalMatches}`,
    `Total goals: ${a.totalGoals}`,
    `Average goals per match: ${a.averageGoalsPerMatch}`,
    `Home wins: ${a.homeWins} (${(a.homeWinRate * 100).toFixed(1)}%)`,
    `Away wins: ${a.awayWins} (${(a.awayWinRate * 100).toFixed(1)}%)`,
    `Draws: ${a.draws} (${(a.drawRate * 100).toFixed(1)}%)`,
  ].join('\n');
}
