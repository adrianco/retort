/**
 * Query layer over the loaded dataset: match search, team records, standings,
 * cup brackets, league statistics and FIFA player search.
 */
import { Dataset, Match, Player, Source } from './data.js';
import { clean, Competition, COMPETITIONS, parseCompetition, parseDate, teamKey } from './normalize.js';

export class QueryError extends Error {}

export type Venue = 'home' | 'away' | 'either';

export interface MatchFilter {
  team?: string;
  opponent?: string;
  venue?: Venue;
  competition?: string;
  season?: number;
  dateFrom?: string;
  dateTo?: string;
  /** e.g. "final", "semifinals", "group stage", "Round 3" */
  stage?: string;
  round?: string | number;
  /** Restrict to one source file (disables de-duplication). */
  source?: Source;
  /** Include rows that duplicate a match already present in a preferred file. */
  includeDuplicates?: boolean;
  /** Only matches with a known score. */
  playedOnly?: boolean;
}

export interface TeamRecord {
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDifference: number;
  points: number;
  /** percentage, one decimal */
  winRate: number;
}

export interface StandingRow extends TeamRecord {
  position: number;
  team: string;
  teamKey: string;
}

export interface Tie {
  teams: [string, string];
  matches: Match[];
  aggregate: [number, number] | null;
  winner: string | null;
}

export type RankMetric = 'points' | 'win_rate' | 'wins' | 'goals_for' | 'goals_against' | 'goal_difference' | 'points_per_match';

export interface PlayerFilter {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  maxAge?: number;
  sortBy?: 'overall' | 'potential' | 'age' | 'name';
  limit?: number;
}

const POSITION_GROUPS: Record<string, string[]> = {
  goalkeeper: ['GK'],
  defender: ['CB', 'LB', 'RB', 'LCB', 'RCB', 'LWB', 'RWB'],
  midfielder: ['CM', 'CAM', 'CDM', 'LM', 'RM', 'LCM', 'RCM', 'LAM', 'RAM', 'LDM', 'RDM'],
  forward: ['ST', 'CF', 'LF', 'RF', 'LW', 'RW', 'LS', 'RS'],
};
const POSITION_SYNONYMS: Record<string, string> = {
  goalkeepers: 'goalkeeper', keeper: 'goalkeeper', goleiro: 'goalkeeper',
  defenders: 'defender', defence: 'defender', defense: 'defender', zagueiro: 'defender',
  midfielders: 'midfielder', midfield: 'midfielder', meia: 'midfielder',
  forwards: 'forward', attacker: 'forward', attackers: 'forward', striker: 'forward',
  strikers: 'forward', atacante: 'forward',
};

/** Traditional rivalries (clássicos), as pairs of team keys. */
export const RIVALRIES: [string, string, string][] = [
  ['flamengo', 'fluminense', 'Fla-Flu'],
  ['flamengo', 'vasco', 'Clássico dos Milhões'],
  ['flamengo', 'botafogo', 'Clássico da Rivalidade'],
  ['fluminense', 'vasco', 'Clássico dos Gigantes'],
  ['fluminense', 'botafogo', 'Clássico Vovô'],
  ['botafogo', 'vasco', 'Clássico da Amizade'],
  ['corinthians', 'palmeiras', 'Derby Paulista'],
  ['corinthians', 'sao paulo', 'Majestoso'],
  ['palmeiras', 'sao paulo', 'Choque-Rei'],
  ['corinthians', 'santos', 'Clássico Alvinegro'],
  ['palmeiras', 'santos', 'Clássico da Saudade'],
  ['santos', 'sao paulo', 'San-São'],
  ['gremio', 'internacional', 'Grenal'],
  ['atletico mg', 'cruzeiro', 'Clássico Mineiro'],
  ['bahia', 'vitoria', 'Ba-Vi'],
  ['sport', 'nautico', 'Clássico dos Clássicos'],
  ['sport', 'santa cruz', 'Clássico das Multidões'],
  ['nautico', 'santa cruz', 'Clássico das Emoções'],
  ['ceara', 'fortaleza', 'Clássico-Rei'],
  ['athletico pr', 'coritiba', 'Atletiba'],
  ['goias', 'vila nova', 'Derby do Cerrado'],
  ['goias', 'atletico go', 'Clássico Goiano'],
  ['avai', 'figueirense', 'Clássico de Florianópolis'],
  ['remo', 'paysandu', 'Re-Pa'],
];

