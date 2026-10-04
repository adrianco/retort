/**
 * The soccer knowledge base: answers questions about matches, teams,
 * competitions, statistics and players from the loaded datasets.
 *
 * Every answer is a plain data structure using display names; turning
 * answers into readable text is the job of format.ts.
 */
import {
  COMPETITION_NAMES,
  type CompetitionId,
  isLeague,
  normaliseStage,
  parseCompetition,
  relegationPlaces,
} from './competitions.js';
import { normaliseDateInput } from './dates.js';
import { derbyBetween } from './derbies.js';
import type { LoadedData } from './datasets.js';
import type { DatasetInfo, Match, Player } from './model.js';
import { TeamRegistry, identifyTeam } from './teams.js';
import { fold, percentage, round } from './text.js';

export class NotFound extends Error {}

export type Venue = 'home' | 'away' | 'any';

export interface MatchView {
  date: string;
  time?: string;
  competition: string;
  season: number;
  round?: number;
  stage?: string;
  homeTeam: string;
  awayTeam: string;
  homeGoals: number;
  awayGoals: number;
  arena?: string;
  derby?: string;
  stats?: Match['stats'];
}

export interface MatchFilter {
  team?: string;
  opponent?: string;
  venue?: Venue;
  competition?: string;
  season?: number;
  dateFrom?: string;
  dateTo?: string;
  stage?: string;
}

export interface TeamRecord {
  played: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDifference: number;
  points: number;
  winRate: number;
}

export interface StandingRow extends TeamRecord {
  position: number;
  team: string;
}

export type RankingMeasure = 'goals_scored' | 'goals_conceded' | 'points' | 'wins' | 'win_rate' | 'home_win_rate' | 'away_win_rate';

export interface PlayerFilter {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
}

const POSITION_GROUPS: { [group: string]: string[] } = {
  forward: ['ST', 'CF', 'LS', 'RS', 'LW', 'RW', 'LF', 'RF'],
  midfielder: ['CM', 'CDM', 'CAM', 'LM', 'RM', 'LCM', 'RCM', 'LDM', 'RDM', 'LAM', 'RAM'],
  defender: ['CB', 'LCB', 'RCB', 'LB', 'RB', 'LWB', 'RWB'],
  goalkeeper: ['GK'],
};

const POSITION_ALIASES: { [alias: string]: string } = {
  forward: 'forward', forwards: 'forward', attacker: 'forward', attackers: 'forward', striker: 'forward', strikers: 'forward', fw: 'forward', winger: 'forward', wingers: 'forward',
  midfielder: 'midfielder', midfielders: 'midfielder', midfield: 'midfielder', mf: 'midfielder',
  defender: 'defender', defenders: 'defender', defence: 'defender', defense: 'defender', df: 'defender',
  goalkeeper: 'goalkeeper', goalkeepers: 'goalkeeper', keeper: 'goalkeeper', goalie: 'goalkeeper',
};

const DEMONYMS: { [demonym: string]: string } = {
  brazilian: 'brazil', brasileiro: 'brazil', brasil: 'brazil', argentine: 'argentina', argentinian: 'argentina',
  uruguayan: 'uruguay', paraguayan: 'paraguay', chilean: 'chile', colombian: 'colombia', peruvian: 'peru',
  ecuadorian: 'ecuador', venezuelan: 'venezuela', bolivian: 'bolivia', mexican: 'mexico', portuguese: 'portugal',
  spanish: 'spain', french: 'france', german: 'germany', italian: 'italy', english: 'england', dutch: 'netherlands',
  belgian: 'belgium', croatian: 'croatia', american: 'united states', japanese: 'japan',
};

function emptyRecord(): TeamRecord {
  return { played: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0, goalDifference: 0, points: 0, winRate: 0 };
}

function addResult(record: TeamRecord, goalsFor: number, goalsAgainst: number): void {
  record.played++;
  record.goalsFor += goalsFor;
  record.goalsAgainst += goalsAgainst;
  if (goalsFor > goalsAgainst) record.wins++;
  else if (goalsFor === goalsAgainst) record.draws++;
  else record.losses++;
  record.goalDifference = record.goalsFor - record.goalsAgainst;
  record.points = record.wins * 3 + record.draws;
  record.winRate = percentage(record.wins, record.played);
}

function byMostRecent(a: Match, b: Match): number {
  return b.date.localeCompare(a.date) || (b.time ?? '').localeCompare(a.time ?? '');
}

