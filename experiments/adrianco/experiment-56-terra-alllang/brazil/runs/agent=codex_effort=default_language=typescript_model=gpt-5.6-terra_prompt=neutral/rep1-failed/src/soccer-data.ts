import { readFileSync } from "node:fs";
import { join } from "node:path";
import { parseCsv } from "./csv.js";
import type { Competition, Match, Player, TeamRecord } from "./domain.js";

const canonicalAliases: Record<string, string> = {
  "sport club corinthians paulista": "corinthians", "corinthians paulista": "corinthians",
  "sao paulo fc": "sao paulo", "são paulo fc": "sao paulo", "atletico mineiro": "atletico",
  "atlético mineiro": "atletico", "atletico paranaense": "athletico",
  "atlético paranaense": "athletico", "athletico paranaense": "athletico"
};

/** Accent/case/state-suffix independent key used for matching names across sources. */
export function normalizeTeam(value: string): string {
  const key = value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase()
    .replace(/\([^)]*\)/g, "").replace(/[–—-]\s*[a-z]{2}$/i, "")
    .replace(/[^a-z0-9]+/g, " ").trim();
  return canonicalAliases[key] ?? key;
}

function num(value: string | undefined): number { const n = Number(value); return Number.isFinite(n) ? n : 0; }
function isoDate(value: string): string {
  const br = /^(\d{2})\/(\d{2})\/(\d{4})$/.exec(value);
  return br ? `${br[3]}-${br[2]}-${br[1]}` : value.slice(0, 10);
}
function csv(base: string, file: string) { return parseCsv(readFileSync(join(base, file), "utf8")); }

export class SoccerData {
  readonly matches: Match[];
  readonly players: Player[];

  constructor(dataDir: string) {
    const brasileirao = csv(dataDir, "Brasileirao_Matches.csv").map((r): Match => ({ source: "Brasileirao_Matches.csv", competition: "Brasileirão", date: isoDate(r.datetime), season: num(r.season), round: r.round, homeTeam: r.home_team, awayTeam: r.away_team, homeGoals: num(r.home_goal), awayGoals: num(r.away_goal) }));
    const cup = csv(dataDir, "Brazilian_Cup_Matches.csv").map((r): Match => ({ source: "Brazilian_Cup_Matches.csv", competition: "Copa do Brasil", date: isoDate(r.datetime), season: num(r.season), round: r.round, homeTeam: r.home_team, awayTeam: r.away_team, homeGoals: num(r.home_goal), awayGoals: num(r.away_goal) }));
    const libertadores = csv(dataDir, "Libertadores_Matches.csv").map((r): Match => ({ source: "Libertadores_Matches.csv", competition: "Libertadores", date: isoDate(r.datetime), season: num(r.season), stage: r.stage, homeTeam: r.home_team, awayTeam: r.away_team, homeGoals: num(r.home_goal), awayGoals: num(r.away_goal) }));
    const historical = csv(dataDir, "novo_campeonato_brasileiro.csv").map((r): Match => ({ source: "novo_campeonato_brasileiro.csv", competition: "Brasileirão", date: isoDate(r.Data), season: num(r.Ano), round: r.Rodada, homeTeam: r.Equipe_mandante, awayTeam: r.Equipe_visitante, homeGoals: num(r.Gols_mandante), awayGoals: num(r.Gols_visitante) }));
    const extended = csv(dataDir, "BR-Football-Dataset.csv").map((r): Match => ({ source: "BR-Football-Dataset.csv", competition: r.tournament as Competition, date: isoDate(r.date), season: Number(r.date.slice(0, 4)) || undefined, homeTeam: r.home, awayTeam: r.away, homeGoals: num(r.home_goal), awayGoals: num(r.away_goal), extras: { homeCorners: num(r.home_corner), awayCorners: num(r.away_corner), totalCorners: num(r.total_corners), homeShots: num(r.home_shots), awayShots: num(r.away_shots) } }));
    this.matches = [...brasileirao, ...cup, ...libertadores, ...historical, ...extended];
    this.players = csv(dataDir, "fifa_data.csv").map((r): Player => ({ id: r.ID, name: r.Name, age: r.Age ? num(r.Age) : undefined, nationality: r.Nationality, overall: r.Overall ? num(r.Overall) : undefined, potential: r.Potential ? num(r.Potential) : undefined, club: r.Club, position: r.Position, jerseyNumber: r["Jersey Number"] }));
  }

