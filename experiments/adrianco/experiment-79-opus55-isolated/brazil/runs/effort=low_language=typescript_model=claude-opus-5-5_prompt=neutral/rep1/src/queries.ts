/** Query layer over the loaded dataset: matches, teams, players, competitions, statistics. */
import { COMPETITIONS, Competition, Dataset, Match, Player, loadDataset } from './data.js';
import { fold } from './teams.js';

export interface MatchFilter {
  /** Team playing at home or away. */
  team?: string;
  /** Restricts `team` matches to those against this opponent. */
  opponent?: string;
  homeTeam?: string;
  awayTeam?: string;
  competition?: string;
  season?: number;
  dateFrom?: string;
  dateTo?: string;
  /** e.g. "final", "semifinals", "group stage". */
  stage?: string;
}

export type Venue = 'home' | 'away' | 'all';

export interface TeamRecord {
  team: string;
  matches: number;
  wins: number;
  draws: number;
  losses: number;
  goalsFor: number;
  goalsAgainst: number;
  goalDifference: number;
  points: number;
  winRate: number;
}

export interface HeadToHead {
  teamA: string;
  teamB: string;
  matches: Match[];
  winsA: number;
  winsB: number;
  draws: number;
  goalsA: number;
  goalsB: number;
}

export interface LeagueStats {
  matches: number;
  goals: number;
  goalsPerMatch: number;
  homeWins: number;
  draws: number;
  awayWins: number;
  homeWinRate: number;
  drawRate: number;
  awayWinRate: number;
}

export interface PlayerFilter {
  name?: string;
  nationality?: string;
  club?: string;
  /** Exact position code (ST, GK...) or a group: forward, midfielder, defender, goalkeeper. */
  position?: string;
  minOverall?: number;
  maxAge?: number;
  /** Only players at clubs that appear in the Brazilian match data. */
  brazilianClubsOnly?: boolean;
  sortBy?: 'overall' | 'potential' | 'age';
}

export class UnknownEntityError extends Error {}

const POSITION_GROUPS: Record<string, string[]> = {
  goalkeeper: ['GK'],
  defender: ['CB', 'LCB', 'RCB', 'LB', 'RB', 'LWB', 'RWB'],
  midfielder: ['CM', 'LCM', 'RCM', 'CDM', 'LDM', 'RDM', 'CAM', 'LAM', 'RAM', 'LM', 'RM'],
  forward: ['ST', 'LS', 'RS', 'CF', 'LF', 'RF', 'LW', 'RW'],
};
const POSITION_WORDS: Record<string, string> = {
  goalkeeper: 'goalkeeper', goalkeepers: 'goalkeeper', keeper: 'goalkeeper', goleiro: 'goalkeeper',
  defender: 'defender', defenders: 'defender', defence: 'defender', defense: 'defender', zagueiro: 'defender',
  midfielder: 'midfielder', midfielders: 'midfielder', midfield: 'midfielder', meia: 'midfielder',
  forward: 'forward', forwards: 'forward', striker: 'forward', strikers: 'forward', attacker: 'forward',
  attackers: 'forward', atacante: 'forward',
};

/** Traditional rivalries (clássicos), as pairs of team names. */
const DERBIES: [string, string, string][] = [
  ['Flamengo', 'Fluminense', 'Fla-Flu'],
  ['Flamengo', 'Vasco', 'Clássico dos Milhões'],
  ['Flamengo', 'Botafogo', 'Clássico da Rivalidade'],
  ['Fluminense', 'Vasco', 'Clássico dos Gigantes'],
  ['Fluminense', 'Botafogo', 'Clássico Vovô'],
  ['Botafogo', 'Vasco', 'Clássico da Amizade'],
  ['Corinthians', 'Palmeiras', 'Derby Paulista'],
  ['Corinthians', 'São Paulo', 'Majestoso'],
  ['Palmeiras', 'São Paulo', 'Choque-Rei'],
  ['Santos', 'Corinthians', 'Clássico Alvinegro'],
  ['Santos', 'São Paulo', 'San-São'],
  ['Santos', 'Palmeiras', 'Clássico da Saudade'],
  ['Grêmio', 'Internacional', 'Grenal'],
  ['Atlético-MG', 'Cruzeiro', 'Clássico Mineiro'],
  ['Bahia', 'Vitória', 'Ba-Vi'],
  ['Athletico-PR', 'Coritiba', 'Atletiba'],
  ['Sport', 'Náutico', 'Clássico dos Clássicos'],
  ['Sport', 'Santa Cruz', 'Clássico das Multidões'],
  ['Ceará', 'Fortaleza', 'Clássico-Rei'],
  ['Goiás', 'Vila Nova', 'Derby do Cerrado'],
  ['Avaí', 'Figueirense', 'Clássico de Florianópolis'],
  ['Remo', 'Paysandu', 'Re-Pa'],
];

