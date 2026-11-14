/**
 * MCP server definition: registers the Brazilian soccer tools on an McpServer.
 * Every tool returns human-readable text that an LLM can quote directly.
 */
import { McpServer } from '@modelcontextprotocol/sdk/server/mcp.js';
import { z } from 'zod';
import { Match, Player, SOURCE_FILES } from './data.js';
import { COMPETITIONS } from './normalize.js';
import { MatchFilter, QueryError, SoccerDB, TeamRecord } from './queries.js';

const competitionArg = z
  .string()
  .optional()
  .describe('Competition: "Brasileirão" / "Serie A", "Serie B", "Serie C", "Copa do Brasil" or "Libertadores". Omit for all.');
const seasonArg = z.number().int().optional().describe('Season year, e.g. 2019');
const venueArg = z.enum(['home', 'away', 'either']).optional().describe('Restrict to home or away matches of `team`');
const limitArg = (def: number) => z.number().int().min(1).max(200).optional().describe(`Maximum rows to show (default ${def})`);
const sourceArg = z
  .enum(['brasileirao', 'copa_do_brasil', 'libertadores', 'br_football', 'historical'])
  .optional()
  .describe(
    'Query one specific CSV file instead of the de-duplicated view: brasileirao (Brasileirao_Matches), copa_do_brasil ' +
      '(Brazilian_Cup_Matches), libertadores (Libertadores_Matches), br_football (BR-Football-Dataset), historical (novo_campeonato_brasileiro)',
  );

const matchFilterShape = {
  competition: competitionArg,
  season: seasonArg,
  date_from: z.string().optional().describe('Earliest date (YYYY-MM-DD or DD/MM/YYYY)'),
  date_to: z.string().optional().describe('Latest date (YYYY-MM-DD or DD/MM/YYYY)'),
  source: sourceArg,
};

type FilterArgs = {
  team?: string; opponent?: string; venue?: 'home' | 'away' | 'either'; competition?: string; season?: number;
  date_from?: string; date_to?: string; stage?: string; round?: string; source?: MatchFilter['source'];
};
const toFilter = (a: FilterArgs): MatchFilter => ({
  team: a.team, opponent: a.opponent, venue: a.venue, competition: a.competition, season: a.season,
  dateFrom: a.date_from, dateTo: a.date_to, stage: a.stage, round: a.round, source: a.source,
});

// ------------------------------------------------------------- formatting

export function formatMatch(db: SoccerDB, m: Match): string {
  const score = m.homeGoals !== null && m.awayGoals !== null ? `${m.homeGoals}-${m.awayGoals}` : 'vs';
  const ctx = [`${m.competition}${m.season ? ' ' + m.season : ''}`];
  if (m.stage) ctx.push(m.stage);
  else if (m.round) ctx.push(`Round ${m.round}`);
  if (m.arena) ctx.push(m.arena);
  const unplayed = score === 'vs' ? ' [no result in data]' : '';
  return `${m.date ?? 'date unknown'}: ${db.teamName(m.homeKey)} ${score} ${db.teamName(m.awayKey)} (${ctx.join(', ')})${unplayed}`;
}

function formatRecord(r: TeamRecord): string[] {
  return [
    `- Matches: ${r.matches}`,
    `- Wins: ${r.wins}, Draws: ${r.draws}, Losses: ${r.losses}`,
    `- Goals For: ${r.goalsFor}, Goals Against: ${r.goalsAgainst} (GD ${r.goalDifference >= 0 ? '+' : ''}${r.goalDifference})`,
    `- Points: ${r.points}, Win rate: ${r.winRate.toFixed(1)}%`,
  ];
}
const shortRecord = (r: TeamRecord) =>
  `${r.matches} matches, ${r.wins}W ${r.draws}D ${r.losses}L, goals ${r.goalsFor}-${r.goalsAgainst}, win rate ${r.winRate.toFixed(1)}%`;