const LIB_STAGES = ['group stage', 'round of 16', 'quarterfinals', 'semifinals', 'final'];

const round1 = (n: number) => Math.round(n * 10) / 10;
const round2 = (n: number) => Math.round(n * 100) / 100;
const played = (m: Match) => m.homeGoals !== null && m.awayGoals !== null;

export class SoccerDB {
  readonly matches: Match[];
  readonly players: Player[];
  private readonly domesticKeys = new Set<string>();

  constructor(readonly ds: Dataset) {
    this.matches = ds.matches;
    this.players = ds.players;
    for (const m of ds.matches) {
      if (m.competition !== 'Copa Libertadores') {
        this.domesticKeys.add(m.homeKey);
        this.domesticKeys.add(m.awayKey);
      }
    }
  }

  // ---------------------------------------------------------------- teams

  teamName(key: string): string {
    return this.ds.teamNames.get(key) ?? key;
  }

  /** Resolve a free-text team name to a team key; throws QueryError if unknown or ambiguous. */
  resolveTeam(query: string): string {
    const k = teamKey(query);
    if (this.ds.teamNames.has(k)) return k;
    const c = clean(query);
    if (!c) throw new QueryError('Team name is empty.');
    const hits = [...this.ds.teamNames.keys()].filter(
      (key) => ` ${key} `.includes(` ${k} `) || ` ${key} `.includes(` ${c} `),
    );
    if (hits.length === 1) return hits[0];
    if (hits.length === 0) {
      const loose = [...this.ds.teamNames.keys()].filter((key) => key.includes(c)).slice(0, 8);
      throw new QueryError(
        `No team matching "${query}" found in the match data.` +
          (loose.length ? ` Did you mean: ${loose.map((h) => this.teamName(h)).join(', ')}?` : ''),
      );
    }
    throw new QueryError(
      `"${query}" is ambiguous. Matching teams: ${hits
        .slice(0, 12)
        .map((h) => this.teamName(h))
        .join(', ')}${hits.length > 12 ? ', ...' : ''}. Please be more specific (e.g. add the state).`,
    );
  }

  listTeams(search?: string, competition?: string): { key: string; name: string; matches: number }[] {
    const comp = this.competition(competition);
    const counts = new Map<string, number>();
    for (const m of this.matches) {
      if (!m.primary || (comp && m.competition !== comp)) continue;
      counts.set(m.homeKey, (counts.get(m.homeKey) ?? 0) + 1);
      counts.set(m.awayKey, (counts.get(m.awayKey) ?? 0) + 1);
    }
    const c = search ? clean(search) : '';
    return [...counts.entries()]
      .filter(([k]) => !c || k.includes(c) || clean(this.teamName(k)).includes(c))
      .map(([key, matches]) => ({ key, name: this.teamName(key), matches }))
      .sort((a, b) => b.matches - a.matches || a.name.localeCompare(b.name));
  }

  private competition(s: string | undefined): Competition | undefined {
    if (s === undefined || s.trim() === '' || clean(s) === 'all') return undefined;
    const c = parseCompetition(s);
    if (!c) throw new QueryError(`Unknown competition "${s}". Known competitions: ${COMPETITIONS.join(', ')}.`);
    return c;
  }

  // -------------------------------------------------------------- matches

