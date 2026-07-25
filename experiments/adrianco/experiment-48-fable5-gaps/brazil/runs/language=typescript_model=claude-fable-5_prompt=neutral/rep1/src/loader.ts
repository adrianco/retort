/**
 * Loads the six Kaggle CSV files from data/kaggle/ into a unified Dataset.
 *
 * Matches from the five match files are merged into one list. The same
 * fixture can appear in several files (e.g. a 2015 Brasileirão match is in
 * Brasileirao_Matches.csv, novo_campeonato_brasileiro.csv and
 * BR-Football-Dataset.csv), so matches are deduplicated on
 * (date, home base name, away base name) and their fields merged — the
 * extended-statistics file contributes corners/shots/attacks to matches
 * first seen elsewhere.
 */

import { readFileSync } from "node:fs";
import { join } from "node:path";
import { parseCsv } from "./csv.js";
import { normalizeTeamName } from "./teams.js";
import type { Competition, Dataset, Match, Player } from "./types.js";

const FILES = {
  brasileirao: "Brasileirao_Matches.csv",
  cup: "Brazilian_Cup_Matches.csv",
  libertadores: "Libertadores_Matches.csv",
  extended: "BR-Football-Dataset.csv",
  historical: "novo_campeonato_brasileiro.csv",
  fifa: "fifa_data.csv",
} as const;

function num(s: string | undefined): number | null {
  if (s === undefined || s === null) return null;
  const t = s.trim();
  if (t === "") return null;
  const n = Number(t);
  return Number.isFinite(n) ? n : null;
}

/** Parse "2012-05-19 18:30:00", "2023-09-24" or "29/03/2003" to ISO date. */
export function parseDate(s: string | undefined): string | null {
  if (!s) return null;
  const t = s.trim();
  let m = t.match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (m) return `${m[1]}-${m[2]}-${m[3]}`;
  m = t.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})/);
  if (m) return `${m[3]}-${m[2].padStart(2, "0")}-${m[1].padStart(2, "0")}`;
  return null;
}

function readTable(dataDir: string, file: string) {
  const text = readFileSync(join(dataDir, file), "utf8");
  return parseCsv(text);
}

