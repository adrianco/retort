import { competitionMatches, foldText, normalizeTeamName, teamMatches } from "./normalize.js";
import type { Match, MatchFilter, Player, StandingRow, TeamStats } from "./types.js";
import { SoccerDataStore } from "./data-store.js";

export interface PlayerFilter {
  name?: string;
  nationality?: string;
  club?: string;
  position?: string;
  minOverall?: number;
  minPotential?: number;
  limit?: number;
  offset?: number;
}

export interface StatsFilter {
  competition?: string;
  season?: number;
  team?: string;
  from?: string;
  to?: string;
  limit?: number;
}

export interface Paginated<T> {
  total: number;
  offset: number;
  limit: number;
  items: T[];
}

function boundedLimit(value: number | undefined, fallback = 25, maximum = 200): number {
  return Math.max(1, Math.min(maximum, Math.trunc(value ?? fallback)));
}

function resultForTeam(match: Match, team: string): "win" | "draw" | "loss" {
  const home = teamMatches(match.homeTeamKey, team);
  if (match.homeGoals === match.awayGoals) return "draw";
  const teamWon = home ? match.homeGoals > match.awayGoals : match.awayGoals > match.homeGoals;
  return teamWon ? "win" : "loss";
}

function emptyTeamStats(team: string): TeamStats {
  return { team, matches: 0, wins: 0, draws: 0, losses: 0, goalsFor: 0, goalsAgainst: 0, goalDifference: 0, points: 0, winRate: 0 };
}

export class SoccerService {
  constructor(readonly store: SoccerDataStore) {}

  private canonicalForAnalytics(matches: Match[]): Match[] {
    const groups = new Map<string, Match[]>();
    for (const match of matches) {
      const key = `${match.competition}|${match.season}`;
      const group = groups.get(key) ?? [];
      group.push(match);
      groups.set(key, group);
    }
    return [...groups.values()].flatMap((group) => {
      const competition = group[0]?.competition ?? "";
      const priorities = competition === "Brasileirão Serie A"
        ? ["Brasileirao_Matches.csv", "novo_campeonato_brasileiro.csv", "BR-Football-Dataset.csv"]
        : competition === "Copa do Brasil"
          ? ["Brazilian_Cup_Matches.csv", "BR-Football-Dataset.csv"]
          : competition === "Copa Libertadores"
            ? ["Libertadores_Matches.csv"]
            : ["BR-Football-Dataset.csv"];
      const source = priorities.find((file) => group.some((match) => match.sources.some((entry) => entry.file === file)));
      return source ? group.filter((match) => match.sources.some((entry) => entry.file === source)) : group;
    });
  }

