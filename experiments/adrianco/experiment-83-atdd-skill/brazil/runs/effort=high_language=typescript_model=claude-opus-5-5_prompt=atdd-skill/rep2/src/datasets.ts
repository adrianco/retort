/**
 * Loads the six Kaggle datasets from a directory into one de-duplicated set
 * of matches plus the FIFA player list.
 *
 * The same Brasileirão match can appear in up to three files, so a match is
 * only added once: a record from a different file with the same competition,
 * home and away team within three days of one already loaded is merged into
 * it (contributing extra details such as corners, shots or the stadium).
 */
import { existsSync, readFileSync } from 'node:fs';
import path from 'node:path';
import { parse } from 'csv-parse/sync';
import { type CompetitionId } from './competitions.js';
import { daysBetween, parseDate } from './dates.js';
import type { DatasetInfo, Match, MatchStats, Player } from './model.js';
import { TeamRegistry, identifyTeam } from './teams.js';

type Row = Record<string, string>;

interface RawMatch {
  competition: CompetitionId;
  season?: number;
  date: string;
  time?: string;
  round?: number;
  stage?: string;
  home: string;
  away: string;
  homeGoals: number;
  awayGoals: number;
  arena?: string;
  stats?: MatchStats;
}

interface DatasetDefinition {
  file: string;
  description: string;
  toMatch?: (row: Row) => RawMatch | null;
}

function number(value: string | undefined): number | undefined {
  if (value === undefined || value.trim() === '' || value.trim() === 'NA') return undefined;
  const n = Number(value);
  return Number.isFinite(n) ? n : undefined;
}

function goals(value: string | undefined): number | null {
  const n = number(value);
  return n === undefined ? null : Math.round(n);
}

function played(raw: Omit<RawMatch, 'homeGoals' | 'awayGoals'>, home: string | undefined, away: string | undefined): RawMatch | null {
  const h = goals(home);
  const a = goals(away);
  if (h === null || a === null || !raw.home?.trim() || !raw.away?.trim()) return null;
  return { ...raw, homeGoals: h, awayGoals: a };
}

const EXTENDED_TOURNAMENTS: Record<string, CompetitionId> = {
  'Serie A': 'serie-a',
  'Serie B': 'serie-b',
  'Serie C': 'serie-c',
  'Copa do Brasil': 'copa-do-brasil',
};

export const MATCH_DATASETS: DatasetDefinition[] = [
  {
    file: 'Brasileirao_Matches.csv',
    description: 'Brasileirão Série A matches 2012-2022',
    toMatch: (r) => {
      const d = parseDate(r.datetime);
      if (!d) return null;
      return played(
        { competition: 'serie-a', season: number(r.season), date: d.date, time: d.time, round: number(r.round), home: r.home_team, away: r.away_team },
        r.home_goal,
        r.away_goal,
      );
    },
  },
  {
    file: 'novo_campeonato_brasileiro.csv',
    description: 'Historical Brasileirão Série A matches 2003-2019',
    toMatch: (r) => {
      const d = parseDate(r.Data);
      if (!d) return null;
      return played(
        { competition: 'serie-a', season: number(r.Ano), date: d.date, round: number(r.Rodada), home: r.Equipe_mandante, away: r.Equipe_visitante, arena: r.Arena || undefined },
        r.Gols_mandante,
        r.Gols_visitante,
      );
    },
  },
  {
    file: 'Brazilian_Cup_Matches.csv',
    description: 'Copa do Brasil matches 2012-2021',
    toMatch: (r) => {
      const d = parseDate(r.datetime);
      if (!d) return null;
      return played(
        { competition: 'copa-do-brasil', season: number(r.season), date: d.date, time: d.time, round: number(r.round), home: r.home_team, away: r.away_team },
        r.home_goal,
        r.away_goal,
      );
    },
  },
  {
    file: 'Libertadores_Matches.csv',
    description: 'Copa Libertadores matches 2013-2022',
    toMatch: (r) => {
      const d = parseDate(r.datetime);
      if (!d) return null;
      return played(
        { competition: 'libertadores', season: number(r.season), date: d.date, time: d.time, stage: r.stage?.trim() || undefined, home: r.home_team, away: r.away_team },
        r.home_goal,
        r.away_goal,
      );
    },
  },
  {
    file: 'BR-Football-Dataset.csv',
    description: 'Brazilian league and cup matches 2014-2023 with corners, shots and attacks',
    toMatch: (r) => {
      const d = parseDate(r.date);
      const competition = EXTENDED_TOURNAMENTS[r.tournament?.trim()];
      if (!d || !competition) return null;
      return played(
        {
          competition,
          date: d.date,
          time: r.time?.slice(0, 5) || undefined,
          home: r.home,
          away: r.away,
          stats: {
            homeCorners: number(r.home_corner),
            awayCorners: number(r.away_corner),
            homeShots: number(r.home_shots),
            awayShots: number(r.away_shots),
            homeAttacks: number(r.home_attack),
            awayAttacks: number(r.away_attack),
          },
        },
        r.home_goal,
        r.away_goal,
      );
    },
  },
];

export const PLAYER_DATASET = { file: 'fifa_data.csv', description: 'FIFA 19 player database' };

