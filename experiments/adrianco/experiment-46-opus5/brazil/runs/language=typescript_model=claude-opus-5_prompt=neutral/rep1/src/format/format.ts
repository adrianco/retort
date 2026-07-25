/**
 * Rendering results as text for an LLM to read back to a user.
 *
 * MCP tools return both a structured payload and a text block; this module
 * produces the text. The shapes follow the worked examples in the
 * specification -- one line per match, a labelled block per record, a numbered
 * table for standings -- because those are what the calling model is being
 * asked to paraphrase.
 */

import { COMPETITIONS, type Match, type Player } from '../domain/types.js';
import type { SoccerGraph } from '../graph/graph.js';
import type { Standings } from '../query/competitionQueries.js';
import type { HeadToHeadResult, TeamRecord } from '../query/teamQueries.js';
import type { AggregateStats } from '../query/statsQueries.js';

export function teamName(graph: SoccerGraph, teamId: string): string {
  return graph.teams.get(teamId)?.name ?? teamId;
}

export function percent(fraction: number, digits = 1): string {
  return `${(fraction * 100).toFixed(digits)}%`;
}

export function decimal(value: number, digits = 2): string {
  return value.toFixed(digits);
}

/** "2019-11-24: Flamengo 2-0 Ceará (Brasileirão Série A, Round 36)". */
export function formatMatchLine(graph: SoccerGraph, match: Match): string {
  const score =
    match.homeGoals === null || match.awayGoals === null
      ? 'vs'
      : `${match.homeGoals}-${match.awayGoals}`;
  const context = [COMPETITIONS[match.competition].name, match.season.toString()];
  // Cup rounds carry both a number and a label, and for the early rounds the
  // label is just the number spelled out -- print it once.
  const stage = match.stage ? titleise(match.stage) : undefined;
  if (match.round !== undefined && stage !== `Round ${match.round}`) {
    context.push(`Round ${match.round}`);
  }
  if (stage) context.push(stage);
  if (match.venue) context.push(match.venue);

  return `${match.date}: ${teamName(graph, match.homeTeamId)} ${score} ${teamName(graph, match.awayTeamId)} (${context.join(', ')})`;
}

export function formatMatchList(graph: SoccerGraph, matches: readonly Match[], limit = 25): string {
  if (matches.length === 0) return 'No matches found.';
  const shown = matches.slice(0, limit);
  const lines = shown.map((match) => `- ${formatMatchLine(graph, match)}`);
  if (matches.length > shown.length) {
    lines.push(`- ... and ${matches.length - shown.length} more`);
  }
  return lines.join('\n');
}

export function formatRecord(record: TeamRecord, label = 'Record'): string {
  const lines = [
    `${label}:`,
    `- Matches: ${record.played}`,
    `- Wins: ${record.wins}, Draws: ${record.draws}, Losses: ${record.losses}`,
    `- Goals For: ${record.goalsFor}, Goals Against: ${record.goalsAgainst} (${signed(record.goalDifference)})`,
    `- Points: ${record.points}`,
    `- Win rate: ${percent(record.winRate)}`,
  ];
  if (record.withoutScore > 0) {
    lines.push(`- Excluded: ${record.withoutScore} match(es) with no recorded score`);
  }
  return lines.join('\n');
}

export function formatHeadToHead(graph: SoccerGraph, result: HeadToHeadResult, limit = 15): string {
  const title = result.rivalry
    ? `${result.teamA.name} vs ${result.teamB.name} (${result.rivalry}):`
    : `${result.teamA.name} vs ${result.teamB.name}:`;

  const body = [title, formatMatchList(graph, [...result.matches].reverse(), limit), ''];
  body.push(
    `Head-to-head in dataset: ${result.teamA.name} ${result.aWins} wins, ${result.teamB.name} ${result.bWins} wins, ${result.draws} draws`,
  );
  body.push(`Goals: ${result.teamA.name} ${result.aGoals}, ${result.teamB.name} ${result.bGoals}`);
  if (result.withoutScore > 0) {
    body.push(`(${result.withoutScore} meeting(s) had no recorded score and are excluded from the totals.)`);
  }
  return body.join('\n');
}

