import { competitions, dateOnly, loadData, normalize, sources, teamName } from './data.js';
import type { Competition, Match, MatchSource, Player } from './data.js';

export interface MatchFilter {
  team?: string;
  opponent?: string;
  venue?: 'home' | 'away' | 'either';
  competition?: string;
  season?: number;
  seasons?: number[];
  from?: string;
  to?: string;
  round?: number;
  stage?: string;
  derby?: boolean;
  source?: MatchSource;
  status?: 'played' | 'unscored';
}

export interface Page {
  limit?: number;
  offset?: number;
}

export interface PlayerFilter {
  name?: string;
  nationality?: string;
  club?: string;
  brazilianClub?: boolean;
  position?: string;
  minOverall?: number;
}

const competitionGroups: Record<Competition, string[]> = {
  league: ['Brasileirão', 'Série A', 'Campeonato Brasileiro', 'Brazilian Serie A'],
  serieB: ['Série B', 'Brasileirão B'],
  serieC: ['Série C', 'Brasileirão C'],
  cup: ['Brazilian Cup', 'Copa Brasil'],
  libertadores: ['Libertadores', 'CONMEBOL Libertadores'],
};

export function competitionKey(value: string): Competition {
  const key = normalize(value);
  for (const [id, aliases] of Object.entries(competitionGroups) as [Competition, string[]][]) {
    if ([id, competitions[id], ...aliases].some(alias => normalize(alias) === key)) return id;
  }
  throw new Error(`Unknown competition: ${value}`);
}

const stages = [
  ['final', 'finals', 'finais'],
  ['semifinals', 'semi final', 'semi finals', 'semifinal'],
  ['quarterfinals', 'quarter final', 'quarter finals', 'quarterfinal', 'quartas de final'],
  ['round of 16', 'oitavas de final'],
  ['group stage', 'fase de grupos'],
];

const rivalries = [
  ['Flamengo', 'Fluminense', 'Vasco da Gama', 'Botafogo-RJ'],
  ['Palmeiras', 'Corinthians', 'São Paulo', 'Santos'],
  ['Grêmio', 'Internacional'],
  ['Atlético Mineiro', 'Cruzeiro'],
  ['Bahia', 'Vitória'],
  ['Ceará', 'Fortaleza'],
  ['Athletico Paranaense', 'Coritiba', 'Paraná'],
  ['Sport Recife', 'Santa Cruz', 'Náutico'],
  ['Goiás', 'Vila Nova'],
  ['Paysandu', 'Remo'],
];

const positions: Record<string, string[]> = {
  forward: ['ST', 'CF', 'LF', 'RF', 'LS', 'RS', 'LW', 'RW'],
  midfielder: ['CAM', 'CM', 'CDM', 'LM', 'RM', 'LAM', 'RAM', 'LCM', 'RCM', 'LDM', 'RDM'],
  defender: ['CB', 'LB', 'RB', 'LCB', 'RCB', 'LWB', 'RWB'],
  goalkeeper: ['GK'],
};

const teamKey = (value: string) => normalize(teamName(value));
const newestFirst = (a: Match, b: Match) =>
  (b.date ?? '').localeCompare(a.date ?? '') || (b.time ?? '').localeCompare(a.time ?? '');
const isScored = (match: Match): match is Match & { homeGoals: number; awayGoals: number } =>
  match.homeGoals !== null && match.awayGoals !== null;
const ratio = (numerator: number, denominator: number) =>
  denominator === 0 ? null : Number((numerator / denominator).toFixed(4));

function page<T>(items: T[], { limit = 20, offset = 0 }: Page) {
  return {
    total: items.length,
    offset,
    nextOffset: offset + limit < items.length ? offset + limit : null,
    items: items.slice(offset, offset + limit),
  };
}

function newRecord() {
  return { fixtures: 0, played: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0 };
}

function recordResult(record: ReturnType<typeof newRecord>, scored: number | null, conceded: number | null) {
  record.fixtures++;
  if (scored === null || conceded === null) return;
  record.played++;
  record.goalsFor += scored;
  record.goalsAgainst += conceded;
  if (scored > conceded) record.wins++;
  else if (scored < conceded) record.losses++;
  else record.draws++;
}

