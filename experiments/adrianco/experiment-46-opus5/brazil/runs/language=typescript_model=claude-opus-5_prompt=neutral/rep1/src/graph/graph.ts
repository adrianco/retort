/**
 * The in-memory knowledge graph.
 *
 * Nodes are competitions, seasons, teams, matches, players and stadiums; edges
 * are the relationships the CSVs imply (a team *played* a match, a match
 * *belongs to* a competition-season, a player is *contracted to* a club). The
 * whole corpus is ~24k merged matches and ~18k players, so everything is held
 * in plain arrays with hash indexes over the access paths the tools need --
 * that keeps simple lookups in the sub-millisecond range without a database.
 *
 * The graph is immutable once built and loaded exactly once per process.
 */

import { loadMatches } from '../data/loadMatches.js';
import { loadPlayers } from '../data/loadPlayers.js';
import { resolveDataDir } from '../data/paths.js';
import { TeamRegistry, type Team } from '../domain/teams.js';
import { pushInto } from '../util/collections.js';
import { normalizeName } from '../util/text.js';
import { COMPETITIONS, type CompetitionId, type Match, type Player } from '../domain/types.js';

export interface DatasetInfo {
  dataDir: string;
  /** Rows read per source file, before duplicate fixtures were merged. */
  rawMatchRows: Record<string, number>;
  rawPlayerRows: number;
  mergedMatches: number;
  players: number;
  teams: number;
  skippedRows: number;
  loadMillis: number;
  competitions: Array<{
    id: CompetitionId;
    name: string;
    matches: number;
    seasons: number[];
  }>;
}

export class SoccerGraph {
  readonly teams: TeamRegistry;
  readonly matches: readonly Match[];
  readonly players: readonly Player[];
  readonly info: DatasetInfo;

  private readonly matchById = new Map<string, Match>();
  private readonly matchesByTeam = new Map<string, Match[]>();
  private readonly matchesByCompetitionSeason = new Map<string, Match[]>();
  private readonly playersByClub = new Map<string, Player[]>();
  private readonly playersByNationality = new Map<string, Player[]>();
  private readonly playerById = new Map<string, Player>();
  /** Normalized player name -> players, for exact-name lookup. */
  private readonly playersByName = new Map<string, Player[]>();
  private readonly seasonsByCompetition = new Map<CompetitionId, number[]>();

  constructor(
    teams: TeamRegistry,
    matches: Match[],
    players: Player[],
    info: Omit<DatasetInfo, 'competitions'>,
  ) {
    this.teams = teams;
    this.matches = matches;
    this.players = players;

    for (const match of matches) {
      this.matchById.set(match.id, match);
      pushInto(this.matchesByTeam, match.homeTeamId, match);
      if (match.awayTeamId !== match.homeTeamId) pushInto(this.matchesByTeam, match.awayTeamId, match);
      pushInto(this.matchesByCompetitionSeason, `${match.competition}|${match.season}`, match);
    }

    for (const player of players) {
      this.playerById.set(player.id, player);
      pushInto(this.playersByName, normalizeName(player.name), player);
      if (player.clubTeamId) pushInto(this.playersByClub, player.clubTeamId, player);
      if (player.nationality) pushInto(this.playersByNationality, normalizeName(player.nationality), player);
    }

    // One pass over the fixture list collects both the season set and the
    // match count for every competition.
    const seasonsSeen = new Map<CompetitionId, Set<number>>();
    const countsSeen = new Map<CompetitionId, number>();
    for (const match of matches) {
      let seasons = seasonsSeen.get(match.competition);
      if (!seasons) {
        seasons = new Set();
        seasonsSeen.set(match.competition, seasons);
      }
      seasons.add(match.season);
      countsSeen.set(match.competition, (countsSeen.get(match.competition) ?? 0) + 1);
    }

    const competitions: DatasetInfo['competitions'] = [];
    for (const id of Object.keys(COMPETITIONS) as CompetitionId[]) {
      const seasons = [...(seasonsSeen.get(id) ?? [])].sort((a, b) => a - b);
      this.seasonsByCompetition.set(id, seasons);
      competitions.push({
        id,
        name: COMPETITIONS[id].name,
        matches: countsSeen.get(id) ?? 0,
        seasons,
      });
    }

    this.info = { ...info, competitions };
  }

  matchesFor(teamId: string): readonly Match[] {
    return this.matchesByTeam.get(teamId) ?? [];
  }

