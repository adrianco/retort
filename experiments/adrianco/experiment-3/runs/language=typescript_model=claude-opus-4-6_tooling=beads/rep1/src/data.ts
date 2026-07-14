import { parse } from "csv-parse/sync";
import { readFileSync } from "node:fs";
import { join } from "node:path";

export interface Match {
  date: string;
  homeTeam: string;
  awayTeam: string;
  homeGoals: number;
  awayGoals: number;
  season: number;
  competition: string;
  round?: string;
  stage?: string;
  stadium?: string;
  homeCorners?: number;
  awayCorners?: number;
  homeShots?: number;
  awayShots?: number;
}

export interface Player {
  id: number;
  name: string;
  age: number;
  nationality: string;
  overall: number;
  potential: number;
  club: string;
  position: string;
  jerseyNumber: number | null;
  height: string;
  weight: string;
  preferredFoot: string;
  crossing: number;
  finishing: number;
  dribbling: number;
  shortPassing: number;
  longPassing: number;
  ballControl: number;
  acceleration: number;
  sprintSpeed: number;
  shotPower: number;
  stamina: number;
  strength: number;
  aggression: number;
  interceptions: number;
  positioning: number;
  vision: number;
  composure: number;
}

const TEAM_NAME_MAP: Record<string, string> = {
  "Sao Paulo": "São Paulo",
  "Sao Paulo-SP": "São Paulo",
  "São Paulo-SP": "São Paulo",
  "Gremio": "Grêmio",
  "Grêmio-RS": "Grêmio",
  "Gremio-RS": "Grêmio",
  "Avai": "Avaí",
  "Avaí-SC": "Avaí",
  "Avai-SC": "Avaí",
  "Goias": "Goiás",
  "Goiás-GO": "Goiás",
  "Goias-GO": "Goiás",
  "Ceara": "Ceará",
  "Ceará-CE": "Ceará",
  "Ceara-CE": "Ceará",
  "Parana": "Paraná",
  "Cuiaba": "Cuiabá",
  "Cuiabá-MT": "Cuiabá",
  "Cuiaba-MT": "Cuiabá",
  "America-MG": "América-MG",
  "América - MG": "América-MG",
  "America-RN": "América-RN",
  "Atletico-MG": "Atlético-MG",
  "Atlético-MG-MG": "Atlético-MG",
  "Atletico-GO": "Atlético-GO",
  "Atlético-GO-GO": "Atlético-GO",
  "Atletico-PR": "Athletico-PR",
  "Athletico-PR-PR": "Athletico-PR",
};

export function normalizeTeamName(name: string): string {
  const trimmed = name.trim();
  if (TEAM_NAME_MAP[trimmed]) return TEAM_NAME_MAP[trimmed];

  // Strip state suffix like "-SP", "-RJ" etc. (2 uppercase letters after dash at end)
  const stateMatch = trimmed.match(/^(.+)-([A-Z]{2})$/);
  if (stateMatch) {
    const baseName = stateMatch[1];
    if (TEAM_NAME_MAP[baseName]) return TEAM_NAME_MAP[baseName];
    return baseName;
  }

  return trimmed;
}

export function teamMatches(teamName: string, query: string): boolean {
  const normalizedTeam = normalizeTeamName(teamName).toLowerCase();
  const normalizedQuery = normalizeTeamName(query).toLowerCase();
  return (
    normalizedTeam === normalizedQuery ||
    normalizedTeam.includes(normalizedQuery) ||
    normalizedQuery.includes(normalizedTeam)
  );
}

function parseDate(raw: string): string {
  if (!raw) return "";
  const trimmed = raw.trim();

  // DD/MM/YYYY
  const brMatch = trimmed.match(/^(\d{2})\/(\d{2})\/(\d{4})$/);
  if (brMatch) return `${brMatch[3]}-${brMatch[2]}-${brMatch[1]}`;

  // Already ISO-ish (2023-09-24 or 2023-09-24 18:30:00)
  if (trimmed.match(/^\d{4}-\d{2}-\d{2}/)) return trimmed.slice(0, 10);

  return trimmed;
}

function safeInt(val: unknown): number {
  if (val === undefined || val === null || val === "") return 0;
  const n = Number(val);
  return isNaN(n) ? 0 : Math.round(n);
}

export class SoccerData {
  matches: Match[] = [];
  players: Player[] = [];
  private loaded = false;

  constructor(private dataDir: string) {}

  load(): void {
    if (this.loaded) return;
    this.loadBrasileirao();
    this.loadCupMatches();
    this.loadLibertadores();
    this.loadExtendedStats();
    this.loadHistorical();
    this.loadPlayers();
    this.loaded = true;
  }

