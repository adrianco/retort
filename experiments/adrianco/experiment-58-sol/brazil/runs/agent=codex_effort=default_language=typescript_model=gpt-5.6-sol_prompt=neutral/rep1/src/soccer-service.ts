import {
  competitionKey,
  foldText,
  matchesCompetition,
  matchesTeam,
  teamKey,
} from "./normalize.js";
import type { SoccerData } from "./data-loader.js";
import type {
  GraphEdge,
  GraphNode,
  MatchSearchCriteria,
  MatchSearchResult,
  Player,
  PlayerSearchCriteria,
  SoccerGraph,
  SoccerMatch,
  Standing,
  TeamRecord,
} from "./types.js";

export interface TeamStatisticsOptions {
  season?: number;
  competition?: string;
  venue?: "home" | "away" | "all";
}

export interface CompetitionStatistics {
  competition: string;
  season?: number;
  matches: number;
  goals: number;
  averageGoals: number;
  homeWins: number;
  awayWins: number;
  draws: number;
  homeWinRate: number;
  biggestWins: SoccerMatch[];
}

export interface HeadToHeadResult {
  team1: TeamRecord;
  team2: TeamRecord;
  draws: number;
  matches: SoccerMatch[];
}

export interface NaturalLanguageAnswer {
  question: string;
  intent: string;
  answer: string;
  data: unknown;
}

const FORWARD_POSITIONS = new Set(["ST", "CF", "LW", "RW", "LF", "RF", "LS", "RS"]);
const MIDFIELD_POSITIONS = new Set(["CAM", "CM", "CDM", "LM", "RM", "LAM", "RAM", "LCM", "RCM", "LDM", "RDM"]);
const DEFENDER_POSITIONS = new Set(["CB", "LB", "RB", "LWB", "RWB", "LCB", "RCB"]);

const DERBIES = [
  ["Flamengo", "Fluminense"], ["Flamengo", "Vasco da Gama"], ["Flamengo", "Botafogo"],
  ["Corinthians", "Palmeiras"], ["Corinthians", "São Paulo"], ["Palmeiras", "São Paulo"],
  ["Grêmio", "Internacional"], ["Atlético Mineiro", "Cruzeiro"], ["Santos", "São Paulo"],
] as const;

function round(value: number, places = 2): number {
  const factor = 10 ** places;
  return Math.round(value * factor) / factor;
}

function recordFor(team: string, matches: SoccerMatch[]): TeamRecord {
  const key = teamKey(team);
  let wins = 0;
  let draws = 0;
  let losses = 0;
  let goalsFor = 0;
  let goalsAgainst = 0;
  let label = team;

  for (const match of matches) {
    const isHome = match.homeTeamKey === key;
    const isAway = match.awayTeamKey === key;
    if (!isHome && !isAway) continue;
    label = isHome ? match.homeTeam : match.awayTeam;
    const scored = isHome ? match.homeGoals : match.awayGoals;
    const conceded = isHome ? match.awayGoals : match.homeGoals;
    goalsFor += scored;
    goalsAgainst += conceded;
    if (scored > conceded) wins++;
    else if (scored < conceded) losses++;
    else draws++;
  }
  const count = wins + draws + losses;
  return {
    team: label,
    matches: count,
    wins,
    draws,
    losses,
    goalsFor,
    goalsAgainst,
    goalDifference: goalsFor - goalsAgainst,
    points: wins * 3 + draws,
    winRate: count === 0 ? 0 : round((wins / count) * 100, 1),
  };
}

function formatMatch(match: SoccerMatch): string {
  const context = [match.competition, match.round ? `Round ${match.round}` : match.stage]
    .filter(Boolean).join(", ");
  return `${match.date}: ${match.homeTeam} ${match.homeGoals}-${match.awayGoals} ${match.awayTeam} (${context})`;
}

