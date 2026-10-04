/** Loads the six Kaggle CSV files into one normalised, de-duplicated dataset. */
import { existsSync, readFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { parseCsv } from './csv.js';
import { ParsedName, TeamRegistry, fold, parseTeamName } from './teams.js';

export const COMPETITIONS = {
  serieA: 'Brasileirão Série A',
  serieB: 'Brasileirão Série B',
  serieC: 'Brasileirão Série C',
  cup: 'Copa do Brasil',
  libertadores: 'Copa Libertadores',
} as const;
export type Competition = (typeof COMPETITIONS)[keyof typeof COMPETITIONS];

export const FILES = {
  brasileirao: 'Brasileirao_Matches.csv',
  cup: 'Brazilian_Cup_Matches.csv',
  libertadores: 'Libertadores_Matches.csv',
  extended: 'BR-Football-Dataset.csv',
  historical: 'novo_campeonato_brasileiro.csv',
  fifa: 'fifa_data.csv',
} as const;

export interface MatchStats {
  homeCorners?: number;
  awayCorners?: number;
  homeAttacks?: number;
  awayAttacks?: number;
  homeShots?: number;
  awayShots?: number;
}

export interface Match {
  competition: Competition;
  season: number;
  /** ISO date, YYYY-MM-DD. */
  date: string;
  time?: string;
  round?: string;
  stage?: string;
  home: string;
  away: string;
  homeGoals: number;
  awayGoals: number;
  arena?: string;
  stats?: MatchStats;
  /** CSV files this match was found in. */
  sources: string[];
}

export interface Player {
  id: number;
  name: string;
  age?: number;
  nationality: string;
  overall: number;
  potential: number;
  club: string;
  /** Normalised team id of the club, comparable with match data. */
  clubId?: string;
  position: string;
  jersey?: number;
  height?: string;
  weight?: string;
  foot?: string;
  value?: string;
  wage?: string;
  skills: Record<string, number>;
}

export interface Dataset {
  matches: Match[];
  players: Player[];
  teams: TeamRegistry;
  /** Rows read per CSV file (before de-duplication and dropping unplayed games). */
  rowCounts: Record<string, number>;
}

export function defaultDataDir(): string {
  if (process.env.BRAZILIAN_SOCCER_DATA_DIR) return resolve(process.env.BRAZILIAN_SOCCER_DATA_DIR);
  const here = dirname(fileURLToPath(import.meta.url));
  for (const c of [join(here, '..', 'data', 'kaggle'), join(process.cwd(), 'data', 'kaggle')]) {
    if (existsSync(c)) return c;
  }
  throw new Error('Could not locate data/kaggle; set BRAZILIAN_SOCCER_DATA_DIR');
}

/** Accepts "2023-09-24", "2012-05-19 18:30:00" and "29/03/2003". */
export function parseDate(s: string): { date: string; time?: string } | undefined {
  const t = s.trim();
  let m = t.match(/^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}:\d{2})(?::\d{2})?)?/);
  if (m) return { date: `${m[1]}-${m[2]}-${m[3]}`, time: m[4] };
  m = t.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (m) return { date: `${m[3]}-${m[2].padStart(2, '0')}-${m[1].padStart(2, '0')}` };
  return undefined;
}

function int(s: string | undefined): number | undefined {
  if (s === undefined || s.trim() === '') return undefined;
  const n = Number(s);
  return Number.isFinite(n) ? Math.round(n) : undefined;
}

interface RawMatch extends Omit<Match, 'home' | 'away' | 'sources'> {
  home: ParsedName;
  away: ParsedName;
  source: string;
}

const SKILLS = [
  'Crossing', 'Finishing', 'HeadingAccuracy', 'ShortPassing', 'Volleys', 'Dribbling', 'Curve',
  'FKAccuracy', 'LongPassing', 'BallControl', 'Acceleration', 'SprintSpeed', 'Agility', 'Reactions',
  'Balance', 'ShotPower', 'Jumping', 'Stamina', 'Strength', 'LongShots', 'Aggression',
  'Interceptions', 'Positioning', 'Vision', 'Penalties', 'Composure', 'Marking', 'StandingTackle',
  'SlidingTackle', 'GKDiving', 'GKHandling', 'GKKicking', 'GKPositioning', 'GKReflexes',
];

const EXTENDED_TOURNAMENTS: Record<string, Competition> = {
  'serie a': COMPETITIONS.serieA,
  'serie b': COMPETITIONS.serieB,
  'serie c': COMPETITIONS.serieC,
  'copa do brasil': COMPETITIONS.cup,
};

