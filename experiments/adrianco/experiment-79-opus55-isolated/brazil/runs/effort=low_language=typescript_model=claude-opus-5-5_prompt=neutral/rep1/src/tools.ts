/** MCP tool definitions: each tool validates its input and renders a plain-text answer. */
import { z } from 'zod';
import { COMPETITIONS, Match, Player } from './data.js';
import { MatchFilter, SoccerKB, TeamRecord, resolveCompetition } from './queries.js';

export interface ToolDef {
  name: string;
  description: string;
  schema: z.ZodRawShape;
  run(kb: SoccerKB, args: any): string;
}

const team = (what: string) =>
  z.string().min(1).describe(`${what}. Any common spelling works: "Flamengo", "Flamengo-RJ", "Sao Paulo", "Atlético Mineiro".`);
const competition = z
  .string()
  .optional()
  .describe('Competition: "Brasileirão" (Série A), "Série B", "Série C", "Copa do Brasil" or "Libertadores". Omit for all.');
const season = z.number().int().min(1900).max(2100).optional().describe('Season year, e.g. 2019');
const isoDate = (what: string) =>
  z.string().regex(/^\d{4}-\d{2}-\d{2}$/, 'Use YYYY-MM-DD').optional().describe(`${what} (YYYY-MM-DD, inclusive)`);
const limit = (def: number) => z.number().int().min(1).max(500).default(def).describe('Maximum rows to list');
const venue = z.enum(['home', 'away', 'all']).default('all').describe('Count home matches, away matches, or both');

const f1 = (n: number) => n.toFixed(1);

function scope(f: { competition?: string; season?: number }): string {
  const parts = [f.season, f.competition ? resolveCompetition(f.competition) : undefined].filter(Boolean);
  return parts.length ? parts.join(' ') : 'all competitions';
}

export function formatMatch(kb: SoccerKB, m: Match, withStats = false): string {
  const detail = [m.competition + (m.competition === COMPETITIONS.libertadores || m.competition === COMPETITIONS.cup ? ` ${m.season}` : '')];
  if (m.stage) detail.push(m.stage);
  else if (m.round) detail.push(`Round ${m.round}`);
  if (m.arena) detail.push(m.arena);
  let line = `${m.date}: ${kb.teamName(m.home)} ${m.homeGoals}-${m.awayGoals} ${kb.teamName(m.away)} (${detail.join(', ')})`;
  const s = m.stats;
  if (withStats && s && s.homeShots !== undefined) {
    line += ` [shots ${s.homeShots}-${s.awayShots}, corners ${s.homeCorners}-${s.awayCorners}]`;
  }
  return line;
}

function listMatches(kb: SoccerKB, ms: Match[], max: number, withStats = false): string[] {
  const lines = ms.slice(0, max).map((m) => `- ${formatMatch(kb, m, withStats)}`);
  if (ms.length > max) lines.push(`- ... (${ms.length - max} more matches in dataset)`);
  return lines;
}

function recordLines(r: TeamRecord): string[] {
  return [
    `- Matches: ${r.matches}`,
    `- Wins: ${r.wins}, Draws: ${r.draws}, Losses: ${r.losses}`,
    `- Goals For: ${r.goalsFor}, Goals Against: ${r.goalsAgainst} (difference ${signed(r.goalDifference)})`,
    `- Points: ${r.points}`,
    `- Win rate: ${f1(r.winRate)}%`,
  ];
}

const signed = (n: number) => (n > 0 ? `+${n}` : `${n}`);

function playerLine(p: Player): string {
  return `${p.name} - Overall: ${p.overall}, Potential: ${p.potential}, Position: ${p.position || 'n/a'}, Age: ${p.age ?? 'n/a'}, Club: ${p.club || 'Free agent'}, Nationality: ${p.nationality}`;
}

function matchFilter(a: any): MatchFilter {
  return {
    team: a.team, opponent: a.opponent, homeTeam: a.home_team, awayTeam: a.away_team, competition: a.competition,
    season: a.season, dateFrom: a.date_from, dateTo: a.date_to, stage: a.stage,
  };
}