function formatRecord(record: TeamRecord, context?: string): string {
  return [
    `${record.team}${context ? ` ${context}` : ""}:`,
    `- Matches: ${record.matches}`,
    `- Wins: ${record.wins}, Draws: ${record.draws}, Losses: ${record.losses}`,
    `- Goals For: ${record.goalsFor}, Goals Against: ${record.goalsAgainst}`,
    `- Points: ${record.points}, Win rate: ${record.winRate}%`,
  ].join("\n");
}

function positionMatches(playerPosition: string | undefined, query: string): boolean {
  if (!playerPosition) return false;
  const wanted = foldText(query);
  const position = playerPosition.toUpperCase();
  if (wanted.startsWith("forward") || wanted.startsWith("attacker")) return FORWARD_POSITIONS.has(position);
  if (wanted.startsWith("midfield")) return MIDFIELD_POSITIONS.has(position);
  if (wanted.startsWith("defen")) return DEFENDER_POSITIONS.has(position);
  if (wanted.includes("goalkeeper") || wanted === "gk") return position === "GK";
  return position === query.toUpperCase();
}

export class SoccerService {
  readonly data: SoccerData;
  private readonly teamNames: Map<string, string>;

  constructor(data: SoccerData) {
    this.data = data;
    this.teamNames = new Map<string, string>();
    for (const match of data.matches) {
      this.teamNames.set(match.homeTeamKey, match.homeTeam);
      this.teamNames.set(match.awayTeamKey, match.awayTeam);
    }
  }

  searchMatches(criteria: MatchSearchCriteria = {}): MatchSearchResult {
    const limit = Math.min(Math.max(criteria.limit ?? 50, 1), 500);
    const offset = Math.max(criteria.offset ?? 0, 0);
    let matches = this.data.matches.filter((match) => {
      if (criteria.team && !matchesTeam(match.homeTeamKey, criteria.team) && !matchesTeam(match.awayTeamKey, criteria.team)) return false;
      if (criteria.opponent) {
        if (!criteria.team) return false;
        const primaryKey = teamKey(criteria.team);
        const opponentMatches = match.homeTeamKey === primaryKey
          ? matchesTeam(match.awayTeamKey, criteria.opponent)
          : match.awayTeamKey === primaryKey && matchesTeam(match.homeTeamKey, criteria.opponent);
        if (!opponentMatches) return false;
      }
      if (criteria.homeTeam && !matchesTeam(match.homeTeamKey, criteria.homeTeam)) return false;
      if (criteria.awayTeam && !matchesTeam(match.awayTeamKey, criteria.awayTeam)) return false;
      if (criteria.competition && !matchesCompetition(match.competition, criteria.competition)) return false;
      if (criteria.season !== undefined && match.season !== criteria.season) return false;
      if (criteria.dateFrom && match.date < criteria.dateFrom) return false;
      if (criteria.dateTo && match.date > criteria.dateTo) return false;
      if (criteria.stage && !foldText(match.stage ?? "").includes(foldText(criteria.stage))) return false;
      if (criteria.round && !foldText(match.round ?? "").includes(foldText(criteria.round))) return false;
      return true;
    });
    matches = matches.sort((a, b) => criteria.sort === "asc" ? a.date.localeCompare(b.date) : b.date.localeCompare(a.date));
    return { matches: matches.slice(offset, offset + limit), total: matches.length, offset, limit };
  }

  getTeamStatistics(team: string, options: TeamStatisticsOptions = {}): TeamRecord {
    const venue = options.venue ?? "all";
    const matches = this.data.matches.filter((match) => {
      const teamMatches = venue === "home" ? matchesTeam(match.homeTeamKey, team)
        : venue === "away" ? matchesTeam(match.awayTeamKey, team)
          : matchesTeam(match.homeTeamKey, team) || matchesTeam(match.awayTeamKey, team);
      return teamMatches &&
        (options.season === undefined || match.season === options.season) &&
        (!options.competition || matchesCompetition(match.competition, options.competition));
    });
    return recordFor(team, matches);
  }