export function resolveCompetition(q: string): Competition {
  const f = fold(q);
  if (f.includes('libertadores')) return COMPETITIONS.libertadores;
  if (f.includes('copa') || f.includes('cup')) return COMPETITIONS.cup;
  if (/serie b|second division/.test(f)) return COMPETITIONS.serieB;
  if (/serie c|third division/.test(f)) return COMPETITIONS.serieC;
  if (/brasileir|serie a|campeonato|league/.test(f)) return COMPETITIONS.serieA;
  throw new UnknownEntityError(
    `Unknown competition "${q}". Known competitions: ${Object.values(COMPETITIONS).join(', ')}`,
  );
}

const pct = (n: number, d: number) => (d ? (100 * n) / d : 0);

export class SoccerKB {
  readonly data: Dataset;
  private derbyNames = new Map<string, string>();

  constructor(data: Dataset = loadDataset()) {
    this.data = data;
    for (const [a, b, name] of DERBIES) {
      const ia = data.teams.resolve(a);
      const ib = data.teams.resolve(b);
      if (ia && ib) this.derbyNames.set(pairKey(ia, ib), name);
    }
  }

  teamName(id: string): string {
    return this.data.teams.name(id);
  }

  /** Resolve user text to a team id, or throw with a helpful message. */
  team(query: string): string {
    const id = this.data.teams.resolve(query);
    if (!id) throw new UnknownEntityError(`No team matching "${query}" was found in the match data.`);
    return id;
  }

  derbyName(a: string, b: string): string | undefined {
    return this.derbyNames.get(pairKey(a, b));
  }

  // ---- Matches -------------------------------------------------------------

  /** Matches satisfying the filter, most recent first. */
  findMatches(f: MatchFilter = {}): Match[] {
    const team = f.team ? this.team(f.team) : undefined;
    const opp = f.opponent ? this.team(f.opponent) : undefined;
    const home = f.homeTeam ? this.team(f.homeTeam) : undefined;
    const away = f.awayTeam ? this.team(f.awayTeam) : undefined;
    const comp = f.competition ? resolveCompetition(f.competition) : undefined;
    const stage = f.stage ? fold(f.stage).replace(/s$/, '') : undefined;
    const res = this.data.matches.filter(
      (m) =>
        (!comp || m.competition === comp) &&
        (f.season === undefined || m.season === f.season) &&
        (!team || m.home === team || m.away === team) &&
        (!opp || m.home === opp || m.away === opp) &&
        (!home || m.home === home) &&
        (!away || m.away === away) &&
        (!f.dateFrom || m.date >= f.dateFrom) &&
        (!f.dateTo || m.date <= f.dateTo) &&
        (!stage || (m.stage !== undefined && fold(m.stage).replace(/s$/, '') === stage)),
    );
    return res.reverse();
  }

  headToHead(a: string, b: string, f: Omit<MatchFilter, 'team' | 'opponent'> = {}): HeadToHead {
    const ia = this.team(a);
    const ib = this.team(b);
    const matches = this.findMatches({ ...f, team: a, opponent: b });
    const h: HeadToHead = { teamA: ia, teamB: ib, matches, winsA: 0, winsB: 0, draws: 0, goalsA: 0, goalsB: 0 };
    for (const m of matches) {
      const [ga, gb] = m.home === ia ? [m.homeGoals, m.awayGoals] : [m.awayGoals, m.homeGoals];
      h.goalsA += ga;
      h.goalsB += gb;
      if (ga > gb) h.winsA++;
      else if (gb > ga) h.winsB++;
      else h.draws++;
    }
    return h;
  }

