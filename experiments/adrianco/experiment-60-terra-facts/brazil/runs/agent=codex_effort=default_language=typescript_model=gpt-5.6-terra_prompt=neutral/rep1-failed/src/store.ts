import { readFile } from "node:fs/promises";
import { join } from "node:path";
import { isoDate, numberOrUndefined, parseCsv } from "./csv.ts";
import { sameTeam } from "./normalization.ts";
import type { Competition, Match, MatchFilter, Player } from "./types.ts";

const file = (root: string, name: string) => join(root, name);

export class SoccerStore {
  readonly matches: Match[];
  readonly players: Player[];

  constructor(matches: Match[], players: Player[]) {
    this.matches = matches;
    this.players = players;
  }

  static async load(dataDirectory = join(process.cwd(), "data/kaggle")): Promise<SoccerStore> {
    const read = async (name: string) => parseCsv(await readFile(file(dataDirectory, name), "utf8"));
    const [serieA, cup, libertadores, extended, historic, fifa] = await Promise.all([
      read("Brasileirao_Matches.csv"), read("Brazilian_Cup_Matches.csv"), read("Libertadores_Matches.csv"),
      read("BR-Football-Dataset.csv"), read("novo_campeonato_brasileiro.csv"), read("fifa_data.csv"),
    ]);
    const match = (row: Record<string, string>, competition: Competition, source: string, keys: { home: string; away: string; homeGoals: string; awayGoals: string; date: string; season?: string; round?: string; stage?: string; stadium?: string }, index: number): Match => ({
      id: `${source}-${index}`, competition, source, date: isoDate(row[keys.date]), season: numberOrUndefined(keys.season ? row[keys.season] : undefined),
      round: keys.round ? row[keys.round] || undefined : undefined, stage: keys.stage ? row[keys.stage] || undefined : undefined,
      stadium: keys.stadium ? row[keys.stadium] || undefined : undefined, homeTeam: row[keys.home], awayTeam: row[keys.away],
      homeGoals: numberOrUndefined(row[keys.homeGoals]) ?? 0, awayGoals: numberOrUndefined(row[keys.awayGoals]) ?? 0,
    });
    const matches = [
      ...serieA.map((r, i) => match(r, "Brasileirão", "serie-a", { home: "home_team", away: "away_team", homeGoals: "home_goal", awayGoals: "away_goal", date: "datetime", season: "season", round: "round" }, i)),
      ...cup.map((r, i) => match(r, "Copa do Brasil", "cup", { home: "home_team", away: "away_team", homeGoals: "home_goal", awayGoals: "away_goal", date: "datetime", season: "season", round: "round" }, i)),
      ...libertadores.map((r, i) => match(r, "Libertadores", "libertadores", { home: "home_team", away: "away_team", homeGoals: "home_goal", awayGoals: "away_goal", date: "datetime", season: "season", stage: "stage" }, i)),
      ...extended.map((r, i) => match(r, "Brazilian Football", "extended", { home: "home", away: "away", homeGoals: "home_goal", awayGoals: "away_goal", date: "date" }, i)),
      ...historic.map((r, i) => match(r, "Brasileirão", "historic", { home: "Equipe_mandante", away: "Equipe_visitante", homeGoals: "Gols_mandante", awayGoals: "Gols_visitante", date: "Data", season: "Ano", round: "Rodada", stadium: "Arena" }, i)),
    ];
    const players = fifa.map((r) => ({ id: r.ID, name: r.Name, age: numberOrUndefined(r.Age), nationality: r.Nationality || undefined, overall: numberOrUndefined(r.Overall), potential: numberOrUndefined(r.Potential), club: r.Club || undefined, position: r.Position || undefined, jerseyNumber: numberOrUndefined(r["Jersey Number"]), height: r.Height || undefined, weight: r.Weight || undefined }));
    return new SoccerStore(matches, players);
  }

  findMatches(filter: MatchFilter = {}): Match[] {
    const limit = Math.min(Math.max(filter.limit ?? 50, 1), 20_000);
    return this.matches.filter((m) =>
      (!filter.team || sameTeam(m.homeTeam, filter.team) || sameTeam(m.awayTeam, filter.team)) &&
      (!filter.opponent || (filter.team ? ((sameTeam(m.homeTeam, filter.team) && sameTeam(m.awayTeam, filter.opponent)) || (sameTeam(m.awayTeam, filter.team) && sameTeam(m.homeTeam, filter.opponent))) : sameTeam(m.homeTeam, filter.opponent) || sameTeam(m.awayTeam, filter.opponent))) &&
      (!filter.competition || m.competition === filter.competition) && (!filter.season || m.season === filter.season) &&
      (!filter.from || (m.date !== undefined && m.date >= filter.from)) && (!filter.to || (m.date !== undefined && m.date <= filter.to)) &&
      (!filter.round || m.round?.toLowerCase().includes(filter.round.toLowerCase())) && (!filter.stage || m.stage?.toLowerCase().includes(filter.stage.toLowerCase()))
    ).sort((a, b) => (b.date ?? "").localeCompare(a.date ?? "")).slice(0, limit);
  }