  compareTeams(team1: string, team2: string, options: Omit<TeamStatisticsOptions, "venue"> = {}): HeadToHeadResult {
    const matches = this.searchMatches({
      team: team1,
      opponent: team2,
      ...(options.season !== undefined ? { season: options.season } : {}),
      ...(options.competition ? { competition: options.competition } : {}),
      limit: 500,
    }).matches;
    const first = recordFor(team1, matches);
    const second = recordFor(team2, matches);
    return { team1: first, team2: second, draws: first.draws, matches };
  }

  searchPlayers(criteria: PlayerSearchCriteria = {}): Player[] {
    const limit = Math.min(Math.max(criteria.limit ?? 20, 1), 500);
    return this.data.players
      .filter((player) => {
        if (criteria.name && !foldText(player.name).includes(foldText(criteria.name))) return false;
        if (criteria.nationality && !foldText(player.nationality).includes(foldText(criteria.nationality))) return false;
        if (criteria.club && (!player.clubKey || !matchesTeam(player.clubKey, criteria.club))) return false;
        if (criteria.position && !positionMatches(player.position, criteria.position)) return false;
        if (criteria.minOverall !== undefined && (player.overall ?? 0) < criteria.minOverall) return false;
        if (criteria.maxAge !== undefined && (player.age ?? Number.POSITIVE_INFINITY) > criteria.maxAge) return false;
        return true;
      })
      .sort((a, b) => (b.overall ?? 0) - (a.overall ?? 0) || a.name.localeCompare(b.name))
      .slice(0, limit);
  }

  getStandings(season: number, competition = "Brasileirão Série A"): Standing[] {
    const matches = this.data.matches.filter((match) => match.season === season && matchesCompetition(match.competition, competition));
    const keys = new Set(matches.flatMap((match) => [match.homeTeamKey, match.awayTeamKey]));
    const standings = [...keys].map((key) => recordFor(this.teamNames.get(key) ?? key, matches));
    standings.sort((a, b) => b.points - a.points || b.wins - a.wins || b.goalDifference - a.goalDifference || b.goalsFor - a.goalsFor || a.team.localeCompare(b.team));
    return standings.map((record, index) => ({ ...record, position: index + 1 }));
  }

  getCompetitionStatistics(competition: string, season?: number): CompetitionStatistics {
    const matches = this.data.matches.filter((match) =>
      matchesCompetition(match.competition, competition) && (season === undefined || match.season === season));
    let homeWins = 0;
    let awayWins = 0;
    let draws = 0;
    let goals = 0;
    for (const match of matches) {
      goals += match.homeGoals + match.awayGoals;
      if (match.homeGoals > match.awayGoals) homeWins++;
      else if (match.homeGoals < match.awayGoals) awayWins++;
      else draws++;
    }
    const biggestWins = [...matches]
      .sort((a, b) => Math.abs(b.homeGoals - b.awayGoals) - Math.abs(a.homeGoals - a.awayGoals) || b.date.localeCompare(a.date))
      .slice(0, 10);
    return {
      competition: matches[0]?.competition ?? competition,
      ...(season !== undefined ? { season } : {}),
      matches: matches.length,
      goals,
      averageGoals: matches.length === 0 ? 0 : round(goals / matches.length),
      homeWins,
      awayWins,
      draws,
      homeWinRate: matches.length === 0 ? 0 : round((homeWins / matches.length) * 100, 1),
      biggestWins,
    };
  }

  bestTeamRecord(season: number, competition: string, venue: "home" | "away" | "all"): TeamRecord | null {
    const filtered = this.data.matches.filter((match) => match.season === season && matchesCompetition(match.competition, competition));
    const keys = new Set(filtered.flatMap((match) => [match.homeTeamKey, match.awayTeamKey]));
    const records = [...keys].map((key) => this.getTeamStatistics(this.teamNames.get(key) ?? key, { season, competition, venue }));
    return records.filter((record) => record.matches > 0)
      .sort((a, b) => b.points - a.points || b.winRate - a.winRate || b.goalDifference - a.goalDifference)[0] ?? null;
  }

