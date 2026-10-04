/** Turns knowledge-base answers into readable text for the LLM to relay. */
import { COMPETITION_LABELS, COMPETITION_NAMES, type CompetitionId } from './competitions.js';
import type { MatchView, SoccerKnowledge } from './knowledge.js';

type Answer<K extends keyof SoccerKnowledge> = SoccerKnowledge[K] extends (...args: never[]) => infer R ? R : never;

const LABEL_BY_NAME = new Map<string, string>(
  (Object.keys(COMPETITION_NAMES) as CompetitionId[]).map((id) => [COMPETITION_NAMES[id], COMPETITION_LABELS[id]]),
);

export function matchLine(m: MatchView): string {
  const label = LABEL_BY_NAME.get(m.competition) ?? m.competition;
  const detail = m.stage ? `${label} ${m.stage}` : m.round !== undefined ? `${label} Round ${m.round}` : label;
  const derby = m.derby ? ` [${m.derby}]` : '';
  return `${m.date}: ${m.homeTeam} ${m.homeGoals}-${m.awayGoals} ${m.awayTeam} (${detail})${derby}`;
}

function bullets(lines: string[]): string {
  return lines.map((l) => `- ${l}`).join('\n');
}

function more(total: number, shown: number): string {
  return total > shown ? `\n- ... (${total - shown} more matches in dataset)` : '';
}

export function formatMatches(a: Answer<'findMatches'>, title: string): string {
  if (a.total === 0) return `${title}\nNo matches found in the datasets.`;
  let text = `${title} (${a.total} found):\n${bullets(a.matches.map(matchLine))}${more(a.total, a.matches.length)}`;
  if (a.headToHead) {
    const h = a.headToHead;
    text += `\n\nHead-to-head in dataset: ${h.team} ${h.teamWins} wins, ${h.opponent} ${h.opponentWins} wins, ${h.draws} draws`;
  }
  return text;
}

function recordLines(r: { played: number; wins: number; draws: number; losses: number; goalsFor: number; goalsAgainst: number; winRate: number }): string[] {
  return [
    `Matches: ${r.played}`,
    `Wins: ${r.wins}, Draws: ${r.draws}, Losses: ${r.losses}`,
    `Goals For: ${r.goalsFor}, Goals Against: ${r.goalsAgainst}`,
    `Win rate: ${r.winRate.toFixed(1)}%`,
  ];
}

export function formatTeamRecord(a: Answer<'teamRecord'>): string {
  const scope = [
    a.filters.venue !== 'any' ? `${a.filters.venue} record` : 'record',
    a.filters.season || a.filters.competition ? `(${[a.filters.season, a.filters.competition].filter(Boolean).join(' ')})` : '',
    a.filters.dateFrom || a.filters.dateTo ? `from ${a.filters.dateFrom ?? 'the start'} to ${a.filters.dateTo ?? 'the end'}` : '',
  ].filter(Boolean).join(' ');
  const competitions = a.byCompetition.length > 1
    ? `\n\nBy competition:\n${bullets(a.byCompetition.map((c) => `${c.competition}: ${c.played} played, ${c.wins}W ${c.draws}D ${c.losses}L`))}`
    : '';
  return `${a.team} ${scope}:\n${bullets(recordLines(a))}${competitions}`;
}

export function formatHeadToHead(a: Answer<'headToHead'>): string {
  return [
    `${a.team} vs ${a.opponent} head-to-head (${a.played} matches):`,
    `- ${a.team} wins: ${a.wins}, ${a.opponent} wins: ${a.losses}, Draws: ${a.draws}`,
    `- Goals: ${a.team} ${a.goalsFor}, ${a.opponent} ${a.goalsAgainst}`,
    a.byCompetition.length ? `\nBy competition:\n${bullets(a.byCompetition.map((c) => `${c.competition}: ${c.wins}W ${c.draws}D ${c.losses}L`))}` : '',
    a.matches.length ? `\nMost recent meetings:\n${bullets(a.matches.map(matchLine))}` : '',
  ].filter(Boolean).join('\n');
}

export function formatCompetitions(a: Answer<'teamCompetitions'>): string {
  if (!a.competitions.length) return `${a.team} has no matches in the datasets.`;
  return `Competitions ${a.team} has played in:\n${bullets(
    a.competitions.map((c) => `${c.competition}: ${c.matches} matches, seasons ${c.seasons[0]}-${c.seasons[c.seasons.length - 1]} (${c.wins}W ${c.draws}D ${c.losses}L)`),
  )}`;
}