function summarize(record: ReturnType<typeof newRecord>) {
  return {
    ...record,
    goalDifference: record.goalsFor - record.goalsAgainst,
    points: record.wins * 3 + record.draws,
    winRate: ratio(record.wins, record.played),
    goalsPerMatch: ratio(record.goalsFor, record.played),
  };
}

type TeamRecord = ReturnType<typeof newRecord>;
type Records = { team: string; overall: TeamRecord; home: TeamRecord; away: TeamRecord };

function records(matches: Match[]): Records[] {
  const byTeam = new Map<string, Records>();
  for (const match of matches) {
    for (const venue of ['home', 'away'] as const) {
      const team = match[venue];
      const key = teamKey(team);
      const totals = byTeam.get(key) ?? { team, overall: newRecord(), home: newRecord(), away: newRecord() };
      const goals = venue === 'home' ? match.homeGoals : match.awayGoals;
      const conceded = venue === 'home' ? match.awayGoals : match.homeGoals;
      recordResult(totals.overall, goals, conceded);
      recordResult(totals[venue], goals, conceded);
      byTeam.set(key, totals);
    }
  }
  return [...byTeam.values()];
}

export class SoccerGraph {
  private readonly data;
  private readonly brazilianClubs = new Set<string>();

  constructor(directory?: string) {
    this.data = loadData(directory);
    for (const match of this.data.matches) {
      if (match.competition === 'libertadores') continue;
      this.brazilianClubs.add(teamKey(match.home));
      this.brazilianClubs.add(teamKey(match.away));
    }
  }

  coverage() {
    return {
      sources: Object.entries(sources).map(([key, file]) => ({
        key, file, rows: key === 'players' ? this.data.players.length : this.data.raw[key as MatchSource].length,
      })),
      competitions: Object.entries(competitions).map(([key, name]) => ({
        key, name,
        seasons: [...new Set(this.data.matches.filter(m => m.competition === key)
          .map(m => m.season).filter(season => season !== null))].sort((a, b) => a - b),
      })),
    };
  }

  private select(filter: MatchFilter): Match[] {
    const { team, opponent, venue = 'either', competition, season, seasons, from, to, round, stage, derby, source, status } = filter;
    const target = team && teamKey(team);
    const rival = opponent && teamKey(opponent);
    if ((opponent || venue !== 'either') && !target) throw new Error('Specify a team with opponent or venue filters.');
    const category = competition && competitionKey(competition);
    const start = from && dateOnly(from);
    const end = to && dateOnly(to);
    if ((from && !start) || (to && !end)) throw new Error('Use a valid ISO or DD/MM/YYYY date.');
    if (start && end && start > end) throw new Error('The start date must precede or equal the end date.');
    const stageKey = stage && (stages.find(group => group.includes(normalize(stage)))?.[0] ?? normalize(stage));

    return (source ? this.data.raw[source] : this.data.matches).filter(match => {
      if (category && match.competition !== category) return false;
      if (season !== undefined && match.season !== season) return false;
      if (seasons && (match.season === null || !seasons.includes(match.season))) return false;
      if (round !== undefined && match.round !== round) return false;
      if (stageKey === 'knockout') {
        if (!match.stage || match.stage === 'group stage') return false;
      } else if (stageKey && normalize(match.stage ?? '') !== stageKey) return false;
      if (status && (status === 'played') !== isScored(match)) return false;
      if (start && (!match.date || match.date < start)) return false;
      if (end && (!match.date || match.date > end)) return false;
      if (!target && !derby) return true;
      const home = teamKey(match.home);
      const away = teamKey(match.away);
      if (derby && !rivalries.some(group => group.some(t => teamKey(t) === home) &&
        group.some(t => teamKey(t) === away))) return false;
      if (!target) return true;
      return (venue !== 'away' && home === target && (!rival || away === rival)) ||
        (venue !== 'home' && away === target && (!rival || home === rival));
    });
  }

  matches(filter: MatchFilter & Page & { order?: 'newest' | 'oldest' }) {
    const matches = this.select(filter).sort(newestFirst);
    if (filter.order === 'oldest') matches.reverse();
    return page(matches, filter);
  }

