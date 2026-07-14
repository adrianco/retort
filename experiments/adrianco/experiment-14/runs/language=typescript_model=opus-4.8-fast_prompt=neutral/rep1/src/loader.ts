/**
 * Brazilian Soccer MCP — Dataset loaders
 * --------------------------------------
 * Context: Reads the six provided Kaggle CSV files from `data/kaggle/` and
 * converts each into the normalized `Match` / `Player` model defined in
 * `types.ts`. Each loader knows the quirks of its source file (column names,
 * language, date format, which competition it represents) and delegates all
 * value-cleaning to `normalize.ts`.
 *
 * Parsing uses `csv-parse` in sync mode with `bom: true` so the FIFA file's
 * leading byte-order-mark and its quoted fields containing commas
 * (e.g. "Jul 1, 2004") are handled correctly.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { parse } from "csv-parse/sync";
import type { Competition, Match, Player } from "./types.js";
import { canonicalTeam, parseDate, parseInt0, parseNum } from "./normalize.js";

type Row = Record<string, string>;

function read(dataDir: string, file: string): Row[] {
  const text = readFileSync(join(dataDir, file), "utf8");
  return parse(text, {
    columns: true,
    bom: true,
    skip_empty_lines: true,
    relax_column_count: true,
    trim: true,
  }) as Row[];
}

function makeMatch(
  competition: Competition,
  source: string,
  rawHome: string,
  rawAway: string,
  homeGoals: number | null,
  awayGoals: number | null,
  date: string | null,
  season: number | null,
  extra: Partial<Match> = {},
): Match {
  const home = canonicalTeam(rawHome);
  const away = canonicalTeam(rawAway);
  return {
    competition,
    date,
    season,
    round: extra.round ?? null,
    stage: extra.stage ?? null,
    homeTeam: home.display,
    homeTeamId: home.id,
    awayTeam: away.display,
    awayTeamId: away.id,
    homeGoals,
    awayGoals,
    venue: extra.venue ?? null,
    source,
    stats: extra.stats,
  };
}

/** Brasileirao_Matches.csv — Série A 2012–2022. */
export function loadBrasileirao(dataDir: string): Match[] {
  const file = "Brasileirao_Matches.csv";
  return read(dataDir, file).map((r) =>
    makeMatch(
      "Brasileirão Série A",
      file,
      r.home_team,
      r.away_team,
      parseInt0(r.home_goal),
      parseInt0(r.away_goal),
      parseDate(r.datetime),
      parseInt0(r.season),
      { round: r.round || null },
    ),
  );
}

/** Brazilian_Cup_Matches.csv — Copa do Brasil. */
export function loadCopaDoBrasil(dataDir: string): Match[] {
  const file = "Brazilian_Cup_Matches.csv";
  return read(dataDir, file).map((r) =>
    makeMatch(
      "Copa do Brasil",
      file,
      r.home_team,
      r.away_team,
      parseInt0(r.home_goal),
      parseInt0(r.away_goal),
      parseDate(r.datetime),
      parseInt0(r.season),
      { round: r.round || null },
    ),
  );
}

/** Libertadores_Matches.csv — Copa Libertadores. */
export function loadLibertadores(dataDir: string): Match[] {
  const file = "Libertadores_Matches.csv";
  return read(dataDir, file).map((r) =>
    makeMatch(
      "Copa Libertadores",
      file,
      r.home_team,
      r.away_team,
      parseInt0(r.home_goal),
      parseInt0(r.away_goal),
      parseDate(r.datetime),
      parseInt0(r.season),
      { stage: r.stage || null },
    ),
  );
}

/** novo_campeonato_brasileiro.csv — Série A 2003–2019 (Portuguese columns). */
export function loadNovoBrasileirao(dataDir: string): Match[] {
  const file = "novo_campeonato_brasileiro.csv";
  return read(dataDir, file).map((r) =>
    makeMatch(
      "Brasileirão Série A",
      file,
      r.Equipe_mandante,
      r.Equipe_visitante,
      parseInt0(r.Gols_mandante),
      parseInt0(r.Gols_visitante),
      parseDate(r.Data),
      parseInt0(r.Ano),
      { round: r.Rodada || null, venue: r.Arena || null },
    ),
  );
}

const TOURNAMENT_MAP: Record<string, Competition> = {
  "Serie A": "Brasileirão Série A",
  "Serie B": "Brasileirão Série B",
  "Serie C": "Brasileirão Série C",
  "Copa do Brasil": "Copa do Brasil",
};