  /** Matches matching the filter, most recent first (undated matches last). */
  findMatches(f: MatchFilter = {}): Match[] {
    const team = f.team ? this.resolveTeam(f.team) : undefined;
    const opp = f.opponent ? this.resolveTeam(f.opponent) : undefined;
    const comp = this.competition(f.competition);
    const venue = f.venue ?? 'either';
    const from = f.dateFrom ? parseDate(f.dateFrom).date : null;
    const to = f.dateTo ? parseDate(f.dateTo).date : null;
    if (f.dateFrom && !from) throw new QueryError(`Unrecognised date "${f.dateFrom}" (use YYYY-MM-DD or DD/MM/YYYY).`);
    if (f.dateTo && !to) throw new QueryError(`Unrecognised date "${f.dateTo}" (use YYYY-MM-DD or DD/MM/YYYY).`);
    const stage = f.stage ? clean(f.stage).replace(/s$/, '') : undefined;
    const round = f.round !== undefined && f.round !== '' ? String(f.round) : undefined;

    const out = this.matches.filter((m) => {
      if (f.source ? m.source !== f.source : !f.includeDuplicates && !m.primary) return false;
      if (comp && m.competition !== comp) return false;
      if (f.season !== undefined && m.season !== f.season) return false;
      if (team) {
        const isHome = m.homeKey === team;
        const isAway = m.awayKey === team;
        if (venue === 'home' ? !isHome : venue === 'away' ? !isAway : !isHome && !isAway) return false;
        if (opp && !(isHome ? m.awayKey === opp : m.homeKey === opp)) return false;
      } else if (opp && m.homeKey !== opp && m.awayKey !== opp) return false;
      if (from && (!m.date || m.date < from)) return false;
      if (to && (!m.date || m.date > to)) return false;
      if (stage && (!m.stage || clean(m.stage).replace(/s$/, '') !== stage)) return false;
      if (round && m.round !== round) return false;
      if (f.playedOnly && !played(m)) return false;
      return true;
    });
    return out.sort((a, b) => (b.date ?? '').localeCompare(a.date ?? ''));
  }

  /** Win/draw/loss tally for a team over a set of matches (unplayed matches ignored). */
  tally(matches: Match[], key: string, venue: Venue = 'either'): TeamRecord {
    const r = { matches: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0 };
    for (const m of matches) {
      if (!played(m)) continue;
      const home = m.homeKey === key;
      if (!home && m.awayKey !== key) continue;
      if ((venue === 'home' && !home) || (venue === 'away' && home)) continue;
      const gf = (home ? m.homeGoals : m.awayGoals) as number;
      const ga = (home ? m.awayGoals : m.homeGoals) as number;
      r.matches++;
      r.goalsFor += gf;
      r.goalsAgainst += ga;
      if (gf > ga) r.wins++;
      else if (gf === ga) r.draws++;
      else r.losses++;
    }
    return {
      ...r,
      goalDifference: r.goalsFor - r.goalsAgainst,
      points: r.wins * 3 + r.draws,
      winRate: r.matches ? round1((r.wins / r.matches) * 100) : 0,
    };
  }

  headToHead(teamA: string, teamB: string, f: Omit<MatchFilter, 'team' | 'opponent' | 'venue'> = {}) {
    const a = this.resolveTeam(teamA);
    const b = this.resolveTeam(teamB);
    if (a === b) throw new QueryError('Head-to-head needs two different teams.');
    const matches = this.findMatches({ ...f, team: teamA, opponent: teamB });
    const rec = this.tally(matches, a);
    const rivalry = RIVALRIES.find(([x, y]) => (x === a && y === b) || (x === b && y === a));
    return {
      teamA: this.teamName(a),
      teamB: this.teamName(b),
      keyA: a,
      keyB: b,
      rivalry: rivalry ? rivalry[2] : null,
      matches,
      played: rec.matches,
      winsA: rec.wins,
      winsB: rec.losses,
      draws: rec.draws,
      goalsA: rec.goalsFor,
      goalsB: rec.goalsAgainst,
      homeRecordA: this.tally(matches, a, 'home'),
      homeRecordB: this.tally(matches, b, 'home'),
    };
  }

  teamStats(team: string, f: Omit<MatchFilter, 'team'> = {}) {
    const key = this.resolveTeam(team);
    const venue = f.venue ?? 'either';
    const matches = this.findMatches({ ...f, team, venue, playedOnly: true });
    const byCompetition = COMPETITIONS.map((c) => ({
      competition: c,
      record: this.tally(matches.filter((m) => m.competition === c), key, venue),
    })).filter((x) => x.record.matches > 0);
    return {
      team: this.teamName(key),
      teamKey: key,
      venue,
      overall: this.tally(matches, key, venue),
      home: this.tally(matches, key, 'home'),
      away: this.tally(matches, key, 'away'),
      byCompetition,
      matches,
    };
  }