  private readCsv(filename: string): Record<string, string>[] {
    const filepath = join(this.dataDir, filename);
    const content = readFileSync(filepath, "utf-8");
    return parse(content, {
      columns: true,
      skip_empty_lines: true,
      relax_column_count: true,
      trim: true,
    });
  }

  private loadBrasileirao(): void {
    const rows = this.readCsv("Brasileirao_Matches.csv");
    for (const row of rows) {
      this.matches.push({
        date: parseDate(row["datetime"] || ""),
        homeTeam: normalizeTeamName(row["home_team"] || ""),
        awayTeam: normalizeTeamName(row["away_team"] || ""),
        homeGoals: safeInt(row["home_goal"]),
        awayGoals: safeInt(row["away_goal"]),
        season: safeInt(row["season"]),
        competition: "Brasileirão Serie A",
        round: row["round"] || undefined,
      });
    }
  }

  private loadCupMatches(): void {
    const rows = this.readCsv("Brazilian_Cup_Matches.csv");
    for (const row of rows) {
      this.matches.push({
        date: parseDate(row["datetime"] || ""),
        homeTeam: normalizeTeamName(row["home_team"] || ""),
        awayTeam: normalizeTeamName(row["away_team"] || ""),
        homeGoals: safeInt(row["home_goal"]),
        awayGoals: safeInt(row["away_goal"]),
        season: safeInt(row["season"]),
        competition: "Copa do Brasil",
        round: row["round"] || undefined,
      });
    }
  }

  private loadLibertadores(): void {
    const rows = this.readCsv("Libertadores_Matches.csv");
    for (const row of rows) {
      this.matches.push({
        date: parseDate(row["datetime"] || ""),
        homeTeam: normalizeTeamName(row["home_team"] || ""),
        awayTeam: normalizeTeamName(row["away_team"] || ""),
        homeGoals: safeInt(row["home_goal"]),
        awayGoals: safeInt(row["away_goal"]),
        season: safeInt(row["season"]),
        competition: "Copa Libertadores",
        stage: row["stage"] || undefined,
      });
    }
  }

  private loadExtendedStats(): void {
    const rows = this.readCsv("BR-Football-Dataset.csv");
    for (const row of rows) {
      this.matches.push({
        date: parseDate(row["date"] || ""),
        homeTeam: normalizeTeamName(row["home"] || ""),
        awayTeam: normalizeTeamName(row["away"] || ""),
        homeGoals: safeInt(row["home_goal"]),
        awayGoals: safeInt(row["away_goal"]),
        season: safeInt((row["date"] || "").slice(0, 4)),
        competition: row["tournament"] || "Unknown",
        homeCorners: safeInt(row["home_corner"]),
        awayCorners: safeInt(row["away_corner"]),
        homeShots: safeInt(row["home_shots"]),
        awayShots: safeInt(row["away_shots"]),
      });
    }
  }

  private loadHistorical(): void {
    const rows = this.readCsv("novo_campeonato_brasileiro.csv");
    for (const row of rows) {
      this.matches.push({
        date: parseDate(row["Data"] || ""),
        homeTeam: normalizeTeamName(row["Equipe_mandante"] || ""),
        awayTeam: normalizeTeamName(row["Equipe_visitante"] || ""),
        homeGoals: safeInt(row["Gols_mandante"]),
        awayGoals: safeInt(row["Gols_visitante"]),
        season: safeInt(row["Ano"]),
        competition: "Brasileirão Serie A",
        round: row["Rodada"] || undefined,
        stadium: row["Arena"] || undefined,
      });
    }
  }

  private loadPlayers(): void {
    const rows = this.readCsv("fifa_data.csv");
    for (const row of rows) {
      this.players.push({
        id: safeInt(row["ID"]),
        name: row["Name"] || "",
        age: safeInt(row["Age"]),
        nationality: row["Nationality"] || "",
        overall: safeInt(row["Overall"]),
        potential: safeInt(row["Potential"]),
        club: row["Club"] || "",
        position: row["Position"] || "",
        jerseyNumber: row["Jersey Number"] ? safeInt(row["Jersey Number"]) : null,
        height: row["Height"] || "",
        weight: row["Weight"] || "",
        preferredFoot: row["Preferred Foot"] || "",
        crossing: safeInt(row["Crossing"]),
        finishing: safeInt(row["Finishing"]),
        dribbling: safeInt(row["Dribbling"]),
        shortPassing: safeInt(row["ShortPassing"]),
        longPassing: safeInt(row["LongPassing"]),
        ballControl: safeInt(row["BallControl"]),
        acceleration: safeInt(row["Acceleration"]),
        sprintSpeed: safeInt(row["SprintSpeed"]),
        shotPower: safeInt(row["ShotPower"]),
        stamina: safeInt(row["Stamina"]),
        strength: safeInt(row["Strength"]),
        aggression: safeInt(row["Aggression"]),
        interceptions: safeInt(row["Interceptions"]),
        positioning: safeInt(row["Positioning"]),
        vision: safeInt(row["Vision"]),
        composure: safeInt(row["Composure"]),
      });
    }
  }