  teamStats(filter: MatchFilter & { team: string }) {
    const matches = this.select(filter);
    const target = teamKey(filter.team);
    const summarizeTeam = (subset: Match[]) => {
      const totals = records(subset).find(row => teamKey(row.team) === target);
      return {
        overall: summarize(totals?.overall ?? newRecord()),
        home: summarize(totals?.home ?? newRecord()),
        away: summarize(totals?.away ?? newRecord()),
      };
    };
    const byCompetition = [...new Set(matches.map(match => match.competition))];
    const bySeason = [...new Set(matches.map(match => match.season))]
      .sort((a, b) => (a ?? 0) - (b ?? 0));
    return {
      team: matches.length ? (teamKey(matches[0].home) === target ? matches[0].home : matches[0].away)
        : teamName(filter.team),
      ...summarizeTeam(matches),
      competitions: byCompetition.map(competition => ({
        competition, name: competitions[competition], ...summarizeTeam(matches.filter(m => m.competition === competition)),
      })),
      seasons: bySeason.map(season => ({ season, ...summarizeTeam(matches.filter(m => m.season === season)) })),
    };
  }

  headToHead(filter: MatchFilter & Page & { team: string; opponent: string }) {
    if (teamKey(filter.team) === teamKey(filter.opponent)) throw new Error('Choose two distinct teams.');
    const matches = this.select(filter);
    const teams = records(matches).map(row => ({ team: row.team, ...summarize(row.overall) }));
    return { teams, ...page(matches.sort(newestFirst), filter) };
  }

  private findPlayers(filter: PlayerFilter): Player[] {
    const name = filter.name && normalize(filter.name);
    const nationality = filter.nationality && normalize(filter.nationality);
    const club = filter.club && teamKey(filter.club);
    const partialClub = filter.club && !this.brazilianClubs.has(teamKey(filter.club)) && normalize(filter.club);
    const position = filter.position && normalize(filter.position);
    const accepted = position && (positions[position.replace(/s$/, '')] ?? [position.toUpperCase()]);
    return this.data.players.filter(player =>
      (!name || normalize(player.name).includes(name)) &&
      (!nationality || normalize(player.nationality) === (['brasil', 'brazilian', 'brasileiro'].includes(nationality) ? 'brazil' : nationality)) &&
      (!club || teamKey(player.club) === club || (partialClub && normalize(player.club).includes(partialClub))) &&
      (filter.brazilianClub === undefined || this.brazilianClubs.has(teamKey(player.club)) === filter.brazilianClub) &&
      (!accepted || accepted.includes(player.position)) &&
      (filter.minOverall === undefined || player.overall >= filter.minOverall),
    ).sort((a, b) => b.overall - a.overall || b.potential - a.potential || a.name.localeCompare(b.name));
  }

  players(filter: PlayerFilter & Page) {
    const players = this.findPlayers(filter);
    const clubs = new Map<string, { club: string; players: number; ratings: number }>();
    for (const player of players) {
      const key = teamKey(player.club);
      if (!key) continue;
      const club = clubs.get(key) ?? { club: teamName(player.club), players: 0, ratings: 0 };
      club.players++;
      club.ratings += player.overall;
      clubs.set(key, club);
    }
    const byClub = [...clubs.values()].map(({ club, players, ratings }) =>
      ({ club, players, averageOverall: ratio(ratings, players) }))
      .sort((a, b) => b.players - a.players || a.club.localeCompare(b.club));
    return { ...page(players, filter), byClub: page(byClub, filter),
      note: 'Club, age and ratings are from the supplied FIFA snapshot.' };
  }

  clubProfile(filter: MatchFilter & Page & { team: string; nationality?: string; position?: string }) {
    const roster = this.findPlayers({ club: filter.team, nationality: filter.nationality, position: filter.position });
    return {
      ...this.teamStats(filter),
      recentMatches: this.matches(filter),
      fifaRoster: {
        ...page(roster, filter),
        averageOverall: ratio(roster.reduce((sum, player) => sum + player.overall, 0), roster.length),
        note: 'Roster entries reflect the FIFA snapshot and do not imply participation in the listed matches.',
      },
    };
  }

