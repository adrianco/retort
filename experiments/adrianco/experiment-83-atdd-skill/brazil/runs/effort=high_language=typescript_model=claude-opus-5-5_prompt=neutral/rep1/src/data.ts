/**
 * Dataset loading.
 *
 * Reads the six Kaggle CSV files, normalises team names and dates, and builds
 * an in-memory "knowledge graph":
 *   Team  --played-->  Match  <--in-- Competition/Season
 *   Player --plays-for--> Club (linked to Team when the club is Brazilian)
 *
 * Several files cover the same matches (e.g. Série A 2012-2019 appears in
 * three files). Matches are merged so every real fixture is counted once;
 * secondary sources enrich the primary record (arena, round, shots/corners)
 * and the list of contributing files is kept in `sources`.
 */
import { existsSync } from "node:fs";
import { join, resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { readCsvFile } from "./csv.js";
import { daysBetween, foldText, parseDate, parseIntOrNull, parseNum } from "./normalize.js";
import { TeamRegistry, type Team } from "./teams.js";

export type Competition = "serie-a" | "serie-b" | "serie-c" | "copa-do-brasil" | "libertadores";

export const COMPETITIONS: Record<Competition, string> = {
  "serie-a": "Brasileirão Série A",
  "serie-b": "Brasileirão Série B",
  "serie-c": "Brasileirão Série C",
  "copa-do-brasil": "Copa do Brasil",
  libertadores: "Copa Libertadores",
};

export const LEAGUES: Competition[] = ["serie-a", "serie-b", "serie-c"];

export const FILES = {
  brasileirao: "Brasileirao_Matches.csv",
  cup: "Brazilian_Cup_Matches.csv",
  libertadores: "Libertadores_Matches.csv",
  brFootball: "BR-Football-Dataset.csv",
  historical: "novo_campeonato_brasileiro.csv",
  fifa: "fifa_data.csv",
} as const;

export interface MatchStats {
  homeCorners: number | null;
  awayCorners: number | null;
  homeAttacks: number | null;
  awayAttacks: number | null;
  homeShots: number | null;
  awayShots: number | null;
}

export interface Match {
  id: number;
  competition: Competition;
  season: number;
  /** ISO date YYYY-MM-DD */
  date: string;
  time?: string;
  round?: number;
  /** Libertadores stage or Copa do Brasil round label */
  stage?: string;
  homeId: string;
  awayId: string;
  homeGoals: number;
  awayGoals: number;
  arena?: string;
  stats?: MatchStats;
  /** CSV files that contain this match */
  sources: string[];
}

export interface Player {
  id: number;
  name: string;
  age: number | null;
  nationality: string;
  overall: number | null;
  potential: number | null;
  club: string;
  /** Canonical team id when the club is a Brazilian club present in match data */
  teamId?: string;
  position: string;
  jerseyNumber: number | null;
  height: string;
  weight: string;
  preferredFoot: string;
  value: string;
  wage: string;
  /** All remaining numeric attributes (Crossing, Finishing, ...) */
  skills: Record<string, number>;
  /** folded name for searching */
  searchName: string;
}

export interface SourceInfo {
  file: string;
  rows: number;
  loaded: number;
  skipped: number;
}

export interface Dataset {
  matches: Match[];
  players: Player[];
  teams: TeamRegistry;
  sources: SourceInfo[];
  /** Brazilian club names in the FIFA file */
  brazilianClubs: Set<string>;
  loadMs: number;
}

interface RawMatch {
  competition: Competition;
  season: number;
  date: string;
  time?: string;
  round?: number;
  stage?: string;
  home: string;
  away: string;
  origin: "domestic" | "international";
  homeGoals: number;
  awayGoals: number;
  arena?: string;
  stats?: MatchStats;
  source: string;
}

const SKILL_COLUMNS = [
  "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys", "Dribbling", "Curve",
  "FKAccuracy", "LongPassing", "BallControl", "Acceleration", "SprintSpeed", "Agility", "Reactions",
  "Balance", "ShotPower", "Jumping", "Stamina", "Strength", "LongShots", "Aggression", "Interceptions",
  "Positioning", "Vision", "Penalties", "Composure", "Marking", "StandingTackle", "SlidingTackle",
  "GKDiving", "GKHandling", "GKKicking", "GKPositioning", "GKReflexes",
  "International Reputation", "Weak Foot", "Skill Moves",
];

export function defaultDataDir(): string {
  const candidates = [
    process.env.BRAZIL_SOCCER_DATA_DIR,
    resolve(process.cwd(), "data/kaggle"),
    resolve(dirname(fileURLToPath(import.meta.url)), "../data/kaggle"),
  ].filter((p): p is string => !!p);
  for (const c of candidates) if (existsSync(join(c, FILES.fifa))) return c;
  return candidates[candidates.length - 1];
}

function mapTournament(t: string): Competition | null {
  const f = foldText(t);
  if (f === "serie a") return "serie-a";
  if (f === "serie b") return "serie-b";
  if (f === "serie c") return "serie-c";
  if (f.includes("copa do brasil")) return "copa-do-brasil";
  if (f.includes("libertadores")) return "libertadores";
  return null;
}

function loadRawMatches(dir: string, sources: SourceInfo[]): RawMatch[] {
  const out: RawMatch[] = [];
  const track = (file: string, rows: number, before: number) => {
    const loaded = out.length - before;
    sources.push({ file, rows, loaded, skipped: rows - loaded });
  };

  // Load order defines merge priority (first wins, later ones enrich).

  // 1. Brasileirao_Matches.csv (Série A 2012-2022, with rounds)
  {
    const rows = readCsvFile(join(dir, FILES.brasileirao));
    const before = out.length;
    for (const r of rows) {
      const d = parseDate(r.datetime);
      const hg = parseIntOrNull(r.home_goal);
      const ag = parseIntOrNull(r.away_goal);
      if (!d || hg === null || ag === null) continue;
      out.push({
        competition: "serie-a",
        season: parseIntOrNull(r.season) ?? +d.date.slice(0, 4),
        date: d.date,
        time: d.time,
        round: parseIntOrNull(r.round) ?? undefined,
        home: r.home_team,
        away: r.away_team,
        origin: "domestic",
        homeGoals: hg,
        awayGoals: ag,
        source: FILES.brasileirao,
      });
    }
    track(FILES.brasileirao, rows.length, before);
  }

  // 2. novo_campeonato_brasileiro.csv (Série A 2003-2019, with arena)
  {
    const rows = readCsvFile(join(dir, FILES.historical));
    const before = out.length;
    for (const r of rows) {
      const d = parseDate(r.Data);
      const hg = parseIntOrNull(r.Gols_mandante);
      const ag = parseIntOrNull(r.Gols_visitante);
      if (!d || hg === null || ag === null) continue;
      out.push({
        competition: "serie-a",
        season: parseIntOrNull(r.Ano) ?? +d.date.slice(0, 4),
        date: d.date,
        round: parseIntOrNull(r.Rodada) ?? undefined,
        // Ambiguous names already carry a suffix ("Atlético-MG"). The UF
        // columns are not used: they contain errors (e.g. Vitória "ES", Bahia "BH").
        home: r.Equipe_mandante,
        away: r.Equipe_visitante,
        origin: "domestic",
        homeGoals: hg,
        awayGoals: ag,
        arena: r.Arena?.trim() || undefined,
        source: FILES.historical,
      });
    }
    track(FILES.historical, rows.length, before);
  }

  // 3. Brazilian_Cup_Matches.csv (Copa do Brasil 2012-2021)
  {
    const rows = readCsvFile(join(dir, FILES.cup));
    const before = out.length;
    for (const r of rows) {
      const d = parseDate(r.datetime);
      const hg = parseIntOrNull(r.home_goal);
      const ag = parseIntOrNull(r.away_goal);
      if (!d || hg === null || ag === null) continue;
      out.push({
        competition: "copa-do-brasil",
        season: parseIntOrNull(r.season) ?? +d.date.slice(0, 4),
        date: d.date,
        time: d.time,
        round: parseIntOrNull(r.round) ?? undefined,
        home: r.home_team,
        away: r.away_team,
        origin: "domestic",
        homeGoals: hg,
        awayGoals: ag,
        source: FILES.cup,
      });
    }
    track(FILES.cup, rows.length, before);
  }

  // 4. Libertadores_Matches.csv (2013-2022)
  {
    const rows = readCsvFile(join(dir, FILES.libertadores));
    const before = out.length;
    for (const r of rows) {
      const d = parseDate(r.datetime);
      const hg = parseIntOrNull(r.home_goal);
      const ag = parseIntOrNull(r.away_goal);
      if (!d || hg === null || ag === null) continue; // e.g. unplayed 2022 final ("NA", "-")
      out.push({
        competition: "libertadores",
        season: parseIntOrNull(r.season) ?? +d.date.slice(0, 4),
        date: d.date,
        time: d.time,
        stage: r.stage?.trim() || undefined,
        home: r.home_team,
        away: r.away_team,
        origin: "international",
        homeGoals: hg,
        awayGoals: ag,
        source: FILES.libertadores,
      });
    }
    track(FILES.libertadores, rows.length, before);
  }

  // 5. BR-Football-Dataset.csv (Série A/B/C + Copa do Brasil 2014-2023, with stats)
  {
    const rows = readCsvFile(join(dir, FILES.brFootball));
    const before = out.length;
    for (const r of rows) {
      const comp = mapTournament(r.tournament);
      const d = parseDate(r.date);
      const hg = parseIntOrNull(r.home_goal);
      const ag = parseIntOrNull(r.away_goal);
      if (!comp || !d || hg === null || ag === null) continue;
      const year = +d.date.slice(0, 4);
      const month = +d.date.slice(5, 7);
      // League seasons that overran into the next calendar year (2020 season
      // finished in Feb 2021 because of COVID) belong to the previous season.
      const season = comp !== "copa-do-brasil" && month <= 3 ? year - 1 : year;
      out.push({
        competition: comp,
        season,
        date: d.date,
        time: parseDate(`${d.date} ${r.time}`)?.time,
        home: r.home,
        away: r.away,
        origin: "domestic",
        homeGoals: hg,
        awayGoals: ag,
        stats: {
          homeCorners: parseNum(r.home_corner),
          awayCorners: parseNum(r.away_corner),
          homeAttacks: parseNum(r.home_attack),
          awayAttacks: parseNum(r.away_attack),
          homeShots: parseNum(r.home_shots),
          awayShots: parseNum(r.away_shots),
        },
        source: FILES.brFootball,
      });
    }
    track(FILES.brFootball, rows.length, before);
  }
  return out;
}

function mergeMatches(raw: RawMatch[], teams: TeamRegistry): Match[] {
  const merged: Match[] = [];
  const leagueIndex = new Map<string, Match>();
  const cupIndex = new Map<string, Match[]>();

  for (const r of raw) {
    const homeId = teams.idFor(r.home, r.origin);
    const awayId = teams.idFor(r.away, r.origin);
    let existing: Match | undefined;
    const isLeague = LEAGUES.includes(r.competition);
    const leagueKey = `${r.competition}|${r.season}|${homeId}|${awayId}`;
    const cupKey = `${r.competition}|${homeId}|${awayId}`;
    if (isLeague) {
      existing = leagueIndex.get(leagueKey);
    } else {
      existing = cupIndex.get(cupKey)?.find((m) => daysBetween(m.date, r.date) <= 3);
    }

    if (existing) {
      if (existing.round === undefined && r.round !== undefined) existing.round = r.round;
      if (!existing.stage && r.stage) existing.stage = r.stage;
      if (!existing.arena && r.arena) existing.arena = r.arena;
      if (!existing.time && r.time) existing.time = r.time;
      if (!existing.stats && r.stats) existing.stats = r.stats;
      if (!existing.sources.includes(r.source)) existing.sources.push(r.source);
      continue;
    }

    const m: Match = {
      id: merged.length + 1,
      competition: r.competition,
      season: r.season,
      date: r.date,
      time: r.time,
      round: r.round,
      stage: r.stage,
      homeId,
      awayId,
      homeGoals: r.homeGoals,
      awayGoals: r.awayGoals,
      arena: r.arena,
      stats: r.stats,
      sources: [r.source],
    };
    merged.push(m);
    if (isLeague) leagueIndex.set(leagueKey, m);
    else {
      const list = cupIndex.get(cupKey) ?? [];
      list.push(m);
      cupIndex.set(cupKey, list);
    }
  }

  // Copa do Brasil rounds are numeric in the source; label the last round of
  // each season as the final when it has a single two-legged tie.
  const cupBySeason = new Map<number, Match[]>();
  for (const m of merged) {
    if (m.competition !== "copa-do-brasil") continue;
    const list = cupBySeason.get(m.season) ?? [];
    list.push(m);
    cupBySeason.set(m.season, list);
  }
  for (const list of cupBySeason.values()) {
    for (const m of list) if (m.round !== undefined) m.stage = `round ${m.round}`;
    const rounds = list.map((m) => m.round).filter((r): r is number => r !== undefined);
    const maxRound = rounds.length ? Math.max(...rounds) : undefined;
    const last = list.filter((m) => m.round === maxRound);
    const pair = new Set(last.flatMap((m) => [m.homeId, m.awayId]));
    if (maxRound !== undefined && last.length <= 2 && pair.size === 2) {
      for (const m of last) m.stage = "final";
    } else {
      // Round info missing or incomplete (seasons only in BR-Football): if the
      // last two matches of the season are between the same pair of clubs and
      // come after every labelled round, they form the final.
      const sorted = [...list].sort((a, b) => a.date.localeCompare(b.date));
      const [a, b] = sorted.slice(-2);
      if (a && b && a.round === undefined && b.round === undefined && new Set([a.homeId, a.awayId, b.homeId, b.awayId]).size === 2) {
        a.stage = "final";
        b.stage = "final";
      }
    }
  }

  // Drop stray league rows whose teams barely appear in that competition
  // season (mislabelled tournament rows in BR-Football-Dataset.csv, e.g. a
  // Brasília vs Taguatinga match tagged "Serie A").
  const appearances = new Map<string, number>();
  const seasonKey = (m: Match, t: string) => `${m.competition}|${m.season}|${t}`;
  for (const m of merged) {
    if (!LEAGUES.includes(m.competition)) continue;
    for (const t of [m.homeId, m.awayId]) appearances.set(seasonKey(m, t), (appearances.get(seasonKey(m, t)) ?? 0) + 1);
  }
  const kept = merged.filter(
    (m) =>
      !LEAGUES.includes(m.competition) ||
      ((appearances.get(seasonKey(m, m.homeId)) ?? 0) > 2 && (appearances.get(seasonKey(m, m.awayId)) ?? 0) > 2),
  );
  merged.length = 0;
  merged.push(...kept);

  merged.sort((a, b) => a.date.localeCompare(b.date) || a.id - b.id);
  merged.forEach((m, i) => (m.id = i + 1));
  return merged;
}

function loadPlayers(dir: string, teams: TeamRegistry, sources: SourceInfo[]): { players: Player[]; brazilianClubs: Set<string> } {
  const rows = readCsvFile(join(dir, FILES.fifa));
  const players: Player[] = [];
  for (const r of rows) {
    const id = parseIntOrNull(r.ID);
    if (id === null || !r.Name) continue;
    const skills: Record<string, number> = {};
    for (const c of SKILL_COLUMNS) {
      const v = parseNum(r[c]);
      if (v !== null) skills[c] = v;
    }
    players.push({
      id,
      name: r.Name.trim(),
      age: parseIntOrNull(r.Age),
      nationality: r.Nationality?.trim() ?? "",
      overall: parseIntOrNull(r.Overall),
      potential: parseIntOrNull(r.Potential),
      club: r.Club?.trim() ?? "",
      position: r.Position?.trim() ?? "",
      jerseyNumber: parseIntOrNull(r["Jersey Number"]),
      height: r.Height?.trim() ?? "",
      weight: r.Weight?.trim() ?? "",
      preferredFoot: r["Preferred Foot"]?.trim() ?? "",
      value: r.Value?.trim() ?? "",
      wage: r.Wage?.trim() ?? "",
      skills,
      searchName: foldText(r.Name),
    });
  }
  sources.push({ file: FILES.fifa, rows: rows.length, loaded: players.length, skipped: rows.length - players.length });

  // A club is treated as Brazilian when most of its squad is Brazilian
  // (FIFA 19 includes 20 Série A clubs, each with an all-Brazilian squad).
  const byClub = new Map<string, { total: number; br: number }>();
  for (const p of players) {
    if (!p.club) continue;
    const s = byClub.get(p.club) ?? { total: 0, br: 0 };
    s.total++;
    if (p.nationality === "Brazil") s.br++;
    byClub.set(p.club, s);
  }
  const brazilianClubs = new Set<string>();
  for (const [club, s] of byClub) if (s.total >= 10 && s.br / s.total >= 0.75) brazilianClubs.add(club);

  // Link Brazilian clubs to match-data teams (cross-file relationship).
  const clubToTeam = new Map<string, string>();
  for (const club of brazilianClubs) {
    const hit = teams.search(club)[0];
    if (hit && hit.known) clubToTeam.set(club, hit.id);
  }
  for (const p of players) {
    const t = clubToTeam.get(p.club);
    if (t) p.teamId = t;
  }
  return { players, brazilianClubs };
}

export function loadDataset(dir: string = defaultDataDir()): Dataset {
  const t0 = performance.now();
  const sources: SourceInfo[] = [];
  const raw = loadRawMatches(dir, sources);
  const teams = new TeamRegistry();
  for (const r of raw) {
    teams.observe(r.home, r.origin);
    teams.observe(r.away, r.origin);
  }
  teams.finalize();
  const matches = mergeMatches(raw, teams);
  const { players, brazilianClubs } = loadPlayers(dir, teams, sources);
  return { matches, players, teams, sources, brazilianClubs, loadMs: performance.now() - t0 };
}

let cached: Dataset | undefined;
/** Lazily loaded singleton dataset. */
export function getDataset(): Dataset {
  if (!cached) cached = loadDataset();
  return cached;
}

export type { Team };
