import { HeadToHead, Match, Player, StandingsEntry, TeamStats } from './types.js';
import { AggregateStats } from './queries.js';

export function formatMatch(m: Match): string {
  const meta = [m.competition, m.season ? `${m.season}` : undefined, m.round ? `Round ${m.round}` : undefined, m.stage]
    .filter(Boolean)
    .join(' · ');
  return `${m.date}: ${m.homeTeam} ${m.homeGoals}-${m.awayGoals} ${m.awayTeam} (${meta})`;
}

export function formatMatchList(matches: Match[], limit = 50): string {
  if (matches.length === 0) return 'No matches found.';
  const shown = matches.slice(0, limit).map(formatMatch).join('\n');
  const more = matches.length > limit ? `\n... and ${matches.length - limit} more` : '';
  return `${shown}${more}\nTotal: ${matches.length} match${matches.length === 1 ? '' : 'es'}`;
}

export function formatTeamStats(s: TeamStats, label?: string): string {
  const header = label ? `${label}\n` : '';
  return (
    `${header}` +
    `Team: ${s.team}\n` +
    `Played: ${s.played}\n` +
    `W/D/L: ${s.wins}/${s.draws}/${s.losses}\n` +
    `Goals For/Against: ${s.goalsFor}/${s.goalsAgainst} (diff ${s.goalDifference >= 0 ? '+' : ''}${s.goalDifference})\n` +
    `Points: ${s.points}\n` +
    `Win rate: ${(s.winRate * 100).toFixed(1)}%`
  );
}

export function formatHeadToHead(h: HeadToHead, sampleMatches = 5): string {
  const lines: string[] = [];
  lines.push(`Head-to-head: ${h.teamA} vs ${h.teamB}`);
  lines.push(`Matches: ${h.totalMatches}`);
  lines.push(`${h.teamA} wins: ${h.teamAWins}`);
  lines.push(`${h.teamB} wins: ${h.teamBWins}`);
  lines.push(`Draws: ${h.draws}`);
  lines.push(`Goals: ${h.teamA} ${h.teamAGoals} - ${h.teamBGoals} ${h.teamB}`);
  if (h.matches.length > 0) {
    lines.push('');
    lines.push(`Most recent matches:`);
    const recent = h.matches.slice(-sampleMatches).reverse();
    for (const m of recent) lines.push(`- ${formatMatch(m)}`);
  }
  return lines.join('\n');
}

export function formatStandings(entries: StandingsEntry[], limit = 30): string {
  if (entries.length === 0) return 'No standings available for this season/competition.';
  const header = 'Pos | Team                          | P  | W  | D  | L  | GF | GA | GD  | Pts';
  const sep = '----+-------------------------------+----+----+----+----+----+----+-----+----';
  const rows = entries.slice(0, limit).map((e) => {
    const team = e.team.length > 29 ? e.team.slice(0, 28) + '…' : e.team.padEnd(29);
    const gd = (e.goalDifference >= 0 ? '+' : '') + e.goalDifference;
    return ` ${String(e.position).padStart(2)} | ${team} | ${String(e.played).padStart(2)} | ${String(e.wins).padStart(2)} | ${String(e.draws).padStart(2)} | ${String(e.losses).padStart(2)} | ${String(e.goalsFor).padStart(2)} | ${String(e.goalsAgainst).padStart(2)} | ${gd.padStart(3)} | ${String(e.points).padStart(3)}`;
  });
  return [header, sep, ...rows].join('\n');
}

export function formatPlayer(p: Player): string {
  const bits = [
    p.position ? `Pos: ${p.position}` : null,
    p.overall != null ? `Overall: ${p.overall}` : null,
    p.potential != null ? `Potential: ${p.potential}` : null,
    p.club ? `Club: ${p.club}` : null,
    p.nationality ? `Nationality: ${p.nationality}` : null,
    p.age != null ? `Age: ${p.age}` : null,
  ].filter(Boolean);
  return `${p.name} — ${bits.join(', ')}`;
}

export function formatPlayerList(players: Player[], limit = 25): string {
  if (players.length === 0) return 'No players found.';
  const shown = players.slice(0, limit).map((p, i) => `${i + 1}. ${formatPlayer(p)}`).join('\n');
  const more = players.length > limit ? `\n... and ${players.length - limit} more` : '';
  return `${shown}${more}\nTotal: ${players.length} player${players.length === 1 ? '' : 's'}`;
}

export function formatAggregate(a: AggregateStats, label?: string): string {
  const head = label ? `${label}\n` : '';
  return (
    `${head}` +
    `Total matches: ${a.totalMatches}\n` +
    `Total goals: ${a.totalGoals}\n` +
    `Average goals/match: ${a.averageGoalsPerMatch.toFixed(2)}\n` +
    `Home wins: ${a.homeWins} (${(a.homeWinRate * 100).toFixed(1)}%)\n` +
    `Away wins: ${a.awayWins} (${(a.awayWinRate * 100).toFixed(1)}%)\n` +
    `Draws: ${a.draws} (${(a.drawRate * 100).toFixed(1)}%)`
  );
}
