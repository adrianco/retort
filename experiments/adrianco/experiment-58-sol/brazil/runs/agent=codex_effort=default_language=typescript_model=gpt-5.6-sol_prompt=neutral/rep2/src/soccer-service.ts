import { includesNormalized, normalizeCompetition, normalizeTeamName, normalizeText, parseSoccerDate } from "./normalize.js";
import { SoccerKnowledgeBase } from "./knowledge-base.js";
import type {
  MatchFilters,
  Player,
  PlayerFilters,
  QueryResult,
  SoccerMatch,
  Standing,
  TeamRecord,
} from "./types.js";

const DERBIES = [
  ["flamengo", "fluminense"], ["flamengo", "vasco"], ["flamengo", "botafogo"],
  ["corinthians", "palmeiras"], ["corinthians", "sao paulo"], ["palmeiras", "sao paulo"],
  ["gremio", "internacional"], ["atletico mg", "cruzeiro"], ["bahia", "vitoria"],
  ["santos", "sao paulo"], ["santos", "corinthians"], ["santos", "palmeiras"],
] as const;

function boundedLimit(value: number | undefined, fallback = 25, maximum = 200): number {
  if (value === undefined) return fallback;
  return Math.max(1, Math.min(maximum, Math.floor(value)));
}

function formatMatch(match: SoccerMatch): string {
  const context = [match.competition, match.stage ?? (match.round ? `Round ${match.round}` : undefined)]
    .filter(Boolean)
    .join(" · ");
  return `- ${match.date}: ${match.homeTeam} ${match.homeGoals}-${match.awayGoals} ${match.awayTeam} (${context})`;
}

function emptyRecord(team: string): TeamRecord {
  return { team, matches: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0, goalDifference: 0, points: 0, winRate: 0 };
}

function addMatchToRecord(record: TeamRecord, match: SoccerMatch, teamKey: string): void {
  const atHome = match.homeTeamKey === teamKey;
  const goalsFor = atHome ? match.homeGoals : match.awayGoals;
  const goalsAgainst = atHome ? match.awayGoals : match.homeGoals;
  record.matches += 1;
  record.goalsFor += goalsFor;
  record.goalsAgainst += goalsAgainst;
  if (goalsFor > goalsAgainst) record.wins += 1;
  else if (goalsFor < goalsAgainst) record.losses += 1;
  else record.draws += 1;
  record.points = record.wins * 3 + record.draws;
  record.goalDifference = record.goalsFor - record.goalsAgainst;
  record.winRate = record.matches === 0 ? 0 : Number(((record.wins / record.matches) * 100).toFixed(1));
}

function positionMatches(actual: string | undefined, requested: string): boolean {
  const value = normalizeText(actual ?? "").toUpperCase();
  const key = normalizeText(requested);
  if (["forward", "forwards", "attacker", "attackers", "atacante", "atacantes"].includes(key)) {
    return ["ST", "CF", "LF", "RF", "LW", "RW"].includes(value);
  }
  if (["midfielder", "midfielders", "meio campo"].includes(key)) {
    return value.includes("M") && !["LWB", "RWB"].includes(value);
  }
  if (["defender", "defenders", "defensor", "defensores"].includes(key)) {
    return ["LB", "LWB", "CB", "LCB", "RCB", "RB", "RWB"].includes(value);
  }
  if (["goalkeeper", "goalkeepers", "keeper", "keepers", "goleiro", "goleiros"].includes(key)) {
    return value === "GK";
  }
  return normalizeText(actual ?? "").includes(key);
}

export class SoccerService {
  constructor(readonly graph: SoccerKnowledgeBase) {}