/** BR-Football-Dataset.csv — extended stats across Série A/B/C & Copa. */
export function loadBrFootball(dataDir: string): Match[] {
  const file = "BR-Football-Dataset.csv";
  const out: Match[] = [];
  for (const r of read(dataDir, file)) {
    const competition = TOURNAMENT_MAP[r.tournament];
    if (!competition) continue;
    const date = parseDate(r.date);
    // BR-Football has no season column, so we infer it from the date's year.
    // Brazilian league seasons run within a calendar year (≈May–Dec) — the sole
    // modern exception is the COVID-delayed 2020 season, which finished in
    // Feb 2021. So Série A/B/C matches played in Jan/Feb belong to the *previous*
    // year's season; without this they'd be mis-bucketed and fail to dedupe
    // against the authoritative, explicitly-seasoned datasets.
    let season = date ? Number(date.slice(0, 4)) : null;
    if (season !== null && date) {
      const month = Number(date.slice(5, 7));
      if (month <= 2) season -= 1;
    }
    out.push(
      makeMatch(
        competition,
        file,
        r.home,
        r.away,
        parseInt0(r.home_goal),
        parseInt0(r.away_goal),
        date,
        season,
        {
          stats: {
            homeCorners: parseNum(r.home_corner),
            awayCorners: parseNum(r.away_corner),
            homeShots: parseNum(r.home_shots),
            awayShots: parseNum(r.away_shots),
            homeAttacks: parseNum(r.home_attack),
            awayAttacks: parseNum(r.away_attack),
            totalCorners: parseNum(r.total_corners),
          },
        },
      ),
    );
  }
  return out;
}

/** fifa_data.csv — FIFA player database. */
export function loadPlayers(dataDir: string): Player[] {
  const file = "fifa_data.csv";
  return read(dataDir, file)
    .filter((r) => r.Name && r.ID)
    .map((r) => {
      const club = canonicalTeam(r.Club || "");
      return {
        id: parseInt0(r.ID) ?? 0,
        name: r.Name,
        age: parseInt0(r.Age),
        nationality: r.Nationality || "",
        overall: parseInt0(r.Overall),
        potential: parseInt0(r.Potential),
        club: r.Club || "",
        clubId: r.Club ? club.id : "",
        position: r.Position || "",
        jerseyNumber: parseInt0(r["Jersey Number"]),
        height: r.Height || "",
        weight: r.Weight || "",
        preferredFoot: r["Preferred Foot"] || "",
        value: r.Value || "",
        wage: r.Wage || "",
      } satisfies Player;
    });
}

export interface LoadedData {
  matches: Match[];
  players: Player[];
}

/** "Richness" score used to choose the best record among duplicates. */
function richness(m: Match): number {
  let s = 0;
  if (m.stats) s += 8;
  if (m.round) s += 2;
  if (m.venue) s += 1;
  if (m.stage) s += 1;
  return s;
}

/** Merge two records of the same real-world match, keeping the most data. */
function mergeMatch(a: Match, b: Match): Match {
  const [rich, poor] = richness(a) >= richness(b) ? [a, b] : [b, a];
  // Sources disagree on dates by ~1 day (local vs UTC kickoff). Prefer the
  // earlier date, which corresponds to the Brazilian local match day.
  const dates = [a.date, b.date].filter((d): d is string => !!d).sort();
  return {
    ...rich,
    date: dates[0] ?? rich.date ?? poor.date,
    round: rich.round ?? poor.round,
    stage: rich.stage ?? poor.stage,
    venue: rich.venue ?? poor.venue,
    homeGoals: rich.homeGoals ?? poor.homeGoals,
    awayGoals: rich.awayGoals ?? poor.awayGoals,
    stats: rich.stats ?? poor.stats,
  };
}

/**
 * Collapse duplicate matches that appear across overlapping datasets. The same
 * Série A games are present in up to three files (Brasileirao_Matches,
 * novo_campeonato_brasileiro, BR-Football-Dataset); without this, seasons in the
 * 2012–2019 overlap would be double/triple-counted in standings and stats.
 *
 * Keying strategy: within a single competition + season, an ordered (home, away)
 * fixture is unique (round-robin leagues play each ordered pairing once; cup
 * legs swap home/away). We therefore key on competition + season + home id +
 * away id. This is deliberately date-independent because the sources disagree on
 * dates by up to a day (local kickoff vs UTC). When season is unknown we fall
 * back to a date-based key; records with neither are kept as-is.
 */
export function dedupeMatches(matches: Match[]): Match[] {
  const byKey = new Map<string, Match>();
  const kept: Match[] = [];
  for (const m of matches) {
    let key: string | null = null;
    if (m.season !== null) {
      key = `${m.competition}|S${m.season}|${m.homeTeamId}|${m.awayTeamId}`;
    } else if (m.date) {
      key = `${m.competition}|${m.date}|${m.homeTeamId}|${m.awayTeamId}`;
    }
    if (key === null) {
      kept.push(m);
      continue;
    }
    const existing = byKey.get(key);
    byKey.set(key, existing ? mergeMatch(existing, m) : m);
  }
  return [...byKey.values(), ...kept];
}

/** Load and merge every dataset into a single, de-duplicated collection. */
export function loadAll(dataDir: string): LoadedData {
  const matches = dedupeMatches([
    ...loadBrasileirao(dataDir),
    ...loadNovoBrasileirao(dataDir),
    ...loadCopaDoBrasil(dataDir),
    ...loadLibertadores(dataDir),
    ...loadBrFootball(dataDir),
  ]);
  const players = loadPlayers(dataDir);
  return { matches, players };
}