function byOldest(a: Match, b: Match): number {
  return -byMostRecent(a, b);
}

export class SoccerKnowledge {
  readonly teams: TeamRegistry;
  private readonly matches: Match[];
  private readonly players: Player[];
  private readonly datasets: DatasetInfo[];
  private readonly brazilianClubKeys: Set<string>;

  constructor(data: LoadedData) {
    this.teams = data.teams;
    this.matches = data.matches;
    this.players = data.players;
    this.datasets = data.datasets;
    this.brazilianClubKeys = new Set(
      data.matches.filter((m) => m.competition === 'serie-a').flatMap((m) => [m.homeKey, m.awayKey]),
    );
  }

  // ---- Matches ----------------------------------------------------------------

  view(m: Match): MatchView {
    const derby = derbyBetween(m.homeKey, m.awayKey);
    const view: MatchView = {
      date: m.date,
      competition: COMPETITION_NAMES[m.competition],
      season: m.season,
      homeTeam: this.teams.name(m.homeKey),
      awayTeam: this.teams.name(m.awayKey),
      homeGoals: m.homeGoals,
      awayGoals: m.awayGoals,
    };
    if (m.time) view.time = m.time;
    if (m.round !== undefined) view.round = m.round;
    if (m.stage) view.stage = m.stage;
    if (m.arena) view.arena = m.arena;
    if (derby) view.derby = derby;
    if (m.stats && Object.values(m.stats).some((v) => v !== undefined)) view.stats = m.stats;
    return view;
  }

  team(query: string): string {
    const key = this.teams.resolve(query);
    if (!key) throw new NotFound(`I couldn't find a team called "${query}" in the match data.`);
    return key;
  }

  competition(query: string | undefined): CompetitionId | undefined {
    return query ? parseCompetition(query) : undefined;
  }

  filterMatches(filter: MatchFilter): Match[] {
    const team = filter.team ? this.team(filter.team) : undefined;
    const opponent = filter.opponent ? this.team(filter.opponent) : undefined;
    const competition = this.competition(filter.competition);
    const from = filter.dateFrom ? normaliseDateInput(filter.dateFrom) : undefined;
    const to = filter.dateTo ? normaliseDateInput(filter.dateTo) : undefined;
    const stage = filter.stage ? normaliseStage(filter.stage) : undefined;
    const venue = filter.venue ?? 'any';

    return this.matches
      .filter((m) => {
        if (competition && m.competition !== competition) return false;
        if (filter.season !== undefined && m.season !== filter.season) return false;
        if (from && m.date < from) return false;
        if (to && m.date > to) return false;
        if (stage && m.stage !== stage) return false;
        if (team) {
          const home = m.homeKey === team && (!opponent || m.awayKey === opponent);
          const away = m.awayKey === team && (!opponent || m.homeKey === opponent);
          if (venue === 'home' ? !home : venue === 'away' ? !away : !(home || away)) return false;
        } else if (opponent && m.homeKey !== opponent && m.awayKey !== opponent) {
          return false;
        }
        return true;
      })
      .sort(byMostRecent);
  }

  findMatches(filter: MatchFilter, limit = 20) {
    const found = this.filterMatches(filter);
    const result: {
      total: number;
      matches: MatchView[];
      headToHead?: { team: string; opponent: string; teamWins: number; opponentWins: number; draws: number };
    } = { total: found.length, matches: found.slice(0, limit).map((m) => this.view(m)) };
    if (filter.team && filter.opponent) {
      const record = this.recordOf(this.team(filter.team), found);
      result.headToHead = {
        team: this.teams.name(this.team(filter.team)),
        opponent: this.teams.name(this.team(filter.opponent)),
        teamWins: record.wins,
        opponentWins: record.losses,
        draws: record.draws,
      };
    }
    return result;
  }

  derbies(filter: { season?: number; competition?: string; team?: string }, limit = 100) {
    const found = this.filterMatches(filter).filter((m) => derbyBetween(m.homeKey, m.awayKey));
    return { total: found.length, matches: found.slice(0, limit).map((m) => this.view(m)) };
  }

  // ---- Teams --------------------------------------------------------------------

