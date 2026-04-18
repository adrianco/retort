import { readCSV } from "./csv.js";
import { join, dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { existsSync } from "node:fs";
export function normalizeTeam(name) {
    if (!name)
        return "";
    let n = name.trim();
    // remove state suffix like "-SP" or " - SP"
    n = n.replace(/\s*-\s*[A-Z]{2}\s*$/u, "");
    // remove country code in parentheses, keep it if needed but strip for matching
    n = n.replace(/\s*\([A-Z]{2,4}\)\s*$/u, "");
    // collapse whitespace
    n = n.replace(/\s+/g, " ").trim();
    return n.toLowerCase();
}
export function parseDate(s) {
    if (!s)
        return null;
    const t = s.trim();
    // ISO form like 2023-09-03 or 2012-05-19 18:30:00
    const iso = /^(\d{4})-(\d{2})-(\d{2})/.exec(t);
    if (iso)
        return `${iso[1]}-${iso[2]}-${iso[3]}`;
    // Brazilian DD/MM/YYYY
    const br = /^(\d{2})\/(\d{2})\/(\d{4})/.exec(t);
    if (br)
        return `${br[3]}-${br[2]}-${br[1]}`;
    return null;
}
function toNum(s) {
    const n = Number(s);
    return Number.isFinite(n) ? n : 0;
}
function toNumOrNull(s) {
    if (s === undefined || s === null || s === "")
        return null;
    const n = Number(s);
    return Number.isFinite(n) ? n : null;
}
function findDataDir() {
    const __dirname = dirname(fileURLToPath(import.meta.url));
    const candidates = [
        process.env.BSOC_DATA_DIR,
        join(process.cwd(), "data", "kaggle"),
        resolve(__dirname, "..", "data", "kaggle"),
        resolve(__dirname, "..", "..", "data", "kaggle"),
    ].filter(Boolean);
    for (const p of candidates) {
        if (existsSync(p))
            return p;
    }
    throw new Error("Could not locate data/kaggle directory");
}
export class Dataset {
    matches = [];
    players = [];
    static load(dataDir) {
        const dir = dataDir ?? findDataDir();
        const ds = new Dataset();
        ds.loadBrasileirao(join(dir, "Brasileirao_Matches.csv"));
        ds.loadCup(join(dir, "Brazilian_Cup_Matches.csv"));
        ds.loadLibertadores(join(dir, "Libertadores_Matches.csv"));
        ds.loadBRFootball(join(dir, "BR-Football-Dataset.csv"));
        ds.loadNovoBrasileirao(join(dir, "novo_campeonato_brasileiro.csv"));
        ds.loadFifa(join(dir, "fifa_data.csv"));
        return ds;
    }
    loadBrasileirao(path) {
        if (!existsSync(path))
            return;
        for (const r of readCSV(path)) {
            this.matches.push({
                competition: "Brasileirão Serie A",
                season: toNumOrNull(r.season),
                round: r.round ?? null,
                stage: null,
                date: parseDate(r.datetime),
                homeTeam: r.home_team,
                awayTeam: r.away_team,
                homeGoal: toNum(r.home_goal),
                awayGoal: toNum(r.away_goal),
            });
        }
    }
    loadCup(path) {
        if (!existsSync(path))
            return;
        for (const r of readCSV(path)) {
            this.matches.push({
                competition: "Copa do Brasil",
                season: toNumOrNull(r.season),
                round: r.round ?? null,
                stage: null,
                date: parseDate(r.datetime),
                homeTeam: r.home_team,
                awayTeam: r.away_team,
                homeGoal: toNum(r.home_goal),
                awayGoal: toNum(r.away_goal),
            });
        }
    }
    loadLibertadores(path) {
        if (!existsSync(path))
            return;
        for (const r of readCSV(path)) {
            this.matches.push({
                competition: "Copa Libertadores",
                season: toNumOrNull(r.season),
                round: null,
                stage: r.stage ?? null,
                date: parseDate(r.datetime),
                homeTeam: r.home_team,
                awayTeam: r.away_team,
                homeGoal: toNum(r.home_goal),
                awayGoal: toNum(r.away_goal),
            });
        }
    }
    loadBRFootball(path) {
        if (!existsSync(path))
            return;
        for (const r of readCSV(path)) {
            const date = parseDate(r.date);
            const season = date ? Number(date.slice(0, 4)) : null;
            this.matches.push({
                competition: r.tournament || "BR Football",
                season,
                round: null,
                stage: null,
                date,
                homeTeam: r.home,
                awayTeam: r.away,
                homeGoal: toNum(r.home_goal),
                awayGoal: toNum(r.away_goal),
            });
        }
    }
    loadNovoBrasileirao(path) {
        if (!existsSync(path))
            return;
        for (const r of readCSV(path)) {
            this.matches.push({
                competition: "Brasileirão Historical",
                season: toNumOrNull(r.Ano),
                round: r.Rodada ?? null,
                stage: null,
                date: parseDate(r.Data),
                homeTeam: r.Equipe_mandante,
                awayTeam: r.Equipe_visitante,
                homeGoal: toNum(r.Gols_mandante),
                awayGoal: toNum(r.Gols_visitante),
                venue: r.Arena || null,
            });
        }
    }
    loadFifa(path) {
        if (!existsSync(path))
            return;
        for (const r of readCSV(path)) {
            if (!r.Name)
                continue;
            this.players.push({
                id: toNum(r.ID),
                name: r.Name,
                age: toNumOrNull(r.Age),
                nationality: r.Nationality ?? "",
                overall: toNumOrNull(r.Overall),
                potential: toNumOrNull(r.Potential),
                club: r.Club ?? "",
                position: r.Position ?? "",
                jerseyNumber: r["Jersey Number"] ?? "",
                height: r.Height ?? "",
                weight: r.Weight ?? "",
            });
        }
    }
}
