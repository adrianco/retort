/**
 * Player search over the FIFA database.
 *
 * Name matching is layered: an exact normalized hit wins, then a prefix or
 * substring hit, then fuzzy similarity. That ordering matters because FIFA
 * abbreviates given names ("Gabriel Barbosa" is filed as "Gabriel Barbosa",
 * but "Alisson" and "Casemiro" are mononyms and "L. Messi" is initialled), so a
 * pure substring search either misses or floods.
 */

import { pushInto } from '../util/collections.js';
import { normalizeName, similarity } from '../util/text.js';
import type { Player, PositionGroup } from '../domain/types.js';
import type { SoccerGraph } from '../graph/graph.js';

export type PlayerSort = 'overall' | 'potential' | 'age' | 'value' | 'wage' | 'name';

export interface PlayerFilter {
  name?: string;
  nationality?: string;
  /** Substring of the raw FIFA club label, or a resolvable team name. */
  club?: string;
  /** Exact FIFA position code, e.g. "LW". */
  position?: string;
  positionGroup?: PositionGroup;
  minOverall?: number;
  maxOverall?: number;
  minAge?: number;
  maxAge?: number;
  sortBy?: PlayerSort;
  ascending?: boolean;
  limit?: number;
}

export interface PlayerSearchResult {
  players: Player[];
  total: number;
  notes: string[];
}

export function searchPlayers(graph: SoccerGraph, filter: PlayerFilter): PlayerSearchResult {
  const notes: string[] = [];
  let candidates = pickCandidates(graph, filter, notes);

  if (filter.nationality) {
    const wanted = normalizeName(filter.nationality);
    candidates = candidates.filter((p) => normalizeName(p.nationality) === wanted);
  }
  if (filter.club) {
    candidates = filterByClub(graph, candidates, filter.club, notes);
  }
  if (filter.position) {
    const wanted = filter.position.trim().toUpperCase();
    candidates = candidates.filter((p) => p.position.toUpperCase() === wanted);
  }
  if (filter.positionGroup) {
    candidates = candidates.filter((p) => p.positionGroup === filter.positionGroup);
  }
  if (filter.minOverall !== undefined) {
    candidates = candidates.filter((p) => (p.overall ?? -1) >= filter.minOverall!);
  }
  if (filter.maxOverall !== undefined) {
    candidates = candidates.filter((p) => (p.overall ?? Infinity) <= filter.maxOverall!);
  }
  if (filter.minAge !== undefined) {
    candidates = candidates.filter((p) => (p.age ?? -1) >= filter.minAge!);
  }
  if (filter.maxAge !== undefined) {
    candidates = candidates.filter((p) => (p.age ?? Infinity) <= filter.maxAge!);
  }

  const sorted = sortPlayers(candidates, filter);
  const limit = filter.limit ?? 25;
  return { players: sorted.slice(0, limit), total: sorted.length, notes };
}

/** Narrow to a starting set using whichever index the filter allows. */
function pickCandidates(graph: SoccerGraph, filter: PlayerFilter, notes: string[]): Player[] {
  if (filter.name) return searchByName(graph, filter.name, notes);
  if (filter.nationality) {
    const indexed = graph.playersOfNationality(filter.nationality);
    if (indexed.length > 0) return [...indexed];
  }
  return [...graph.players];
}

function searchByName(graph: SoccerGraph, name: string, notes: string[]): Player[] {
  const wanted = normalizeName(name);
  // A query of pure punctuation normalises to '', which is a substring of every
  // name and would return an arbitrary player as an exact hit.
  if (wanted === '') return [];
  const exact = graph.playersNamed(name);
  if (exact.length > 0) return [...exact];

  const contains = graph.players.filter((p) => p.normalizedName.includes(wanted));
  if (contains.length > 0) return contains;

  // Last resort: FIFA's initialled forms ("G. Barbosa") mean a full given name
  // may share only the surname, so rank by best token similarity.
  const scored = graph.players
    .map((p) => ({ player: p, score: nameSimilarity(p.normalizedName, wanted) }))
    .filter((entry) => entry.score >= 0.6)
    .sort((a, b) => b.score - a.score);
  if (scored.length > 0) {
    notes.push(`No exact match for "${name}"; showing the closest names in the FIFA database.`);
  }
  return scored.map((entry) => entry.player);
}

/** `normalized` is already accent-folded and lower-cased (Player.normalizedName). */
function nameSimilarity(normalized: string, wanted: string): number {
  const whole = similarity(normalized, wanted);
  const tokens = wanted.split(' ').filter(Boolean);
  const perToken = tokens.map((token) =>
    Math.max(...normalized.split(' ').map((part) => similarity(part, token)), 0),
  );
  const tokenScore = perToken.length === 0 ? 0 : perToken.reduce((a, b) => a + b, 0) / perToken.length;
  return Math.max(whole, tokenScore);
}