  searchMatches(opts: {
    team?: string;
    homeTeam?: string;
    awayTeam?: string;
    competition?: string;
    season?: number;
    dateFrom?: string;
    dateTo?: string;
    limit?: number;
  }): Match[] {
    let results = this.matches;

    if (opts.team) {
      results = results.filter(
        (m) => teamMatches(m.homeTeam, opts.team!) || teamMatches(m.awayTeam, opts.team!)
      );
    }
    if (opts.homeTeam) {
      results = results.filter((m) => teamMatches(m.homeTeam, opts.homeTeam!));
    }
    if (opts.awayTeam) {
      results = results.filter((m) => teamMatches(m.awayTeam, opts.awayTeam!));
    }
    if (opts.competition) {
      const comp = opts.competition.toLowerCase();
      results = results.filter((m) => m.competition.toLowerCase().includes(comp));
    }
    if (opts.season) {
      results = results.filter((m) => m.season === opts.season);
    }
    if (opts.dateFrom) {
      results = results.filter((m) => m.date >= opts.dateFrom!);
    }
    if (opts.dateTo) {
      results = results.filter((m) => m.date <= opts.dateTo!);
    }

    results.sort((a, b) => b.date.localeCompare(a.date));
    return results.slice(0, opts.limit || 50);
  }

  headToHead(team1: string, team2: string): {
    matches: Match[];
    team1Wins: number;
    team2Wins: number;
    draws: number;
    team1Goals: number;
    team2Goals: number;
  } {
    const matches = this.matches.filter(
      (m) =>
        (teamMatches(m.homeTeam, team1) && teamMatches(m.awayTeam, team2)) ||
        (teamMatches(m.homeTeam, team2) && teamMatches(m.awayTeam, team1))
    );
    matches.sort((a, b) => b.date.localeCompare(a.date));

    let team1Wins = 0;
    let team2Wins = 0;
    let draws = 0;
    let team1Goals = 0;
    let team2Goals = 0;

    for (const m of matches) {
      const t1Home = teamMatches(m.homeTeam, team1);
      const t1g = t1Home ? m.homeGoals : m.awayGoals;
      const t2g = t1Home ? m.awayGoals : m.homeGoals;
      team1Goals += t1g;
      team2Goals += t2g;
      if (t1g > t2g) team1Wins++;
      else if (t2g > t1g) team2Wins++;
      else draws++;
    }

    return { matches: matches.slice(0, 50), team1Wins, team2Wins, draws, team1Goals, team2Goals };
  }

  teamStats(
    team: string,
    opts?: { season?: number; competition?: string; homeOnly?: boolean; awayOnly?: boolean }
  ): {
    matches: number;
    wins: number;
    draws: number;
    losses: number;
    goalsFor: number;
    goalsAgainst: number;
    points: number;
  } {
    let filtered = this.matches.filter((m) => {
      const isHome = teamMatches(m.homeTeam, team);
      const isAway = teamMatches(m.awayTeam, team);
      if (!isHome && !isAway) return false;
      if (opts?.homeOnly && !isHome) return false;
      if (opts?.awayOnly && !isAway) return false;
      return true;
    });

    if (opts?.season) filtered = filtered.filter((m) => m.season === opts.season);
    if (opts?.competition) {
      const comp = opts.competition.toLowerCase();
      filtered = filtered.filter((m) => m.competition.toLowerCase().includes(comp));
    }

    let wins = 0,
      draws = 0,
      losses = 0,
      goalsFor = 0,
      goalsAgainst = 0;

    for (const m of filtered) {
      const isHome = teamMatches(m.homeTeam, team);
      const gf = isHome ? m.homeGoals : m.awayGoals;
      const ga = isHome ? m.awayGoals : m.homeGoals;
      goalsFor += gf;
      goalsAgainst += ga;
      if (gf > ga) wins++;
      else if (gf < ga) losses++;
      else draws++;
    }

    return {
      matches: filtered.length,
      wins,
      draws,
      losses,
      goalsFor,
      goalsAgainst,
      points: wins * 3 + draws,
    };
  }