  private recordOf(team: string, matches: Match[]): TeamRecord {
    const record = emptyRecord();
    for (const m of matches) {
      if (m.homeKey === team) addResult(record, m.homeGoals, m.awayGoals);
      else if (m.awayKey === team) addResult(record, m.awayGoals, m.homeGoals);
    }
    return record;
  }

  private byCompetition(team: string, matches: Match[]) {
    const groups = new Map<CompetitionId, Match[]>();
    for (const m of matches) groups.set(m.competition, [...(groups.get(m.competition) ?? []), m]);
    return [...groups.entries()]
      .map(([id, ms]) => ({ competition: COMPETITION_NAMES[id], ...this.recordOf(team, ms) }))
      .sort((a, b) => b.played - a.played);
  }

  teamRecord(filter: MatchFilter & { team: string }) {
    const team = this.team(filter.team);
    const matches = this.filterMatches(filter);
    return {
      team: this.teams.name(team),
      filters: {
        season: filter.season,
        competition: filter.competition ? COMPETITION_NAMES[parseCompetition(filter.competition)] : undefined,
        venue: filter.venue ?? 'any',
        dateFrom: filter.dateFrom,
        dateTo: filter.dateTo,
      },
      ...this.recordOf(team, matches),
      byCompetition: this.byCompetition(team, matches),
    };
  }

  headToHead(teamQuery: string, opponentQuery: string, competition?: string, season?: number, limit = 10) {
    const team = this.team(teamQuery);
    const opponent = this.team(opponentQuery);
    const matches = this.filterMatches({ team: teamQuery, opponent: opponentQuery, competition, season });
    return {
      team: this.teams.name(team),
      opponent: this.teams.name(opponent),
      ...this.recordOf(team, matches),
      byCompetition: this.byCompetition(team, matches),
      matches: matches.slice(0, limit).map((m) => this.view(m)),
    };
  }

  teamCompetitions(teamQuery: string) {
    const team = this.team(teamQuery);
    const matches = this.filterMatches({ team: teamQuery });
    const groups = new Map<CompetitionId, Match[]>();
    for (const m of matches) groups.set(m.competition, [...(groups.get(m.competition) ?? []), m]);
    return {
      team: this.teams.name(team),
      competitions: [...groups.entries()]
        .map(([id, ms]) => {
          const seasons = [...new Set(ms.map((m) => m.season))].sort((a, b) => a - b);
          return { competition: COMPETITION_NAMES[id], matches: ms.length, seasons, ...this.recordOf(team, ms) };
        })
        .sort((a, b) => b.matches - a.matches),
    };
  }

  teamRankings(measure: RankingMeasure, scope: { competition?: string; season?: number; minMatches?: number }, limit = 10) {
    const matches = this.filterMatches({ competition: scope.competition, season: scope.season });
    const records = new Map<string, TeamRecord>();
    const recordFor = (key: string) => records.get(key) ?? records.set(key, emptyRecord()).get(key)!;
    for (const m of matches) {
      if (measure !== 'away_win_rate') addResult(recordFor(m.homeKey), m.homeGoals, m.awayGoals);
      if (measure !== 'home_win_rate') addResult(recordFor(m.awayKey), m.awayGoals, m.homeGoals);
    }
    const isRate = measure.endsWith('win_rate');
    const mostPlayed = Math.max(0, ...[...records.values()].map((r) => r.played));
    const minMatches = scope.minMatches ?? (isRate ? Math.max(1, Math.ceil(mostPlayed * 0.3)) : 1);
    const value = (r: TeamRecord): number => {
      switch (measure) {
        case 'goals_scored': return r.goalsFor;
        case 'goals_conceded': return r.goalsAgainst;
        case 'points': return r.points;
        case 'wins': return r.wins;
        default: return r.winRate;
      }
    };
    const ascending = measure === 'goals_conceded';
    const rankings = [...records.entries()]
      .filter(([, r]) => r.played >= minMatches)
      .map(([key, r]) => ({ team: this.teams.name(key), value: value(r), played: r.played, wins: r.wins, draws: r.draws, losses: r.losses, goalsFor: r.goalsFor, goalsAgainst: r.goalsAgainst }))
      .sort((a, b) => (ascending ? a.value - b.value : b.value - a.value) || b.played - a.played || a.team.localeCompare(b.team))
      .slice(0, limit)
      .map((r, i) => ({ rank: i + 1, ...r }));
    return {
      measure,
      competition: scope.competition ? COMPETITION_NAMES[parseCompetition(scope.competition)] : 'All competitions',
      season: scope.season,
      minimumMatches: minMatches,
      rankings,
    };
  }