  /** Competitions and seasons a team appears in, plus its FIFA squad (cross-file). */
  teamProfile(team: string) {
    const key = this.resolveTeam(team);
    const matches = this.findMatches({ team });
    const competitions = COMPETITIONS.map((c) => {
      const ms = matches.filter((m) => m.competition === c);
      const seasons = [...new Set(ms.map((m) => m.season).filter((s): s is number => s !== null))].sort();
      return { competition: c, seasons, record: this.tally(ms, key) };
    }).filter((c) => c.seasons.length > 0);
    const states = matches.map((m) => (m.homeKey === key ? m.homeState : m.awayState)).filter(Boolean);
    const players = this.playersOfTeam(key);
    return {
      team: this.teamName(key),
      teamKey: key,
      state: states[0] ?? null,
      aliases: this.rawNames(key),
      competitions,
      overall: this.tally(matches, key),
      rivals: RIVALRIES.filter(([a, b]) => a === key || b === key).map(([a, b, n]) => ({
        team: this.teamName(a === key ? b : a),
        name: n,
      })),
      players,
      firstMatch: matches.filter((m) => m.date).at(-1)?.date ?? null,
      lastMatch: matches.find((m) => m.date)?.date ?? null,
    };
  }

  private rawNames(key: string): string[] {
    const s = new Set<string>();
    for (const m of this.matches) {
      if (m.homeKey === key) s.add(m.homeRaw);
      if (m.awayKey === key) s.add(m.awayRaw);
    }
    return [...s].sort();
  }

  // ---------------------------------------------------------- competitions

  /** League table calculated from results (3 pts/win; ties broken by wins, GD, GF). */
  standings(season: number, competition = 'Brasileirão Série A') {
    const comp = this.competition(competition) ?? 'Brasileirão Série A';
    const all = this.findMatches({ competition: comp, season });
    if (!all.length) {
      throw new QueryError(`No ${comp} matches for season ${season}. Available seasons: ${this.seasons(comp).join(', ')}.`);
    }
    const ms = all.filter(played);
    const keys = new Set<string>();
    for (const m of all) {
      keys.add(m.homeKey);
      keys.add(m.awayKey);
    }
    const rows = [...keys]
      .map((k) => ({ teamKey: k, team: this.teamName(k), ...this.tally(ms, k) }))
      .sort(
        (a, b) =>
          b.points - a.points || b.wins - a.wins || b.goalDifference - a.goalDifference ||
          b.goalsFor - a.goalsFor || a.team.localeCompare(b.team),
      )
      .map((r, i): StandingRow => ({ position: i + 1, ...r }));
    const n = rows.length;
    const isLeague = comp !== 'Copa do Brasil' && comp !== 'Copa Libertadores';
    // A double round-robin is complete when every team has played 2*(n-1) matches.
    const complete = isLeague && comp !== 'Série C' && rows.every((r) => r.matches === 2 * (n - 1));
    return {
      competition: comp,
      season,
      rows,
      isLeague,
      complete,
      matchesPlayed: ms.length,
      matchesUnplayed: all.length - ms.length,
      champion: complete ? rows[0].team : null,
      relegated: complete && comp === 'Brasileirão Série A' ? rows.slice(-4).map((r) => r.team) : [],
    };
  }

  seasons(competition?: string): number[] {
    const comp = this.competition(competition);
    const s = new Set<number>();
    for (const m of this.matches) {
      if (m.primary && m.season !== null && (!comp || m.competition === comp)) s.add(m.season);
    }
    return [...s].sort();
  }

  /** Knockout view of a cup season: matches grouped by stage and paired into ties. */
  cupSummary(competition: string, season: number) {
    const comp = this.competition(competition);
    if (comp !== 'Copa do Brasil' && comp !== 'Copa Libertadores') {
      throw new QueryError('cupSummary applies to Copa do Brasil or Copa Libertadores; use standings for leagues.');
    }
    const ms = this.findMatches({ competition: comp, season }).reverse();
    if (!ms.length) {
      throw new QueryError(`No ${comp} matches for season ${season}. Available seasons: ${this.seasons(comp).join(', ')}.`);
    }
    const order = (stage: string) => {
      const i = LIB_STAGES.indexOf(stage);
      if (i >= 0) return 100 + i;
      const n = Number(stage.replace(/\D/g, ''));
      return Number.isFinite(n) && stage.startsWith('Round') ? n : 50;
    };
    const names = [...new Set(ms.map((m) => m.stage ?? 'Unlabelled'))].sort((a, b) => order(a) - order(b));
    const stages = names.map((name) => {
      const sm = ms.filter((m) => (m.stage ?? 'Unlabelled') === name);
      const knockout = name !== 'group stage' && name !== 'Unlabelled';
      return { stage: name, matches: sm, ties: knockout ? this.ties(sm) : [] };
    });
    const final = stages.find((s) => s.stage === 'final');
    const finalTie = final && final.ties.length === 1 ? final.ties[0] : null;
    return { competition: comp, season, stages, final: finalTie, champion: finalTie?.winner ?? null };
  }