export function loadDataset(dataDir = defaultDataDir()): Dataset {
  const teams = new TeamRegistry();
  const rowCounts: Record<string, number> = {};
  const read = (file: string) => {
    const rows = parseCsv(readFileSync(join(dataDir, file), 'utf8'));
    rowCounts[file] = rows.length;
    return rows;
  };
  const raw: RawMatch[] = [];
  const add = (
    source: string,
    r: { comp: Competition; season?: number; when: string; home: string; away: string; hg?: string; ag?: string } & Partial<Pick<Match, 'round' | 'stage' | 'arena' | 'stats' | 'time'>>,
  ) => {
    const d = parseDate(r.when);
    const hg = int(r.hg);
    const ag = int(r.ag);
    // Unplayed / unknown-result rows ("NA", "-") carry no usable information.
    if (!d || hg === undefined || ag === undefined || !r.home.trim() || !r.away.trim()) return;
    raw.push({
      competition: r.comp,
      season: r.season ?? Number(d.date.slice(0, 4)),
      date: d.date,
      time: r.time ?? d.time,
      round: r.round || undefined,
      stage: r.stage || undefined,
      arena: r.arena || undefined,
      stats: r.stats,
      homeGoals: hg,
      awayGoals: ag,
      home: teams.observe(r.home),
      away: teams.observe(r.away),
      source,
    });
  };

  // Order matters: earlier files win on conflicting fields when duplicates merge.
  // The state columns of the two Brasileirão files are not used: the names
  // already carry a suffix where needed and the historical file's are unreliable.
  for (const r of read(FILES.historical)) {
    add(FILES.historical, {
      comp: COMPETITIONS.serieA, season: int(r.Ano), when: r.Data, home: r.Equipe_mandante,
      away: r.Equipe_visitante, hg: r.Gols_mandante, ag: r.Gols_visitante, round: r.Rodada, arena: r.Arena,
    });
  }
  for (const r of read(FILES.brasileirao)) {
    add(FILES.brasileirao, {
      comp: COMPETITIONS.serieA, season: int(r.season), when: r.datetime, home: r.home_team,
      away: r.away_team, hg: r.home_goal, ag: r.away_goal, round: r.round,
    });
  }
  for (const r of read(FILES.cup)) {
    add(FILES.cup, {
      comp: COMPETITIONS.cup, season: int(r.season), when: r.datetime, home: r.home_team,
      away: r.away_team, hg: r.home_goal, ag: r.away_goal, round: r.round,
    });
  }
  for (const r of read(FILES.libertadores)) {
    add(FILES.libertadores, {
      comp: COMPETITIONS.libertadores, season: int(r.season), when: r.datetime, home: r.home_team,
      away: r.away_team, hg: r.home_goal, ag: r.away_goal, stage: r.stage,
    });
  }
  for (const r of read(FILES.extended)) {
    const comp = EXTENDED_TOURNAMENTS[fold(r.tournament)];
    if (!comp) continue;
    const d = parseDate(r.date);
    // This file has no season column. The pandemic-delayed 2020 season ran
    // until early March 2021 (the 2021 competitions started on 9 March).
    const season = d && d.date >= '2021-01-01' && d.date < '2021-03-08' ? 2020 : undefined;
    add(FILES.extended, {
      comp, season, when: r.date, time: r.time?.slice(0, 5), home: r.home, away: r.away, hg: r.home_goal,
      ag: r.away_goal,
      stats: {
        homeCorners: int(r.home_corner), awayCorners: int(r.away_corner), homeAttacks: int(r.home_attack),
        awayAttacks: int(r.away_attack), homeShots: int(r.home_shots), awayShots: int(r.away_shots),
      },
    });
  }

  const matches = dropMislabelled(dedupe(raw, teams));
  matches.sort((a, b) => a.date.localeCompare(b.date));
  markCupFinals(matches);

  const leagueTeams = new Set<string>();
  for (const m of matches) {
    if (m.competition !== COMPETITIONS.libertadores) leagueTeams.add(m.home).add(m.away);
  }
  const players = read(FILES.fifa).map((r): Player => {
    const skills: Record<string, number> = {};
    for (const k of SKILLS) {
      const v = int(r[k]);
      if (v !== undefined) skills[k] = v;
    }
    const club = r.Club.trim();
    const clubId = club ? teams.idOf(parseTeamName(club), false) : undefined;
    return {
      id: Number(r.ID), name: r.Name, age: int(r.Age), nationality: r.Nationality, overall: int(r.Overall) ?? 0,
      potential: int(r.Potential) ?? 0, club, clubId: clubId && leagueTeams.has(clubId) ? clubId : undefined,
      position: r.Position, jersey: int(r['Jersey Number']), height: r.Height || undefined,
      weight: r.Weight || undefined, foot: r['Preferred Foot'] || undefined, value: r.Value || undefined,
      wage: r.Wage || undefined, skills,
    };
  });
  dropForeignNamesakes(players);

  return { matches, players, teams, rowCounts };
}