const MEASURE_LABELS: { [measure: string]: string } = {
  goals_scored: 'goals scored',
  goals_conceded: 'fewest goals conceded',
  points: 'points',
  wins: 'wins',
  win_rate: 'win rate',
  home_win_rate: 'home win rate',
  away_win_rate: 'away win rate',
};

export function formatRankings(a: Answer<'teamRankings'>): string {
  const rate = a.measure.endsWith('win_rate');
  const scope = [a.competition, a.season].filter(Boolean).join(' ');
  if (!a.rankings.length) return `No teams to rank by ${MEASURE_LABELS[a.measure]} in ${scope}.`;
  return `Teams ranked by ${MEASURE_LABELS[a.measure]} (${scope}${rate ? `, minimum ${a.minimumMatches} matches` : ''}):\n${a.rankings
    .map((r) => `${r.rank}. ${r.team} - ${rate ? `${r.value.toFixed(1)}%` : r.value} (${r.played} played, ${r.wins}W ${r.draws}D ${r.losses}L)`)
    .join('\n')}`;
}

export function formatTeamProfile(a: Answer<'teamProfile'>): string {
  const squad = a.squad.size
    ? `Squad in FIFA data: ${a.squad.size} players (avg rating: ${a.squad.averageOverall})\n${bullets(a.squad.players.map((p) => `${p.name} - Overall: ${p.overall}, Position: ${p.position}, Nationality: ${p.nationality}`))}`
    : 'Squad in FIFA data: no players listed for this club.';
  return [
    `${a.team} profile`,
    `All matches in dataset:\n${bullets(recordLines(a.record))}`,
    a.competitions.length ? `By competition:\n${bullets(a.competitions.map((c) => `${c.competition}: ${c.played} played, ${c.wins}W ${c.draws}D ${c.losses}L`))}` : '',
    a.recentMatches.length ? `Recent matches:\n${bullets(a.recentMatches.map(matchLine))}` : '',
    squad,
  ].filter(Boolean).join('\n\n');
}

export function formatStandings(a: Answer<'standings'>): string {
  const rows = a.table.map((r) => {
    const note = r.position === 1 ? ' - Champion' : a.relegated.includes(r.team) ? ' - Relegated' : '';
    return `${r.position}. ${r.team} - ${r.points} pts (${r.wins}W, ${r.draws}D, ${r.losses}L, GF ${r.goalsFor}, GA ${r.goalsAgainst}, GD ${r.goalDifference >= 0 ? '+' : ''}${r.goalDifference})${note}`;
  });
  return `${a.season} ${a.competition} Final Standings (calculated from ${a.matches} matches):\n${rows.join('\n')}${
    a.relegated.length ? `\n\nRelegated: ${a.relegated.join(', ')}` : ''
  }`;
}

export function formatBracket(a: Answer<'knockoutBracket'>): string {
  return `${a.competition} ${a.season} knockout stages:\n${a.stages
    .map((s) => `\n${s.stage[0].toUpperCase()}${s.stage.slice(1)}:\n${bullets(s.matches.map(matchLine))}`)
    .join('\n')}`;
}

export function formatStatistics(a: Answer<'matchStatistics'>): string {
  const scope = [a.team, a.competition, a.season].filter(Boolean).join(', ');
  if (a.matches === 0) return `No matches found for ${scope}.`;
  return [
    `Match statistics (${scope}):`,
    `- Matches: ${a.matches}`,
    `- Total goals: ${a.goals}`,
    `- Average goals per match: ${a.averageGoals.toFixed(2)}`,
    `- Home win rate: ${a.homeWinRate.toFixed(1)}%`,
    `- Draw rate: ${a.drawRate.toFixed(1)}%`,
    `- Away win rate: ${a.awayWinRate.toFixed(1)}%`,
    a.averageCorners !== null ? `- Average corners per match: ${a.averageCorners.toFixed(2)} (${a.matchesWithCorners} matches with corner data)` : '',
    a.averageShots !== null ? `- Average shots per match: ${a.averageShots.toFixed(2)} (${a.matchesWithShots} matches with shot data)` : '',
  ].filter(Boolean).join('\n');
}

