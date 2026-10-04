/**
 * Loads the six Kaggle CSV files into one in-memory knowledge graph:
 *
 *   Team  --plays-->  Match  --in-->  Competition/Season
 *   Player --member of--> Club (linked to Team when it is a Brazilian club)
 *
 * All match files are mapped onto a single Match shape. The same fixture often
 * appears in several files (e.g. 2012-2019 Série A is in three of them), so
 * matches are de-duplicated: the first source in priority order is canonical,
 * later copies are flagged with `duplicateOf` and contribute any extra
 * statistics (corners/shots/attacks, stadium) to the canonical record.
 */

import { readFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import { parseCsv, type CsvRow } from "./csv.js";
import { parseDate, daysBetween } from "./dates.js";
import { parseTeamName, CLUB_BY_KEY, type ClubInfo } from "./teams.js";

export type CompetitionId = "brasileirao" | "serie-b" | "serie-c" | "copa-do-brasil" | "libertadores";

export const COMPETITION_NAMES: Record<CompetitionId, string> = {
  brasileirao: "Brasileirão Série A",
  "serie-b": "Brasileirão Série B",
  "serie-c": "Brasileirão Série C",
  "copa-do-brasil": "Copa do Brasil",
  libertadores: "Copa Libertadores",
};

export type SourceId =
  | "Brasileirao_Matches.csv"
  | "Brazilian_Cup_Matches.csv"
  | "Libertadores_Matches.csv"
  | "novo_campeonato_brasileiro.csv"
  | "BR-Football-Dataset.csv"
  | "fifa_data.csv";

export const MATCH_SOURCES: SourceId[] = [
  "Brasileirao_Matches.csv",
  "Brazilian_Cup_Matches.csv",
  "Libertadores_Matches.csv",
  "novo_campeonato_brasileiro.csv",
  "BR-Football-Dataset.csv",
];

export interface MatchStats {
  homeCorners?: number;
  awayCorners?: number;
  homeAttacks?: number;
  awayAttacks?: number;
  homeShots?: number;
  awayShots?: number;
}

export interface Match {
  id: string;
  source: SourceId;
  competition: CompetitionId;
  season: number;
  /** ISO date (YYYY-MM-DD); null if the source had no usable date. */
  date: string | null;
  time?: string;
  round?: string;
  stage?: string;
  home: string;
  away: string;
  homeName: string;
  awayName: string;
  homeGoals: number;
  awayGoals: number;
  stadium?: string;
  stats?: MatchStats;
  /** Set when this row is a copy of a match already loaded from a higher-priority file. */
  duplicateOf?: string;
}

export interface Team {
  key: string;
  name: string;
  state?: string;
  club?: ClubInfo;
  rawNames: Set<string>;
}

export interface Player {
  id: number;
  name: string;
  age?: number;
  nationality: string;
  overall?: number;
  potential?: number;
  club: string;
  /** Team key when the club is one of the curated Brazilian clubs. */
  clubKey?: string;
  position: string;
  jerseyNumber?: number;
  height?: string;
  weight?: string;
  value?: string;
  wage?: string;
  preferredFoot?: string;
  joined?: string;
  loanedFrom?: string;
  contractValidUntil?: string;
  skills: Record<string, number>;
}

export interface Dataset {
  matches: Match[];
  /** Matches without duplicates - the default population for all queries. */
  canonical: Match[];
  teams: Map<string, Team>;
  players: Player[];
  stats: {
    rowsPerSource: Record<string, number>;
    duplicatesPerSource: Record<string, number>;
    loadMs: number;
  };
}

export const SKILL_COLUMNS = [
  "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys", "Dribbling", "Curve",
  "FKAccuracy", "LongPassing", "BallControl", "Acceleration", "SprintSpeed", "Agility", "Reactions",
  "Balance", "ShotPower", "Jumping", "Stamina", "Strength", "LongShots", "Aggression", "Interceptions",
  "Positioning", "Vision", "Penalties", "Composure", "Marking", "StandingTackle", "SlidingTackle",
  "GKDiving", "GKHandling", "GKKicking", "GKPositioning", "GKReflexes",
];

export function defaultDataDir(): string {
  const here = dirname(fileURLToPath(import.meta.url));
  // Works from both src/ (tsx/vitest) and dist/ (compiled).
  return join(here, "..", "data", "kaggle");
}

const num = (s: string | undefined): number | undefined => {
  if (s === undefined) return undefined;
  const t = s.trim();
  if (t === "" || t.toUpperCase() === "NA" || t === "-") return undefined;
  const n = Number(t);
  return Number.isFinite(n) ? n : undefined;
};

function displayScore(name: string): number {
  let score = 0;
  if (/[^\x00-\x7f]/.test(name)) score += 2;
  if (/\./.test(name)) score -= 3;
  if (/\b(FC|EC|SC)\b/.test(name)) score -= 1;
  return score;
}

class Loader {
  matches: Match[] = [];
  teams = new Map<string, Team>();
  rowsPerSource: Record<string, number> = {};
  duplicatesPerSource: Record<string, number> = {};

  team(raw: string): { key: string; name: string } {
    const parsed = parseTeamName(raw);
    let team = this.teams.get(parsed.key);
    if (!team) {
      team = {
        key: parsed.key,
        name: parsed.club?.name ?? parsed.displayBase,
        state: parsed.state,
        club: parsed.club,
        rawNames: new Set(),
      };
      this.teams.set(parsed.key, team);
    }
    // Prefer accented, punctuation-free spellings for display ("Grêmio" over "Gremio", "ABC" over "A.b.c.").
    if (!team.club && displayScore(parsed.displayBase) > displayScore(team.name)) team.name = parsed.displayBase;
    team.rawNames.add(raw.trim());
    return { key: parsed.key, name: raw.trim() };
  }

  add(m: Omit<Match, "id">): void {
    const id = `${m.source.replace(/\.csv$/, "")}#${++this.counter}`;
    this.rowsPerSource[m.source] = (this.rowsPerSource[m.source] ?? 0) + 1;
    this.matches.push({ ...m, id });
  }

  /** Flag cross-file copies of the same fixture (same competition, teams and date +/- 3 days). */
  dedupe(): void {
    const fixtureIndex = new Map<string, Match[]>();
    for (const match of this.matches) {
      const fk = `${match.competition}|${match.home}|${match.away}`;
      const existing = fixtureIndex.get(fk) ?? [];
      const dup = existing.find(
        (e) =>
          e.source !== match.source &&
          (e.date && match.date ? daysBetween(e.date, match.date) <= 3 : e.season === match.season),
      );
      if (dup) {
        match.duplicateOf = dup.id;
        this.duplicatesPerSource[match.source] = (this.duplicatesPerSource[match.source] ?? 0) + 1;
        if (match.stats && !dup.stats) dup.stats = match.stats;
        if (match.stadium && !dup.stadium) dup.stadium = match.stadium;
      } else {
        existing.push(match);
        fixtureIndex.set(fk, existing);
      }
    }
  }
  private counter = 0;

  /**
   * Minor clubs are sometimes written with a state ("Ypiranga RS") and
   * sometimes without ("Ypiranga"). When a bare key has exactly one stated
   * variant, fold the bare key into it.
   */
  mergeStatelessVariants(): void {
    const variants = new Map<string, string[]>();
    for (const key of this.teams.keys()) {
      const m = /^(.*)-([a-z]{2})$/.exec(key);
      if (m && !CLUB_BY_KEY.has(key)) {
        const list = variants.get(m[1]) ?? [];
        list.push(key);
        variants.set(m[1], list);
      }
    }
    // Foreign Libertadores clubs ("River Plate", "Peñarol") must not be folded into
    // Brazilian namesakes ("River Plate - SE", "Penarol - AM").
    const foreign = new Set<string>();
    for (const m of this.matches) if (m.competition === "libertadores") foreign.add(m.home).add(m.away);
    const remap = new Map<string, string>();
    for (const [bare, stated] of variants) {
      if (stated.length === 1 && this.teams.has(bare) && !CLUB_BY_KEY.has(bare) && !foreign.has(bare)) {
        remap.set(bare, stated[0]);
      }
    }
    if (remap.size === 0) return;
    for (const [from, to] of remap) {
      const src = this.teams.get(from)!;
      const dst = this.teams.get(to)!;
      for (const r of src.rawNames) dst.rawNames.add(r);
      this.teams.delete(from);
    }
    for (const m of this.matches) {
      m.home = remap.get(m.home) ?? m.home;
      m.away = remap.get(m.away) ?? m.away;
    }
  }
}

function seasonFromBrFootball(date: string, competition: CompetitionId): number {
  const year = Number(date.slice(0, 4));
  // The 2020 seasons were delayed by COVID-19 and finished in early 2021.
  if (year === 2021) {
    const cutoff = competition === "copa-do-brasil" ? "2021-03-08" : "2021-03-01";
    if (date < cutoff) return 2020;
  }
  return year;
}

const BR_FOOTBALL_COMPETITIONS: Record<string, CompetitionId> = {
  "Serie A": "brasileirao",
  "Serie B": "serie-b",
  "Serie C": "serie-c",
  "Copa do Brasil": "copa-do-brasil",
};

function loadMatches(loader: Loader, read: (f: SourceId) => CsvRow[]): void {
  // Order matters: earlier sources are canonical when fixtures overlap.
  for (const r of read("Brasileirao_Matches.csv")) {
    const d = parseDate(r.datetime);
    const hg = num(r.home_goal), ag = num(r.away_goal), season = num(r.season);
    if (hg === undefined || ag === undefined || season === undefined) continue;
    const h = loader.team(r.home_team), a = loader.team(r.away_team);
    loader.add({
      source: "Brasileirao_Matches.csv", competition: "brasileirao", season,
      date: d?.date ?? null, time: d?.time, round: r.round || undefined,
      home: h.key, away: a.key, homeName: h.name, awayName: a.name, homeGoals: hg, awayGoals: ag,
    });
  }

  for (const r of read("Brazilian_Cup_Matches.csv")) {
    const d = parseDate(r.datetime);
    const hg = num(r.home_goal), ag = num(r.away_goal), season = num(r.season);
    if (hg === undefined || ag === undefined || season === undefined) continue;
    const h = loader.team(r.home_team), a = loader.team(r.away_team);
    loader.add({
      source: "Brazilian_Cup_Matches.csv", competition: "copa-do-brasil", season,
      date: d?.date ?? null, time: d?.time, round: r.round || undefined,
      home: h.key, away: a.key, homeName: h.name, awayName: a.name, homeGoals: hg, awayGoals: ag,
    });
  }

  for (const r of read("Libertadores_Matches.csv")) {
    const d = parseDate(r.datetime);
    const hg = num(r.home_goal), ag = num(r.away_goal), season = num(r.season);
    if (hg === undefined || ag === undefined || season === undefined) continue;
    const h = loader.team(r.home_team), a = loader.team(r.away_team);
    loader.add({
      source: "Libertadores_Matches.csv", competition: "libertadores", season,
      date: d?.date ?? null, time: d?.time, stage: r.stage || undefined,
      home: h.key, away: a.key, homeName: h.name, awayName: a.name, homeGoals: hg, awayGoals: ag,
    });
  }

  for (const r of read("novo_campeonato_brasileiro.csv")) {
    const d = parseDate(r.Data);
    const hg = num(r.Gols_mandante), ag = num(r.Gols_visitante), season = num(r.Ano);
    if (hg === undefined || ag === undefined || season === undefined) continue;
    // The *_UF columns are unreliable (e.g. Bahia is tagged "BH", Vitória "ES"),
    // so rely on the team names, which already disambiguate (e.g. "Botafogo-RJ").
    const h = loader.team(r.Equipe_mandante), a = loader.team(r.Equipe_visitante);
    loader.add({
      source: "novo_campeonato_brasileiro.csv", competition: "brasileirao", season,
      date: d?.date ?? null, round: r.Rodada || undefined, stadium: r.Arena?.trim() || undefined,
      home: h.key, away: a.key, homeName: r.Equipe_mandante, awayName: r.Equipe_visitante, homeGoals: hg, awayGoals: ag,
    });
  }

  for (const r of read("BR-Football-Dataset.csv")) {
    const competition = BR_FOOTBALL_COMPETITIONS[r.tournament];
    const d = parseDate(r.date);
    const hg = num(r.home_goal), ag = num(r.away_goal);
    if (!competition || !d || hg === undefined || ag === undefined) continue;
    const h = loader.team(r.home), a = loader.team(r.away);
    loader.add({
      source: "BR-Football-Dataset.csv", competition, season: seasonFromBrFootball(d.date, competition),
      date: d.date, time: r.time ? r.time.slice(0, 5) : undefined,
      home: h.key, away: a.key, homeName: h.name, awayName: a.name, homeGoals: hg, awayGoals: ag,
      stats: {
        homeCorners: num(r.home_corner), awayCorners: num(r.away_corner),
        homeAttacks: num(r.home_attack), awayAttacks: num(r.away_attack),
        homeShots: num(r.home_shots), awayShots: num(r.away_shots),
      },
    });
  }
}

function loadPlayers(rows: CsvRow[]): Player[] {
  const players: Player[] = [];
  for (const r of rows) {
    const id = num(r.ID);
    if (id === undefined || !r.Name) continue;
    const club = (r.Club ?? "").trim();
    const parsed = club ? parseTeamName(club) : undefined;
    const skills: Record<string, number> = {};
    for (const c of SKILL_COLUMNS) {
      const v = num(r[c]);
      if (v !== undefined) skills[c] = v;
    }
    players.push({
      id,
      name: r.Name.trim(),
      age: num(r.Age),
      nationality: (r.Nationality ?? "").trim(),
      overall: num(r.Overall),
      potential: num(r.Potential),
      club,
      clubKey: parsed?.club?.key,
      position: (r.Position ?? "").trim(),
      jerseyNumber: num(r["Jersey Number"]),
      height: r.Height || undefined,
      weight: r.Weight || undefined,
      value: r.Value || undefined,
      wage: r.Wage || undefined,
      preferredFoot: r["Preferred Foot"] || undefined,
      joined: r.Joined || undefined,
      loanedFrom: r["Loaned From"] || undefined,
      contractValidUntil: r["Contract Valid Until"] || undefined,
      skills,
    });
  }
  return players;
}

export function loadDataset(dataDir: string = defaultDataDir()): Dataset {
  const t0 = performance.now();
  const read = (f: SourceId) => parseCsv(readFileSync(join(dataDir, f), "utf8"));
  const loader = new Loader();
  loadMatches(loader, read);
  loader.mergeStatelessVariants();
  loader.dedupe();
  const players = loadPlayers(read("fifa_data.csv"));
  loader.rowsPerSource["fifa_data.csv"] = players.length;
  return {
    matches: loader.matches,
    canonical: loader.matches.filter((m) => !m.duplicateOf),
    teams: loader.teams,
    players,
    stats: {
      rowsPerSource: loader.rowsPerSource,
      duplicatesPerSource: loader.duplicatesPerSource,
      loadMs: performance.now() - t0,
    },
  };
}