/**
 * The same fixture appears in several files. League fixtures are unique per
 * (competition, season, home, away); cup ties can repeat, so those must also
 * be within two days of each other. Rows from the same file are never merged.
 */
function dedupe(raw: RawMatch[], teams: TeamRegistry): Match[] {
  const out: Match[] = [];
  const index = new Map<string, Match[]>();
  const isCup = (c: Competition) => c === COMPETITIONS.cup || c === COMPETITIONS.libertadores;
  for (const r of raw) {
    const { source, home, away, ...rest } = r;
    const m: Match = { ...rest, home: teams.idOf(home), away: teams.idOf(away), sources: [source] };
    // The cup file has a couple of corrupt rows where a team "plays itself".
    if (m.home === m.away) continue;
    const key = `${m.competition}|${isCup(m.competition) ? '' : m.season}|${m.home}|${m.away}`;
    const bucket = index.get(key) ?? [];
    let dup = bucket.find(
      (o) => !o.sources.includes(source) && (!isCup(m.competition) || dayDiff(o.date, m.date) <= 2),
    );
    // The extended file occasionally lists a league fixture with home and away swapped.
    dup ??= index
      .get(`${m.competition}|${isCup(m.competition) ? '' : m.season}|${m.away}|${m.home}`)
      ?.find(
        (o) =>
          !o.sources.includes(source) && dayDiff(o.date, m.date) <= 2 && o.homeGoals === m.awayGoals &&
          o.awayGoals === m.homeGoals,
      );
    if (dup) {
      dup.sources.push(source);
      dup.time ??= m.time;
      dup.round ??= m.round;
      dup.stage ??= m.stage;
      dup.arena ??= m.arena;
      dup.stats ??= m.stats;
    } else {
      out.push(m);
      bucket.push(m);
      index.set(key, bucket);
    }
  }
  return out;
}

/**
 * The Copa do Brasil files carry no stage. The final is the last tie of the
 * season: the closing match plus the other leg between the same two teams.
 */
function markCupFinals(sorted: Match[]) {
  const bySeason = new Map<number, Match[]>();
  for (const m of sorted) {
    if (m.competition !== COMPETITIONS.cup) continue;
    bySeason.set(m.season, [...(bySeason.get(m.season) ?? []), m]);
  }
  for (const ms of bySeason.values()) {
    const last = ms[ms.length - 1];
    // A final is played late in the year (the 2020 one slipped to March 2021);
    // anything earlier means the season's data stops before the final.
    const month = Number(last.date.slice(5, 7));
    if (month < 7 && Number(last.date.slice(0, 4)) === last.season) continue;
    for (const m of ms) {
      const samePair = (m.home === last.home && m.away === last.away) || (m.home === last.away && m.away === last.home);
      if (samePair && dayDiff(m.date, last.date) <= 30) m.stage = 'final';
    }
  }
}

/**
 * The extended file tags a few lower-league games as "Serie A". Where the two
 * dedicated Série A files cover a season, they define who took part in it.
 */
function dropMislabelled(matches: Match[]): Match[] {
  const participants = new Map<number, Set<string>>();
  for (const m of matches) {
    if (m.competition !== COMPETITIONS.serieA || m.sources[0] === FILES.extended) continue;
    const set = participants.get(m.season) ?? new Set();
    participants.set(m.season, set.add(m.home).add(m.away));
  }
  // A league fixture happens once per season, so a second copy is a stray row.
  const fixture = (m: Match) => `${m.season}|${m.home}|${m.away}`;
  const seen = new Set<string>();
  for (const m of matches) {
    if (m.competition === COMPETITIONS.serieA && m.sources.length > 1) seen.add(fixture(m));
  }
  return matches.filter((m) => {
    if (m.competition !== COMPETITIONS.serieA || m.sources[0] !== FILES.extended) return true;
    const set = participants.get(m.season);
    return !set || (set.has(m.home) && set.has(m.away) && !seen.has(fixture(m)));
  });
}

function dayDiff(a: string, b: string): number {
  return Math.abs(Date.parse(a) - Date.parse(b)) / 86_400_000;
}

/**
 * A FIFA club whose name collides with a Brazilian team (e.g. Portugal's
 * "Boavista FC") is only treated as that team when its squad is mostly Brazilian.
 */
function dropForeignNamesakes(players: Player[]) {
  const tally = new Map<string, { total: number; br: number }>();
  for (const p of players) {
    if (!p.clubId) continue;
    const t = tally.get(p.club) ?? { total: 0, br: 0 };
    t.total++;
    if (p.nationality === 'Brazil') t.br++;
    tally.set(p.club, t);
  }
  for (const p of players) {
    const t = p.clubId ? tally.get(p.club) : undefined;
    if (t && t.br * 2 <= t.total) p.clubId = undefined;
  }
}