  teamProfile(teamQuery: string, squadLimit = 11) {
    const team = this.team(teamQuery);
    const matches = this.filterMatches({ team: teamQuery });
    const squad = this.players.filter((p) => p.clubKey === team).sort((a, b) => b.overall - a.overall);
    return {
      team: this.teams.name(team),
      record: this.recordOf(team, matches),
      competitions: this.byCompetition(team, matches),
      recentMatches: matches.slice(0, 5).map((m) => this.view(m)),
      squad: {
        size: squad.length,
        averageOverall: squad.length ? round(squad.reduce((s, p) => s + p.overall, 0) / squad.length, 1) : null,
        players: squad.slice(0, squadLimit).map((p) => this.playerView(p)),
      },
    };
  }

  // ---- Competitions --------------------------------------------------------------

  standings(season: number, competitionQuery = 'Brasileirão') {
    const competition = parseCompetition(competitionQuery);
    if (!isLeague(competition)) {
      throw new NotFound(`${COMPETITION_NAMES[competition]} is a knockout competition; ask for its bracket instead of a table.`);
    }
    const matches = this.matches.filter((m) => m.competition === competition && m.season === season);
    if (matches.length === 0) throw new NotFound(`There are no ${COMPETITION_NAMES[competition]} matches for ${season} in the data.`);
    const records = new Map<string, TeamRecord>();
    const recordFor = (key: string) => records.get(key) ?? records.set(key, emptyRecord()).get(key)!;
    for (const m of matches) {
      addResult(recordFor(m.homeKey), m.homeGoals, m.awayGoals);
      addResult(recordFor(m.awayKey), m.awayGoals, m.homeGoals);
    }
    const table: StandingRow[] = [...records.entries()]
      .map(([key, r]) => ({ team: this.teams.name(key), ...r }))
      .sort((a, b) => b.points - a.points || b.wins - a.wins || b.goalDifference - a.goalDifference || b.goalsFor - a.goalsFor || a.team.localeCompare(b.team))
      .map((r, i) => ({ position: i + 1, ...r }));
    const places = relegationPlaces(competition, season);
    const relegated = places > 0 && table.length >= places * 2 ? table.slice(-places).map((r) => r.team) : [];
    return {
      competition: COMPETITION_NAMES[competition],
      season,
      matches: matches.length,
      champion: table[0]?.team ?? null,
      relegated,
      table,
    };
  }

  knockoutBracket(competitionQuery: string, season: number) {
    const competition = parseCompetition(competitionQuery);
    const matches = this.matches.filter((m) => m.competition === competition && m.season === season && m.stage).sort(byOldest);
    if (matches.length === 0) throw new NotFound(`There is no knockout information for ${COMPETITION_NAMES[competition]} ${season} in the data.`);
    const order = ['group stage', 'round of 16', 'quarterfinals', 'semifinals', 'final'];
    const stages = [...new Set(matches.map((m) => m.stage!))].sort((a, b) => {
      const ia = order.indexOf(a);
      const ib = order.indexOf(b);
      return (ia < 0 ? -1 : ia) - (ib < 0 ? -1 : ib);
    });
    return {
      competition: COMPETITION_NAMES[competition],
      season,
      stages: stages
        .filter((s) => s !== 'group stage')
        .map((stage) => ({ stage, matches: matches.filter((m) => m.stage === stage).map((m) => this.view(m)) })),
    };
  }

  // ---- Statistics ------------------------------------------------------------------