  searchMatches(filter: MatchFilter = {}): Paginated<Match> {
    let matches = this.store.matches.filter((match) => {
      if (filter.team && !teamMatches(match.homeTeamKey, filter.team) && !teamMatches(match.awayTeamKey, filter.team)) return false;
      if (filter.opponent) {
        if (!filter.team) return false;
        const hasPair = (teamMatches(match.homeTeamKey, filter.team) && teamMatches(match.awayTeamKey, filter.opponent)) ||
          (teamMatches(match.awayTeamKey, filter.team) && teamMatches(match.homeTeamKey, filter.opponent));
        if (!hasPair) return false;
      }
      if (filter.homeTeam && !teamMatches(match.homeTeamKey, filter.homeTeam)) return false;
      if (filter.awayTeam && !teamMatches(match.awayTeamKey, filter.awayTeam)) return false;
      if (filter.competition && !competitionMatches(match.competition, filter.competition)) return false;
      if (filter.season !== undefined && match.season !== filter.season) return false;
      if (filter.from && match.date < filter.from) return false;
      if (filter.to && match.date > filter.to) return false;
      if (filter.round && !foldText(match.round ?? "").includes(foldText(filter.round))) return false;
      if (filter.stage && !foldText(match.stage ?? "").includes(foldText(filter.stage))) return false;
      return true;
    });
    if (filter.finals) {
      const maxRounds = new Map<string, number>();
      const roundCounts = new Map<string, Map<number, number>>();
      for (const match of matches) {
        const round = Number(match.round);
        if (Number.isFinite(round)) {
          const key = `${match.competition}|${match.season}`;
          maxRounds.set(key, Math.max(maxRounds.get(key) ?? -Infinity, round));
          const counts = roundCounts.get(key) ?? new Map<number, number>();
          counts.set(round, (counts.get(round) ?? 0) + 1);
          roundCounts.set(key, counts);
        }
      }
      matches = matches.filter((match) => {
        if (foldText(match.stage ?? "") === "final" || foldText(match.round ?? "") === "final") return true;
        const round = Number(match.round);
        const key = `${match.competition}|${match.season}`;
        const maxRound = maxRounds.get(key);
        return Number.isFinite(round) && round === maxRound && (roundCounts.get(key)?.get(round) ?? Infinity) <= 2;
      });
    }
    matches = matches.sort((a, b) => filter.newestFirst === false ? a.date.localeCompare(b.date) : b.date.localeCompare(a.date));
    const offset = Math.max(0, Math.trunc(filter.offset ?? 0));
    const limit = boundedLimit(filter.limit);
    return { total: matches.length, offset, limit, items: matches.slice(offset, offset + limit) };
  }

  teamStats(team: string, filter: Omit<MatchFilter, "team" | "opponent" | "limit" | "offset"> & { venue?: "home" | "away" | "all" } = {}): TeamStats {
    const stats = emptyTeamStats(team);
    const allMatches = this.canonicalForAnalytics(this.store.matches.filter((match) => {
      const isHome = teamMatches(match.homeTeamKey, team);
      const isAway = teamMatches(match.awayTeamKey, team);
      if (!isHome && !isAway) return false;
      if (filter.venue === "home" && !isHome) return false;
      if (filter.venue === "away" && !isAway) return false;
      if (filter.competition && !competitionMatches(match.competition, filter.competition)) return false;
      if (filter.season !== undefined && match.season !== filter.season) return false;
      if (filter.from && match.date < filter.from) return false;
      if (filter.to && match.date > filter.to) return false;
      return true;
    }));
    for (const match of allMatches) {
      const home = teamMatches(match.homeTeamKey, team);
      stats.matches++;
      stats.goalsFor += home ? match.homeGoals : match.awayGoals;
      stats.goalsAgainst += home ? match.awayGoals : match.homeGoals;
      const result = resultForTeam(match, team);
      if (result === "win") stats.wins++;
      else if (result === "draw") stats.draws++;
      else stats.losses++;
    }
    stats.goalDifference = stats.goalsFor - stats.goalsAgainst;
    stats.points = stats.wins * 3 + stats.draws;
    stats.winRate = stats.matches ? Number(((stats.wins / stats.matches) * 100).toFixed(1)) : 0;
    return stats;
  }

  headToHead(teamA: string, teamB: string, filter: Omit<MatchFilter, "team" | "opponent"> = {}) {
    const searched = this.searchMatches({ ...filter, team: teamA, opponent: teamB, limit: 200 });
    const matches = this.canonicalForAnalytics(searched.items);
    let teamAWins = 0;
    let teamBWins = 0;
    let draws = 0;
    for (const match of matches) {
      const outcome = resultForTeam(match, teamA);
      if (outcome === "win") teamAWins++;
      else if (outcome === "loss") teamBWins++;
      else draws++;
    }
    return { teamA, teamB, matches: matches.length, teamAWins, teamBWins, draws, results: matches };
  }

