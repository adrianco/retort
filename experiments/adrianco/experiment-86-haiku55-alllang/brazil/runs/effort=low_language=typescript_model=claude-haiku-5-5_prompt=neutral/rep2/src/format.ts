/**
 * Context: turns query results into the plain-text answer layout the spec
 * shows (match lines, records, standings tables). LLM clients read these
 * strings directly, so the wording stays stable and factual.
 */
import type { HeadToHead, LeagueStats, RankedTeam, RankMetric, StandingRow, TeamRecord, ClubSummary } from './queries.js';
import type { Match, Player } from './types.js';

const pct = (x: number) => `${(x * 100).toFixed(1)}%`;

export function formatMatchLine(m: Match): string {
  const detail = m.round ? `Round ${m.round}` : m.stage ? m.stage : undefined;
  const tag = detail ? ` (${m.competition}, ${detail})` : ` (${m.competition})`;
  return `- ${m.date}: ${m.home.name} ${m.homeGoals}-${m.awayGoals} ${m.away.name}${tag}`;
}

export function formatMatches(title: string, matches: Match[], total: number, limit: number): string {
  if (matches.length === 0) return `${title}\nNo matches found.`;
  const lines = matches.slice(0, limit).map(formatMatchLine);
  const more = total > limit ? `\n- ... (${total - limit} more matches in dataset)` : '';
  return `${title}\n${lines.join('\n')}${more}\nTotal matches: ${total}`;
}

export function formatTeamRecord(r: TeamRecord, label: string): string {
  if (r.matches === 0) return `${r.team} ${label}: no matches found.`;
  return [
    `${r.team} ${label}:`,
    `- Matches: ${r.matches}`,
    `- Wins: ${r.wins}, Draws: ${r.draws}, Losses: ${r.losses}`,
    `- Goals For: ${r.goalsFor}, Goals Against: ${r.goalsAgainst}`,
    `- Win rate: ${pct(r.winRate)}`,
  ].join('\n');
}

export function formatHeadToHead(h: HeadToHead, limit: number): string {
  if (h.matches.length === 0) return `${h.teamA} vs ${h.teamB}: no head-to-head matches in dataset.`;
  const lines = h.matches.slice(0, limit).map(formatMatchLine);
  const more = h.matches.length > limit ? `\n- ... (${h.matches.length - limit} more matches in dataset)` : '';
  return [
    `${h.teamA} vs ${h.teamB} (head-to-head in dataset):`,
    ...lines,
    more,
    `Head-to-head in dataset: ${h.teamA} ${h.winsA} wins, ${h.teamB} ${h.winsB} wins, ${h.draws} draws`,
    `Goals: ${h.teamA} ${h.goalsA} - ${h.goalsB} ${h.teamB}`,
  ].filter((l) => l !== '').join('\n');
}

export function formatStandings(title: string, rows: StandingRow[]): string {
  if (rows.length === 0) return `${title}\nNo matches found.`;
  const lines = rows.map(
    (r) => `${r.position}. ${r.team} - ${r.points} pts (${r.wins}W, ${r.draws}D, ${r.losses}L, GF ${r.goalsFor}, GA ${r.goalsAgainst})`,
  );
  return `${title}\n${lines.join('\n')}`;
}

export function formatRanking(title: string, metric: RankMetric, rows: RankedTeam[]): string {
  if (rows.length === 0) return `${title}\nNo teams match the filters.`;
  const fmt = (v: number) => (metric === 'win_rate' ? pct(v) : metric === 'points_per_match' ? v.toFixed(2) : String(v));
  const lines = rows.map((r, i) => `${i + 1}. ${r.team} - ${fmt(r.value)} (${r.matches} matches, ${r.wins}W, ${r.draws}D, ${r.losses}L)`);
  return `${title}\n${lines.join('\n')}`;
}

export function formatLeagueStats(title: string, s: LeagueStats): string {
  if (s.matches === 0) return `${title}\nNo matches found.`;
  return [
    title,
    `Matches: ${s.matches}`,
    `Average goals per match: ${s.goalsPerMatch.toFixed(2)}`,
    `Home win rate: ${pct(s.homeWinRate)}`,
    `Draw rate: ${pct(s.drawRate)}`,
    `Away win rate: ${pct(s.awayWinRate)}`,
  ].join('\n');
}

export function formatPlayers(title: string, players: Player[]): string {
  if (players.length === 0) return `${title}\nNo players found.`;
  const lines = players.map((p) => {
    const parts = [
      `Overall: ${p.overall ?? 'n/a'}`,
      p.position ? `Position: ${p.position}` : undefined,
      `Club: ${p.club || 'n/a'}`,
      `Nationality: ${p.nationality}`,
      p.age !== undefined ? `Age: ${p.age}` : undefined,
    ].filter(Boolean);
    return `- ${p.name} - ${parts.join(', ')}`;
  });
  return `${title}\n${lines.join('\n')}`;
}

export function formatClubSummary(title: string, rows: ClubSummary[]): string {
  if (rows.length === 0) return `${title}\nNo players found.`;
  const lines = rows.map((r) => `- ${r.club}: ${r.players} players (avg overall ${r.averageOverall.toFixed(1)})`);
  return `${title}\n${lines.join('\n')}`;
}

export const RANK_METRICS: RankMetric[] = ['win_rate', 'wins', 'goals_for', 'goal_difference', 'points_per_match'];