  matchStatistics(filter: { competition?: string; season?: number; team?: string }) {
    const matches = this.filterMatches(filter);
    const total = matches.length;
    const goals = matches.reduce((s, m) => s + m.homeGoals + m.awayGoals, 0);
    const homeWins = matches.filter((m) => m.homeGoals > m.awayGoals).length;
    const draws = matches.filter((m) => m.homeGoals === m.awayGoals).length;
    const awayWins = total - homeWins - draws;
    const withCorners = matches.filter((m) => m.stats?.homeCorners !== undefined && m.stats?.awayCorners !== undefined);
    const withShots = matches.filter((m) => m.stats?.homeShots !== undefined && m.stats?.awayShots !== undefined);
    return {
      competition: filter.competition ? COMPETITION_NAMES[parseCompetition(filter.competition)] : 'All competitions',
      season: filter.season,
      team: filter.team ? this.teams.name(this.team(filter.team)) : undefined,
      matches: total,
      goals,
      averageGoals: total ? round(goals / total, 2) : 0,
      homeWins,
      draws,
      awayWins,
      homeWinRate: percentage(homeWins, total),
      drawRate: percentage(draws, total),
      awayWinRate: percentage(awayWins, total),
      matchesWithCorners: withCorners.length,
      averageCorners: withCorners.length
        ? round(withCorners.reduce((s, m) => s + m.stats!.homeCorners! + m.stats!.awayCorners!, 0) / withCorners.length, 2)
        : null,
      matchesWithShots: withShots.length,
      averageShots: withShots.length
        ? round(withShots.reduce((s, m) => s + m.stats!.homeShots! + m.stats!.awayShots!, 0) / withShots.length, 2)
        : null,
    };
  }

  biggestWins(filter: { competition?: string; season?: number; team?: string }, limit = 10) {
    const matches = this.filterMatches(filter)
      .filter((m) => m.homeGoals !== m.awayGoals)
      .sort((a, b) => {
        const margin = Math.abs(b.homeGoals - b.awayGoals) - Math.abs(a.homeGoals - a.awayGoals);
        return margin || Math.max(b.homeGoals, b.awayGoals) - Math.max(a.homeGoals, a.awayGoals) || byOldest(a, b);
      });
    return {
      competition: filter.competition ? COMPETITION_NAMES[parseCompetition(filter.competition)] : 'All competitions',
      matches: matches.slice(0, limit).map((m) => ({ ...this.view(m), margin: Math.abs(m.homeGoals - m.awayGoals) })),
    };
  }

  compareSeasons(seasons: number[], competitionQuery = 'Brasileirão') {
    const competition = parseCompetition(competitionQuery);
    return {
      competition: COMPETITION_NAMES[competition],
      seasons: seasons.map((season) => {
        const stats = this.matchStatistics({ competition: competitionQuery, season });
        let champion: string | null = null;
        let topScoringTeam: { team: string; goals: number } | null = null;
        if (stats.matches > 0) {
          if (isLeague(competition)) champion = this.standings(season, competitionQuery).champion;
          const top = this.teamRankings('goals_scored', { competition: competitionQuery, season }, 1).rankings[0];
          if (top) topScoringTeam = { team: top.team, goals: top.value };
        }
        return {
          season,
          matches: stats.matches,
          goals: stats.goals,
          averageGoals: stats.averageGoals,
          homeWinRate: stats.homeWinRate,
          drawRate: stats.drawRate,
          awayWinRate: stats.awayWinRate,
          champion,
          topScoringTeam,
        };
      }),
    };
  }

  // ---- Players -----------------------------------------------------------------------

  playerView(p: Player) {
    return {
      name: p.name,
      age: p.age,
      nationality: p.nationality,
      overall: p.overall,
      potential: p.potential,
      club: p.club,
      position: p.position,
      jerseyNumber: p.jerseyNumber,
    };
  }

  private nationalityMatches(p: Player, wanted: string): boolean {
    const f = fold(wanted);
    const country = DEMONYMS[f] ?? f;
    return fold(p.nationality) === country;
  }

  private clubMatcher(query: string): (p: Player) => boolean {
    const key = this.clubKey(query);
    const f = fold(query);
    return key !== null ? (p) => p.clubKey === key : (p) => fold(p.club).includes(f);
  }

  /** The club a person means: by team identity, then by the teams in the match data, then by exact club name. */
  private clubKey(query: string): string | null {
    const identity = identifyTeam(query).key;
    if (this.players.some((p) => p.clubKey === identity)) return identity;
    const resolved = this.teams.resolve(query);
    if (resolved) return resolved;
    const f = fold(query);
    return this.players.find((p) => fold(p.club) === f)?.clubKey ?? null;
  }

  private positionMatcher(query: string): (p: Player) => boolean {
    const group = POSITION_ALIASES[fold(query)];
    const codes = group ? POSITION_GROUPS[group] : [query.trim().toUpperCase()];
    return (p) => codes.includes(p.position);
  }

  private nameMatches(p: Player, query: string): boolean {
    const name = fold(p.name);
    return fold(query).split(' ').every((token) => name.includes(token));
  }

