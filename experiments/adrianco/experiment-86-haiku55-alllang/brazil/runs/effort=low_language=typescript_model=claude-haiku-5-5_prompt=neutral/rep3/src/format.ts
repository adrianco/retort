/*
 * Context: Renders query results as the plain-text layouts shown in the spec
 * (e.g. "Flamengo vs Fluminense" match lists, standings tables, player lists), so an LLM
 * can quote them directly. Kept free of MCP types so it is easy to unit test.
 * Related: queries.ts (data), server.ts (returns these strings as tool output).
 */
import type { Match, Player } from './types.js';
import type { AggregateStats, ClubSummary, HeadToHead, StandingRow, TeamStats } from './queries.js';

export function scoreLine(m: Match): string {
  return `${m.date}: ${m.home} ${m.homeGoals}-${m.awayGoals} ${m.away} (${m.competition}${m.round ? ` ${m.round}` : ''})`;
}

export function formatMatches(title: string, total: number, shown: Match[]): string {
  if (total === 0) return `${title}\nNo matches found.`;
  const lines = shown.map((m) => `- ${scoreLine(m)}`);
  const more = total > shown.length ? `\n- ... (${total - shown.length} more matches in dataset)` : '';
  return `${title} — ${total} match${total === 1 ? '' : 'es'}:\n${lines.join('\n')}${more}`;
}

export function formatTeamStats(s: TeamStats): string {
  const scope = [s.filter.competition, s.filter.season !== undefined ? String(s.filter.season) : undefined]
    .filter(Boolean)
    .join(' ');
  const venue = s.venue === 'any' ? '' : ` ${s.venue}`;
  const title = `${s.team.name}${scope ? ` (${scope})` : ''}${venue} record`;
  if (s.played === 0) return `${title}:\nNo matches found.`;
  return [
    `${title}:`,
    `- Matches: ${s.played}`,
    `- Wins: ${s.wins}, Draws: ${s.draws}, Losses: ${s.losses}`,
    `- Goals For: ${s.goalsFor}, Goals Against: ${s.goalsAgainst}`,
    `- Win rate: ${s.winRate.toFixed(1)}%`,
  ].join('\n');
}

export function formatHeadToHead(h: HeadToHead, recent = 5): string {
  if (h.played === 0) return `${h.teamA.name} vs ${h.teamB.name}: no meetings in dataset.`;
  const recentLines = h.meetings.slice(-recent).reverse().map((m) => `- ${scoreLine(m)}`);
  return [
    `${h.teamA.name} vs ${h.teamB.name} head-to-head in dataset:`,
    `Matches: ${h.played}, ${h.teamA.name} wins: ${h.wins}, ${h.teamB.name} wins: ${h.losses}, Draws: ${h.draws}`,
    `Goals: ${h.teamA.name} ${h.goalsFor} - ${h.goalsAgainst} ${h.teamB.name}`,
    `Most recent ${recentLines.length}:`,
    ...recentLines,
  ].join('\n');
}

export function formatStandings(title: string, rows: StandingRow[]): string {
  if (rows.length === 0) return `${title}\nNo matches found.`;
  const header = '#  Team                      Pts  W   D   L   GF   GA   GD';
  const body = rows.map((r) =>
    `${String(r.position).padEnd(3)}${r.team.padEnd(26)}${String(r.points).padEnd(5)}${String(r.wins).padEnd(4)}` +
    `${String(r.draws).padEnd(4)}${String(r.losses).padEnd(4)}${String(r.goalsFor).padEnd(5)}${String(r.goalsAgainst).padEnd(5)}` +
    `${r.goalDifference >= 0 ? '+' : ''}${r.goalDifference}`);
  return [`${title} (calculated from matches):`, header, ...body].join('\n');
}

export function formatAggregate(title: string, a: AggregateStats): string {
  return [
    `${title}:`,
    `- Matches: ${a.matches}`,
    `- Total goals: ${a.totalGoals}`,
    `- Average goals per match: ${a.avgGoalsPerMatch.toFixed(2)}`,
    `- Home win rate: ${a.homeWinRate.toFixed(1)}%`,
    `- Draw rate: ${a.drawRate.toFixed(1)}%`,
    `- Away win rate: ${a.awayWinRate.toFixed(1)}%`,
  ].join('\n');
}

export function formatPlayers(title: string, total: number, players: Player[]): string {
  if (total === 0) return `${title}\nNo players found.`;
  const lines = players.map((p, i) =>
    `${i + 1}. ${p.name} - Overall: ${p.overall ?? 'n/a'}, Potential: ${p.potential ?? 'n/a'}, ` +
    `Position: ${p.position || 'n/a'}, Club: ${p.club || 'n/a'}, Nationality: ${p.nationality}, Age: ${p.age ?? 'n/a'}`);
  const more = total > players.length ? `\n... (${total - players.length} more players in dataset)` : '';
  return `${title} — ${total} player${total === 1 ? '' : 's'}:\n${lines.join('\n')}${more}`;
}

export function formatClubSummaries(title: string, rows: ClubSummary[]): string {
  if (rows.length === 0) return `${title}\nNo clubs found.`;
  const lines = rows.map((r) =>
    `- ${r.club}: ${r.players} player${r.players === 1 ? '' : 's'} (avg overall ${r.avgOverall.toFixed(1)})` +
    (r.topPlayer ? `, top: ${r.topPlayer.name} (${r.topPlayer.overall})` : ''));
  return `${title}:\n${lines.join('\n')}`;
}