  private ties(matches: Match[]): Tie[] {
    const groups = new Map<string, Match[]>();
    for (const m of matches) {
      const id = [m.homeKey, m.awayKey].sort().join('|');
      if (!groups.has(id)) groups.set(id, []);
      groups.get(id)!.push(m);
    }
    return [...groups.values()].map((ms) => {
      const a = ms[0].homeKey;
      const b = ms[0].awayKey;
      let aggregate: [number, number] | null = [0, 0];
      for (const m of ms) {
        if (!played(m)) {
          aggregate = null;
          break;
        }
        aggregate[0] += (m.homeKey === a ? m.homeGoals : m.awayGoals) as number;
        aggregate[1] += (m.homeKey === a ? m.awayGoals : m.homeGoals) as number;
      }
      const winner =
        aggregate && aggregate[0] !== aggregate[1] ? this.teamName(aggregate[0] > aggregate[1] ? a : b) : null;
      return { teams: [this.teamName(a), this.teamName(b)], matches: ms, aggregate, winner };
    });
  }

  // ------------------------------------------------------------ statistics

  leagueStats(f: MatchFilter = {}) {
    const ms = this.findMatches({ ...f, playedOnly: true });
    let goals = 0, home = 0, draws = 0, away = 0, homeGoals = 0;
    for (const m of ms) {
      const h = m.homeGoals as number, a = m.awayGoals as number;
      goals += h + a;
      homeGoals += h;
      if (h > a) home++;
      else if (h === a) draws++;
      else away++;
    }
    const n = ms.length;
    const pct = (x: number) => (n ? round1((x / n) * 100) : 0);
    const highest = [...ms].sort(
      (x, y) => (y.homeGoals! + y.awayGoals!) - (x.homeGoals! + x.awayGoals!) || (y.date ?? '').localeCompare(x.date ?? ''),
    )[0] ?? null;
    return {
      matches: n,
      totalGoals: goals,
      avgGoalsPerMatch: n ? round2(goals / n) : 0,
      avgHomeGoals: n ? round2(homeGoals / n) : 0,
      avgAwayGoals: n ? round2((goals - homeGoals) / n) : 0,
      homeWins: home,
      draws,
      awayWins: away,
      homeWinRate: pct(home),
      drawRate: pct(draws),
      awayWinRate: pct(away),
      highestScoringMatch: highest,
    };
  }

  biggestWins(f: MatchFilter = {}, limit = 10): Match[] {
    return this.findMatches({ ...f, playedOnly: true })
      .filter((m) => m.homeGoals !== m.awayGoals)
      .sort(
        (a, b) =>
          Math.abs(b.homeGoals! - b.awayGoals!) - Math.abs(a.homeGoals! - a.awayGoals!) ||
          (b.homeGoals! + b.awayGoals!) - (a.homeGoals! + a.awayGoals!) ||
          (b.date ?? '').localeCompare(a.date ?? ''),
      )
      .slice(0, limit);
  }