  findDerbies(season?: number): SoccerMatch[] {
    return DERBIES.flatMap(([team1, team2]) => this.compareTeams(team1, team2, season === undefined ? {} : { season }).matches)
      .sort((a, b) => b.date.localeCompare(a.date));
  }

  getCompetitionFinals(competition: string, season?: number): SoccerMatch[] {
    const matches = this.data.matches.filter((match) => matchesCompetition(match.competition, competition) && (season === undefined || match.season === season));
    const labelled = matches.filter((match) => {
      const label = foldText(match.stage ?? match.round ?? "");
      return (label === "final" || label.includes("finals")) && !label.includes("semi") && !label.includes("quarter");
    });
    if (labelled.length > 0) return labelled.sort((a, b) => b.date.localeCompare(a.date));

    const bySeason = new Map<number, SoccerMatch[]>();
    for (const match of matches) {
      if (!match.round || !Number.isFinite(Number(match.round))) continue;
      const group = bySeason.get(match.season) ?? [];
      group.push(match);
      bySeason.set(match.season, group);
    }
    return [...bySeason.values()].flatMap((group) => {
      const finalRound = Math.max(...group.map((match) => Number(match.round)));
      const finalists = group.filter((match) => Number(match.round) === finalRound);
      return finalists.length <= 2 ? finalists : [];
    }).sort((a, b) => b.date.localeCompare(a.date));
  }

  competitionsForTeam(team: string): Array<{ competition: string; matches: number; firstSeason: number; lastSeason: number }> {
    const matches = this.data.matches.filter((match) => matchesTeam(match.homeTeamKey, team) || matchesTeam(match.awayTeamKey, team));
    const groups = new Map<string, SoccerMatch[]>();
    for (const match of matches) {
      const group = groups.get(match.competition) ?? [];
      group.push(match);
      groups.set(match.competition, group);
    }
    return [...groups.entries()].map(([competition, group]) => ({
      competition,
      matches: group.length,
      firstSeason: Math.min(...group.map((match) => match.season)),
      lastSeason: Math.max(...group.map((match) => match.season)),
    })).sort((a, b) => b.matches - a.matches);
  }

  exploreGraph(options: { team?: string; player?: string; competition?: string; season?: number; limit?: number }): SoccerGraph {
    const limit = Math.min(Math.max(options.limit ?? 30, 1), 100);
    const matchResult = this.searchMatches({
      ...(options.team ? { team: options.team } : {}),
      ...(options.competition ? { competition: options.competition } : {}),
      ...(options.season !== undefined ? { season: options.season } : {}),
      limit,
    });
    const players = this.searchPlayers({
      ...(options.player ? { name: options.player } : {}),
      ...(options.team ? { club: options.team } : {}),
      limit,
    });
    const nodes = new Map<string, GraphNode>();
    const edges: GraphEdge[] = [];
    const addTeam = (key: string, label: string): string => {
      const id = `team:${key}`;
      nodes.set(id, { id, type: "team", label });
      return id;
    };
    for (const match of matchResult.matches) {
      const matchId = match.id;
      const competitionId = `competition:${competitionKey(match.competition)}`;
      const homeId = addTeam(match.homeTeamKey, match.homeTeam);
      const awayId = addTeam(match.awayTeamKey, match.awayTeam);
      nodes.set(matchId, { id: matchId, type: "match", label: `${match.homeTeam} ${match.homeGoals}-${match.awayGoals} ${match.awayTeam}`, properties: { date: match.date, season: match.season } });
      nodes.set(competitionId, { id: competitionId, type: "competition", label: match.competition });
      edges.push({ from: homeId, to: matchId, type: "HOME_TEAM" }, { from: awayId, to: matchId, type: "AWAY_TEAM" }, { from: matchId, to: competitionId, type: "PLAYED_IN" });
    }
    for (const player of players) {
      const playerId = `player:${player.id}`;
      nodes.set(playerId, { id: playerId, type: "player", label: player.name, properties: { overall: player.overall ?? null, position: player.position ?? null } });
      if (player.club && player.clubKey) edges.push({ from: playerId, to: addTeam(player.clubKey, player.club), type: "PLAYS_FOR" });
    }
    return { nodes: [...nodes.values()], edges, truncated: matchResult.total > limit };
  }