  standings(competition: string, season: number) {
    const category = competitionKey(competition);
    if (category !== 'league' && category !== 'serieB') {
      throw new Error('A season-wide league table is available for Série A and B. Use competition_results for staged competitions.');
    }
    const matches = this.select({ competition, season });
    const table = records(matches).map(row => ({ team: row.team, ...summarize(row.overall) }))
      .sort((a, b) => b.points - a.points || b.wins - a.wins || b.goalDifference - a.goalDifference ||
        b.goalsFor - a.goalsFor || a.team.localeCompare(b.team));
    const scoredMatches = matches.filter(isScored).length;
    const expectedMatches = table.length * (table.length - 1);
    const completeDoubleRoundRobin = expectedMatches > 0 && scoredMatches === expectedMatches &&
      new Set(matches.filter(isScored).map(m => `${teamKey(m.home)}|${teamKey(m.away)}`)).size === expectedMatches;
    return {
      competition: competitions[category], season, scoredMatches, expectedMatches, completeDoubleRoundRobin,
      calculatedWinner: completeDoubleRoundRobin ? table[0].team : null,
      relegationPlaces: completeDoubleRoundRobin && category === 'league' && season >= 2006 && table.length === 20
        ? table.slice(-4).map(row => row.team) : null,
      standings: table.map((row, index) => ({ rank: index + 1, ...row })),
      note: 'Calculated from available results using 3/1/0 points, wins, goal difference, then goals for. Unresolved ties use team name. Administrative adjustments are unavailable.',
    };
  }

  competitionResults(filter: MatchFilter & Page & { competition: string; season: number }) {
    const matches = this.select(filter);
    const stageOrder = ['group stage', 'round of 16', 'quarterfinals', 'semifinals', 'final'];
    return {
      competition: competitions[competitionKey(filter.competition)],
      season: filter.season,
      stages: stageOrder.map(stage => ({ stage, fixtures: matches.filter(m => m.stage === stage).length }))
        .filter(stage => stage.fixtures > 0),
      ...page(matches.sort((a, b) => -newestFirst(a, b)), filter),
      topScorersAvailable: false,
      note: 'The match files contain team scores. Individual scorers and penalty shootout details are unavailable.',
    };
  }

  statistics(filter: MatchFilter & Page & {
    rankBy?: 'wins' | 'winRate' | 'goalsFor' | 'points';
    rankVenue?: 'home' | 'away' | 'overall';
    minMatches?: number;
  }) {
    const matches = this.select(filter);
    const scored = matches.filter(isScored);
    const goals = scored.reduce((sum, m) => sum + m.homeGoals + m.awayGoals, 0);
    const homeWins = scored.filter(match => match.homeGoals > match.awayGoals).length;
    const awayWins = scored.filter(match => match.homeGoals < match.awayGoals).length;
    const draws = scored.length - homeWins - awayWins;
    const bySeason = new Map<number | null, typeof scored>();
    for (const match of scored) {
      const season = bySeason.get(match.season) ?? [];
      season.push(match);
      bySeason.set(match.season, season);
    }
    const { rankBy = 'winRate', rankVenue = 'overall', minMatches = 1 } = filter;
    const rankings = records(matches).map(row => ({ team: row.team, ...summarize(row[rankVenue]) }))
      .filter(row => row.played >= minMatches)
      .sort((a, b) => (b[rankBy] ?? 0) - (a[rankBy] ?? 0) || b.played - a.played || a.team.localeCompare(b.team));
    const biggestWins = scored.filter(match => match.homeGoals !== match.awayGoals)
      .map(match => ({
        ...match,
        winner: match.homeGoals > match.awayGoals ? match.home : match.away,
        margin: Math.abs(match.homeGoals - match.awayGoals),
      }))
      .sort((a, b) => b.margin - a.margin || newestFirst(a, b));
    return {
      fixtures: matches.length, played: scored.length, goals, homeWins, awayWins, draws,
      averageGoals: ratio(goals, scored.length), homeWinRate: ratio(homeWins, scored.length),
      awayWinRate: ratio(awayWins, scored.length),
      seasons: [...bySeason].sort(([a], [b]) => (a ?? 0) - (b ?? 0)).map(([season, results]) => {
        const seasonGoals = results.reduce((sum, m) => sum + m.homeGoals + m.awayGoals, 0);
        return { season, played: results.length, goals: seasonGoals, averageGoals: ratio(seasonGoals, results.length) };
      }),
      rankVenue, rankBy, rankings: page(rankings, filter), biggestWins: page(biggestWins, filter),
    };
  }
}