  /** Rank teams by a metric over the filtered matches (home, away or all matches). */
  rankTeams(metric: RankMetric, f: MatchFilter = {}, opts: { minMatches?: number; limit?: number } = {}) {
    const venue = f.venue ?? 'either';
    const ms = this.findMatches({ ...f, team: undefined, venue: undefined, playedOnly: true });
    const keys = new Set<string>();
    for (const m of ms) {
      keys.add(m.homeKey);
      keys.add(m.awayKey);
    }
    const value = (r: TeamRecord): number => {
      switch (metric) {
        case 'points': return r.points;
        case 'win_rate': return r.winRate;
        case 'wins': return r.wins;
        case 'goals_for': return r.goalsFor;
        case 'goals_against': return r.goalsAgainst;
        case 'goal_difference': return r.goalDifference;
        case 'points_per_match': return r.matches ? round2(r.points / r.matches) : 0;
      }
    };
    const rate = metric === 'win_rate' || metric === 'points_per_match';
    const min = opts.minMatches ?? (rate ? 10 : 1);
    return [...keys]
      .map((k) => {
        const record = this.tally(ms, k, venue);
        return { team: this.teamName(k), teamKey: k, record, value: value(record) };
      })
      .filter((r) => r.record.matches >= min)
      .sort((a, b) => b.value - a.value || b.record.matches - a.record.matches || a.team.localeCompare(b.team))
      .slice(0, opts.limit ?? 10);
  }

  compareSeasons(seasonA: number, seasonB: number, competition = 'Brasileirão Série A') {
    const one = (season: number) => {
      const comp = this.competition(competition) ?? 'Brasileirão Série A';
      const stats = this.leagueStats({ competition: comp, season });
      if (!stats.matches) {
        throw new QueryError(`No played ${comp} matches for season ${season}. Available: ${this.seasons(comp).join(', ')}.`);
      }
      const isCup = comp === 'Copa do Brasil' || comp === 'Copa Libertadores';
      const champion = isCup ? this.cupSummary(comp, season).champion : this.standings(season, comp).champion;
      const topAttack = this.rankTeams('goals_for', { competition: comp, season }, { limit: 1 })[0];
      const bestDefence = isCup ? null : this.rankTeams('goals_against', { competition: comp, season }, { limit: 100 }).at(-1) ?? null;
      return { season, competition: comp, stats, champion, topAttack, bestDefence };
    };
    return { a: one(seasonA), b: one(seasonB) };
  }

  /** Matches between traditional rivals. */
  derbies(f: MatchFilter = {}): { match: Match; name: string }[] {
    const name = new Map<string, string>();
    for (const [a, b, n] of RIVALRIES) name.set([a, b].sort().join('|'), n);
    return this.findMatches(f)
      .map((m) => ({ match: m, name: name.get([m.homeKey, m.awayKey].sort().join('|')) }))
      .filter((x): x is { match: Match; name: string } => x.name !== undefined);
  }

  /** Corner / shot / attack averages from the extended statistics file. */
  extendedStats(f: Omit<MatchFilter, 'source'> = {}) {
    const key = f.team ? this.resolveTeam(f.team) : undefined;
    const ms = this.findMatches({ ...f, source: 'br_football', playedOnly: true });
    const sum = { corners: [0, 0, 0], shots: [0, 0, 0], attacks: [0, 0, 0] }; // for, against, n
    const add = (acc: number[], a: number | null, b: number | null) => {
      if (a === null || b === null) return;
      acc[0] += a;
      acc[1] += b;
      acc[2]++;
    };
    for (const m of ms) {
      const s = m.stats!;
      const flip = key !== undefined && m.awayKey === key;
      add(sum.corners, flip ? s.awayCorners : s.homeCorners, flip ? s.homeCorners : s.awayCorners);
      add(sum.shots, flip ? s.awayShots : s.homeShots, flip ? s.homeShots : s.awayShots);
      add(sum.attacks, flip ? s.awayAttacks : s.homeAttacks, flip ? s.homeAttacks : s.awayAttacks);
    }
    const avg = (acc: number[]) =>
      acc[2] ? { for: round2(acc[0] / acc[2]), against: round2(acc[1] / acc[2]), matches: acc[2] } : null;
    return {
      team: key ? this.teamName(key) : null,
      matches: ms.length,
      record: key ? this.tally(ms, key, f.venue ?? 'either') : null,
      corners: avg(sum.corners),
      shots: avg(sum.shots),
      attacks: avg(sum.attacks),
    };
  }

  // --------------------------------------------------------------- players

