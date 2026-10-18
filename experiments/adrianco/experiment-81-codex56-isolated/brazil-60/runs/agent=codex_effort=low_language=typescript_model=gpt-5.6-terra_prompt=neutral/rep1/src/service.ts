import { Match, Player, SoccerData, matchesName, normalize } from "./data.js";

export type MatchFilter = { team?: string; opponent?: string; competition?: string; season?: number; from?: string; to?: string; stage?: string; limit?: number };
type DisplayMatch = ReturnType<typeof displayMatch>;
type StandingRow = { team: string; played: number; wins: number; draws: number; losses: number; goalsFor: number; goalsAgainst: number; points: number };

function displayMatch(match: Match) {
  return { date: match.date, competition: match.competition, season: match.season, round: match.round, stage: match.stage, home: match.home, away: match.away, score: `${match.homeGoals}-${match.awayGoals}`, homeGoals: match.homeGoals, awayGoals: match.awayGoals, source: match.source };
}

function isBrasileirao(competition: string): boolean {
  const value = normalize(competition);
  return value.includes("brasileirao") || value === "serie a" || value === "seriea";
}

/** Unlike search normalization, standings must not merge clubs from different states. */
function teamKey(team: string): string {
  return team.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();
}

/** The modern and historical league CSVs overlap from 2012 through 2019. */
function standingsMatches(matches: readonly Match[], competition: string, season: number): Match[] {
  const requested = normalize(competition);
  const inSeason = matches.filter((match) => match.season === season);
  if (isBrasileirao(competition)) {
    const modern = inSeason.filter((match) => match.source === "brasileirao");
    return modern.length ? modern : inSeason.filter((match) => match.source === "historical");
  }
  const namedSources: Record<string, string> = { "copa do brasil": "brazilian-cup", libertadores: "libertadores" };
  const source = namedSources[requested];
  return source ? inSeason.filter((match) => match.source === source) : inSeason.filter((match) => normalize(match.competition).includes(requested));
}

export class SoccerService {
  constructor(readonly data: SoccerData) {}

  findMatches(filter: MatchFilter = {}) {
    const limit = filter.limit ?? 100;
    const matches = this.data.matches.filter((match) =>
      (!filter.team || matchesName(match.home, filter.team) || matchesName(match.away, filter.team)) &&
      (!filter.opponent || matchesName(match.home, filter.opponent) || matchesName(match.away, filter.opponent)) &&
      (!filter.competition || normalize(match.competition).includes(normalize(filter.competition))) &&
      (!filter.season || match.season === filter.season) &&
      (!filter.from || match.date >= filter.from) && (!filter.to || match.date <= filter.to) &&
      (!filter.stage || normalize(match.stage ?? "").includes(normalize(filter.stage))),
    ).sort((a, b) => b.date.localeCompare(a.date));
    return { count: matches.length, matches: matches.slice(0, limit).map(displayMatch), truncated: matches.length > limit };
  }

  teamStats(team: string, filter: Omit<MatchFilter, "team" | "opponent" | "limit"> & { venue?: "home" | "away" | "all" } = {}) {
    const matches = this.findMatches({ ...filter, team, limit: Number.MAX_SAFE_INTEGER }).matches;
    let wins = 0, draws = 0, losses = 0, goalsFor = 0, goalsAgainst = 0;
    for (const match of matches) {
      const atHome = matchesName(match.home, team);
      if ((filter.venue === "home" && !atHome) || (filter.venue === "away" && atHome)) continue;
      const own = atHome ? match.homeGoals : match.awayGoals, opponent = atHome ? match.awayGoals : match.homeGoals;
      goalsFor += own; goalsAgainst += opponent;
      if (own > opponent) wins++; else if (own < opponent) losses++; else draws++;
    }
    const played = wins + draws + losses;
    return { team, venue: filter.venue ?? "all", matches: played, wins, draws, losses, goalsFor, goalsAgainst, points: wins * 3 + draws, winRate: played ? +(wins / played * 100).toFixed(1) : 0 };
  }

  headToHead(teamA: string, teamB: string, filter: Omit<MatchFilter, "team" | "opponent" | "limit"> = {}) {
    const matches = this.findMatches({ ...filter, team: teamA, opponent: teamB, limit: Number.MAX_SAFE_INTEGER }).matches;
    let teamAWins = 0, teamBWins = 0, draws = 0;
    for (const match of matches) {
      const aHome = matchesName(match.home, teamA), a = aHome ? match.homeGoals : match.awayGoals, b = aHome ? match.awayGoals : match.homeGoals;
      if (a > b) teamAWins++; else if (b > a) teamBWins++; else draws++;
    }
    return { teamA, teamB, matches: matches.length, teamAWins, teamBWins, draws, recent: matches.slice(0, 20) };
  }

  standings(competition: string, season: number) {
    const rows = new Map<string, StandingRow>();
    const add = (team: string, goalsFor: number, goalsAgainst: number) => {
      const key = teamKey(team);
      const row = rows.get(key) ?? { team, played: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0, points: 0 };
      row.played++; row.goalsFor += goalsFor; row.goalsAgainst += goalsAgainst;
      if (goalsFor > goalsAgainst) { row.wins++; row.points += 3; } else if (goalsFor === goalsAgainst) { row.draws++; row.points++; } else row.losses++;
      rows.set(key, row);
    };
    for (const match of standingsMatches(this.data.matches, competition, season)) { add(match.home, match.homeGoals, match.awayGoals); add(match.away, match.awayGoals, match.homeGoals); }
    return [...rows.values()].sort((a, b) => b.points - a.points || (b.goalsFor - b.goalsAgainst) - (a.goalsFor - a.goalsAgainst) || b.goalsFor - a.goalsFor || a.team.localeCompare(b.team)).map((row, index) => ({ ...row, position: index + 1 }));
  }

  players(filter: { name?: string; nationality?: string; club?: string; position?: string; limit?: number } = {}) {
    const limit = filter.limit ?? 100;
    const players = this.data.players.filter((player) => (!filter.name || matchesName(player.name, filter.name)) && (!filter.nationality || matchesName(player.nationality, filter.nationality)) && (!filter.club || matchesName(player.club, filter.club)) && (!filter.position || matchesName(player.position, filter.position))).sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0));
    return { count: players.length, players: players.slice(0, limit).map((player: Player) => ({ id: player.id, name: player.name, age: player.age, nationality: player.nationality, overall: player.overall, potential: player.potential, club: player.club, position: player.position })), truncated: players.length > limit };
  }

  aggregate(filter: Omit<MatchFilter, "limit"> = {}) {
    const matches: DisplayMatch[] = this.findMatches({ ...filter, limit: Number.MAX_SAFE_INTEGER }).matches;
    const totalGoals = matches.reduce((total, match) => total + match.homeGoals + match.awayGoals, 0), homeWins = matches.filter((match) => match.homeGoals > match.awayGoals).length, draws = matches.filter((match) => match.homeGoals === match.awayGoals).length;
    const biggestWins = [...matches].sort((a, b) => Math.abs(b.homeGoals - b.awayGoals) - Math.abs(a.homeGoals - a.awayGoals)).slice(0, 10);
    return { matches: matches.length, totalGoals, goalsPerMatch: matches.length ? +(totalGoals / matches.length).toFixed(2) : 0, homeWinRate: matches.length ? +(homeWins / matches.length * 100).toFixed(1) : 0, drawRate: matches.length ? +(draws / matches.length * 100).toFixed(1) : 0, biggestWins };
  }
}