export function formatStandings(standings: Standings, limit = 30): string {
  if (standings.rows.length === 0) {
    return `No matches found for ${standings.competitionName} ${standings.season}.`;
  }

  const header = `${standings.season} ${standings.competitionName} ${standings.complete ? 'Final Standings' : 'Standings (partial data)'} (calculated from matches):`;
  const lines = standings.rows.slice(0, limit).map((row) => {
    const tag =
      row.position === 1 && standings.champion
        ? ' - Champion'
        : standings.relegated.some((r) => r.team.id === row.team.id)
          ? ' - Relegated'
          : '';
    const r = row.record;
    return `${row.position}. ${row.team.name} - ${r.points} pts (${r.wins}W, ${r.draws}D, ${r.losses}L) GF ${r.goalsFor} GA ${r.goalsAgainst} ${signed(r.goalDifference)}${tag}`;
  });

  const notes = standings.notes.map((note) => `Note: ${note}`);
  return [header, ...lines, '', ...notes].join('\n');
}

export function formatPlayerLine(player: Player, index?: number): string {
  const prefix = index === undefined ? '-' : `${index}.`;
  const parts = [
    `Overall: ${player.overall ?? 'n/a'}`,
    `Position: ${player.position || 'n/a'}`,
    `Club: ${player.club || 'unattached'}`,
    `Nationality: ${player.nationality || 'n/a'}`,
  ];
  return `${prefix} ${player.name} - ${parts.join(', ')}`;
}

export function formatPlayerList(players: readonly Player[]): string {
  if (players.length === 0) return 'No players found.';
  return players.map((player, index) => formatPlayerLine(player, index + 1)).join('\n');
}

export function formatPlayerProfile(player: Player): string {
  const lines = [
    `${player.name}`,
    `- Age: ${player.age ?? 'n/a'}`,
    `- Nationality: ${player.nationality || 'n/a'}`,
    `- Club: ${player.club || 'unattached'}${player.jerseyNumber !== null ? ` (#${player.jerseyNumber})` : ''}`,
    `- Position: ${player.position || 'n/a'} (${player.positionGroup})`,
    `- Overall: ${player.overall ?? 'n/a'}, Potential: ${player.potential ?? 'n/a'}`,
    `- Preferred foot: ${player.preferredFoot || 'n/a'}`,
    `- Height/Weight: ${player.height || 'n/a'} / ${player.weight || 'n/a'}`,
    `- Value: ${money(player.valueEur)}, Wage: ${money(player.wageEur)} per week`,
    `- Contract until: ${player.contractValidUntil || 'n/a'}`,
  ];

  const topSkills = Object.entries(player.skills)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 8)
    .map(([skill, value]) => `${skill} ${value}`);
  if (topSkills.length > 0) lines.push(`- Best attributes: ${topSkills.join(', ')}`);

  return lines.join('\n');
}

export function formatAggregateStats(stats: AggregateStats, label: string): string {
  if (stats.matchesWithScore === 0) {
    return `${label}: no matches with a recorded score.`;
  }
  const lines = [
    `${label}:`,
    `- Matches: ${stats.matches}${stats.matches !== stats.matchesWithScore ? ` (${stats.matchesWithScore} with a recorded score)` : ''}`,
    `- Date range: ${stats.firstDate} to ${stats.lastDate}`,
    `- Goals: ${stats.goals} (${decimal(stats.goalsPerMatch)} per match)`,
    `- Home wins: ${stats.homeWins} (${percent(stats.homeWinRate)})`,
    `- Draws: ${stats.draws} (${percent(stats.drawRate)})`,
    `- Away wins: ${stats.awayWins} (${percent(stats.awayWinRate)})`,
    `- Home goals ${stats.homeGoals} vs away goals ${stats.awayGoals}`,
    `- Both teams scored: ${percent(stats.bothTeamsScoredRate)}`,
    `- Biggest winning margin: ${stats.biggestMargin} goals; highest scoring match: ${stats.highestScoring} goals`,
  ];
  return lines.join('\n');
}

export function money(value: number | null): string {
  if (value === null) return 'n/a';
  if (value >= 1e6) return `€${(value / 1e6).toFixed(1)}M`;
  if (value >= 1e3) return `€${(value / 1e3).toFixed(0)}K`;
  return `€${value}`;
}

export function signed(value: number): string {
  return value > 0 ? `+${value}` : `${value}`;
}

export function titleise(value: string): string {
  return value.replace(/\b[a-z]/g, (c) => c.toUpperCase());
}

export function bullets(items: string[]): string {
  return items.map((item) => `- ${item}`).join('\n');
}