  searchMatches(filters: MatchFilters): QueryResult<SoccerMatch[]> {
    const teamKey = filters.team ? this.requireTeam(filters.team) : undefined;
    const opponentKey = filters.opponent ? this.requireTeam(filters.opponent) : undefined;
    const competitionKey = filters.competition ? this.requireCompetition(filters.competition) : undefined;
    const from = filters.dateFrom ? parseSoccerDate(filters.dateFrom).timestamp : undefined;
    const to = filters.dateTo ? parseSoccerDate(filters.dateTo).timestamp : undefined;
    let matches = teamKey ? [...(this.graph.teamMatches.get(teamKey) ?? [])] : [...this.graph.matches];
    matches = matches.filter((match) => {
      if (teamKey && match.homeTeamKey !== teamKey && match.awayTeamKey !== teamKey) return false;
      if (opponentKey && match.homeTeamKey !== opponentKey && match.awayTeamKey !== opponentKey) return false;
      if (teamKey && opponentKey && teamKey === opponentKey) return false;
      if (competitionKey && normalizeCompetition(match.competition) !== competitionKey) return false;
      if (filters.season !== undefined && match.season !== filters.season) return false;
      if (from !== undefined && match.timestamp < from) return false;
      if (to !== undefined && match.timestamp > to) return false;
      if (filters.venue === "home" && teamKey && match.homeTeamKey !== teamKey) return false;
      if (filters.venue === "away" && teamKey && match.awayTeamKey !== teamKey) return false;
      if (filters.stage && !includesNormalized(`${match.stage ?? ""} ${match.round ?? ""}`, filters.stage)) return false;
      return true;
    });

    if (filters.stage && normalizeText(filters.stage).includes("final") && competitionKey === "copa do brasil" && matches.length === 0) {
      const cupMatches = (this.graph.competitionMatches.get(competitionKey) ?? []).filter((match) =>
        filters.season === undefined || match.season === filters.season,
      );
      const maxRoundBySeason = new Map<number, number>();
      for (const match of cupMatches) {
        const round = Number(match.round);
        if (Number.isFinite(round)) maxRoundBySeason.set(match.season, Math.max(maxRoundBySeason.get(match.season) ?? 0, round));
      }
      matches = cupMatches.filter((match) => Number(match.round) === maxRoundBySeason.get(match.season));
    }

    const total = matches.length;
    const limited = matches.sort((a, b) => b.timestamp - a.timestamp).slice(0, boundedLimit(filters.limit));
    const description = [filters.team, filters.opponent ? `vs ${filters.opponent}` : undefined, filters.competition, filters.season]
      .filter((value) => value !== undefined)
      .join(" ");
    const formatted = `${total} match${total === 1 ? "" : "es"} found${description ? ` for ${description}` : ""}.\n${limited.map(formatMatch).join("\n")}${total > limited.length ? `\n... ${total - limited.length} more matches` : ""}`;
    return { kind: "matches", summary: `${total} matches found`, data: limited, formatted };
  }

  headToHead(team1: string, team2: string, options: { competition?: string; season?: number; limit?: number } = {}): QueryResult<{
    record: { team1Wins: number; team2Wins: number; draws: number; matches: number };
    matches: SoccerMatch[];
  }> {
    const firstKey = this.requireTeam(team1);
    const secondKey = this.requireTeam(team2);
    if (firstKey === secondKey) throw new Error("Head-to-head teams must be different");
    const result = this.searchMatches({ team: team1, opponent: team2, ...options, limit: options.limit ?? 50 });
    let team1Wins = 0;
    let team2Wins = 0;
    let draws = 0;
    const allMatches = (this.graph.teamMatches.get(firstKey) ?? []).filter((match) => {
      const hasSecond = match.homeTeamKey === secondKey || match.awayTeamKey === secondKey;
      const competitionMatches = !options.competition || normalizeCompetition(match.competition) === this.requireCompetition(options.competition);
      return hasSecond && competitionMatches && (options.season === undefined || match.season === options.season);
    });
    for (const match of allMatches) {
      if (match.homeGoals === match.awayGoals) draws += 1;
      else {
        const winner = match.homeGoals > match.awayGoals ? match.homeTeamKey : match.awayTeamKey;
        if (winner === firstKey) team1Wins += 1;
        else team2Wins += 1;
      }
    }
    const firstName = this.graph.displayTeam(firstKey);
    const secondName = this.graph.displayTeam(secondKey);
    const record = { team1Wins, team2Wins, draws, matches: allMatches.length };
    return {
      kind: "head-to-head",
      summary: `${firstName} vs ${secondName}: ${allMatches.length} matches`,
      data: { record, matches: result.data },
      formatted: `${firstName} vs ${secondName}\nHead-to-head: ${firstName} ${team1Wins} wins, ${secondName} ${team2Wins} wins, ${draws} draws\n${result.data.map(formatMatch).join("\n")}`,
    };
  }

  teamStatistics(team: string, options: { competition?: string; season?: number; venue?: "home" | "away" | "either" } = {}): QueryResult<TeamRecord> {
    const teamKey = this.requireTeam(team);
    const competitionKey = options.competition ? this.requireCompetition(options.competition) : undefined;
    const sourceMatches = competitionKey && options.season !== undefined
      ? this.graph.matchesForStandings(competitionKey, options.season)
      : (this.graph.teamMatches.get(teamKey) ?? []);
    const matches = sourceMatches.filter((match) => {
      if (match.homeTeamKey !== teamKey && match.awayTeamKey !== teamKey) return false;
      if (competitionKey && normalizeCompetition(match.competition) !== competitionKey) return false;
      if (options.season !== undefined && match.season !== options.season) return false;
      if (options.venue === "home" && match.homeTeamKey !== teamKey) return false;
      if (options.venue === "away" && match.awayTeamKey !== teamKey) return false;
      return true;
    });
    const record = emptyRecord(this.graph.displayTeam(teamKey));
    for (const match of matches) addMatchToRecord(record, match, teamKey);
    const scope = [options.venue && options.venue !== "either" ? options.venue : undefined, options.season, options.competition]
      .filter((value) => value !== undefined).join(" ");
    return {
      kind: "team-statistics",
      summary: `${record.team}: ${record.matches} matches`,
      data: record,
      formatted: `${record.team}${scope ? ` ${scope}` : ""} record\n- Matches: ${record.matches}\n- Wins: ${record.wins}, Draws: ${record.draws}, Losses: ${record.losses}\n- Goals For: ${record.goalsFor}, Goals Against: ${record.goalsAgainst}\n- Win rate: ${record.winRate}%`,
    };
  }