  searchPlayers(filter: PlayerFilter, limit = 25) {
    const club = filter.club ? this.clubMatcher(filter.club) : undefined;
    const position = filter.position ? this.positionMatcher(filter.position) : undefined;
    const found = this.players
      .filter((p) =>
        (!filter.name || this.nameMatches(p, filter.name)) &&
        (!filter.nationality || this.nationalityMatches(p, filter.nationality)) &&
        (!club || club(p)) &&
        (!position || position(p)) &&
        (filter.minOverall === undefined || p.overall >= filter.minOverall),
      )
      .sort((a, b) => b.overall - a.overall || (b.potential ?? 0) - (a.potential ?? 0) || a.name.localeCompare(b.name));
    return {
      total: found.length,
      averageOverall: found.length ? round(found.reduce((s, p) => s + p.overall, 0) / found.length, 1) : null,
      players: found.slice(0, limit).map((p) => this.playerView(p)),
    };
  }

  playerProfile(query: string) {
    const f = fold(query);
    const exact = this.players.filter((p) => fold(p.name) === f);
    const partial = exact.length ? exact : this.players.filter((p) => this.nameMatches(p, query));
    if (partial.length === 0) {
      return { player: null, query, otherMatches: [] as string[], suggestions: this.similarlyNamed(query) };
    }
    const sorted = [...partial].sort((a, b) => b.overall - a.overall);
    const p = sorted[0];
    return {
      player: {
        ...this.playerView(p),
        height: p.height,
        weight: p.weight,
        preferredFoot: p.preferredFoot,
        value: p.value,
        wage: p.wage,
        contractValidUntil: p.contractValidUntil,
        attributes: p.attributes,
      },
      query,
      otherMatches: sorted.slice(1, 6).map((o) => `${o.name} (${o.club || 'no club'}, ${o.overall})`),
      suggestions: [] as Array<ReturnType<SoccerKnowledge['playerView']>>,
    };
  }

  /** Players sharing part of a name, best match first, for when nobody has the exact name. */
  private similarlyNamed(query: string, limit = 5) {
    const tokens = fold(query).split(' ').filter((t) => t.length >= 3);
    return this.players
      .map((p) => {
        const words = fold(p.name).split(' ');
        return { p, shared: tokens.filter((t) => words.some((w) => w.startsWith(t))).length };
      })
      .filter((c) => c.shared > 0)
      .sort((a, b) => b.shared - a.shared || b.p.overall - a.p.overall)
      .slice(0, limit)
      .map((c) => this.playerView(c.p));
  }

  playersByClub(filter: { nationality?: string; brazilianClubsOnly?: boolean }, limit = 30) {
    const brazilianOnly = filter.brazilianClubsOnly ?? true;
    const groups = new Map<string, Player[]>();
    for (const p of this.players) {
      if (!p.clubKey) continue;
      if (brazilianOnly && !this.brazilianClubKeys.has(p.clubKey)) continue;
      if (filter.nationality && !this.nationalityMatches(p, filter.nationality)) continue;
      groups.set(p.clubKey, [...(groups.get(p.clubKey) ?? []), p]);
    }
    const clubs = [...groups.entries()]
      .map(([key, ps]) => {
        const sorted = ps.sort((a, b) => b.overall - a.overall);
        return {
          club: this.teams.has(key) ? this.teams.name(key) : sorted[0].club,
          players: ps.length,
          averageOverall: round(ps.reduce((s, p) => s + p.overall, 0) / ps.length, 1),
          bestPlayer: `${sorted[0].name} (${sorted[0].overall})`,
        };
      })
      .sort((a, b) => b.players - a.players || b.averageOverall - a.averageOverall || a.club.localeCompare(b.club));
    return { nationality: filter.nationality, brazilianClubsOnly: brazilianOnly, totalClubs: clubs.length, clubs: clubs.slice(0, limit) };
  }

  // ---- Datasets ----------------------------------------------------------------------

  overview() {
    const seasons = this.matches.map((m) => m.season);
    return {
      datasets: this.datasets,
      totals: {
        matches: this.matches.length,
        teams: new Set(this.matches.flatMap((m) => [m.homeKey, m.awayKey])).size,
        players: this.players.length,
        firstSeason: seasons.length ? Math.min(...seasons) : null,
        lastSeason: seasons.length ? Math.max(...seasons) : null,
      },
      competitions: Object.values(COMPETITION_NAMES),
    };
  }
}