function formatPlayer(p: Player, i?: number): string {
  const prefix = i === undefined ? '-' : `${i + 1}.`;
  return `${prefix} ${p.name} - Overall: ${p.overall}, Position: ${p.position || 'n/a'}, Club: ${p.club || 'none'}, Nationality: ${p.nationality}, Age: ${p.age ?? 'n/a'} (id ${p.id})`;
}

function scope(a: FilterArgs): string {
  const parts: string[] = [];
  if (a.competition) parts.push(a.competition);
  if (a.season) parts.push(String(a.season));
  if (a.date_from || a.date_to) parts.push(`${a.date_from ?? '...'} to ${a.date_to ?? '...'}`);
  if (a.source) parts.push(`file ${SOURCE_FILES[a.source]}`);
  return parts.length ? parts.join(', ') : 'all competitions and seasons in the dataset';
}

function listMatches(db: SoccerDB, ms: Match[], limit: number): string[] {
  const lines = ms.slice(0, limit).map((m) => `- ${formatMatch(db, m)}`);
  if (ms.length > limit) lines.push(`- ... (${ms.length - limit} more matches in dataset)`);
  return lines;
}

// ------------------------------------------------------------------ server

export function createServer(db: SoccerDB): McpServer {
  const server = new McpServer({ name: 'brazilian-soccer-mcp', version: '1.0.0' });

  /** Register a tool whose handler returns text; QueryErrors become tool errors. */
  const tool = <S extends z.ZodRawShape>(
    name: string,
    description: string,
    shape: S,
    handler: (args: z.infer<z.ZodObject<S>>) => string,
  ) => {
    server.registerTool(name, { description, inputSchema: shape }, (async (args: unknown) => {
      try {
        return { content: [{ type: 'text' as const, text: handler(args as z.infer<z.ZodObject<S>>) }] };
      } catch (e) {
        if (e instanceof QueryError) return { content: [{ type: 'text' as const, text: e.message }], isError: true };
        throw e;
      }
    }) as never);
  };

  tool(
    'search_matches',
    'Find matches by team, opponent, venue, competition, season, date range, stage or round. Returns most recent first. ' +
      'Use stage="final" to find cup finals. With `team` and `opponent` a head-to-head tally is appended.',
    {
      team: z.string().optional().describe('Team name, any spelling (e.g. "Flamengo", "Palmeiras-SP", "Atlético Mineiro")'),
      opponent: z.string().optional().describe('Second team, for matches between two teams'),
      venue: venueArg,
      ...matchFilterShape,
      stage: z.string().optional().describe('Cup stage: "group stage", "round of 16", "quarterfinals", "semifinals", "final", or "Round N"'),
      round: z.string().optional().describe('Round number (league round or Copa do Brasil round)'),
      limit: limitArg(20),
    },
    (a) => {
      const ms = db.findMatches(toFilter(a));
      if (!ms.length) return `No matches found (${scope(a)}).`;
      const who = a.team ? (a.opponent ? `${a.team} vs ${a.opponent}` : a.team) : 'Matches';
      const lines = [`${who} - ${ms.length} match${ms.length === 1 ? '' : 'es'} found (${scope(a)}):`, ...listMatches(db, ms, a.limit ?? 20)];
      if (a.team && a.opponent) {
        const h = db.headToHead(a.team, a.opponent, toFilter({ ...a, team: undefined, opponent: undefined }));
        lines.push('', `Head-to-head in dataset: ${h.teamA} ${h.winsA} wins, ${h.teamB} ${h.winsB} wins, ${h.draws} draws`);
      }
      return lines.join('\n');
    },
  );

  tool(
    'head_to_head',
    'Compare two teams head-to-head: wins, draws, goals, home records and the most recent meetings.',
    { team_a: z.string(), team_b: z.string(), ...matchFilterShape, limit: limitArg(10) },
    (a) => {
      const h = db.headToHead(a.team_a, a.team_b, toFilter(a));
      if (!h.matches.length) return `No matches between ${h.teamA} and ${h.teamB} found (${scope(a)}).`;
      return [
        `${h.teamA} vs ${h.teamB}${h.rivalry ? ` (${h.rivalry})` : ''} - ${scope(a)}:`,
        `Head-to-head in dataset: ${h.teamA} ${h.winsA} wins, ${h.teamB} ${h.winsB} wins, ${h.draws} draws (${h.played} played)`,
        `Goals: ${h.teamA} ${h.goalsA}, ${h.teamB} ${h.goalsB}`,
        `${h.teamA} at home: ${shortRecord(h.homeRecordA)}`,
        `${h.teamB} at home: ${shortRecord(h.homeRecordB)}`,
        '',
        'Most recent meetings:',
        ...listMatches(db, h.matches, a.limit ?? 10),
      ].join('\n');
    },
  );

  tool(
    'team_stats',
    'Win/draw/loss record, goals and win rate for a team, optionally by season, competition and home/away venue. Includes a per-competition breakdown.',
    { team: z.string(), venue: venueArg, ...matchFilterShape },
    (a) => {
      const s = db.teamStats(a.team, toFilter(a));
      if (!s.overall.matches) return `No played matches for ${s.team} (${scope(a)}).`;
      const label = s.venue === 'either' ? 'record' : `${s.venue} record`;
      const lines = [`${s.team} ${label} (${scope(a)}):`, ...formatRecord(s.overall)];
      if (s.venue === 'either') {
        lines.push(`- Home: ${shortRecord(s.home)}`, `- Away: ${shortRecord(s.away)}`);
      }
      if (s.byCompetition.length > 1) {
        lines.push('', 'By competition:');
        for (const c of s.byCompetition) lines.push(`- ${c.competition}: ${shortRecord(c.record)}`);
      }
      return lines.join('\n');
    },
  );

  tool(
    'team_profile',
    'Overview of a team across all files: name variants, competitions and seasons played, overall record, rivals, and its players in the FIFA dataset.',
    { team: z.string() },
    (a) => {
      const p = db.teamProfile(a.team);
      const lines = [
        `${p.team}${p.state ? ` (${p.state})` : ''}`,
        `Names used in the datasets: ${p.aliases.join('; ')}`,
        `Matches in dataset: ${p.overall.matches} played, from ${p.firstMatch} to ${p.lastMatch}`,
        `Overall: ${shortRecord(p.overall)}`,
        '',
        'Competitions:',
        ...p.competitions.map(
          (c) => `- ${c.competition}: seasons ${c.seasons[0]}-${c.seasons.at(-1)} (${c.seasons.length} seasons) - ${shortRecord(c.record)}`,
        ),
      ];
      if (p.rivals.length) lines.push('', `Traditional rivals: ${p.rivals.map((r) => `${r.team} (${r.name})`).join(', ')}`);
      lines.push('');
      if (p.players.length) {
        const avg = p.players.reduce((s, x) => s + x.overall, 0) / p.players.length;
        lines.push(`FIFA dataset squad: ${p.players.length} players (avg rating ${avg.toFixed(1)}). Top rated:`);
        p.players.slice(0, 5).forEach((x, i) => lines.push(formatPlayer(x, i)));
      } else lines.push('FIFA dataset squad: no players listed for this club in fifa_data.csv.');
      return lines.join('\n');
    },
  );

  tool(
    'list_teams',
    'List teams present in the match data (optionally filtered by a name fragment or competition) with their match counts.',
    { search: z.string().optional(), competition: competitionArg, limit: limitArg(50) },
    (a) => {
      const teams = db.listTeams(a.search, a.competition);
      if (!teams.length) return 'No teams found.';
      const limit = a.limit ?? 50;
      return [
        `${teams.length} teams found:`,
        ...teams.slice(0, limit).map((t) => `- ${t.name}: ${t.matches} matches`),
        ...(teams.length > limit ? [`- ... (${teams.length - limit} more)`] : []),
      ].join('\n');
    },
  );

  tool(
    'standings',
    'League table for a season calculated from match results (3 points per win). Identifies the champion and the bottom four (relegation zone) for complete Série A seasons.',
    { season: z.number().int(), competition: competitionArg, limit: limitArg(30) },
    (a) => {
      const s = db.standings(a.season, a.competition);
      const lines = [`${s.season} ${s.competition} ${s.complete ? 'Final ' : ''}Standings (calculated from matches):`];
      const releg = new Set(s.relegated);
      for (const r of s.rows.slice(0, a.limit ?? 30)) {
        const tag = s.champion === r.team ? ' - Champion' : releg.has(r.team) ? ' - Relegation zone' : '';
        lines.push(
          `${r.position}. ${r.team} - ${r.points} pts (${r.wins}W, ${r.draws}D, ${r.losses}L), GF ${r.goalsFor}, GA ${r.goalsAgainst}, GD ${r.goalDifference >= 0 ? '+' : ''}${r.goalDifference}${tag}`,
        );
      }
      lines.push('');
      if (!s.isLeague) lines.push('Note: this is a knockout competition; use cup_summary for the bracket and winner.');
      else if (!s.complete) {
        lines.push(
          `Note: season data is incomplete or not a single round-robin table (${s.matchesPlayed} played, ${s.matchesUnplayed} without result), so no champion is declared.`,
        );
      } else if (s.relegated.length) {
        lines.push(`Champion: ${s.champion}. Bottom four (relegated under the current 4-down format): ${s.relegated.join(', ')}.`);
        lines.push('Note: computed purely from results; points deductions and pre-2006 relegation rules are not in the data.');
      } else lines.push(`Champion: ${s.champion}.`);
      return lines.join('\n');
    },
  );

  tool(
    'cup_summary',
    'Bracket for a Copa do Brasil or Copa Libertadores season: knockout ties by stage with aggregate scores, the final and the winner (when determinable from scores).',
    {
      competition: z.string().describe('"Copa do Brasil" or "Libertadores"'),
      season: z.number().int(),
      include_group_stage: z.boolean().optional().describe('Also list group-stage / unlabelled matches (default false)'),
    },
    (a) => {
      const c = db.cupSummary(a.competition, a.season);
      const lines = [`${c.season} ${c.competition} bracket:`];
      for (const st of c.stages) {
        lines.push('', `${st.stage} (${st.matches.length} matches):`);
        if (st.ties.length) {
          for (const t of st.ties) {
            const legs = t.matches
              .map((m) => `${m.date ?? '?'} ${db.teamName(m.homeKey)} ${m.homeGoals ?? '?'}-${m.awayGoals ?? '?'} ${db.teamName(m.awayKey)}`)
              .join('; ');
            const agg = t.aggregate ? `${t.aggregate[0]}-${t.aggregate[1]} on aggregate` : 'result not in data';
            const out = t.winner ? `${t.winner} advance` : t.aggregate ? 'level - decided by away goals/penalties (not in data)' : '';
            lines.push(`- ${t.teams[0]} vs ${t.teams[1]}: ${agg}${out ? ` - ${out}` : ''} [${legs}]`);
          }
        } else if (a.include_group_stage) lines.push(...st.matches.map((m) => `- ${formatMatch(db, m)}`));
        else lines.push('- (set include_group_stage=true to list these matches)');
      }
      lines.push('');
      if (c.champion) lines.push(`Champion: ${c.champion}`);
      else if (c.final) lines.push(`Final: ${c.final.teams.join(' vs ')} - winner cannot be determined from the scores in the data.`);
      else lines.push('The final for this season is not identifiable in the data.');
      return lines.join('\n');
    },
  );

  tool(
    'competition_stats',
    'Aggregate statistics: matches, average goals per match, home win / draw / away win rates and the highest-scoring match, for any competition/season/date filter.',
    { ...matchFilterShape },
    (a) => {
      const s = db.leagueStats(toFilter(a));
      if (!s.matches) return `No played matches found (${scope(a)}).`;
      return [
        `Statistics (${scope(a)}):`,
        `- Matches with results: ${s.matches}`,
        `- Total goals: ${s.totalGoals}`,
        `- Average goals per match: ${s.avgGoalsPerMatch.toFixed(2)} (home ${s.avgHomeGoals.toFixed(2)}, away ${s.avgAwayGoals.toFixed(2)})`,
        `- Home win rate: ${s.homeWinRate.toFixed(1)}% (${s.homeWins})`,
        `- Draw rate: ${s.drawRate.toFixed(1)}% (${s.draws})`,
        `- Away win rate: ${s.awayWinRate.toFixed(1)}% (${s.awayWins})`,
        ...(s.highestScoringMatch ? [`- Highest-scoring match: ${formatMatch(db, s.highestScoringMatch)}`] : []),
      ].join('\n');
    },
  );

  tool(
    'biggest_wins',
    'Largest margins of victory, optionally for one team, competition or season.',
    { team: z.string().optional(), venue: venueArg, ...matchFilterShape, limit: limitArg(10) },
    (a) => {
      const ms = db.biggestWins(toFilter(a), a.limit ?? 10);
      if (!ms.length) return `No decisive matches found (${scope(a)}).`;
      return [`Biggest victories${a.team ? ` involving ${a.team}` : ''} (${scope(a)}):`, ...ms.map((m, i) => `${i + 1}. ${formatMatch(db, m)}`)].join('\n');
    },
  );

  tool(
    'rank_teams',
    'Rank teams by a metric (points, win_rate, wins, goals_for, goals_against, goal_difference, points_per_match) over home, away or all matches. ' +
      'Answers "which team scored the most goals in Serie A 2023?" or "which team has the best away record?".',
    {
      metric: z.enum(['points', 'win_rate', 'wins', 'goals_for', 'goals_against', 'goal_difference', 'points_per_match']),
      venue: venueArg,
      ...matchFilterShape,
      min_matches: z.number().int().min(1).optional().describe('Minimum matches to qualify (default 10 for rate metrics, else 1)'),
      limit: limitArg(10),
    },
    (a) => {
      const rows = db.rankTeams(a.metric, toFilter(a), { minMatches: a.min_matches, limit: a.limit });
      if (!rows.length) return `No teams qualify (${scope(a)}).`;
      const v = a.venue && a.venue !== 'either' ? `${a.venue} matches` : 'all matches';
      return [
        `Teams ranked by ${a.metric} in ${v} (${scope(a)}):`,
        ...rows.map((r, i) => `${i + 1}. ${r.team} - ${a.metric}: ${a.metric === 'win_rate' ? r.value.toFixed(1) + '%' : r.value} (${shortRecord(r.record)})`),
      ].join('\n');
    },
  );

  tool(
    'compare_seasons',
    'Compare two seasons of a competition: goals per match, result distribution, champion, best attack and defence.',
    { season_a: z.number().int(), season_b: z.number().int(), competition: competitionArg },
    (a) => {
      const c = db.compareSeasons(a.season_a, a.season_b, a.competition);
      const one = (x: typeof c.a) => [
        `${x.season} ${x.competition}:`,
        `- Matches: ${x.stats.matches}, Goals: ${x.stats.totalGoals}, Average goals per match: ${x.stats.avgGoalsPerMatch.toFixed(2)}`,
        `- Home wins ${x.stats.homeWinRate.toFixed(1)}%, Draws ${x.stats.drawRate.toFixed(1)}%, Away wins ${x.stats.awayWinRate.toFixed(1)}%`,
        `- Champion: ${x.champion ?? 'not determinable from data'}`,
        ...(x.topAttack ? [`- Best attack: ${x.topAttack.team} (${x.topAttack.value} goals)`] : []),
        ...(x.bestDefence ? [`- Best defence: ${x.bestDefence.team} (${x.bestDefence.value} conceded)`] : []),
      ];
      const d = c.b.stats.avgGoalsPerMatch - c.a.stats.avgGoalsPerMatch;
      return [...one(c.a), '', ...one(c.b), '', `Change in goals per match: ${d >= 0 ? '+' : ''}${d.toFixed(2)}`].join('\n');
    },
  );

  tool(
    'find_derbies',
    'Matches between traditional rivals (Fla-Flu, Derby Paulista, Grenal, Clássico Mineiro, ...), optionally by team, season or competition.',
    { team: z.string().optional(), ...matchFilterShape, limit: limitArg(30) },
    (a) => {
      const ds = db.derbies(toFilter(a));
      if (!ds.length) return `No derbies found (${scope(a)}).`;
      const limit = a.limit ?? 30;
      return [
        `${ds.length} derby matches found (${scope(a)}):`,
        ...ds.slice(0, limit).map((d) => `- [${d.name}] ${formatMatch(db, d.match)}`),
        ...(ds.length > limit ? [`- ... (${ds.length - limit} more)`] : []),
      ].join('\n');
    },
  );

  tool(
    'extended_match_stats',
    'Average corners, shots and attacks per match from the extended statistics file (BR-Football-Dataset.csv, 2014-2023), for a team or for all matches in a competition/season.',
    { team: z.string().optional(), venue: venueArg, competition: competitionArg, season: seasonArg, date_from: matchFilterShape.date_from, date_to: matchFilterShape.date_to },
    (a) => {
      const s = db.extendedStats(toFilter(a));
      if (!s.matches) return `No extended statistics found (${scope(a)}).`;
      const [f, g] = s.team ? ['for', 'against'] : ['home', 'away'];
      const row = (label: string, v: typeof s.corners) =>
        v ? `- ${label}: ${v.for.toFixed(2)} ${f}, ${v.against.toFixed(2)} ${g} per match (${v.matches} matches with data)` : `- ${label}: no data`;
      return [
        `Extended match statistics${s.team ? ` for ${s.team}` : ''} (${scope(a)}; source BR-Football-Dataset.csv):`,
        `- Matches: ${s.matches}`,
        ...(s.record ? [`- Record: ${shortRecord(s.record)}`] : []),
        row('Corners', s.corners),
        row('Shots', s.shots),
        row('Attacks', s.attacks),
      ].join('\n');
    },
  );

  tool(
    'search_players',
    'Search the FIFA player database by name, nationality, club and position (a code like "ST" or a group: goalkeeper, defender, midfielder, forward). Sorted by overall rating by default.',
    {
      name: z.string().optional(),
      nationality: z.string().optional().describe('e.g. "Brazil"'),
      club: z.string().optional().describe('Club name or fragment, e.g. "Santos", "Grêmio"'),
      position: z.string().optional(),
      min_overall: z.number().int().optional(),
      max_age: z.number().int().optional(),
      sort_by: z.enum(['overall', 'potential', 'age', 'name']).optional(),
      limit: limitArg(20),
    },
    (a) => {
      const r = db.searchPlayers({
        name: a.name, nationality: a.nationality, club: a.club, position: a.position,
        minOverall: a.min_overall, maxAge: a.max_age, sortBy: a.sort_by, limit: a.limit,
      });
      if (!r.total) {
        const hint = a.club
          ? ' Note: fifa_data.csv does not include every Brazilian club (e.g. Flamengo, Palmeiras, Corinthians and São Paulo are absent); use club_player_summary to see which clubs are covered.'
          : '';
        return `No players found matching the criteria.${hint}`;
      }
      const lines = [`${r.total} player${r.total === 1 ? '' : 's'} found${r.partialNameMatch ? ' (no exact name match; showing partial matches)' : ''}:`];
      r.players.forEach((p, i) => lines.push(formatPlayer(p, i)));
      if (r.total > r.players.length) lines.push(`... (${r.total - r.players.length} more players in dataset)`);
      return lines.join('\n');
    },
  );

  tool(
    'player_details',
    'Full profile of one player (ratings, physical attributes, skills). Identify by FIFA id or by name (best-rated match is used).',
    { id: z.number().int().optional(), name: z.string().optional() },
    (a) => {
      let p = a.id !== undefined ? db.getPlayer(a.id) : undefined;
      let others = 0;
      if (!p && a.name) {
        const r = db.searchPlayers({ name: a.name, limit: 1 });
        p = r.players[0];
        others = r.total - 1;
      }
      if (!p) return 'Player not found. Provide a FIFA id or a name (try search_players).';
      const top = Object.entries(p.attributes).sort((x, y) => y[1] - x[1]).slice(0, 8);
      const lines = [
        `${p.name} (id ${p.id})`,
        `- Age: ${p.age ?? 'n/a'}, Nationality: ${p.nationality}`,
        `- Club: ${p.club || 'none'}, Position: ${p.position || 'n/a'}, Jersey: ${p.jersey ?? 'n/a'}`,
        `- Overall: ${p.overall}, Potential: ${p.potential ?? 'n/a'}`,
        `- Height: ${p.height || 'n/a'}, Weight: ${p.weight || 'n/a'}, Preferred foot: ${p.preferredFoot || 'n/a'}`,
        `- Value: ${p.value || 'n/a'}, Wage: ${p.wage || 'n/a'}`,
        `- Best attributes: ${top.map(([k, v]) => `${k} ${v}`).join(', ')}`,
        `- All attributes: ${Object.entries(p.attributes).map(([k, v]) => `${k} ${v}`).join(', ')}`,
      ];
      if (p.clubKey) {
        try {
          const key = db.resolveTeam(p.club);
          if (db.playersOfTeam(key).length) {
            lines.push(`- Club in match data: ${db.teamName(key)} - ${shortRecord(db.teamStats(p.club).overall)}`);
          }
        } catch {
          /* club has no match data */
        }
      }
      if (others > 0) lines.push('', `(${others} other players also match "${a.name}"; use search_players to list them.)`);
      return lines.join('\n');
    },
  );

  tool(
    'club_player_summary',
    'Player counts and average FIFA rating per club, optionally for one nationality and/or only Brazilian clubs. Answers "Brazilian players at Brazilian clubs".',
    {
      nationality: z.string().optional().describe('e.g. "Brazil"'),
      brazilian_clubs_only: z.boolean().optional(),
      limit: limitArg(25),
    },
    (a) => {
      const rows = db.clubSummary({ nationality: a.nationality, brazilianClubsOnly: a.brazilian_clubs_only, limit: a.limit });
      if (!rows.length) return 'No clubs found.';
      const what = `${a.nationality ? `${a.nationality} players` : 'Players'} at ${a.brazilian_clubs_only ? 'Brazilian clubs' : 'clubs'}`;
      return [
        `${what} (FIFA dataset):`,
        ...rows.map((r) => `- ${r.club}: ${r.players} players (avg rating: ${r.avgOverall.toFixed(1)}; best: ${r.best.name} ${r.best.overall})`),
      ].join('\n');
    },
  );

  tool('dataset_info', 'Describe the loaded data: files, row counts, competitions and the seasons covered.', {}, () => {
    const lines = ['Brazilian soccer dataset (Kaggle CSV files):'];
    for (const [file, n] of Object.entries(db.ds.counts)) lines.push(`- ${file}: ${n} rows`);
    lines.push('', 'Competitions (de-duplicated across files):');
    for (const c of COMPETITIONS) {
      const s = db.seasons(c);
      const n = db.findMatches({ competition: c }).length;
      lines.push(`- ${c}: ${n} matches, seasons ${s[0]}-${s.at(-1)}`);
    }
    lines.push(
      '',
      `Teams: ${db.ds.teamNames.size}. Players: ${db.players.length} (${db.searchPlayers({ nationality: 'Brazil', limit: 1 }).total} Brazilian).`,
      'Overlapping files are de-duplicated: Série A uses novo_campeonato_brasileiro (2003-2011), Brasileirao_Matches (2012-2022) and BR-Football-Dataset (2023); pass `source` to query one file directly.',
    );
    return lines.join('\n');
  });

  return server;
}