function shiftDate(iso: string, days: number): string {
  const d = new Date(`${iso}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

/**
 * Candidate dedup keys for a match. The extended-statistics file records
 * some kick-off dates one day off from the authoritative files (timezone
 * differences), so a match is considered a duplicate when the same home and
 * away teams met within one calendar day.
 */
function dedupKeys(m: Match): string[] {
  if (!m.date) return [];
  const pair = `${m.home.base}|${m.away.base}`;
  return [0, -1, 1].map((off) => `${shiftDate(m.date!, off)}|${pair}`);
}

export function loadDataset(dataDir: string): Dataset {
  const fileCounts: Record<string, number> = {};
  const matches: Match[] = [];
  const byKey = new Map<string, Match>();
  let duplicatesMerged = 0;

  const add = (m: Match) => {
    const keys = dedupKeys(m);
    const existing = keys.map((k) => byKey.get(k)).find(Boolean);
    if (existing) {
      duplicatesMerged++;
      // Merge: fill in fields the first-seen record lacked.
      existing.sources.push(m.sources[0]);
      if (!existing.stats && m.stats) existing.stats = m.stats;
      if (!existing.stadium && m.stadium) existing.stadium = m.stadium;
      if (!existing.round && m.round) existing.round = m.round;
      if (!existing.stage && m.stage) existing.stage = m.stage;
      if (existing.season === null && m.season !== null) existing.season = m.season;
      return;
    }
    // Register only the exact-date key; neighbor keys are used for lookup.
    if (keys.length) byKey.set(keys[0], m);
    matches.push(m);
  };

  // 1. Brasileirão Série A (2012+)
  {
    const t = readTable(dataDir, FILES.brasileirao);
    fileCounts[FILES.brasileirao] = t.rows.length;
    for (const r of t.rows) {
      const hg = num(r["home_goal"]);
      const ag = num(r["away_goal"]);
      if (hg === null || ag === null) continue;
      add({
        competition: "Brasileirão Série A",
        date: parseDate(r["datetime"]),
        season: num(r["season"]),
        round: r["round"] || null,
        stage: null,
        home: normalizeTeamName(r["home_team"]),
        away: normalizeTeamName(r["away_team"]),
        homeGoals: hg,
        awayGoals: ag,
        stadium: null,
        stats: null,
        sources: [FILES.brasileirao],
      });
    }
  }

  // 2. Historical Brasileirão 2003–2019
  {
    const t = readTable(dataDir, FILES.historical);
    fileCounts[FILES.historical] = t.rows.length;
    for (const r of t.rows) {
      const hg = num(r["Gols_mandante"]);
      const ag = num(r["Gols_visitante"]);
      if (hg === null || ag === null) continue;
      add({
        competition: "Brasileirão Série A",
        date: parseDate(r["Data"]),
        season: num(r["Ano"]),
        round: r["Rodada"] || null,
        stage: null,
        home: normalizeTeamName(r["Equipe_mandante"]),
        away: normalizeTeamName(r["Equipe_visitante"]),
        homeGoals: hg,
        awayGoals: ag,
        stadium: r["Arena"] || null,
        stats: null,
        sources: [FILES.historical],
      });
    }
  }

  // 3. Copa do Brasil
  {
    const t = readTable(dataDir, FILES.cup);
    fileCounts[FILES.cup] = t.rows.length;
    for (const r of t.rows) {
      const hg = num(r["home_goal"]);
      const ag = num(r["away_goal"]);
      if (hg === null || ag === null) continue;
      add({
        competition: "Copa do Brasil",
        date: parseDate(r["datetime"]),
        season: num(r["season"]),
        round: r["round"] || null,
        stage: r["round"] || null,
        home: normalizeTeamName(r["home_team"]),
        away: normalizeTeamName(r["away_team"]),
        homeGoals: hg,
        awayGoals: ag,
        stadium: null,
        stats: null,
        sources: [FILES.cup],
      });
    }
  }

  // 4. Copa Libertadores
  {
    const t = readTable(dataDir, FILES.libertadores);
    fileCounts[FILES.libertadores] = t.rows.length;
    for (const r of t.rows) {
      const hg = num(r["home_goal"]);
      const ag = num(r["away_goal"]);
      if (hg === null || ag === null) continue;
      add({
        competition: "Copa Libertadores",
        date: parseDate(r["datetime"]),
        season: num(r["season"]),
        round: null,
        stage: r["stage"] || null,
        home: normalizeTeamName(r["home_team"]),
        away: normalizeTeamName(r["away_team"]),
        homeGoals: hg,
        awayGoals: ag,
        stadium: null,
        stats: null,
        sources: [FILES.libertadores],
      });
    }
  }

  // 5. Extended statistics (Serie A/B/C + Copa do Brasil, with corners/shots)
  {
    const t = readTable(dataDir, FILES.extended);
    fileCounts[FILES.extended] = t.rows.length;
    const compMap: Record<string, Competition> = {
      "Serie A": "Brasileirão Série A",
      "Serie B": "Brasileirão Série B",
      "Serie C": "Brasileirão Série C",
      "Copa do Brasil": "Copa do Brasil",
    };
    for (const r of t.rows) {
      const comp = compMap[r["tournament"]];
      if (!comp) continue;
      const hg = num(r["home_goal"]);
      const ag = num(r["away_goal"]);
      if (hg === null || ag === null) continue;
      const date = parseDate(r["date"]);
      add({
        competition: comp,
        date,
        season: date ? Number(date.slice(0, 4)) : null,
        round: null,
        stage: null,
        home: normalizeTeamName(r["home"]),
        away: normalizeTeamName(r["away"]),
        homeGoals: hg,
        awayGoals: ag,
        stadium: null,
        stats: {
          homeCorners: num(r["home_corner"]) ?? undefined,
          awayCorners: num(r["away_corner"]) ?? undefined,
          homeShots: num(r["home_shots"]) ?? undefined,
          awayShots: num(r["away_shots"]) ?? undefined,
          homeAttacks: num(r["home_attack"]) ?? undefined,
          awayAttacks: num(r["away_attack"]) ?? undefined,
          halfTimeHome: r["ht_result"] || undefined,
          halfTimeAway: r["at_result"] || undefined,
        },
        sources: [FILES.extended],
      });
    }
  }

  // 6. FIFA players
  const players: Player[] = [];
  {
    const t = readTable(dataDir, FILES.fifa);
    fileCounts[FILES.fifa] = t.rows.length;
    const skillCols = [
      "Crossing", "Finishing", "HeadingAccuracy", "ShortPassing", "Volleys",
      "Dribbling", "Curve", "FKAccuracy", "LongPassing", "BallControl",
      "Acceleration", "SprintSpeed", "Agility", "Reactions", "Balance",
      "ShotPower", "Jumping", "Stamina", "Strength", "LongShots",
      "Aggression", "Interceptions", "Positioning", "Vision", "Penalties",
      "Composure", "Marking", "StandingTackle", "SlidingTackle",
      "GKDiving", "GKHandling", "GKKicking", "GKPositioning", "GKReflexes",
    ];
    for (const r of t.rows) {
      const overall = num(r["Overall"]);
      const id = num(r["ID"]);
      if (overall === null || id === null || !r["Name"]) continue;
      const skills: Record<string, number> = {};
      for (const c of skillCols) {
        const v = num(r[c]);
        if (v !== null) skills[c] = v;
      }
      players.push({
        id,
        name: r["Name"],
        age: num(r["Age"]),
        nationality: r["Nationality"] || "",
        overall,
        potential: num(r["Potential"]),
        club: r["Club"] || "",
        position: r["Position"] || "",
        jerseyNumber: num(r["Jersey Number"]),
        height: r["Height"] || "",
        weight: r["Weight"] || "",
        preferredFoot: r["Preferred Foot"] || "",
        value: r["Value"] || "",
        wage: r["Wage"] || "",
        skills,
      });
    }
  }

  // Sort matches chronologically (nulls last) for stable output.
  matches.sort((a, b) => {
    if (a.date === b.date) return 0;
    if (a.date === null) return 1;
    if (b.date === null) return -1;
    return a.date < b.date ? -1 : 1;
  });

  return { matches, players, fileCounts, duplicatesMerged };
}