  searchPlayers(filters: PlayerFilters): QueryResult<Player[]> {
    const name = filters.name ? normalizeText(filters.name) : undefined;
    const nationality = filters.nationality ? normalizeText(filters.nationality) : undefined;
    const club = filters.club ? normalizeTeamName(filters.club) : undefined;
    const position = filters.position ? normalizeText(filters.position) : undefined;
    const matches = this.graph.players
      .filter((player) => {
        if (name && !player.nameKey.includes(name)) return false;
        if (nationality && !player.nationalityKey.includes(nationality === "brazilian" ? "brazil" : nationality)) return false;
        if (club && player.clubKey !== club && !player.clubKey?.includes(club)) return false;
        if (position && !positionMatches(player.position, position)) return false;
        if (filters.minOverall !== undefined && (player.overall ?? 0) < filters.minOverall) return false;
        return true;
      })
      .sort((a, b) => (b.overall ?? -1) - (a.overall ?? -1) || a.name.localeCompare(b.name));
    const total = matches.length;
    const limited = matches.slice(0, boundedLimit(filters.limit, 25, 250));
    const lines = limited.map((player, index) =>
      `${index + 1}. ${player.name} — Overall: ${player.overall ?? "N/A"}, Position: ${player.position ?? "N/A"}, Club: ${player.club ?? "Free agent"}, Nationality: ${player.nationality}`,
    );
    return {
      kind: "players",
      summary: `${total} players found`,
      data: limited,
      formatted: total === 0
        ? "No players found for the requested filters in the provided FIFA dataset."
        : `${total} player${total === 1 ? "" : "s"} found.\n${lines.join("\n")}${total > limited.length ? `\n... ${total - limited.length} more players` : ""}`,
    };
  }

  standings(season: number, competition = "Brasileirão"): QueryResult<Standing[]> {
    const competitionKey = this.requireCompetition(competition);
    const matches = this.graph.matchesForStandings(competitionKey, season);
    if (matches.length === 0) throw new Error(`No ${competition} matches found for ${season}`);
    const records = new Map<string, TeamRecord>();
    for (const match of matches) {
      for (const teamKey of [match.homeTeamKey, match.awayTeamKey]) {
        const record = records.get(teamKey) ?? emptyRecord(this.graph.displayTeam(teamKey));
        addMatchToRecord(record, match, teamKey);
        records.set(teamKey, record);
      }
    }
    const standings: Standing[] = [...records.values()]
      .sort((a, b) => b.points - a.points || b.wins - a.wins || b.goalDifference - a.goalDifference || b.goalsFor - a.goalsFor || a.team.localeCompare(b.team))
      .map((record, index) => ({ position: index + 1, ...record }));
    const competitionName = this.graph.competitionNames.get(competitionKey) ?? competition;
    return {
      kind: "standings",
      summary: `${season} ${competitionName} standings (${matches.length} matches)`,
      data: standings,
      formatted: `${season} ${competitionName} standings\n${standings.map((entry) => `${entry.position}. ${entry.team} — ${entry.points} pts (${entry.wins}W, ${entry.draws}D, ${entry.losses}L, GD ${entry.goalDifference >= 0 ? "+" : ""}${entry.goalDifference})`).join("\n")}`,
    };
  }