  private isBrazilianClub = (() => {
    let cache: Set<string> | null = null;
    return (clubKey: string): boolean => {
      if (!cache) {
        const total = new Map<string, [number, number]>();
        for (const p of this.players) {
          if (!p.clubKey) continue;
          const t = total.get(p.clubKey) ?? [0, 0];
          t[0]++;
          if (p.nationality === 'Brazil') t[1]++;
          total.set(p.clubKey, t);
        }
        cache = new Set(
          [...total.entries()].filter(([k, [n, br]]) => this.domesticKeys.has(k) && br * 2 > n).map(([k]) => k),
        );
      }
      return cache.has(clubKey);
    };
  })();

  playersOfTeam(key: string): Player[] {
    if (!this.isBrazilianClub(key)) return [];
    return this.players.filter((p) => p.clubKey === key).sort((a, b) => b.overall - a.overall);
  }

  searchPlayers(f: PlayerFilter = {}): { total: number; players: Player[]; partialNameMatch: boolean } {
    const nat = f.nationality ? clean(f.nationality) : '';
    const natNorm = ['brazilian', 'brasil', 'brasileiro', 'brazilians'].includes(nat) ? 'brazil' : nat;
    const clubC = f.club ? clean(f.club) : '';
    const clubK = f.club ? teamKey(f.club) : '';
    let positions: string[] | null = null;
    if (f.position) {
      const p = clean(f.position);
      const group = POSITION_GROUPS[POSITION_SYNONYMS[p] ?? p];
      positions = group ?? [f.position.trim().toUpperCase()];
    }
    const base = this.players.filter((p) => {
      if (natNorm && clean(p.nationality) !== natNorm) return false;
      if (clubC && p.clubKey !== clubK && !clean(p.club).includes(clubC)) return false;
      if (positions && !positions.includes(p.position)) return false;
      if (f.minOverall !== undefined && p.overall < f.minOverall) return false;
      if (f.maxAge !== undefined && (p.age === null || p.age > f.maxAge)) return false;
      return true;
    });
    let result = base;
    let partial = false;
    if (f.name) {
      const toks = clean(f.name).split(' ').filter(Boolean);
      const hay = (p: Player) => ` ${clean(p.name)} `;
      result = base.filter((p) => toks.every((t) => hay(p).includes(t)));
      if (!result.length && toks.length > 1) {
        // Fall back to any whole-word token: FIFA abbreviates names ("G. Barbosa", "Gabriel").
        result = base.filter((p) => toks.some((t) => hay(p).includes(` ${t} `)));
        partial = result.length > 0;
      }
    }
    const sortBy = f.sortBy ?? 'overall';
    result = [...result].sort((a, b) => {
      if (sortBy === 'name') return a.name.localeCompare(b.name);
      if (sortBy === 'age') return (a.age ?? 99) - (b.age ?? 99) || b.overall - a.overall;
      if (sortBy === 'potential') return (b.potential ?? 0) - (a.potential ?? 0) || b.overall - a.overall;
      return b.overall - a.overall || (b.potential ?? 0) - (a.potential ?? 0);
    });
    return { total: result.length, players: result.slice(0, f.limit ?? 20), partialNameMatch: partial };
  }

  getPlayer(id: number): Player | undefined {
    return this.players.find((p) => p.id === id);
  }

  /** Player counts and average rating per club, optionally only Brazilian clubs / one nationality. */
  clubSummary(opts: { nationality?: string; brazilianClubsOnly?: boolean; limit?: number } = {}) {
    const { players } = this.searchPlayers({ nationality: opts.nationality, limit: Infinity });
    const clubs = new Map<string, Player[]>();
    for (const p of players) {
      if (!p.club) continue;
      if (opts.brazilianClubsOnly && !this.isBrazilianClub(p.clubKey)) continue;
      if (!clubs.has(p.club)) clubs.set(p.club, []);
      clubs.get(p.club)!.push(p);
    }
    return [...clubs.entries()]
      .map(([club, ps]) => ({
        club,
        players: ps.length,
        avgOverall: round1(ps.reduce((s, p) => s + p.overall, 0) / ps.length),
        best: ps.reduce((a, b) => (b.overall > a.overall ? b : a)),
      }))
      .sort((a, b) => b.players - a.players || b.avgOverall - a.avgOverall || a.club.localeCompare(b.club))
      .slice(0, opts.limit ?? 25);
  }
}