/**
 * Club filtering works on the raw FIFA label as well as the canonical team.
 *
 * FIFA 19 licensed only some Brazilian clubs, so a request for a club that is
 * absent should say so rather than return an empty list with no explanation.
 */
function filterByClub(
  graph: SoccerGraph,
  players: Player[],
  club: string,
  notes: string[],
): Player[] {
  const wanted = normalizeName(club);
  if (wanted === '') return [];

  // Tried narrowest first. An unanchored substring alone would answer "Sport"
  // with Sporting CP rather than Sport Recife, and "Nacional" with
  // Internacional -- the fragment has to lose to an exact or whole-word hit.
  const exact = players.filter((p) => p.normalizedClub === wanted);
  if (exact.length > 0) return exact;

  const wholeWord = new RegExp(`\\b${wanted.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`);
  const byWord = players.filter((p) => wholeWord.test(p.normalizedClub));
  if (byWord.length > 0) return byWord;

  const byFragment = players.filter((p) => p.normalizedClub.includes(wanted));
  if (byFragment.length > 0) return byFragment;

  const { team } = graph.teams.resolveQuery(club);
  if (team) {
    const linked = players.filter((p) => p.clubTeamId === team.id);
    if (linked.length > 0) return linked;
    // `players` may already be narrowed by name or nationality, so absence
    // here is not evidence about the corpus. Only claim the club is missing
    // from the file when the whole file has been checked.
    const clubIsAbsent = graph.playersOfClub(team.id).length === 0;
    notes.push(
      clubIsAbsent
        ? `${team.name} appears in the match data but has no squad in the FIFA player file, which covers only the clubs licensed in that edition.`
        : `No player in this result set plays for ${team.name}, though the club does have a squad in the FIFA player file.`,
    );
  } else {
    notes.push(`No club in the FIFA player file matches "${club}".`);
  }
  return [];
}

function sortPlayers(players: Player[], filter: PlayerFilter): Player[] {
  const key = filter.sortBy ?? 'overall';
  const direction = filter.ascending ? 1 : -1;
  const value = (player: Player): number | string => {
    switch (key) {
      case 'potential':
        return player.potential ?? -1;
      case 'age':
        return player.age ?? -1;
      case 'value':
        return player.valueEur ?? -1;
      case 'wage':
        return player.wageEur ?? -1;
      case 'name':
        return player.normalizedName;
      default:
        return player.overall ?? -1;
    }
  };

  return [...players].sort((a, b) => {
    const left = value(a);
    const right = value(b);
    if (typeof left === 'string' || typeof right === 'string') {
      return String(left).localeCompare(String(right)) * (filter.ascending ? 1 : -1);
    }
    return (left - right) * direction || a.name.localeCompare(b.name);
  });
}

export interface ClubSquadSummary {
  club: string;
  teamId?: string;
  players: number;
  /** Mean FIFA overall across the rated players; unrated ones are excluded. */
  averageOverall: number;
  topPlayer?: Player;
}

/** A club's squad, best-rated first. */
export function squadOf(graph: SoccerGraph, teamId: string): Player[] {
  return [...graph.playersOfClub(teamId)].sort(byOverallDescending);
}

export function byOverallDescending(a: Player, b: Player): number {
  return (b.overall ?? 0) - (a.overall ?? 0) || a.name.localeCompare(b.name);
}

/**
 * Squad size and mean rating.
 *
 * Both `club_squad` modes and `team_profile` go through this, so a club's
 * average rating cannot differ depending on which one asked.
 */
export function summariseSquad(name: string, players: readonly Player[]): ClubSquadSummary {
  const rated = players.filter((p) => p.overall !== null);
  const sum = rated.reduce((total, p) => total + (p.overall ?? 0), 0);
  const summary: ClubSquadSummary = {
    club: name,
    players: players.length,
    averageOverall: rated.length === 0 ? 0 : sum / rated.length,
  };
  const top = [...players].sort(byOverallDescending)[0];
  if (top) summary.topPlayer = top;
  return summary;
}

/** Squad size and average rating per Brazilian club present in the FIFA file. */
export function brazilianClubSummaries(graph: SoccerGraph): ClubSquadSummary[] {
  const byClub = new Map<string, Player[]>();
  for (const player of graph.players) {
    if (!player.clubTeamId) continue;
    pushInto(byClub, player.clubTeamId, player);
  }

  return [...byClub.entries()]
    .map(([teamId, players]) => ({
      ...summariseSquad(graph.teams.get(teamId)?.name ?? teamId, players),
      teamId,
    }))
    .sort((a, b) => b.averageOverall - a.averageOverall);
}