  competitionStatistics(options: { competition?: string; season?: number; limit?: number } = {}): QueryResult<{
    matches: number; goals: number; averageGoals: number; homeWins: number; awayWins: number; draws: number; homeWinRate: number; biggestWins: SoccerMatch[];
  }> {
    const competitionKey = options.competition ? this.requireCompetition(options.competition) : undefined;
    const matches = this.graph.matches.filter((match) =>
      (!competitionKey || normalizeCompetition(match.competition) === competitionKey) &&
      (options.season === undefined || match.season === options.season),
    );
    if (matches.length === 0) throw new Error("No matches found for the requested scope");
    let goals = 0, homeWins = 0, awayWins = 0, draws = 0;
    for (const match of matches) {
      goals += match.homeGoals + match.awayGoals;
      if (match.homeGoals > match.awayGoals) homeWins += 1;
      else if (match.homeGoals < match.awayGoals) awayWins += 1;
      else draws += 1;
    }
    const biggestWins = [...matches]
      .sort((a, b) => Math.abs(b.homeGoals - b.awayGoals) - Math.abs(a.homeGoals - a.awayGoals) || b.timestamp - a.timestamp)
      .slice(0, boundedLimit(options.limit, 10, 50));
    const data = {
      matches: matches.length,
      goals,
      averageGoals: Number((goals / matches.length).toFixed(2)),
      homeWins,
      awayWins,
      draws,
      homeWinRate: Number(((homeWins / matches.length) * 100).toFixed(1)),
      biggestWins,
    };
    const scope = [options.competition, options.season].filter(Boolean).join(" ") || "all competitions";
    return {
      kind: "competition-statistics",
      summary: `${matches.length} matches analyzed for ${scope}`,
      data,
      formatted: `${scope} statistics\n- Matches: ${data.matches}\n- Average goals per match: ${data.averageGoals}\n- Home win rate: ${data.homeWinRate}%\n- Home wins: ${homeWins}, Away wins: ${awayWins}, Draws: ${draws}\nBiggest wins:\n${biggestWins.map(formatMatch).join("\n")}`,
    };
  }

  teamProfile(team: string, season?: number): QueryResult<{
    team: string; competitions: string[]; record: TeamRecord; players: Player[];
  }> {
    const teamKey = this.requireTeam(team);
    const matches = (this.graph.teamMatches.get(teamKey) ?? []).filter((match) => season === undefined || match.season === season);
    const competitions = [...new Set(matches.map((match) => match.competition))].sort();
    const record = this.teamStatistics(team, { season }).data;
    const players = [...(this.graph.clubPlayers.get(teamKey) ?? [])].sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0));
    const name = this.graph.displayTeam(teamKey);
    return {
      kind: "team-profile",
      summary: `${name}: ${matches.length} matches, ${competitions.length} competitions, ${players.length} FIFA players`,
      data: { team: name, competitions, record, players },
      formatted: `${name}${season ? ` (${season})` : ""}\nCompetitions: ${competitions.join(", ") || "none"}\nRecord: ${record.wins}W ${record.draws}D ${record.losses}L, ${record.goalsFor} GF, ${record.goalsAgainst} GA\nPlayers in FIFA dataset: ${players.length}${players.length ? `\n${players.slice(0, 25).map((player) => `- ${player.name} (${player.position ?? "N/A"}, ${player.overall ?? "N/A"})`).join("\n")}` : ""}`,
    };
  }

  derbies(season?: number, limit = 50): QueryResult<SoccerMatch[]> {
    const pairs = new Set(DERBIES.map(([a, b]) => [a, b].sort().join("|")));
    const matches = this.graph.matches.filter((match) =>
      pairs.has([match.homeTeamKey, match.awayTeamKey].sort().join("|")) && (season === undefined || match.season === season),
    );
    const limited = matches.slice(0, boundedLimit(limit, 50, 200));
    return { kind: "derbies", summary: `${matches.length} derby matches found`, data: limited, formatted: `${matches.length} derby matches found${season ? ` in ${season}` : ""}.\n${limited.map(formatMatch).join("\n")}` };
  }

  bestRecord(options: { competition?: string; season?: number; venue: "home" | "away" }): QueryResult<TeamRecord[]> {
    const competitionKey = options.competition ? this.requireCompetition(options.competition) : undefined;
    const matches = this.graph.matches.filter((match) =>
      (!competitionKey || normalizeCompetition(match.competition) === competitionKey) && (options.season === undefined || match.season === options.season),
    );
    const teamKeys = new Set(matches.map((match) => options.venue === "home" ? match.homeTeamKey : match.awayTeamKey));
    const records = [...teamKeys].map((key) => this.teamStatistics(this.graph.displayTeam(key), options).data)
      .filter((record) => record.matches > 0)
      .sort((a, b) => b.points - a.points || b.winRate - a.winRate || b.goalDifference - a.goalDifference)
      .slice(0, 20);
    return {
      kind: "best-record",
      summary: `Best ${options.venue} records`,
      data: records,
      formatted: `Best ${options.venue} records${options.season ? ` in ${options.season}` : ""}\n${records.map((record, index) => `${index + 1}. ${record.team} — ${record.points} pts, ${record.wins}W ${record.draws}D ${record.losses}L (${record.winRate}%)`).join("\n")}`,
    };
  }

  private requireTeam(team: string): string {
    const key = this.graph.resolveTeam(team);
    if (!key) throw new Error(`Unknown or ambiguous team: ${team}`);
    return key;
  }

  private requireCompetition(competition: string): string {
    const key = this.graph.resolveCompetition(competition);
    if (!key) throw new Error(`Unknown or ambiguous competition: ${competition}`);
    return key;
  }
}