export const tools: ToolDef[] = [
  {
    name: 'search_matches',
    description:
      'Find matches by team (home, away or either), opponent, competition, season, date range or stage (e.g. "final"). ' +
      'Most recent first. Use for "What matches did Palmeiras play in 2019?", "When did Flamengo last play Corinthians?", "Find all Copa do Brasil finals".',
    schema: {
      team: team('Team playing home or away').optional(),
      opponent: team('Opponent of `team`').optional(),
      home_team: team('Team playing at home').optional(),
      away_team: team('Team playing away').optional(),
      competition,
      season,
      date_from: isoDate('Earliest match date'),
      date_to: isoDate('Latest match date'),
      stage: z.string().optional().describe('Knockout stage: "final", "semifinals", "quarterfinals", "round of 16", "group stage"'),
      limit: limit(25),
    },
    run(kb, a) {
      const ms = kb.findMatches(matchFilter(a));
      if (!ms.length) return 'No matches found for those criteria in the dataset.';
      return [`Found ${ms.length} match${ms.length === 1 ? '' : 'es'}:`, ...listMatches(kb, ms, a.limit ?? 25, true)].join('\n');
    },
  },
  {
    name: 'head_to_head',
    description: 'Compare two teams head-to-head: wins, draws, goals and the list of their meetings, optionally within a competition or season.',
    schema: { team_a: team('First team'), team_b: team('Second team'), competition, season, limit: limit(15) },
    run(kb, a) {
      const h = kb.headToHead(a.team_a, a.team_b, { competition: a.competition, season: a.season });
      const [na, nb] = [kb.teamName(h.teamA), kb.teamName(h.teamB)];
      const derby = kb.derbyName(h.teamA, h.teamB);
      if (!h.matches.length) return `No matches between ${na} and ${nb} found in the dataset (${scope(a)}).`;
      return [
        `${na} vs ${nb}${derby ? ` (${derby})` : ''} - ${scope(a)}:`,
        ...listMatches(kb, h.matches, a.limit ?? 15),
        '',
        `Head-to-head in dataset (${h.matches.length} matches): ${na} ${h.winsA} wins, ${nb} ${h.winsB} wins, ${h.draws} draws`,
        `Goals: ${na} ${h.goalsA}, ${nb} ${h.goalsB}`,
      ].join('\n');
    },
  },
  {
    name: 'team_stats',
    description: 'Win/draw/loss record, goals for/against and win rate for one team, optionally limited to a season, competition, or home/away matches.',
    schema: { team: team('Team'), season, competition, venue },
    run(kb, a) {
      const r = kb.teamRecord(a.team, { season: a.season, competition: a.competition, venue: a.venue });
      const v = a.venue && a.venue !== 'all' ? `${a.venue} ` : '';
      if (!r.matches) return `No ${v}matches for ${kb.teamName(r.team)} found (${scope(a)}).`;
      return [`${kb.teamName(r.team)} ${v}record (${scope(a)}):`, ...recordLines(r)].join('\n');
    },
  },
  {
    name: 'team_overview',
    description: 'Everything known about a team across all files: competitions and seasons played, overall record in each, and its players in the FIFA database.',
    schema: { team: team('Team') },
    run(kb, a) {
      const id = kb.team(a.team);
      const name = kb.teamName(id);
      const lines = [`${name} - overview from match and player data:`, '', 'Competitions:'];
      for (const c of kb.teamCompetitions(a.team)) {
        const r = c.record;
        lines.push(
          `- ${c.competition} (${compactYears(c.seasons)}): ${r.matches} matches, ${r.wins}W ${r.draws}D ${r.losses}L, goals ${r.goalsFor}-${r.goalsAgainst}, win rate ${f1(r.winRate)}%`,
        );
      }
      const squad = kb.data.players.filter((p) => p.clubId === id).sort((x, y) => y.overall - x.overall);
      lines.push('');
      if (squad.length) {
        const avg = squad.reduce((s, p) => s + p.overall, 0) / squad.length;
        lines.push(`FIFA squad: ${squad.length} players (avg rating: ${f1(avg)}). Top rated:`);
        squad.slice(0, 5).forEach((p, i) => lines.push(`${i + 1}. ${playerLine(p)}`));
      } else lines.push('FIFA squad: this club is not present in the FIFA player dataset.');
      return lines.join('\n');
    },
  },
  {
    name: 'standings',
    description:
      'League table for a season calculated from match results (3 points per win). Answers "Who won the 2019 Brasileirão?" and "Which teams were relegated?". Defaults to Série A.',
    schema: { season: season.unwrap(), competition, limit: limit(30) },
    run(kb, a) {
      const comp = resolveCompetition(a.competition ?? 'Brasileirão');
      const table = kb.standings(a.season, comp);
      if (!table.length) {
        return `No ${comp} matches for ${a.season} in the dataset. Seasons available: ${compactYears(kb.seasons(comp))}.`;
      }
      const isLeague = comp !== COMPETITIONS.cup && comp !== COMPETITIONS.libertadores;
      const n = table.length;
      const played = table.reduce((s, r) => s + r.matches, 0) / 2;
      const complete = comp === COMPETITIONS.serieA && played >= 0.97 * n * (n - 1);
      const relegated = a.season === 2003 ? 2 : 4;
      const lines = [`${a.season} ${comp} ${complete ? 'Final Standings' : 'Table'} (calculated from matches):`];
      table.slice(0, a.limit ?? 30).forEach((r, i) => {
        let tag = '';
        if (complete && i === 0) tag = ' - Champion';
        else if (complete && i >= n - relegated) tag = ' - Relegated';
        lines.push(
          `${i + 1}. ${kb.teamName(r.team)} - ${r.points} pts (${r.wins}W, ${r.draws}D, ${r.losses}L), goals ${r.goalsFor}:${r.goalsAgainst} (${signed(r.goalDifference)})${tag}`,
        );
      });
      lines.push('');
      if (!isLeague) lines.push('Note: this is a knockout competition; the table only aggregates results. Use competition_knockout for the bracket.');
      else if (!complete) lines.push(`Note: ${played} matches available for this season, so the table may be incomplete or combine groups/play-offs; no champion or relegation is inferred.`);
      else lines.push(`Note: bottom ${relegated} marked as relegated. Points deductions and tribunal decisions are not in the data.`);
      return lines.join('\n');
    },
  },
  {
    name: 'competition_knockout',
    description: 'Knockout bracket of a cup season grouped by stage, with the winner of the final where inferable. For "Show the 2018 Copa Libertadores bracket" or "Who won the 2015 Copa do Brasil?".',
    schema: { competition: z.string().describe('"Libertadores" or "Copa do Brasil"'), season: season.unwrap(), include_group_stage: z.boolean().default(false) },
    run(kb, a) {
      const comp = resolveCompetition(a.competition);
      const ms = kb.findMatches({ competition: comp, season: a.season }).reverse();
      if (!ms.length) return `No ${comp} matches for ${a.season}. Seasons available: ${compactYears(kb.seasons(comp))}.`;
      const stages = new Map<string, Match[]>();
      for (const m of ms) {
        const key = m.stage ?? (m.round ? `Round ${m.round}` : 'Unspecified stage');
        if (key === 'group stage' && !a.include_group_stage) continue;
        stages.set(key, [...(stages.get(key) ?? []), m]);
      }
      const lines = [`${a.season} ${comp} knockout rounds:`];
      for (const [stage, list] of stages) {
        lines.push('', `${stage} (${list.length} matches):`, ...list.map((m) => `- ${formatMatch(kb, m)}`));
      }
      const final = stages.get('final');
      if (final?.length) {
        const agg = new Map<string, number>();
        for (const m of final) {
          agg.set(m.home, (agg.get(m.home) ?? 0) + m.homeGoals);
          agg.set(m.away, (agg.get(m.away) ?? 0) + m.awayGoals);
        }
        const [x, y] = [...agg].sort((p, q) => q[1] - p[1]);
        lines.push('');
        if (agg.size === 2 && x[1] !== y[1]) lines.push(`Champion: ${kb.teamName(x[0])} (${x[1]}-${y[1]} on aggregate over ${final.length} match${final.length > 1 ? 'es' : ''})`);
        else lines.push('Final level on aggregate in the data; the tie-break (penalties/away goals) is not recorded.');
      } else lines.push('', 'The final of this season is not identifiable in the dataset.');
      return lines.join('\n');
    },
  },
  {
    name: 'rank_teams',
    description:
      'Rank teams by win rate, points, wins or goals scored, overall or for home/away matches only. For "Which team has the best home/away record?" and "Which team scored the most goals in Serie A 2019?".',
    schema: {
      metric: z.enum(['winRate', 'points', 'wins', 'goalsFor']).default('winRate'),
      venue,
      competition,
      season,
      min_matches: z.number().int().min(1).optional().describe('Ignore teams with fewer matches (default 10 for win rate, else 1)'),
      limit: limit(10),
    },
    run(kb, a) {
      const metric = a.metric ?? 'winRate';
      const min = a.min_matches ?? (metric === 'winRate' ? 10 : 1);
      const rows = kb.rankTeams({ competition: a.competition, season: a.season, venue: a.venue, metric, minMatches: min });
      if (!rows.length) return `No teams with at least ${min} matches found (${scope(a)}).`;
      const v = a.venue && a.venue !== 'all' ? `${a.venue} ` : '';
      const label = { winRate: 'win rate', points: 'points', wins: 'wins', goalsFor: 'goals scored' }[metric as 'winRate'];
      return [
        `Teams ranked by ${v}${label} (${scope(a)}, min ${min} matches):`,
        ...rows.slice(0, a.limit ?? 10).map(
          (r, i) =>
            `${i + 1}. ${kb.teamName(r.team)} - ${f1(r.winRate)}% wins, ${r.matches} matches (${r.wins}W, ${r.draws}D, ${r.losses}L), goals ${r.goalsFor}-${r.goalsAgainst}, ${r.points} pts`,
        ),
      ].join('\n');
    },
  },
  {
    name: 'league_stats',
    description: 'Aggregate statistics: matches, total goals, average goals per match, home win / draw / away win rates. Filter by competition, season or team.',
    schema: { competition, season, team: team('Only matches involving this team').optional() },
    run(kb, a) {
      const s = kb.leagueStats(matchFilter(a));
      if (!s.matches) return `No matches found (${scope(a)}).`;
      return [
        `Statistics for ${a.team ? kb.teamName(kb.team(a.team)) + ' matches, ' : ''}${scope(a)}:`,
        `- Matches: ${s.matches}`,
        `- Total goals: ${s.goals}`,
        `- Average goals per match: ${s.goalsPerMatch.toFixed(2)}`,
        `- Home win rate: ${f1(s.homeWinRate)}% (${s.homeWins})`,
        `- Draw rate: ${f1(s.drawRate)}% (${s.draws})`,
        `- Away win rate: ${f1(s.awayWinRate)}% (${s.awayWins})`,
      ].join('\n');
    },
  },
  {
    name: 'biggest_wins',
    description: 'Largest winning margins in the dataset, optionally for a team, competition or season.',
    schema: { competition, season, team: team('Only matches involving this team').optional(), limit: limit(10) },
    run(kb, a) {
      const ms = kb.biggestWins(matchFilter(a), a.limit ?? 10);
      if (!ms.length) return `No decisive matches found (${scope(a)}).`;
      return [`Biggest victories (${scope(a)}):`, ...ms.map((m, i) => `${i + 1}. ${formatMatch(kb, m)}`)].join('\n');
    },
  },
  {
    name: 'compare_seasons',
    description: 'Compare two seasons of a competition: goals, averages, home advantage, champion/leader and top-scoring team.',
    schema: { season_a: season.unwrap(), season_b: season.unwrap(), competition },
    run(kb, a) {
      const comp = resolveCompetition(a.competition ?? 'Brasileirão');
      const lines = [`${comp}: ${a.season_a} vs ${a.season_b}`];
      for (const y of [a.season_a, a.season_b]) {
        const s = kb.leagueStats({ competition: comp, season: y });
        lines.push('', `${y}:`);
        if (!s.matches) {
          lines.push('- No matches in dataset');
          continue;
        }
        const leader = kb.standings(y, comp)[0];
        const scorer = kb.rankTeams({ competition: comp, season: y, metric: 'goalsFor' })[0];
        lines.push(
          `- Matches: ${s.matches}, Goals: ${s.goals}, Average goals per match: ${s.goalsPerMatch.toFixed(2)}`,
          `- Home wins ${f1(s.homeWinRate)}%, Draws ${f1(s.drawRate)}%, Away wins ${f1(s.awayWinRate)}%`,
          `- Most points: ${kb.teamName(leader.team)} (${leader.points} pts, ${leader.wins}W ${leader.draws}D ${leader.losses}L)`,
          `- Most goals scored: ${kb.teamName(scorer.team)} (${scorer.goalsFor})`,
        );
      }
      return lines.join('\n');
    },
  },
  {
    name: 'find_derbies',
    description: 'Matches between traditional rivals (Fla-Flu, Derby Paulista, Grenal, Clássico Mineiro, ...), optionally for a season, competition or team.',
    schema: { season, competition, team: team('Only derbies involving this team').optional(), limit: limit(40) },
    run(kb, a) {
      const ms = kb.derbies(matchFilter(a));
      if (!ms.length) return `No derby matches found (${scope(a)}).`;
      const max = a.limit ?? 40;
      const lines = ms.slice(0, max).map((m) => `- ${kb.derbyName(m.home, m.away)}: ${formatMatch(kb, m)}`);
      if (ms.length > max) lines.push(`- ... (${ms.length - max} more)`);
      return [`Derbies (${scope(a)}): ${ms.length} matches`, ...lines].join('\n');
    },
  },
  {
    name: 'search_players',
    description:
      'Search the FIFA player database by name, nationality, club, position (code like "ST" or group: forward, midfielder, defender, goalkeeper) and rating. Sorted by overall rating. For "Who are the top Brazilian players?", "Which players play for Santos?".',
    schema: {
      name: z.string().optional().describe('Full or partial player name; accents optional'),
      nationality: z.string().optional().describe('Country, e.g. "Brazil"'),
      club: z.string().optional().describe('Club name or part of it'),
      position: z.string().optional(),
      min_overall: z.number().int().min(0).max(100).optional(),
      max_age: z.number().int().min(10).max(60).optional(),
      brazilian_clubs_only: z.boolean().optional().describe('Only players at clubs that appear in the Brazilian match data'),
      sort_by: z.enum(['overall', 'potential', 'age']).default('overall'),
      limit: limit(20),
    },
    run(kb, a) {
      const ps = kb.findPlayers({
        name: a.name, nationality: a.nationality, club: a.club, position: a.position, minOverall: a.min_overall,
        maxAge: a.max_age, brazilianClubsOnly: a.brazilian_clubs_only, sortBy: a.sort_by,
      });
      if (!ps.length) {
        return 'No players found for those criteria. Note the FIFA dataset only includes licensed clubs (e.g. Flamengo, Palmeiras, Corinthians and São Paulo are absent).';
      }
      const max = a.limit ?? 20;
      const avg = ps.reduce((s, p) => s + p.overall, 0) / ps.length;
      const lines = ps.slice(0, max).map((p, i) => `${i + 1}. ${playerLine(p)}`);
      if (ps.length > max) lines.push(`... (${ps.length - max} more players)`);
      return [`Found ${ps.length} player${ps.length === 1 ? '' : 's'} (avg rating: ${f1(avg)}):`, ...lines].join('\n');
    },
  },
  {
    name: 'player_profile',
    description: 'Detailed profile of a player (ratings, physical attributes, skills) plus the recent results of their club when it is a Brazilian team. For "Who is Gabriel Barbosa?".',
    schema: { name: z.string().min(1).describe('Player name or part of it') },
    run(kb, a) {
      const ps = kb.findPlayers({ name: a.name });
      if (!ps.length) {
        const words: string[] = a.name.split(/\s+/).filter((w: string) => w.length > 2);
        const near = words.flatMap((w) => kb.findPlayers({ name: w }).slice(0, 3));
        const hint = near.length ? ` Closest by partial name: ${near.map((o) => `${o.name} (${o.club || 'no club'}, ${o.overall})`).join('; ')}.` : '';
        return `No player matching "${a.name}" in the FIFA dataset.${hint}`;
      }
      const p = ps[0];
      const top = Object.entries(p.skills).sort((x, y) => y[1] - x[1]).slice(0, 8);
      const lines = [
        `${p.name} (FIFA ID ${p.id})`,
        `- Nationality: ${p.nationality}, Age: ${p.age ?? 'n/a'}`,
        `- Club: ${p.club || 'Free agent'}, Position: ${p.position || 'n/a'}, Jersey: ${p.jersey ?? 'n/a'}`,
        `- Overall: ${p.overall}, Potential: ${p.potential}`,
        `- Height: ${p.height ?? 'n/a'}, Weight: ${p.weight ?? 'n/a'}, Preferred foot: ${p.foot ?? 'n/a'}`,
        `- Value: ${p.value ?? 'n/a'}, Wage: ${p.wage ?? 'n/a'}`,
        `- Best skills: ${top.map(([k, v]) => `${k} ${v}`).join(', ')}`,
      ];
      if (p.clubId) {
        const recent = kb.data.matches.filter((m) => m.home === p.clubId || m.away === p.clubId).slice(-3).reverse();
        lines.push('', `Latest ${kb.teamName(p.clubId)} matches in dataset:`, ...recent.map((m) => `- ${formatMatch(kb, m)}`));
      }
      if (ps.length > 1) {
        lines.push('', `Other matches for "${a.name}": ${ps.slice(1, 6).map((o) => `${o.name} (${o.club || 'no club'}, ${o.overall})`).join('; ')}${ps.length > 6 ? ` and ${ps.length - 6} more` : ''}`);
      }
      return lines.join('\n');
    },
  },
  {
    name: 'brazilian_club_squads',
    description: 'Brazilian clubs present in the FIFA data with squad size, average rating and best player; optionally count only players of one nationality (e.g. Brazilian players at Brazilian clubs).',
    schema: { nationality: z.string().optional().describe('e.g. "Brazil" to count only Brazilian players') },
    run(kb, a) {
      const rows = kb.brazilianClubSquads(a.nationality);
      if (!rows.length) return 'No players at Brazilian clubs found for those criteria.';
      return [
        `${a.nationality ? `${a.nationality} players` : 'Players'} at Brazilian clubs (FIFA dataset):`,
        ...rows.map((r) => `- ${r.club}: ${r.players} players (avg rating: ${f1(r.avgOverall)}), best: ${r.best.name} (${r.best.overall}, ${r.best.position})`),
      ].join('\n');
    },
  },
  {
    name: 'dataset_info',
    description: 'Describe the loaded data: rows per CSV file, competitions, seasons covered and match counts after de-duplication.',
    schema: {},
    run(kb) {
      const lines = ['Source files (rows read):', ...Object.entries(kb.data.rowCounts).map(([f, n]) => `- ${f}: ${n}`), ''];
      lines.push(`Matches after merging duplicates across files and dropping unplayed fixtures: ${kb.data.matches.length}`);
      for (const c of Object.values(COMPETITIONS)) {
        lines.push(`- ${c}: ${kb.findMatches({ competition: c }).length} matches, seasons ${compactYears(kb.seasons(c))}`);
      }
      lines.push(`Players: ${kb.data.players.length} (${kb.findPlayers({ nationality: 'Brazil' }).length} Brazilian)`);
      return lines.join('\n');
    },
  },
];

/** [2012, 2013, 2014, 2016] -> "2012-2014, 2016" */
export function compactYears(years: number[]): string {
  const out: string[] = [];
  for (let i = 0; i < years.length; i++) {
    let j = i;
    while (years[j + 1] === years[j] + 1) j++;
    out.push(i === j ? `${years[i]}` : `${years[i]}-${years[j]}`);
    i = j;
  }
  return out.join(', ') || 'none';
}

/** Run a tool by name with validated arguments; errors become readable text. */
export function callTool(kb: SoccerKB, name: string, args: unknown = {}): string {
  const tool = tools.find((t) => t.name === name);
  if (!tool) throw new Error(`Unknown tool: ${name}`);
  return tool.run(kb, z.object(tool.schema).parse(args));
}