  searchPlayers(filter: { name?: string; nationality?: string; club?: string; position?: string; limit?: number } = {}): Player[] {
    const includes = (value: string | undefined, term: string | undefined) => !term || !!value && value.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().includes(term.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase());
    return this.players.filter((p) => includes(p.name, filter.name) && includes(p.nationality, filter.nationality) && includes(p.club, filter.club) && includes(p.position, filter.position)).sort((a, b) => (b.overall ?? -1) - (a.overall ?? -1)).slice(0, Math.min(filter.limit ?? 50, 500));
  }

  record(team: string, options: { season?: number; competition?: Competition; venue?: "home" | "away" | "all" } = {}) {
    const relevant = this.findMatches({ team, season: options.season, competition: options.competition, limit: 20_000 }).filter((m) =>
      options.venue === "all" || !options.venue
        ? true
        : options.venue === "home" ? sameTeam(m.homeTeam, team) : sameTeam(m.awayTeam, team)
    );
    let wins = 0, draws = 0, losses = 0, goalsFor = 0, goalsAgainst = 0;
    for (const m of relevant) { const home = sameTeam(m.homeTeam, team); const gf = home ? m.homeGoals : m.awayGoals, ga = home ? m.awayGoals : m.homeGoals; goalsFor += gf; goalsAgainst += ga; if (gf > ga) wins++; else if (gf === ga) draws++; else losses++; }
    return { team, matches: relevant.length, wins, draws, losses, goalsFor, goalsAgainst, points: wins * 3 + draws, winRate: relevant.length ? Number((wins / relevant.length * 100).toFixed(1)) : 0 };
  }

  headToHead(teamA: string, teamB: string, options: { season?: number; competition?: Competition } = {}) {
    const matches = this.findMatches({ team: teamA, opponent: teamB, ...options, limit: 20_000 }); let teamAWins = 0, teamBWins = 0, draws = 0;
    for (const m of matches) { if (m.homeGoals === m.awayGoals) draws++; else if ((sameTeam(m.homeTeam, teamA) && m.homeGoals > m.awayGoals) || (sameTeam(m.awayTeam, teamA) && m.awayGoals > m.homeGoals)) teamAWins++; else teamBWins++; }
    return { teamA, teamB, matches, teamAWins, teamBWins, draws };
  }

  standings(season: number, competition: Competition = "Brasileirão") {
    const table = new Map<string, { team: string; played: number; wins: number; draws: number; losses: number; goalsFor: number; goalsAgainst: number; points: number }>();
    const add = (team: string, goalsFor: number, goalsAgainst: number) => { const row = table.get(team) ?? { team, played: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0, points: 0 }; row.played++; row.goalsFor += goalsFor; row.goalsAgainst += goalsAgainst; if (goalsFor > goalsAgainst) { row.wins++; row.points += 3; } else if (goalsFor === goalsAgainst) { row.draws++; row.points++; } else row.losses++; table.set(team, row); };
    this.findMatches({ season, competition, limit: 20_000 }).forEach((m) => { add(m.homeTeam, m.homeGoals, m.awayGoals); add(m.awayTeam, m.awayGoals, m.homeGoals); });
    return [...table.values()].sort((a, b) => b.points - a.points || (b.goalsFor - b.goalsAgainst) - (a.goalsFor - a.goalsAgainst) || b.goalsFor - a.goalsFor).map((row, index) => ({ rank: index + 1, ...row, goalDifference: row.goalsFor - row.goalsAgainst }));
  }

  statistics(options: { competition?: Competition; season?: number } = {}) {
    const matches = this.findMatches({ ...options, limit: 20_000 }); const totalGoals = matches.reduce((sum, m) => sum + m.homeGoals + m.awayGoals, 0);
    const biggestWins = [...matches].sort((a, b) => Math.abs(b.homeGoals - b.awayGoals) - Math.abs(a.homeGoals - a.awayGoals)).slice(0, 10);
    return { matches: matches.length, totalGoals, averageGoalsPerMatch: matches.length ? Number((totalGoals / matches.length).toFixed(2)) : 0, homeWins: matches.filter((m) => m.homeGoals > m.awayGoals).length, awayWins: matches.filter((m) => m.awayGoals > m.homeGoals).length, draws: matches.filter((m) => m.homeGoals === m.awayGoals).length, biggestWins };
  }
}