  answerQuestion(question: string): NaturalLanguageAnswer {
    const folded = foldText(question);
    const year = Number(folded.match(/\b(19|20)\d{2}\b/)?.[0]);
    const season = Number.isInteger(year) && year > 1900 ? year : undefined;
    const teams = this.extractTeams(question);
    const competition = folded.includes("libertadores") ? "Copa Libertadores"
      : folded.includes("copa do brasil") ? "Copa do Brasil"
        : folded.includes("brasileir") || folded.includes("serie a") ? "Brasileirão Série A" : undefined;

    if (folded.includes("top scorer") || folded.includes("artilheiro")) {
      return { question, intent: "unsupported_top_scorers", answer: "The supplied datasets contain final match scores but no goal-scorer events, so top scorers cannot be inferred reliably.", data: null };
    }
    if (folded.startsWith("who is ") || folded.startsWith("quem e ")) {
      const name = question.replace(/^\s*(?:who is|quem [ée])\s+/i, "").replace(/[?!.]+$/, "").trim();
      return this.playerAnswer(question, "player_search", this.searchPlayers({ name, limit: 20 }));
    }
    if ((folded.includes("highest rated") || folded.includes("top ")) && (folded.includes("player") || folded.includes("jogador"))) {
      const players = this.searchPlayers({ ...(teams[0] ? { club: teams[0] } : {}), ...(folded.includes("brazil") ? { nationality: "Brazil" } : {}), limit: 20 });
      return this.playerAnswer(question, "top_players", players);
    }
    if (folded.includes("player") || folded.includes("forward") || folded.includes("midfielder") || folded.includes("defender") || folded.includes("goalkeeper")) {
      const position = ["forward", "midfielder", "defender", "goalkeeper"].find((value) => folded.includes(value));
      const players = this.searchPlayers({ ...(teams[0] ? { club: teams[0] } : {}), ...(folded.includes("brazil") ? { nationality: "Brazil" } : {}), ...(position ? { position } : {}), limit: 50 });
      return this.playerAnswer(question, "player_search", players);
    }
    if (folded.includes("standings") || folded.includes("who won") || folded.includes("champion") || folded.includes("relegated")) {
      if (!season) return { question, intent: "standings", answer: "Please include a season year for standings.", data: [] };
      const standings = this.getStandings(season, competition ?? "Brasileirão Série A");
      const selected = folded.includes("relegated") ? standings.slice(-4) : standings;
      const lines = selected.map((team) => `${team.position}. ${team.team} — ${team.points} pts (${team.wins}W ${team.draws}D ${team.losses}L, GD ${team.goalDifference})`);
      return { question, intent: folded.includes("relegated") ? "relegation" : "standings", answer: lines.length ? lines.join("\n") : "No matching standings data was found.", data: selected };
    }
    if ((folded.includes("most goals") || folded.includes("scored the most")) && season) {
      const standings = this.getStandings(season, competition ?? "Brasileirão Série A")
        .sort((a, b) => b.goalsFor - a.goalsFor || b.points - a.points);
      const leader = standings[0];
      return { question, intent: "top_scoring_team", answer: leader ? `${leader.team} scored the most goals: ${leader.goalsFor} in ${leader.matches} matches.` : "No matching season data was found.", data: leader ?? null };
    }
    if ((folded.includes("final") || folded.includes("bracket")) && competition) {
      const matches = folded.includes("final")
        ? this.getCompetitionFinals(competition, season)
        : this.searchMatches({ competition, ...(season ? { season } : {}), limit: 100 }).matches;
      return { question, intent: folded.includes("bracket") ? "competition_bracket" : "competition_finals", answer: matches.map(formatMatch).join("\n") || "No matching tournament matches were found.", data: matches };
    }
    if (folded.includes("average goal") || folded.includes("biggest win") || folded.includes("home win rate")) {
      const stats = this.getCompetitionStatistics(competition ?? "Brasileirão Série A", season);
      const answer = folded.includes("biggest win")
        ? stats.biggestWins.map(formatMatch).join("\n")
        : `${stats.competition}${season ? ` ${season}` : ""}: ${stats.averageGoals} goals per match; home win rate ${stats.homeWinRate}% (${stats.matches} matches).`;
      return { question, intent: "competition_statistics", answer: answer || "No matching matches were found.", data: stats };
    }
    if (folded.includes("best home record") || folded.includes("best away record")) {
      if (!season) return { question, intent: "best_team_record", answer: "Please include a season year.", data: null };
      const venue = folded.includes("away") ? "away" : "home";
      const record = this.bestTeamRecord(season, competition ?? "Brasileirão Série A", venue);
      return { question, intent: "best_team_record", answer: record ? formatRecord(record, `${venue} record`) : "No matching data was found.", data: record };
    }
    if (folded.includes("derb")) {
      const matches = this.findDerbies(season);
      return { question, intent: "derbies", answer: matches.slice(0, 50).map(formatMatch).join("\n") || "No matching derbies were found.", data: matches };
    }
    if (folded.includes("competition") && teams[0]) {
      const competitions = this.competitionsForTeam(teams[0]);
      return { question, intent: "team_competitions", answer: competitions.map((item) => `${item.competition}: ${item.matches} matches (${item.firstSeason}-${item.lastSeason})`).join("\n"), data: competitions };
    }
    if ((folded.includes("record") || folded.includes("statistics")) && teams[0]) {
      const venue = folded.includes("home") ? "home" : folded.includes("away") ? "away" : "all";
      const record = this.getTeamStatistics(teams[0], { ...(season ? { season } : {}), ...(competition ? { competition } : {}), venue });
      return { question, intent: "team_statistics", answer: formatRecord(record, `${venue} record${season ? ` in ${season}` : ""}`), data: record };
    }
    if (teams.length >= 2) {
      const comparison = this.compareTeams(teams[0]!, teams[1]!, { ...(season ? { season } : {}), ...(competition ? { competition } : {}) });
      const latest = comparison.matches[0];
      const answer = folded.includes("last play") || folded.includes("what was the score")
        ? latest ? formatMatch(latest) : "No head-to-head match was found."
        : `${comparison.team1.team} vs ${comparison.team2.team}: ${comparison.team1.wins} wins, ${comparison.team2.wins} wins, ${comparison.draws} draws.\n${comparison.matches.slice(0, 20).map(formatMatch).join("\n")}`;
      return { question, intent: "head_to_head", answer, data: comparison };
    }
    if (teams[0]) {
      const result = this.searchMatches({ team: teams[0], ...(season ? { season } : {}), ...(competition ? { competition } : {}), limit: 50 });
      return { question, intent: "match_search", answer: result.matches.map(formatMatch).join("\n") || "No matching matches were found.", data: result };
    }
    return {
      question,
      intent: "help",
      answer: "I can search matches, compare teams, calculate records and standings, find players, analyze competitions, and explore team/player/competition relationships. Include a team, competition, or season for a specific answer.",
      data: this.data.summary,
    };
  }

  private extractTeams(question: string): string[] {
    const query = ` ${foldText(question)} `;
    return [...this.teamNames.entries()]
      .filter(([key, label]) => query.includes(` ${key} `) || query.includes(` ${foldText(label)} `))
      .sort((a, b) => b[0].length - a[0].length)
      .filter(([key], index, all) => !all.slice(0, index).some(([earlier]) => earlier.includes(key)))
      .map(([, label]) => label)
      .slice(0, 2);
  }

  private playerAnswer(question: string, intent: string, players: Player[]): NaturalLanguageAnswer {
    const answer = players.map((player, index) =>
      `${index + 1}. ${player.name} — Overall: ${player.overall ?? "N/A"}, Position: ${player.position ?? "N/A"}, Club: ${player.club ?? "N/A"}`,
    ).join("\n");
    return { question, intent, answer: answer || "No matching players were found.", data: players };
  }
}