  searchPlayers(filter: PlayerFilter = {}): Paginated<Player> {
    const name = foldText(filter.name ?? "");
    const nationality = foldText(filter.nationality ?? "");
    const club = normalizeTeamName(filter.club ?? "");
    const position = foldText(filter.position ?? "");
    const players = this.store.players.filter((player) => {
      if (name && !foldText(player.name).includes(name)) return false;
      if (nationality && !foldText(player.nationality).includes(nationality)) return false;
      if (club && !teamMatches(normalizeTeamName(player.club), club)) return false;
      if (position && !foldText(player.position).includes(position)) return false;
      if (filter.minOverall !== undefined && (player.overall ?? -Infinity) < filter.minOverall) return false;
      if (filter.minPotential !== undefined && (player.potential ?? -Infinity) < filter.minPotential) return false;
      return true;
    }).sort((a, b) => (b.overall ?? -1) - (a.overall ?? -1) || a.name.localeCompare(b.name));
    const offset = Math.max(0, Math.trunc(filter.offset ?? 0));
    const limit = boundedLimit(filter.limit);
    return { total: players.length, offset, limit, items: players.slice(offset, offset + limit) };
  }

  standings(season: number, competition = "Brasileirão Serie A"): StandingRow[] {
    const matches = this.canonicalForAnalytics(this.store.matches.filter((match) => match.season === season && competitionMatches(match.competition, competition)));
    const table = new Map<string, TeamStats>();
    const display = new Map<string, string>();
    for (const match of matches) {
      display.set(match.homeTeamKey, match.homeTeam);
      display.set(match.awayTeamKey, match.awayTeam);
      for (const [key, isHome] of [[match.homeTeamKey, true], [match.awayTeamKey, false]] as const) {
        const row = table.get(key) ?? emptyTeamStats(display.get(key) ?? key);
        row.matches++;
        row.goalsFor += isHome ? match.homeGoals : match.awayGoals;
        row.goalsAgainst += isHome ? match.awayGoals : match.homeGoals;
        if (match.homeGoals === match.awayGoals) row.draws++;
        else if ((isHome && match.homeGoals > match.awayGoals) || (!isHome && match.awayGoals > match.homeGoals)) row.wins++;
        else row.losses++;
        table.set(key, row);
      }
    }
    const sorted = [...table.values()];
    for (const row of sorted) {
      row.goalDifference = row.goalsFor - row.goalsAgainst;
      row.points = row.wins * 3 + row.draws;
      row.winRate = row.matches ? Number(((row.wins / row.matches) * 100).toFixed(1)) : 0;
    }
    sorted.sort((a, b) => b.points - a.points || b.wins - a.wins || b.goalDifference - a.goalDifference || b.goalsFor - a.goalsFor || a.team.localeCompare(b.team));
    return sorted.map((row, index) => ({ ...row, position: index + 1 }));
  }

  competitionSummary(competition: string, season?: number) {
    const matches = this.store.matches.filter((match) => competitionMatches(match.competition, competition) && (season === undefined || match.season === season));
    const stages = [...new Set(matches.map((match) => match.stage || match.round).filter((value): value is string => Boolean(value)))];
    const teams = [...new Set(matches.flatMap((match) => [match.homeTeamKey, match.awayTeamKey]))];
    const isLeague = foldText(competition).includes("brasileir") || foldText(competition).includes("serie a");
    const standings = season === undefined || !isLeague ? [] : this.standings(season, competition);
    const finalMatches = season === undefined || isLeague ? [] : this.searchMatches({ competition, season, finals: true, limit: 200, newestFirst: false }).items;
    const finalistScores = new Map<string, { team: string; goals: number }>();
    for (const match of finalMatches) {
      const home = finalistScores.get(match.homeTeamKey) ?? { team: match.homeTeam, goals: 0 };
      const away = finalistScores.get(match.awayTeamKey) ?? { team: match.awayTeam, goals: 0 };
      home.goals += match.homeGoals;
      away.goals += match.awayGoals;
      finalistScores.set(match.homeTeamKey, home);
      finalistScores.set(match.awayTeamKey, away);
    }
    const finalists = [...finalistScores.values()].sort((a, b) => b.goals - a.goals);
    const cupWinner = finalists.length >= 2 && finalists[0]!.goals > finalists[1]!.goals ? finalists[0]!.team : undefined;
    return {
      competition: normalizeCompetitionForDisplay(matches[0]?.competition ?? competition), season,
      matches: matches.length, teams: teams.length, stages, champion: standings[0]?.team ?? cupWinner,
      finalists, finalMatches,
      firstMatch: matches.at(0)?.date, lastMatch: matches.at(-1)?.date,
      standings: standings.slice(0, 20)
    };
  }