  findMatches(filters: { team?: string; opponent?: string; competition?: string; season?: number; from?: string; to?: string; stage?: string; limit?: number } = {}): Match[] {
    const team = filters.team && normalizeTeam(filters.team), opponent = filters.opponent && normalizeTeam(filters.opponent);
    return this.matches.filter((m) => {
      const h = normalizeTeam(m.homeTeam), a = normalizeTeam(m.awayTeam);
      return (!team || h.includes(team) || a.includes(team)) && (!opponent || h.includes(opponent) || a.includes(opponent)) &&
        (!filters.competition || m.competition.toLocaleLowerCase().includes(filters.competition.toLocaleLowerCase())) &&
        (!filters.season || m.season === filters.season) && (!filters.from || m.date >= filters.from) && (!filters.to || m.date <= filters.to) &&
        (!filters.stage || (m.stage ?? "").toLowerCase().includes(filters.stage.toLowerCase()));
    }).sort((a, b) => b.date.localeCompare(a.date)).slice(0, filters.limit ?? 100);
  }

  teamStatistics(team: string, filters: { season?: number; competition?: string; homeOnly?: boolean } = {}): TeamRecord {
    const key = normalizeTeam(team); const result: TeamRecord = { team, matches: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0, points: 0, winRate: 0 };
    for (const m of this.findMatches({ team, season: filters.season, competition: filters.competition, limit: Number.MAX_SAFE_INTEGER })) {
      const home = normalizeTeam(m.homeTeam).includes(key); if (filters.homeOnly && !home) continue;
      const gf = home ? m.homeGoals : m.awayGoals, ga = home ? m.awayGoals : m.homeGoals;
      result.matches++; result.goalsFor += gf; result.goalsAgainst += ga;
      if (gf > ga) { result.wins++; result.points += 3; } else if (gf === ga) { result.draws++; result.points++; } else result.losses++;
    }
    result.winRate = result.matches ? Number((100 * result.wins / result.matches).toFixed(1)) : 0; return result;
  }

  headToHead(teamA: string, teamB: string, filters: { season?: number; competition?: string } = {}) {
    const matches = this.findMatches({ ...filters, team: teamA, opponent: teamB, limit: Number.MAX_SAFE_INTEGER });
    let aWins = 0, bWins = 0, draws = 0;
    for (const m of matches) { const aHome = normalizeTeam(m.homeTeam).includes(normalizeTeam(teamA)); const ag = aHome ? m.homeGoals : m.awayGoals, bg = aHome ? m.awayGoals : m.homeGoals; if (ag > bg) aWins++; else if (ag < bg) bWins++; else draws++; }
    return { teamA, teamB, matches, teamAWins: aWins, teamBWins: bWins, draws };
  }

  searchPlayers(filters: { name?: string; nationality?: string; club?: string; position?: string; limit?: number } = {}): Player[] {
    const includes = (actual: string, expected?: string) => !expected || actual.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().includes(expected.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase());
    return this.players.filter((p) => includes(p.name, filters.name) && includes(p.nationality, filters.nationality) && includes(p.club, filters.club) && includes(p.position, filters.position)).sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0)).slice(0, filters.limit ?? 50);
  }

  standings(season: number, competition = "Brasileirão"): TeamRecord[] {
    const table = new Map<string, TeamRecord>();
    for (const m of this.findMatches({ season, competition, limit: Number.MAX_SAFE_INTEGER })) for (const name of [m.homeTeam, m.awayTeam]) if (!table.has(normalizeTeam(name))) table.set(normalizeTeam(name), { team: name, matches: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0, points: 0, winRate: 0 });
    for (const m of this.findMatches({ season, competition, limit: Number.MAX_SAFE_INTEGER })) { const h = table.get(normalizeTeam(m.homeTeam))!, a = table.get(normalizeTeam(m.awayTeam))!; for (const [r, gf, ga] of [[h, m.homeGoals, m.awayGoals], [a, m.awayGoals, m.homeGoals]] as const) { r.matches++; r.goalsFor += gf; r.goalsAgainst += ga; if (gf > ga) { r.wins++; r.points += 3; } else if (gf === ga) { r.draws++; r.points++; } else r.losses++; r.winRate = Number((r.wins * 100 / r.matches).toFixed(1)); } }
    return [...table.values()].sort((a, b) => b.points - a.points || (b.goalsFor - b.goalsAgainst) - (a.goalsFor - a.goalsAgainst) || b.goalsFor - a.goalsFor);
  }
}