  matchesIn(competition: CompetitionId, season: number): readonly Match[] {
    return this.matchesByCompetitionSeason.get(`${competition}|${season}`) ?? [];
  }

  seasonsOf(competition: CompetitionId): readonly number[] {
    return this.seasonsByCompetition.get(competition) ?? [];
  }

  getMatch(id: string): Match | undefined {
    return this.matchById.get(id);
  }

  playersOfClub(teamId: string): readonly Player[] {
    return this.playersByClub.get(teamId) ?? [];
  }

  playersOfNationality(nationality: string): readonly Player[] {
    return this.playersByNationality.get(normalizeName(nationality)) ?? [];
  }

  playersNamed(name: string): readonly Player[] {
    return this.playersByName.get(normalizeName(name)) ?? [];
  }

  getPlayer(id: string): Player | undefined {
    return this.playerById.get(id);
  }

  /** Competitions a team has appeared in, with match counts and season span. */
  competitionsOf(teamId: string): Array<{ competition: CompetitionId; matches: number; seasons: number[] }> {
    const byCompetition = new Map<CompetitionId, Set<number>>();
    const counts = new Map<CompetitionId, number>();
    for (const match of this.matchesFor(teamId)) {
      let seasons = byCompetition.get(match.competition);
      if (!seasons) {
        seasons = new Set();
        byCompetition.set(match.competition, seasons);
      }
      seasons.add(match.season);
      counts.set(match.competition, (counts.get(match.competition) ?? 0) + 1);
    }
    return [...byCompetition.entries()]
      .map(([competition, seasons]) => ({
        competition,
        matches: counts.get(competition) ?? 0,
        seasons: [...seasons].sort((a, b) => a - b),
      }))
      .sort((a, b) => b.matches - a.matches);
  }

  /** Every opponent a team has faced, ordered by number of meetings. */
  opponentsOf(teamId: string): Array<{ team: Team; meetings: number }> {
    const counts = new Map<string, number>();
    for (const match of this.matchesFor(teamId)) {
      const other = match.homeTeamId === teamId ? match.awayTeamId : match.homeTeamId;
      if (other === teamId) continue;
      counts.set(other, (counts.get(other) ?? 0) + 1);
    }
    return [...counts.entries()]
      .map(([id, meetings]) => ({ team: this.teams.get(id)!, meetings }))
      .filter((entry) => entry.team !== undefined)
      .sort((a, b) => b.meetings - a.meetings);
  }

  /** Teams that appear in at least one match, i.e. not player-only clubs. */
  teamsWithMatches(): Team[] {
    return [...this.matchesByTeam.keys()]
      .map((id) => this.teams.get(id))
      .filter((team): team is Team => team !== undefined)
      .sort((a, b) => a.name.localeCompare(b.name));
  }

  /** Stadiums recorded in the data, with the teams that hosted there. */
  venuesOf(teamId: string): Array<{ venue: string; matches: number }> {
    const counts = new Map<string, number>();
    for (const match of this.matchesFor(teamId)) {
      if (match.homeTeamId !== teamId || !match.venue) continue;
      counts.set(match.venue, (counts.get(match.venue) ?? 0) + 1);
    }
    return [...counts.entries()]
      .map(([venue, matches]) => ({ venue, matches }))
      .sort((a, b) => b.matches - a.matches);
  }
}

/** Read every CSV and build the graph. Takes roughly a second. */
export function buildGraph(dataDirOverride?: string): SoccerGraph {
  const startedAt = process.hrtime.bigint();
  const dataDir = resolveDataDir(dataDirOverride);
  const teams = new TeamRegistry();

  const matchResult = loadMatches(dataDir, teams);
  const playerResult = loadPlayers(dataDir, teams);

  const loadMillis = Number(process.hrtime.bigint() - startedAt) / 1e6;

  return new SoccerGraph(teams, matchResult.matches, playerResult.players, {
    dataDir,
    rawMatchRows: matchResult.rawCounts,
    rawPlayerRows: playerResult.rawCount,
    mergedMatches: matchResult.matches.length,
    players: playerResult.players.length,
    teams: teams.size,
    skippedRows: matchResult.skipped + playerResult.skipped,
    loadMillis: Math.round(loadMillis),
  });
}

let cached: SoccerGraph | undefined;

/** Process-wide singleton so the CSVs are parsed once. */
export function getGraph(): SoccerGraph {
  cached ??= buildGraph();
  return cached;
}