  searchPlayers(opts: {
    name?: string;
    nationality?: string;
    club?: string;
    position?: string;
    minOverall?: number;
    maxOverall?: number;
    limit?: number;
  }): Player[] {
    let results = this.players;

    if (opts.name) {
      const q = opts.name.toLowerCase();
      results = results.filter((p) => p.name.toLowerCase().includes(q));
    }
    if (opts.nationality) {
      const q = opts.nationality.toLowerCase();
      results = results.filter((p) => p.nationality.toLowerCase().includes(q));
    }
    if (opts.club) {
      const q = opts.club.toLowerCase();
      results = results.filter((p) => p.club.toLowerCase().includes(q));
    }
    if (opts.position) {
      const q = opts.position.toLowerCase();
      results = results.filter((p) => p.position.toLowerCase().includes(q));
    }
    if (opts.minOverall !== undefined) {
      results = results.filter((p) => p.overall >= opts.minOverall!);
    }
    if (opts.maxOverall !== undefined) {
      results = results.filter((p) => p.overall <= opts.maxOverall!);
    }

    results.sort((a, b) => b.overall - a.overall);
    return results.slice(0, opts.limit || 50);
  }

  competitionStandings(
    season: number,
    competition?: string
  ): {
    team: string;
    matches: number;
    wins: number;
    draws: number;
    losses: number;
    goalsFor: number;
    goalsAgainst: number;
    goalDifference: number;
    points: number;
  }[] {
    const comp = competition?.toLowerCase() || "brasileir";
    const seasonMatches = this.matches.filter(
      (m) => m.season === season && m.competition.toLowerCase().includes(comp)
    );

    const standings = new Map<
      string,
      {
        matches: number;
        wins: number;
        draws: number;
        losses: number;
        goalsFor: number;
        goalsAgainst: number;
      }
    >();

    for (const m of seasonMatches) {
      for (const [team, gf, ga] of [
        [m.homeTeam, m.homeGoals, m.awayGoals] as const,
        [m.awayTeam, m.awayGoals, m.homeGoals] as const,
      ]) {
        const s = standings.get(team) || {
          matches: 0,
          wins: 0,
          draws: 0,
          losses: 0,
          goalsFor: 0,
          goalsAgainst: 0,
        };
        s.matches++;
        s.goalsFor += gf;
        s.goalsAgainst += ga;
        if (gf > ga) s.wins++;
        else if (gf < ga) s.losses++;
        else s.draws++;
        standings.set(team, s);
      }
    }

    return Array.from(standings.entries())
      .map(([team, s]) => ({
        team,
        ...s,
        goalDifference: s.goalsFor - s.goalsAgainst,
        points: s.wins * 3 + s.draws,
      }))
      .sort((a, b) => b.points - a.points || b.goalDifference - a.goalDifference || b.goalsFor - a.goalsFor);
  }

  biggestWins(opts?: { competition?: string; limit?: number }): Match[] {
    let filtered = this.matches;
    if (opts?.competition) {
      const comp = opts.competition.toLowerCase();
      filtered = filtered.filter((m) => m.competition.toLowerCase().includes(comp));
    }
    return [...filtered]
      .sort((a, b) => Math.abs(b.homeGoals - b.awayGoals) - Math.abs(a.homeGoals - a.awayGoals))
      .slice(0, opts?.limit || 20);
  }

  averageGoals(opts?: { competition?: string; season?: number }): {
    totalMatches: number;
    totalGoals: number;
    avgGoalsPerMatch: number;
    homeWinRate: number;
    awayWinRate: number;
    drawRate: number;
  } {
    let filtered = this.matches;
    if (opts?.competition) {
      const comp = opts.competition.toLowerCase();
      filtered = filtered.filter((m) => m.competition.toLowerCase().includes(comp));
    }
    if (opts?.season) filtered = filtered.filter((m) => m.season === opts.season);

    const totalMatches = filtered.length;
    const totalGoals = filtered.reduce((s, m) => s + m.homeGoals + m.awayGoals, 0);
    const homeWins = filtered.filter((m) => m.homeGoals > m.awayGoals).length;
    const awayWins = filtered.filter((m) => m.awayGoals > m.homeGoals).length;
    const draws = filtered.filter((m) => m.homeGoals === m.awayGoals).length;

    return {
      totalMatches,
      totalGoals,
      avgGoalsPerMatch: totalMatches > 0 ? Math.round((totalGoals / totalMatches) * 100) / 100 : 0,
      homeWinRate: totalMatches > 0 ? Math.round((homeWins / totalMatches) * 1000) / 10 : 0,
      awayWinRate: totalMatches > 0 ? Math.round((awayWins / totalMatches) * 1000) / 10 : 0,
      drawRate: totalMatches > 0 ? Math.round((draws / totalMatches) * 1000) / 10 : 0,
    };
  }
}