  statistics(filter: StatsFilter = {}) {
    const matches = this.canonicalForAnalytics(this.store.matches.filter((match) => {
      if (filter.competition && !competitionMatches(match.competition, filter.competition)) return false;
      if (filter.season !== undefined && match.season !== filter.season) return false;
      if (filter.team && !teamMatches(match.homeTeamKey, filter.team) && !teamMatches(match.awayTeamKey, filter.team)) return false;
      if (filter.from && match.date < filter.from) return false;
      if (filter.to && match.date > filter.to) return false;
      return true;
    }));
    const totalGoals = matches.reduce((sum, match) => sum + match.homeGoals + match.awayGoals, 0);
    const homeWins = matches.filter((match) => match.homeGoals > match.awayGoals).length;
    const awayWins = matches.filter((match) => match.awayGoals > match.homeGoals).length;
    const draws = matches.length - homeWins - awayWins;
    const biggestVictories = [...matches]
      .sort((a, b) => Math.abs(b.homeGoals - b.awayGoals) - Math.abs(a.homeGoals - a.awayGoals) || b.date.localeCompare(a.date))
      .slice(0, boundedLimit(filter.limit, 10, 50))
      .map((match) => ({ ...match, margin: Math.abs(match.homeGoals - match.awayGoals) }));
    return {
      matches: matches.length,
      totalGoals,
      averageGoals: matches.length ? Number((totalGoals / matches.length).toFixed(2)) : 0,
      homeWins, awayWins, draws,
      homeWinRate: matches.length ? Number(((homeWins / matches.length) * 100).toFixed(1)) : 0,
      awayWinRate: matches.length ? Number(((awayWins / matches.length) * 100).toFixed(1)) : 0,
      drawRate: matches.length ? Number(((draws / matches.length) * 100).toFixed(1)) : 0,
      biggestVictories
    };
  }

  relationships(team: string, season?: number) {
    const key = normalizeTeamName(team);
    const matches = this.store.matches.filter((match) => (match.homeTeamKey === key || match.awayTeamKey === key) && (season === undefined || match.season === season));
    const players = this.store.players.filter((player) => teamMatches(normalizeTeamName(player.club), team));
    const competitions = [...new Set(matches.map((match) => match.competition))];
    const opponents = [...new Set(matches.map((match) => match.homeTeamKey === key ? match.awayTeam : match.homeTeam))];
    return {
      root: { type: "team", id: key, label: team },
      nodes: [
        ...competitions.map((label) => ({ type: "competition", id: foldText(label), label })),
        ...opponents.map((label) => ({ type: "team", id: normalizeTeamName(label), label })),
        ...players.map((player) => ({ type: "player", id: player.id, label: player.name }))
      ],
      edges: [
        ...competitions.map((label) => ({ from: key, to: foldText(label), relationship: "played_in" })),
        ...opponents.map((label) => ({ from: key, to: normalizeTeamName(label), relationship: "played_against" })),
        ...players.map((player) => ({ from: player.id, to: key, relationship: "plays_for" }))
      ],
      counts: { matches: matches.length, competitions: competitions.length, opponents: opponents.length, players: players.length }
    };
  }
}

function normalizeCompetitionForDisplay(value: string): string {
  return value;
}