  /** Matches between traditional rivals. */
  derbies(f: MatchFilter = {}): Match[] {
    return this.findMatches(f).filter((m) => this.derbyNames.has(pairKey(m.home, m.away)));
  }

  // ---- Teams ---------------------------------------------------------------

  teamRecord(team: string, f: Omit<MatchFilter, 'team'> & { venue?: Venue } = {}): TeamRecord {
    const id = this.team(team);
    const table = tabulate(this.findMatches({ ...f, team }), f.venue ?? 'all');
    return table.get(id) ?? emptyRecord(id);
  }

  /** Per-competition breakdown of everything a team has played. */
  teamCompetitions(team: string): { competition: Competition; seasons: number[]; record: TeamRecord }[] {
    const id = this.team(team);
    const byComp = new Map<Competition, Match[]>();
    for (const m of this.findMatches({ team })) {
      const list = byComp.get(m.competition) ?? [];
      list.push(m);
      byComp.set(m.competition, list);
    }
    return [...byComp].map(([competition, ms]) => ({
      competition,
      seasons: [...new Set(ms.map((m) => m.season))].sort((x, y) => x - y),
      record: tabulate(ms, 'all').get(id) ?? emptyRecord(id),
    }));
  }

  /** Records for every team matching the filter, ranked by the chosen metric. */
  rankTeams(
    f: MatchFilter & { venue?: Venue; minMatches?: number; metric?: 'winRate' | 'points' | 'goalsFor' | 'wins' } = {},
  ): TeamRecord[] {
    const metric = f.metric ?? 'winRate';
    const min = f.minMatches ?? 1;
    return [...tabulate(this.findMatches(f), f.venue ?? 'all').values()]
      .filter((r) => r.matches >= min)
      .sort((a, b) => b[metric] - a[metric] || b.matches - a.matches || b.goalDifference - a.goalDifference);
  }

  // ---- Competitions --------------------------------------------------------

  /** League table calculated from results: 3 points a win, then wins, goal difference, goals scored. */
  standings(season: number, competition = 'Brasileirão'): TeamRecord[] {
    const ms = this.findMatches({ season, competition });
    return [...tabulate(ms, 'all').values()].sort(
      (a, b) =>
        b.points - a.points || b.wins - a.wins || b.goalDifference - a.goalDifference || b.goalsFor - a.goalsFor,
    );
  }

  seasons(competition?: string): number[] {
    const comp = competition ? resolveCompetition(competition) : undefined;
    const s = new Set<number>();
    for (const m of this.data.matches) if (!comp || m.competition === comp) s.add(m.season);
    return [...s].sort((a, b) => a - b);
  }

  // ---- Statistics ----------------------------------------------------------

  leagueStats(f: MatchFilter = {}): LeagueStats {
    const ms = this.findMatches(f);
    let goals = 0, homeWins = 0, draws = 0;
    for (const m of ms) {
      goals += m.homeGoals + m.awayGoals;
      if (m.homeGoals > m.awayGoals) homeWins++;
      else if (m.homeGoals === m.awayGoals) draws++;
    }
    const n = ms.length;
    const awayWins = n - homeWins - draws;
    return {
      matches: n, goals, goalsPerMatch: n ? goals / n : 0, homeWins, draws, awayWins,
      homeWinRate: pct(homeWins, n), drawRate: pct(draws, n), awayWinRate: pct(awayWins, n),
    };
  }

  biggestWins(f: MatchFilter = {}, limit = 10): Match[] {
    const margin = (m: Match) => Math.abs(m.homeGoals - m.awayGoals);
    const total = (m: Match) => m.homeGoals + m.awayGoals;
    return this.findMatches(f)
      .filter((m) => margin(m) > 0)
      .sort((a, b) => margin(b) - margin(a) || total(b) - total(a) || b.date.localeCompare(a.date))
      .slice(0, limit);
  }

  // ---- Players -------------------------------------------------------------