export function formatBiggestWins(a: Answer<'biggestWins'>): string {
  if (!a.matches.length) return 'No wins found.';
  return `Biggest victories (${a.competition}):\n${a.matches.map((m, i) => `${i + 1}. ${matchLine(m)} - margin ${m.margin}`).join('\n')}`;
}

export function formatSeasonComparison(a: Answer<'compareSeasons'>): string {
  return `${a.competition} season comparison:\n${a.seasons
    .map((s) =>
      s.matches === 0
        ? `\n${s.season}: no matches in the datasets`
        : `\n${s.season}:\n${bullets([
            `Matches: ${s.matches}, Goals: ${s.goals}`,
            `Average goals per match: ${s.averageGoals.toFixed(2)}`,
            `Home wins ${s.homeWinRate.toFixed(1)}%, Draws ${s.drawRate.toFixed(1)}%, Away wins ${s.awayWinRate.toFixed(1)}%`,
            s.champion ? `Champion: ${s.champion}` : '',
            s.topScoringTeam ? `Top scoring team: ${s.topScoringTeam.team} (${s.topScoringTeam.goals} goals)` : '',
          ].filter(Boolean))}`,
    )
    .join('\n')}`;
}

export function formatPlayers(a: Answer<'searchPlayers'>, title: string): string {
  if (a.total === 0) return `${title}\nNo players found matching those criteria.`;
  return `${title} (${a.total} found, avg rating: ${a.averageOverall}):\n${a.players
    .map((p, i) => `${i + 1}. ${p.name} - Overall: ${p.overall}, Position: ${p.position || 'n/a'}, Club: ${p.club || 'no club'}, Nationality: ${p.nationality}, Age: ${p.age ?? 'n/a'}`)
    .join('\n')}${a.total > a.players.length ? `\n... (${a.total - a.players.length} more)` : ''}`;
}

export function formatPlayerProfile(a: Answer<'playerProfile'>): string {
  const p = a.player;
  if (!p) {
    const similar = a.suggestions.map((s) => `${s.name} (${s.club || 'no club'}, Overall: ${s.overall})`);
    return `No player named "${a.query}" is in the FIFA player data.${similar.length ? `\nPlayers with similar names: ${similar.join('; ')}` : ''}`;
  }
  const top = Object.entries(p.attributes)
    .filter(([k]) => !k.startsWith('GK') || p.position === 'GK')
    .sort(([, x], [, y]) => y - x)
    .slice(0, 6)
    .map(([k, v]) => `${k} ${v}`)
    .join(', ');
  return [
    `${p.name}`,
    `- Club: ${p.club || 'no club'}, Position: ${p.position}, Jersey: ${p.jerseyNumber ?? 'n/a'}`,
    `- Nationality: ${p.nationality}, Age: ${p.age ?? 'n/a'}`,
    `- Overall: ${p.overall}, Potential: ${p.potential ?? 'n/a'}`,
    `- Height: ${p.height ?? 'n/a'}, Weight: ${p.weight ?? 'n/a'}, Preferred foot: ${p.preferredFoot ?? 'n/a'}`,
    `- Value: ${p.value ?? 'n/a'}, Wage: ${p.wage ?? 'n/a'}`,
    top ? `- Best attributes: ${top}` : '',
    a.otherMatches.length ? `\nOther players matching the name: ${a.otherMatches.join('; ')}` : '',
  ].filter(Boolean).join('\n');
}

export function formatPlayersByClub(a: Answer<'playersByClub'>): string {
  const who = a.nationality ? `${a.nationality} players` : 'Players';
  const where = a.brazilianClubsOnly ? 'at Brazilian clubs' : 'by club';
  if (!a.clubs.length) return `${who} ${where}: none found in the FIFA data.`;
  return `${who} ${where}:\n${bullets(a.clubs.map((c) => `${c.club}: ${c.players} players (avg rating: ${c.averageOverall}, best: ${c.bestPlayer})`))}`;
}

export function formatOverview(a: Answer<'overview'>): string {
  return [
    'Datasets loaded:',
    bullets(a.datasets.map((d) => `${d.file}: ${d.records} records${d.loaded ? '' : ' (missing)'} - ${d.description}`)),
    `\nAfter merging duplicates: ${a.totals.matches} distinct matches between ${a.totals.teams} teams (seasons ${a.totals.firstSeason}-${a.totals.lastSeason}), and ${a.totals.players} players.`,
    `Competitions: ${a.competitions.join(', ')}`,
  ].join('\n');
}