const ATTRIBUTE_COLUMNS = [
  'Crossing', 'Finishing', 'HeadingAccuracy', 'ShortPassing', 'Volleys', 'Dribbling', 'Curve', 'FKAccuracy',
  'LongPassing', 'BallControl', 'Acceleration', 'SprintSpeed', 'Agility', 'Reactions', 'Balance', 'ShotPower',
  'Jumping', 'Stamina', 'Strength', 'LongShots', 'Aggression', 'Interceptions', 'Positioning', 'Vision',
  'Penalties', 'Composure', 'Marking', 'StandingTackle', 'SlidingTackle', 'GKDiving', 'GKHandling', 'GKKicking',
  'GKPositioning', 'GKReflexes',
];

function readRows(dir: string, file: string): Row[] | null {
  const full = path.join(dir, file);
  if (!existsSync(full)) return null;
  return parse(readFileSync(full, 'utf8'), {
    columns: true,
    bom: true,
    skip_empty_lines: true,
    relax_column_count: true,
    relax_quotes: true,
  }) as Row[];
}

/** League seasons occasionally ran into the next year (the 2020 Brasileirão finished in February 2021). */
function inferSeason(raw: RawMatch): number {
  const year = Number(raw.date.slice(0, 4));
  const month = Number(raw.date.slice(5, 7));
  const league = raw.competition === 'serie-a' || raw.competition === 'serie-b' || raw.competition === 'serie-c';
  return league && month <= 3 ? year - 1 : year;
}

export interface LoadedData {
  matches: Match[];
  players: Player[];
  datasets: DatasetInfo[];
  teams: TeamRegistry;
}

export function loadDatasets(dir: string): LoadedData {
  const teams = new TeamRegistry();
  const matches: Match[] = [];
  const index = new Map<string, Match[]>();
  const datasets: DatasetInfo[] = [];

  for (const def of MATCH_DATASETS) {
    const rows = readRows(dir, def.file);
    datasets.push({ file: def.file, description: def.description, records: rows?.length ?? 0, loaded: rows !== null });
    for (const row of rows ?? []) {
      const raw = def.toMatch!(row);
      if (!raw) continue;
      const homeKey = teams.register(raw.home);
      const awayKey = teams.register(raw.away);
      const key = `${raw.competition}|${homeKey}|${awayKey}`;
      const candidates = index.get(key) ?? [];
      const duplicate = candidates.find((m) => !m.sources.includes(def.file) && daysBetween(m.date, raw.date) <= 3);
      if (duplicate) {
        duplicate.sources.push(def.file);
        duplicate.stats ??= raw.stats;
        duplicate.arena ??= raw.arena;
        duplicate.round ??= raw.round;
        duplicate.time ??= raw.time;
        continue;
      }
      const match: Match = {
        competition: raw.competition,
        season: raw.season ?? inferSeason(raw),
        date: raw.date,
        time: raw.time,
        round: raw.round,
        stage: raw.stage,
        homeKey,
        awayKey,
        homeGoals: raw.homeGoals,
        awayGoals: raw.awayGoals,
        arena: raw.arena,
        stats: raw.stats,
        sources: [def.file],
      };
      candidates.push(match);
      index.set(key, candidates);
      matches.push(match);
    }
  }

  labelCupStages(matches);

  const playerRows = readRows(dir, PLAYER_DATASET.file);
  datasets.push({ ...PLAYER_DATASET, records: playerRows?.length ?? 0, loaded: playerRows !== null });
  const players = (playerRows ?? []).map(toPlayer).filter((p): p is Player => p !== null);

  return { matches, players, datasets, teams };
}

/**
 * The Copa do Brasil file only numbers its rounds. When a season's last round
 * is a single two-legged tie, that round is the final and the rounds before
 * it are the semi-finals, quarter-finals and round of 16.
 */
function labelCupStages(matches: Match[]): void {
  const KNOCKOUT = ['final', 'semifinals', 'quarterfinals', 'round of 16'];
  const bySeason = new Map<number, Match[]>();
  for (const m of matches) {
    if (m.competition !== 'copa-do-brasil' || m.round === undefined) continue;
    bySeason.set(m.season, [...(bySeason.get(m.season) ?? []), m]);
  }
  for (const seasonMatches of bySeason.values()) {
    const lastRound = Math.max(...seasonMatches.map((m) => m.round!));
    const inLastRound = seasonMatches.filter((m) => m.round === lastRound).length;
    if (lastRound < 4 || inLastRound > 2) continue;
    for (const m of seasonMatches) {
      const stage = KNOCKOUT[lastRound - m.round!];
      if (stage) m.stage = stage;
    }
  }
}

function toPlayer(r: Row): Player | null {
  const name = r.Name?.trim();
  const overall = number(r.Overall);
  if (!name || overall === undefined) return null;
  const club = r.Club?.trim() ?? '';
  const attributes: Record<string, number> = {};
  for (const column of ATTRIBUTE_COLUMNS) {
    const value = number(r[column]);
    if (value !== undefined) attributes[column] = value;
  }
  return {
    id: number(r.ID) ?? 0,
    name,
    age: number(r.Age),
    nationality: r.Nationality?.trim() ?? '',
    overall,
    potential: number(r.Potential),
    club,
    clubKey: club ? identifyTeam(club).key : '',
    position: r.Position?.trim() ?? '',
    jerseyNumber: number(r['Jersey Number']),
    height: r.Height || undefined,
    weight: r.Weight || undefined,
    value: r.Value || undefined,
    wage: r.Wage || undefined,
    preferredFoot: r['Preferred Foot'] || undefined,
    contractValidUntil: r['Contract Valid Until'] || undefined,
    attributes,
  };
}