  /** Players satisfying the filter, best first. */
  findPlayers(f: PlayerFilter = {}): Player[] {
    const name = f.name ? fold(f.name) : undefined;
    const nameWords = name?.split(' ');
    const nat = f.nationality ? normalizeNationality(f.nationality) : undefined;
    const club = f.club ? fold(f.club) : undefined;
    // "Santos" should mean the Brazilian club, not also "Santos Laguna"; fall
    // back to substring matching for clubs outside the Brazilian match data.
    const resolved = f.club ? this.data.teams.resolve(f.club) : undefined;
    const clubId = resolved && this.data.players.some((p) => p.clubId === resolved) ? resolved : undefined;
    const positions = f.position ? resolvePositions(f.position) : undefined;
    const sort = f.sortBy ?? 'overall';
    return this.data.players
      .filter((p) => {
        if (nameWords) {
          const pn = fold(p.name);
          if (!nameWords.every((w) => pn.includes(w))) return false;
        }
        if (nat && fold(p.nationality) !== nat) return false;
        if (club && !(clubId ? p.clubId === clubId : fold(p.club).includes(club))) return false;
        if (positions && !positions.includes(p.position)) return false;
        if (f.minOverall !== undefined && p.overall < f.minOverall) return false;
        if (f.maxAge !== undefined && (p.age === undefined || p.age > f.maxAge)) return false;
        if (f.brazilianClubsOnly && !p.clubId) return false;
        return true;
      })
      .sort((a, b) =>
        sort === 'age' ? (a.age ?? 99) - (b.age ?? 99) || b.overall - a.overall
          : b[sort] - a[sort] || b.potential - a.potential || a.name.localeCompare(b.name),
      );
  }

  /** Squad size and average rating for each Brazilian club in the FIFA data. */
  brazilianClubSquads(nationality?: string): { club: string; clubId: string; players: number; avgOverall: number; best: Player }[] {
    const groups = new Map<string, Player[]>();
    for (const p of this.findPlayers({ nationality, brazilianClubsOnly: true })) {
      const g = groups.get(p.clubId!) ?? [];
      g.push(p);
      groups.set(p.clubId!, g);
    }
    return [...groups]
      .map(([clubId, ps]) => ({
        club: ps[0].club, clubId, players: ps.length,
        avgOverall: ps.reduce((s, p) => s + p.overall, 0) / ps.length, best: ps[0],
      }))
      .sort((a, b) => b.avgOverall - a.avgOverall);
  }
}

function pairKey(a: string, b: string): string {
  return a < b ? `${a}|${b}` : `${b}|${a}`;
}

function emptyRecord(team: string): TeamRecord {
  return {
    team, matches: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0, goalDifference: 0, points: 0,
    winRate: 0,
  };
}

function tabulate(matches: Match[], venue: Venue): Map<string, TeamRecord> {
  const table = new Map<string, TeamRecord>();
  const credit = (team: string, gf: number, ga: number) => {
    let r = table.get(team);
    if (!r) table.set(team, (r = emptyRecord(team)));
    r.matches++;
    r.goalsFor += gf;
    r.goalsAgainst += ga;
    if (gf > ga) r.wins++;
    else if (gf === ga) r.draws++;
    else r.losses++;
  };
  for (const m of matches) {
    if (venue !== 'away') credit(m.home, m.homeGoals, m.awayGoals);
    if (venue !== 'home') credit(m.away, m.awayGoals, m.homeGoals);
  }
  for (const r of table.values()) {
    r.goalDifference = r.goalsFor - r.goalsAgainst;
    r.points = r.wins * 3 + r.draws;
    r.winRate = pct(r.wins, r.matches);
  }
  return table;
}

function normalizeNationality(q: string): string {
  const f = fold(q);
  return ({ brazilian: 'brazil', brasil: 'brazil', brasileiro: 'brazil', argentinian: 'argentina', argentine: 'argentina' } as Record<string, string>)[f] ?? f;
}

function resolvePositions(q: string): string[] {
  const group = POSITION_WORDS[fold(q)];
  return group ? POSITION_GROUPS[group] : [q.trim().toUpperCase()];
}
